"""
Stage A — ClinicalTrials.gov API + AACT → Pipeline Input JSON
==============================================================
위치: pipeline/01_criteria_extraction.py

ClinicalTrials.gov API에서 eligibility criteria 원문을 가져오고,
AACT에서 trial metadata (phase, conditions, cohorts)를 보충합니다.

ClinicalTrials.gov API 장점:
  - 줄바꿈(\\n)과 bullet 구조가 보존됨
  - AACT의 ~* flat 변환 문제 없음
  - sub-bullet 들여쓰기가 유지되어 macro_aggregate 구조 보존

입력:
  - ClinicalTrials.gov API (인터넷 필요)
  - data/external/aact/ (trial metadata 보충용, optional)
  - pipeline/nct_ids.txt (30개 선정 프로토콜)

출력:
  - pipeline/output/input_trials.json

사용법 (프로젝트 루트에서):
  python -m pipeline.01_criteria_extraction

  # AACT 없이 API만 사용
  python -m pipeline.01_criteria_extraction --no-aact

  # 단일 trial 테스트
  python -m pipeline.01_criteria_extraction --nct NCT03425643
"""
from __future__ import annotations
import csv
import json
import logging
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stage_a_api")

CT_GOV_API = "https://clinicaltrials.gov/api/v2/studies"


# ═══════════════════════════════════════════════════════════════════════
# 1. ClinicalTrials.gov API
# ═══════════════════════════════════════════════════════════════════════

def fetch_study(nct_id: str, max_retries: int = 3) -> dict | None:
    """Fetch a single study from ClinicalTrials.gov API v2."""
    url = (
        f"{CT_GOV_API}/{nct_id}"
        f"?fields=EligibilityModule|IdentificationModule|DesignModule"
        f"|ArmsInterventionsModule|ConditionsModule"
    )

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited for {nct_id}, waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"HTTP {e.code} for {nct_id}: {e.reason}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {nct_id}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return None
    return None


# ═══════════════════════════════════════════════════════════════════════
# 2. Eligibility Text Parser (ClinicalTrials.gov format)
# ═══════════════════════════════════════════════════════════════════════

def parse_eligibility_text(raw_criteria: str, nct_id: str) -> dict:
    """
    Parse ClinicalTrials.gov eligibility criteria text.

    Format is well-structured:
      - "Inclusion Criteria:\\n\\n* criterion 1\\n* criterion 2\\n\\nExclusion Criteria:\\n\\n* ..."
      - OR numbered: "1. criterion 1\\n2. criterion 2\\n..."
      - Sub-bullets preserved as indented lines within a criterion
    """
    if not raw_criteria or not raw_criteria.strip():
        return {"inclusion": [], "exclusion": [], "parse_method": "empty"}

    text = raw_criteria.strip()

    # Split into inclusion / exclusion blocks
    inc_text, exc_text = _split_inc_exc(text)

    # Parse each block
    inclusion = _parse_criteria_block(inc_text, "inclusion", nct_id)
    exclusion = _parse_criteria_block(exc_text, "exclusion", nct_id)

    parse_method = "ctgov_api"
    if not inclusion and not exclusion:
        inclusion = _parse_criteria_block(text, "inclusion", nct_id)
        parse_method = "ctgov_api_unsplit"

    return {
        "inclusion": inclusion,
        "exclusion": exclusion,
        "parse_method": parse_method,
    }


def _split_inc_exc(text: str) -> tuple[str, str]:
    """Split criteria text into inclusion and exclusion blocks."""
    exc_pattern = re.compile(r"\n\s*Exclusion\s+Criteria\s*:?\s*\n", re.IGNORECASE)
    inc_pattern = re.compile(r"\n?\s*Inclusion\s+Criteria\s*:?\s*\n", re.IGNORECASE)

    inc_match = inc_pattern.search(text)
    exc_match = exc_pattern.search(text)

    if inc_match and exc_match:
        inc_text = text[inc_match.end():exc_match.start()].strip()
        exc_text = text[exc_match.end():].strip()
        return inc_text, exc_text

    if inc_match and not exc_match:
        return text[inc_match.end():].strip(), ""

    if exc_match and not inc_match:
        return text[:exc_match.start()].strip(), text[exc_match.end():].strip()

    return text, ""


