"""
Pre-review structural validator for LLM-generated annotation JSONs.

Attaches `_validation = {passed: bool, issues: [str]}` to each Criterion and
each Relation. No LLM calls — purely structural checks.

Detection patterns (frequency-justified across 4 reference trials
KEYNOTE-671 / ALEX / PACIFIC / KEYNOTE-001):

Relation-level:
  R1  subtype_mismatch              relation_type ↔ target_subtype 부정합
  R2  span_not_in_text              target_text_span ⊄ criterion.text
                                    Multi-tier check: strict → normalized →
                                    token recall ≥ 0.8. Tolerates legitimate
                                    paraphrase from composite splits.
  R3  temporal_props_missing        HAS_TEMPORAL 필수 키 (operator/value/unit/anchor) 누락
  R4  value_props_missing           HAS_VALUE 필수 키 (operator/value) 누락

Criterion-level:
  C1  orphan_parent_role            parent_role set but no IS_PART_OF children
  C2  nested_exception_no_carveout  nested_exception_parent without any
                                    INCLUDES_EXCEPTION relation on its children
  C3  duplicate_entry               criterion_id appears more than once in the
                                    same trial (pipeline emit duplication)

Replaces v0 score/auto_accept/review_tier output (INCEpTION-specific).
The new flat format ({passed, issues}) ports directly to Neo4j edge/node
properties via 07_neo4j_ingest.py.

Usage:
  python pipeline/06_validate_annotation.py
  python pipeline/06_validate_annotation.py --trial NCT03425643
  python pipeline/06_validate_annotation.py --input pipeline/output
"""
from __future__ import annotations
import argparse
import json
import logging
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("06_validate")


# ── Rule tables ────────────────────────────────────────────────────────

# Per relation_type, the set of target_subtype values that are valid.
# Anything outside the set is flagged as subtype_mismatch.
RELATION_SUBTYPE_MAP: dict[str, set[str]] = {
    "REQUIRES_BIOMARKER":     {"Biomarker"},
    "REQUIRES_CONDITION":     {"Condition", "Stage"},
    "EXCLUDES_CONDITION":     {"Condition", "Stage"},
    "REQUIRES_TREATMENT":     {"Drug"},
    "EXCLUDES_TREATMENT":     {"Drug"},
    "EXCLUDES_COMEDICATION":  {"Drug"},
    "REQUIRES_PROCEDURE":     {"Procedure"},
    "EXCLUDES_PROCEDURE":     {"Procedure"},
    "REQUIRES_STATUS":        {"Observation", "Condition"},
    "EXCLUDES_STATUS":        {"Observation", "Condition"},
    "INCLUDES_EXCEPTION":     {"Condition", "Drug", "Procedure", "Observation", "Stage"},
    "HAS_VALUE":              {"Observation", "Condition"},
    "HAS_TEMPORAL":           {"Drug", "Condition", "Procedure", "Observation"},
}

TEMPORAL_REQUIRED = ("operator", "value", "unit", "anchor")
VALUE_REQUIRED = ("operator", "value")

# ── Span containment helpers (R2 multi-tier check) ────────────────────

# Chars to DELETE (concat surrounding text): backslashes from markdown escapes,
# sentence punctuation that the LLM commonly omits, quote marks, and
# comparison operators (frequently corrupted in extraction — `≥` becomes
# `\x02`, `\x1e`, `\x7f` etc. — so compare semantic tokens only).
_SPAN_DELETE_RE = re.compile(r"""[\\,.;:!?'"≥≤><=×]""")
# Chars to SPACIFY (treat as separator): control chars and brackets/slashes.
_SPAN_SPACIFY_RE = re.compile(r"[\x00-\x1f\x7f()/\-]")
_WHITESPACE_RE = re.compile(r"\s+")
_SPAN_RECALL_THRESHOLD = 0.8  # span tokens ≥80% covered by text tokens


