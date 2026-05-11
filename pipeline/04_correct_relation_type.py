"""
Auto-correct relation_type when target_subtype unambiguously determines it.

Background
----------
30-trial validator surfaced 5 systematic subtype_mismatch patterns:
  A  REQUIRES_STATUS / EXCLUDES_STATUS  → Stage      (26 cases)
  B  HAS_VALUE / HAS_TEMPORAL           → LabTest    (handled by 05_rename)
  C  REQUIRES_TREATMENT / EXCLUDES_TREATMENT → Procedure  (10 cases)
  D  EXCLUDES_STATUS → Biomarker         ( 3 cases — not handled here)
  E  REQUIRES_STATUS → Procedure         ( 1 case)

Patterns A, C, E are deterministic — the target_subtype uniquely picks the
correct relation_type. Apply mapping in-place to annotation JSONs.

Pattern D is omitted: converting EXCLUDES_STATUS → REQUIRES_BIOMARKER
requires adding a `status: negative` property and changes semantics.
Surface for manual review instead.

Usage:
  python pipeline/04_correct_relation_type.py --dry-run
  python pipeline/04_correct_relation_type.py
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("correct_relation")


# (current_relation_type, target_subtype) → corrected_relation_type
RELATION_TYPE_CORRECTIONS: dict[tuple[str, str], str] = {
    # Pattern A: Stage belongs to CONDITION axis, not STATUS
    ("REQUIRES_STATUS", "Stage"): "REQUIRES_CONDITION",
    ("EXCLUDES_STATUS", "Stage"): "EXCLUDES_CONDITION",
    # Pattern C: Procedure target → PROCEDURE relation
    ("REQUIRES_TREATMENT", "Procedure"): "REQUIRES_PROCEDURE",
    ("EXCLUDES_TREATMENT", "Procedure"): "EXCLUDES_PROCEDURE",
    # Pattern E
    ("REQUIRES_STATUS", "Procedure"): "REQUIRES_PROCEDURE",
}


def process_file(json_path: Path, dry_run: bool = False) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    criteria = data.get("criteria") or []
    if not criteria:
        return {"trial_id": data.get("trial_id", "?"), "changes": 0}

    counts: Counter = Counter()
    changes = 0

    for c in criteria:
        for r in c.get("relations") or []:
            rt = r.get("relation_type", "")
            subtype = r.get("target_subtype", "")
            new_rt = RELATION_TYPE_CORRECTIONS.get((rt, subtype))
            if new_rt is None:
                continue
            r["relation_type"] = new_rt
            counts[f"{rt}->{new_rt}"] += 1
            changes += 1

    if not dry_run and changes > 0:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "trial_id": data["trial_id"],
        "changes": changes,
        "by_mapping": dict(counts),
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

    grand_total = 0
    grand_map: Counter = Counter()
    affected = 0
    for jf in json_files:
        r = process_file(jf, dry_run=args.dry_run)
        if r["changes"] == 0:
            continue
        affected += 1
        grand_total += r["changes"]
        grand_map.update(r["by_mapping"])
        logger.info("  %s %s  changes=%d  %s",
                    "DRY" if args.dry_run else "✓ ",
                    r["trial_id"], r["changes"], r["by_mapping"])

    print("\n" + "═" * 70)
    print(f"CORRECTION SUMMARY ({len(json_files)} files)")
    print("═" * 70)
    print(f"  Trials affected      : {affected}/{len(json_files)}")
    print(f"  Total corrections    : {grand_total}")
    print(f"  By mapping:")
    for k, n in sorted(grand_map.items(), key=lambda kv: -kv[1]):
        print(f"    {k:50} {n}")
    if args.dry_run:
        print("  (dry-run — no files modified)")


if __name__ == "__main__":
    main()