def _parse_criteria_block(
    block_text: str,
    criterion_type: str,
    nct_id: str,
) -> list[dict]:
    """
    Parse a criteria block into individual criterion entries.

    Handles two formats:
      1. Bullet: "* criterion text" (most common)
      2. Numbered: "1. criterion text"

    Multi-line criteria (sub-bullets, continuation lines) are kept together
    as a single criterion — this preserves macro_aggregate structure.
    """
    if not block_text.strip():
        return []

    prefix = "I" if criterion_type == "inclusion" else "E"
    lines = block_text.split("\n")

    # Detect format
    bullet_lines = [l for l in lines if re.match(r"\s*\*\s+", l)]
    numbered_lines = [l for l in lines if re.match(r"\s*\d{1,2}\.\s+", l)]

    if len(bullet_lines) >= 2:
        return _parse_bullet_format(lines, prefix, criterion_type, nct_id)
    elif len(numbered_lines) >= 2:
        return _parse_numbered_format(lines, prefix, criterion_type, nct_id)
    else:
        return _parse_line_format(lines, prefix, criterion_type, nct_id)


def _parse_bullet_format(
    lines: list[str],
    prefix: str,
    criterion_type: str,
    nct_id: str,
) -> list[dict]:
    """
    Parse bullet-formatted criteria (* criterion).
    Continuation lines (not starting with *) are appended to the previous criterion.
    This preserves sub-bullet structure within a criterion.
    """
    criteria: list[dict] = []
    current_text = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r"\*\s+", stripped):
            if current_text:
                _append_criterion(criteria, current_text, prefix, criterion_type, nct_id)
            current_text = re.sub(r"^\*\s+", "", stripped)
        else:
            if current_text:
                current_text += " " + stripped
            else:
                current_text = stripped

    if current_text:
        _append_criterion(criteria, current_text, prefix, criterion_type, nct_id)

    return criteria


def _parse_numbered_format(
    lines: list[str],
    prefix: str,
    criterion_type: str,
    nct_id: str,
) -> list[dict]:
    """
    Parse numbered criteria (1. criterion).
    Continuation lines are appended to the previous criterion.
    """
    criteria: list[dict] = []
    current_text = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r"\d{1,2}\.\s+", stripped):
            if current_text:
                _append_criterion(criteria, current_text, prefix, criterion_type, nct_id)
            current_text = re.sub(r"^\d{1,2}\.\s+", "", stripped)
        else:
            if current_text:
                current_text += " " + stripped
            else:
                current_text = stripped

    if current_text:
        _append_criterion(criteria, current_text, prefix, criterion_type, nct_id)

    return criteria


def _parse_line_format(
    lines: list[str],
    prefix: str,
    criterion_type: str,
    nct_id: str,
) -> list[dict]:
    """Fallback: each non-empty line is a criterion."""
    criteria: list[dict] = []
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) >= 10:
            _append_criterion(criteria, stripped, prefix, criterion_type, nct_id)
    return criteria


def _append_criterion(
    criteria: list[dict],
    text: str,
    prefix: str,
    criterion_type: str,
    nct_id: str,
) -> None:
    """Clean and append a criterion to the list."""
    text = _clean_criterion(text)
    if _is_valid_criterion(text):
        criteria.append({
            "id": f"{nct_id}_{prefix}{len(criteria) + 1}",
            "type": criterion_type,
            "text": text,
            "protocol_ref": f"{criterion_type.title()} #{len(criteria) + 1}",
        })