def _normalize_for_span(s: str) -> str:
    """NFKC + lowercase, drop sentence punctuation + escapes, spacify
    brackets/slashes, collapse whitespace. NFKC unifies compatibility
    forms (e.g. µ U+00B5 ↔ μ U+03BC, fullwidth digits)."""
    s = unicodedata.normalize("NFKC", s).lower()
    s = _SPAN_DELETE_RE.sub("", s)
    s = _SPAN_SPACIFY_RE.sub(" ", s)
    return _WHITESPACE_RE.sub(" ", s).strip()


def _span_covered_by_text(span: str, text: str) -> bool:
    """
    Three-tier check (return True = pass):
      tier 1: strict substring (cheap, exact extraction)
      tier 2: normalized substring (punctuation/case tolerance)
      tier 3: token recall — span tokens covered by text tokens
              ≥80% means it's a paraphrase reconstruction, not a hallucination
    """
    if not span or not text:
        return True

    if span in text:
        return True

    ns, nt = _normalize_for_span(span), _normalize_for_span(text)
    if ns in nt:
        return True

    sp_tokens = set(ns.split())
    if not sp_tokens:
        return True
    tx_tokens = set(nt.split())
    recall = len(sp_tokens & tx_tokens) / len(sp_tokens)
    return recall >= _SPAN_RECALL_THRESHOLD


# ── Per-relation checks ───────────────────────────────────────────────

def validate_relation(criterion: dict, relation: dict) -> list[str]:
    issues: list[str] = []
    rt = relation.get("relation_type") or ""
    subtype = relation.get("target_subtype")
    span = relation.get("target_text_span") or ""
    text = criterion.get("text") or ""
    props = relation.get("properties") or {}

    # R1: subtype mismatch
    allowed = RELATION_SUBTYPE_MAP.get(rt)
    if allowed is not None and subtype and subtype not in allowed:
        issues.append(f"subtype_mismatch:{rt}->{subtype}")

    # R2: span not covered by criterion text — multi-tier (strict/normalized/recall)
    if span and text and not _span_covered_by_text(span, text):
        issues.append("span_not_in_text")

    # R3: HAS_TEMPORAL required props
    if rt == "HAS_TEMPORAL":
        missing = [k for k in TEMPORAL_REQUIRED if props.get(k) in (None, "")]
        if missing:
            issues.append(f"temporal_props_missing:{','.join(missing)}")

    # R4: HAS_VALUE required props
    if rt == "HAS_VALUE":
        missing = [k for k in VALUE_REQUIRED if props.get(k) in (None, "")]
        if missing:
            issues.append(f"value_props_missing:{','.join(missing)}")

    return issues


# ── Per-criterion checks ──────────────────────────────────────────────

def validate_criterion(criterion: dict, children: list[dict]) -> list[str]:
    """`children` = sibling criteria whose parent_criterion_id == this.criterion_id."""
    issues: list[str] = []
    pr = criterion.get("parent_role")

    # C1: parent_role set but no IS_PART_OF children — applies only to splits
    # that decompose into child_id-suffixed sub-criteria. nested_exception_parent
    # by design IS the carve-out criterion itself (single record, no children);
    # missing carve-out is detected by C2 instead.
    if pr in ("composite_split", "macro_aggregate") and not children:
        issues.append(f"orphan_parent_role:{pr}")

    # C2: nested_exception_parent without an INCLUDES_EXCEPTION carve-out.
    # Carve-out can live on the parent itself (orchestrator default placement)
    # or on its IS_PART_OF children (spec-fidelity placement). Accept either.
    if pr == "nested_exception_parent":
        self_has = any(
            r.get("relation_type") == "INCLUDES_EXCEPTION"
            for r in (criterion.get("relations") or [])
        )
        children_have = any(
            any(r.get("relation_type") == "INCLUDES_EXCEPTION"
                for r in (child.get("relations") or []))
            for child in children
        )
        if not (self_has or children_have):
            issues.append("nested_exception_no_carveout")

    return issues


# ── File processor ────────────────────────────────────────────────────

def _issue_kind(issue: str) -> str:
    """Drop parameter suffix for summary aggregation."""
    return issue.split(":", 1)[0]


