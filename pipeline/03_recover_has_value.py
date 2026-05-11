"""
Post-hoc recovery for HAS_VALUE / HAS_TEMPORAL relations that the pre-fix
orchestrator left with empty properties.

Background
----------
Pre-fix orchestrator (`pipeline/orchestrator.py:268-300`) skipped Prompt 4
fallback when regex returned `is_complete=True` even if it had found zero
matches. This silently dropped 114 HAS_VALUE relations across 30 trials to
empty properties (no operator/value/unit/anchor).

After the orchestrator + regex_extractor fixes:
  - regex_extractor.py now normalizes encoding artifacts (\\>=, \\x1e, etc.)
    and natural-language operators ("at least", "greater than or equal to").
  - orchestrator.py now falls back to Prompt 4 whenever regex returns empty.

This script applies the IMPROVED regex retroactively to existing JSON
target_text_span and criterion text, recovering whatever the new regex can
extract WITHOUT an LLM call. Cases that still fail are tagged for
re-annotation.

Usage:
  python pipeline/03_recover_has_value.py --dry-run
  python pipeline/03_recover_has_value.py            # writes back to JSONs
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# Import the (now improved) extractor. The numeric file prefixes prevent
# `python -m pipeline.03_recover_has_value`, so allow direct script run by
# adding the project root to sys.path and importing as `pipeline.X`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.regex_extractor import extract_constraints  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recover")


REQUIRED_VALUE = ("operator", "value")
REQUIRED_TEMPORAL = ("operator", "value", "unit", "anchor")


def _is_empty(rel: dict, rt: str) -> bool:
    """True if relation has missing required keys for its type."""
    props = rel.get("properties") or {}
    keys = REQUIRED_VALUE if rt == "HAS_VALUE" else REQUIRED_TEMPORAL
    return any(props.get(k) in (None, "") for k in keys)


def _recover_one(rel: dict, criterion_text: str) -> str:
    """
    Attempt to recover properties for one HAS_VALUE/HAS_TEMPORAL relation.
    Returns: "recovered" / "still_empty" / "skipped".
    """
    rt = rel.get("relation_type", "")
    if rt not in ("HAS_VALUE", "HAS_TEMPORAL"):
        return "skipped"

    # Try the relation's own span first (most specific), then fall back to
    # the criterion text (broader context).
    candidates = [rel.get("target_text_span") or "", criterion_text or ""]
    for scope in candidates:
        if not scope:
            continue
        r = extract_constraints(scope)
        extracted = r.has_value if rt == "HAS_VALUE" else r.has_temporal
        if extracted:
            # Strip helper key before persisting
            props = {k: v for k, v in extracted[0].items() if not k.startswith("_")}
            rel["properties"] = props
            return "recovered"

    return "still_empty"


def process_file(json_path: Path, dry_run: bool = False) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    criteria = data.get("criteria") or []
    counts = Counter()
    targeted_rels = 0

    for c in criteria:
        for r in c.get("relations") or []:
            rt = r.get("relation_type", "")
            if rt not in ("HAS_VALUE", "HAS_TEMPORAL"):
                continue
            if not _is_empty(r, rt):
                continue
            targeted_rels += 1
            outcome = _recover_one(r, c.get("text", ""))
            counts[outcome] += 1

    if not dry_run and counts["recovered"] > 0:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "trial_id": data.get("trial_id", "?"),
        "targeted": targeted_rels,
        "recovered": counts["recovered"],
        "still_empty": counts["still_empty"],
    }


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

    g_targeted = g_rec = g_emp = 0
    for jf in json_files:
        r = process_file(jf, dry_run=args.dry_run)
        if r["targeted"] == 0:
            continue
        g_targeted += r["targeted"]
        g_rec += r["recovered"]
        g_emp += r["still_empty"]
        logger.info(
            "  %s %s  targeted=%d  recovered=%d  still_empty=%d",
            "DRY" if args.dry_run else "✓ ",
            r["trial_id"], r["targeted"], r["recovered"], r["still_empty"],
        )

    print("\n" + "═" * 70)
    print(f"RECOVERY SUMMARY ({len(json_files)} files)")
    print("═" * 70)
    print(f"  Targeted (empty HAS_VALUE/HAS_TEMPORAL): {g_targeted}")
    print(f"  Recovered via regex                    : {g_rec}")
    print(f"  Still empty (needs LLM re-annotation)  : {g_emp}")
    if g_targeted:
        rate = g_rec / g_targeted * 100
        print(f"  Recovery rate                          : {rate:.1f}%")
    if args.dry_run:
        print("  (dry-run — no files modified)")


if __name__ == "__main__":
    main()