def _clean_criterion(text: str) -> str:
    """Clean up individual criterion text."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\-•\*]+\s*", "", text)
    text = re.sub(r"^\d{1,2}[.)]\s*", "", text)
    return text.strip()


def _is_valid_criterion(text: str) -> bool:
    """Check if text is a valid criterion (not header, not too short)."""
    if len(text) < 10:
        return False
    skip_patterns = [
        r"^(?:Inclusion|Exclusion)\s+Criteria\s*:?\s*$",
        r"^Key\s+(?:Inclusion|Exclusion)",
    ]
    for pattern in skip_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            if len(text) < 80:
                return False
    return True


# ═══════════════════════════════════════════════════════════════════════
# 3. AACT Metadata Reader (supplementary)
# ═══════════════════════════════════════════════════════════════════════

def read_aact_table(filepath: Path, nct_filter: set[str]) -> list[dict]:
    """Read a pipe-delimited AACT txt file."""
    rows = []
    if not filepath.exists():
        return rows
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            nct = row.get("nct_id", "").strip()
            if nct in nct_filter:
                rows.append(row)
    return rows


def load_aact_metadata(aact_dir: Path, nct_ids: set[str]) -> dict:
    """Load AACT metadata tables (studies, conditions, design_groups)."""
    meta: dict[str, Any] = {"studies": {}, "conditions": {}, "design_groups": {}}

    for row in read_aact_table(aact_dir / "studies.txt", nct_ids):
        nct = row.get("nct_id", "").strip()
        if nct:
            meta["studies"][nct] = row

    for row in read_aact_table(aact_dir / "conditions.txt", nct_ids):
        nct = row.get("nct_id", "").strip()
        meta["conditions"].setdefault(nct, []).append(row)

    for row in read_aact_table(aact_dir / "design_groups.txt", nct_ids):
        nct = row.get("nct_id", "").strip()
        meta["design_groups"].setdefault(nct, []).append(row)

    return meta


# ═══════════════════════════════════════════════════════════════════════
# 4. Trial Data Assembly
# ═══════════════════════════════════════════════════════════════════════

def build_trial_from_api(
    nct_id: str,
    api_data: dict,
    aact_meta: dict | None = None,
) -> dict | None:
    """Build trial data from API response + optional AACT metadata."""
    proto = api_data.get("protocolSection", {})
    elig = proto.get("eligibilityModule", {})
    ident = proto.get("identificationModule", {})
    design = proto.get("designModule", {})
    arms_mod = proto.get("armsInterventionsModule", {})
    cond_mod = proto.get("conditionsModule", {})

    raw_criteria = elig.get("eligibilityCriteria", "")
    if not raw_criteria:
        logger.warning(f"No eligibility criteria for {nct_id}")
        return None

    # Parse criteria
    parsed = parse_eligibility_text(raw_criteria, nct_id)
    all_criteria = parsed["inclusion"] + parsed["exclusion"]

    if not all_criteria:
        logger.warning(f"No criteria extracted for {nct_id}")
        return None

    # Build trial record
    trial: dict[str, Any] = {
        "trial_id": nct_id,
        "criteria": all_criteria,
    }

    # API metadata
    acronym = ident.get("acronym", "").strip()
    if acronym:
        trial["trial_acronym"] = acronym

    title = ident.get("briefTitle", "").strip()
    if title:
        trial["brief_title"] = title

    phases = design.get("phases", [])
    if phases:
        trial["trial_phase"] = "/".join(phases)

    conditions = cond_mod.get("conditions", [])
    if conditions:
        trial["conditions"] = conditions
        trial["disease_domain"] = _infer_domain(conditions)

    arms = arms_mod.get("armGroups", [])
    if len(arms) >= 2:
        cohorts = []
        for arm in arms:
            cohorts.append({
                "id": arm.get("label", ""),
                "description": arm.get("description", ""),
                "group_type": arm.get("type", ""),
            })
        trial["cohorts"] = cohorts

    # Supplement with AACT metadata if available
    if aact_meta:
        study_row = aact_meta.get("studies", {}).get(nct_id)
        if study_row and not trial.get("trial_phase"):
            trial["trial_phase"] = study_row.get("phase", "")

        aact_conditions = aact_meta.get("conditions", {}).get(nct_id, [])
        if aact_conditions and not trial.get("conditions"):
            cond_names = [c.get("name", "").strip() for c in aact_conditions if c.get("name")]
            trial["conditions"] = cond_names
            trial["disease_domain"] = _infer_domain(cond_names)

        aact_groups = aact_meta.get("design_groups", {}).get(nct_id, [])
        if aact_groups and not trial.get("cohorts") and len(aact_groups) >= 2:
            cohorts = []
            for dg in aact_groups:
                dg_title = dg.get("title", "").strip()
                if dg_title:
                    cohorts.append({
                        "id": dg_title,
                        "description": dg.get("description", "").strip(),
                        "group_type": dg.get("group_type", "").strip(),
                    })
            if cohorts:
                trial["cohorts"] = cohorts

    # Extraction metadata
    trial["_extraction_metadata"] = {
        "source": "ClinicalTrials.gov API v2",
        "parse_method": parsed["parse_method"],
        "inclusion_count": len(parsed["inclusion"]),
        "exclusion_count": len(parsed["exclusion"]),
        "total_criteria": len(all_criteria),
        "gender": elig.get("sex", ""),
        "minimum_age": elig.get("minimumAge", ""),
        "maximum_age": elig.get("maximumAge", ""),
    }

    logger.info(
        f"  ✓ {nct_id}: {len(parsed['inclusion'])}I + {len(parsed['exclusion'])}E "
        f"= {len(all_criteria)} criteria (method: {parsed['parse_method']})"
    )
    return trial


def _infer_domain(conditions: list[str]) -> str:
    """Infer disease domain from condition names."""
    combined = " ".join(conditions).lower()
    domain_map = [
        ("nsclc|non-small cell lung|non small cell lung", "NSCLC"),
        ("small cell lung", "SCLC"),
        ("lung", "Lung Cancer"),
        ("pancrea", "Pancreatic Cancer"),
        ("breast", "Breast Cancer"),
        ("melanoma", "Melanoma"),
        ("colorectal|colon|rectal", "Colorectal Cancer"),
        ("renal|kidney", "Renal Cancer"),
        ("bladder|urothelial", "Bladder Cancer"),
        ("head and neck|hnscc", "Head and Neck Cancer"),
        ("mesothelioma", "Mesothelioma"),
        ("lymphoma", "Lymphoma"),
        ("leukemia", "Leukemia"),
        ("glioblastoma|glioma|brain", "Brain Cancer"),
        ("hepatocellular|liver", "Liver Cancer"),
        ("gastric|stomach|esophag", "Gastric/Esophageal Cancer"),
        ("ovarian", "Ovarian Cancer"),
        ("prostate", "Prostate Cancer"),
    ]
    for pattern, domain in domain_map:
        if re.search(pattern, combined):
            return domain
    return "Oncology"


# ═══════════════════════════════════════════════════════════════════════
# 5. Main Pipeline
# ═══════════════════════════════════════════════════════════════════════

def process_trials(
    nct_ids: list[str],
    aact_dir: Path | None = None,
    output_path: Path | None = None,
    api_delay: float = 0.5,
) -> list[dict]:
    """
    Main entry: fetch criteria from ClinicalTrials.gov API,
    supplement with AACT metadata.
    """
    nct_set = set(nct_ids)
    logger.info(f"Processing {len(nct_set)} trials from ClinicalTrials.gov API")

    # Load AACT metadata if available
    aact_meta = None
    if aact_dir and aact_dir.exists():
        logger.info(f"Loading AACT metadata from {aact_dir}")
        aact_meta = load_aact_metadata(aact_dir, nct_set)

    results = []
    missing = []
    total = len(nct_ids)

    for i, nct_id in enumerate(sorted(nct_set), 1):
        logger.info(f"[{i}/{total}] Fetching {nct_id}...")

        api_data = fetch_study(nct_id)
        if not api_data:
            missing.append(nct_id)
            continue

        trial = build_trial_from_api(nct_id, api_data, aact_meta)
        if trial:
            results.append(trial)
        else:
            missing.append(nct_id)

        # Rate limit courtesy
        if i < total:
            time.sleep(api_delay)

    # Summary
    total_criteria = sum(
        t.get("_extraction_metadata", {}).get("total_criteria", 0)
        for t in results
    )
    logger.info(
        f"\n{'═' * 60}\n"
        f"Stage A (ClinicalTrials.gov API) Summary:\n"
        f"  {len(results)}/{len(nct_set)} trials extracted\n"
        f"  {total_criteria} total criteria\n"
        f"  {len(missing)} missing: {missing}\n"
        f"{'═' * 60}"
    )

    # Save
    if output_path and results:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Saved to {output_path}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    import argparse

    _this_dir = Path(__file__).parent
    _project_root = _this_dir.parent
    _default_aact = _project_root / "data" / "external" / "aact"
    _default_nct_list = _this_dir / "nct_ids.txt"
    _default_output = _this_dir / "output" / "input_trials.json"

    parser = argparse.ArgumentParser(
        description="Stage A: Extract eligibility criteria from ClinicalTrials.gov API + AACT metadata"
    )
    parser.add_argument("--aact-dir", type=Path, default=_default_aact,
                        help=f"AACT metadata directory (default: {_default_aact})")
    parser.add_argument("--no-aact", action="store_true",
                        help="Skip AACT metadata, use API only")
    parser.add_argument("--nct", nargs="+", default=None,
                        help="NCT IDs to process")
    parser.add_argument("--nct-list", type=Path, default=_default_nct_list,
                        help=f"File with one NCT ID per line (default: {_default_nct_list})")
    parser.add_argument("--output", "-o", type=Path, default=_default_output,
                        help=f"Output JSON path (default: {_default_output})")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds between API calls (default: 0.5)")

    args = parser.parse_args()

    nct_ids: list[str] = []
    if args.nct:
        # --nct specified: use only these, ignore nct_ids.txt
        nct_ids.extend(args.nct)
    elif args.nct_list and args.nct_list.exists():
        # No --nct: fall back to nct_ids.txt
        lines = args.nct_list.read_text().strip().split("\n")
        nct_ids.extend(line.strip() for line in lines if line.strip().startswith("NCT"))

    if not nct_ids:
        print("Error: provide NCT IDs via --nct or --nct-list")
        sys.exit(1)

    aact_dir = None if args.no_aact else args.aact_dir
    process_trials(nct_ids, aact_dir, args.output, args.delay)


if __name__ == "__main__":
    main()