def process_file(json_path: Path) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    criteria = data.get("criteria") or []
    if not criteria:
        return {"trial_id": data.get("trial_id", "?"), "skipped": True}

    parent_to_children: dict[str, list[dict]] = {}
    for c in criteria:
        pid = c.get("parent_criterion_id")
        if pid:
            parent_to_children.setdefault(pid, []).append(c)

    # C3: detect duplicate criterion_id within the same trial
    id_counts = Counter(c["criterion_id"] for c in criteria)
    duplicate_ids = {cid for cid, n in id_counts.items() if n > 1}

    counts = Counter()
    n_crit_fail = 0
    n_rel_fail = 0
    n_rel_total = 0

    for c in criteria:
        # Drop legacy fields from previous validator versions
        c.pop("review_tier", None)
        c.pop("_validation", None)

        children = parent_to_children.get(c["criterion_id"], [])
        c_issues = validate_criterion(c, children)
        if c["criterion_id"] in duplicate_ids:
            c_issues.append("duplicate_entry")
        c["_validation"] = {"passed": not c_issues, "issues": c_issues}
        if c_issues:
            n_crit_fail += 1
            for i in c_issues:
                counts[_issue_kind(i)] += 1

        for r in c.get("relations") or []:
            r.pop("_validation", None)
            r_issues = validate_relation(c, r)
            r["_validation"] = {"passed": not r_issues, "issues": r_issues}
            n_rel_total += 1
            if r_issues:
                n_rel_fail += 1
                for i in r_issues:
                    counts[_issue_kind(i)] += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "trial_id": data["trial_id"],
        "total_criteria": len(criteria),
        "unique_criterion_ids": len(id_counts),
        "duplicate_ids": sorted(duplicate_ids),
        "total_relations": n_rel_total,
        "criteria_failed": n_crit_fail,
        "relations_failed": n_rel_fail,
        "counts": dict(counts),
    }


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Attach _validation metadata to annotation JSONs."
    )
    parser.add_argument(
        "--input", "-i", type=Path,
        default=Path(__file__).parent / "output",
    )
    parser.add_argument("--trial", type=str, default=None)
    args = parser.parse_args()

    json_files = sorted(args.input.glob("*_annotation.json"))
    json_files = [f for f in json_files if "_backup" not in f.name]
    if args.trial:
        json_files = [f for f in json_files if args.trial in f.name]
    if not json_files:
        print(f"No annotation JSONs in {args.input}", file=sys.stderr)
        sys.exit(1)

    grand = Counter()
    g_crit = g_rel = g_crit_f = g_rel_f = 0

    for jf in json_files:
        result = process_file(jf)
        if result.get("skipped"):
            logger.info("  skip %s: no criteria", result["trial_id"])
            continue
        grand.update(result["counts"])
        g_crit += result["total_criteria"]
        g_rel += result["total_relations"]
        g_crit_f += result["criteria_failed"]
        g_rel_f += result["relations_failed"]
        kinds = ", ".join(f"{k}={v}" for k, v in result["counts"].items()) or "clean"
        dup_note = (
            f"  ⚠ {len(result['duplicate_ids'])} dup id(s): {result['duplicate_ids']}"
            if result["duplicate_ids"] else ""
        )
        logger.info(
            "  ✓ %s  crit %d (unique %d, fail %d)  rel %d (fail %d)  [%s]%s",
            result["trial_id"],
            result["total_criteria"], result["unique_criterion_ids"],
            result["criteria_failed"],
            result["total_relations"], result["relations_failed"],
            kinds, dup_note,
        )

    print("\n" + "═" * 70)
    print(f"VALIDATION SUMMARY ({len(json_files)} trial files)")
    print("═" * 70)
    print(f"  Criteria  : {g_crit_f}/{g_crit} failed")
    print(f"  Relations : {g_rel_f}/{g_rel} failed")
    if grand:
        print("  Issue breakdown:")
        for k, n in sorted(grand.items(), key=lambda kv: -kv[1]):
            print(f"    {k:35} {n}")
    else:
        print("  No issues detected.")


if __name__ == "__main__":
    main()
