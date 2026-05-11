"""
Selective LLM re-extraction for HAS_VALUE / HAS_TEMPORAL relations whose
properties are missing after the orchestrator fix.

Background
----------
Pre-fix orchestrator skipped Prompt 4 fallback when regex returned empty
results, leaving 114 relations with empty properties. Post-hoc regex
(`03_recover_has_value.py`) recovered 58. The remaining 114 (68 temporal +
46 value) need LLM interpretation — natural-language operators ("at least"),
implicit ULN values, multi-word units, etc. that regex can't parse.

This script calls Prompt 4 ONLY on criteria with such failures. One LLM
call per affected criterion (not per relation) since Prompt 4 takes
criterion-level input.

Cost estimate
-------------
At gpt-4.1-mini pricing: ~80k tokens total for ~80 calls = <$0.10 USD.

Usage
-----
  python pipeline/05_reextract_constraints.py --dry-run    # report scope
  python pipeline/05_reextract_constraints.py              # apply
  python pipeline/05_reextract_constraints.py --trial NCT01168973
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# Allow `python pipeline/05_*.py` invocation (numeric prefix blocks `-m`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load both env locations: project root for Neo4j, pipeline/.env for LLM keys.
from dotenv import load_dotenv  # noqa: E402

_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE.parent / ".env")
load_dotenv(_HERE / ".env", override=False)

from pipeline.llm_client import call_llm  # noqa: E402
from pipeline.regex_extractor import extract_constraints  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("reextract")


VALUE_REQUIRED = ("operator", "value")
TEMPORAL_REQUIRED = ("operator", "value", "unit", "anchor")


def _is_missing(rel: dict, rt: str) -> bool:
    """True if relation has missing required keys for its type."""
    props = rel.get("properties") or {}
    keys = VALUE_REQUIRED if rt == "HAS_VALUE" else TEMPORAL_REQUIRED
    return any(props.get(k) in (None, "") for k in keys)


def _strip_prefix_underscores(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def process_criterion(crit: dict, dry_run: bool = False) -> dict:
    """Process a single criterion. Returns counts."""
    text = crit.get("text") or ""
    relations = crit.get("relations") or []

    empty_value = [r for r in relations if r.get("relation_type") == "HAS_VALUE" and _is_missing(r, "HAS_VALUE")]
    empty_temporal = [r for r in relations if r.get("relation_type") == "HAS_TEMPORAL" and _is_missing(r, "HAS_TEMPORAL")]

    if not (empty_value or empty_temporal):
        return {"need_llm": False}

    # Provide regex output as Prompt 4 context (may be empty)
    rx = extract_constraints(text)
    regex_payload = (
        json.dumps({"has_value": rx.has_value, "has_temporal": rx.has_temporal})
        if (rx.has_value or rx.has_temporal) else "null"
    )

    counts = {"need_llm": True, "filled_value": 0, "filled_temporal": 0,
              "still_empty": 0, "llm_calls": 0}

    if dry_run:
        return counts

    try:
        p4 = call_llm("prompt_4", {
            "criterion_text": text,
            "regex_output_or_null": regex_payload,
        })
        counts["llm_calls"] = 1
    except Exception as e:
        logger.warning("  prompt_4 failed for %s: %s", crit.get("criterion_id"), e)
        counts["still_empty"] = len(empty_value) + len(empty_temporal)
        return counts

    hv_list = p4.get("has_value_constraints") or []
    ht_list = p4.get("has_temporal_constraints") or []

    # Fill in order — LLM cannot reliably pair its output to specific
    # relation IDs, so we assume positional correspondence.
    for i, rel in enumerate(empty_value):
        if i < len(hv_list):
            rel["properties"] = _strip_prefix_underscores(hv_list[i])
            counts["filled_value"] += 1
        else:
            counts["still_empty"] += 1

    for i, rel in enumerate(empty_temporal):
        if i < len(ht_list):
            rel["properties"] = _strip_prefix_underscores(ht_list[i])
            counts["filled_temporal"] += 1
        else:
            counts["still_empty"] += 1

    return counts


def process_file(json_path: Path, dry_run: bool = False) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    criteria = data.get("criteria") or []
    agg = Counter()
    for c in criteria:
        result = process_criterion(c, dry_run=dry_run)
        for k, v in result.items():
            if isinstance(v, bool):
                if v: agg[k] += 1
            else:
                agg[k] += v

    if not dry_run and agg["filled_value"] + agg["filled_temporal"] > 0:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return {"trial_id": data["trial_id"], **dict(agg)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=Path,
                        default=Path(__file__).parent / "output")
    parser.add_argument("--trial", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    json_files = sorted(args.input.glob("*_annotation.json"))
    json_files = [f for f in json_files if "_backup" not in f.name]
    if args.trial:
        json_files = [f for f in json_files if args.trial in f.name]
    if not json_files:
        print(f"No annotation JSONs in {args.input}", file=sys.stderr)
        sys.exit(1)

    grand = Counter()
    for jf in json_files:
        r = process_file(jf, dry_run=args.dry_run)
        if r.get("need_llm", 0) == 0:
            continue
        grand["llm_calls"] += r.get("llm_calls", 0)
        grand["filled_value"] += r.get("filled_value", 0)
        grand["filled_temporal"] += r.get("filled_temporal", 0)
        grand["still_empty"] += r.get("still_empty", 0)
        grand["criteria_processed"] += r.get("need_llm", 0)
        logger.info(
            "  %s %s  need_llm=%d  llm_calls=%d  filled(V/T)=%d/%d  still_empty=%d",
            "DRY" if args.dry_run else "✓ ",
            r["trial_id"], r.get("need_llm", 0),
            r.get("llm_calls", 0), r.get("filled_value", 0),
            r.get("filled_temporal", 0), r.get("still_empty", 0),
        )

    print("\n" + "═" * 70)
    print(f"REEXTRACTION SUMMARY ({len(json_files)} files)")
    print("═" * 70)
    print(f"  Criteria needing LLM : {grand['criteria_processed']}")
    print(f"  LLM calls made       : {grand['llm_calls']}")
    print(f"  Filled HAS_VALUE     : {grand['filled_value']}")
    print(f"  Filled HAS_TEMPORAL  : {grand['filled_temporal']}")
    print(f"  Still empty          : {grand['still_empty']}")
    if args.dry_run:
        print("  (dry-run — no LLM calls, no files modified)")


if __name__ == "__main__":
    main()
