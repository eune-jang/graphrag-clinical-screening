"""
[ARCHIVED] One-shot cleanup for the orchestrator nested_exception duplicate-emit bug.

상태: ⚠️ ARCHIVED — orchestrator.py:357 소스 버그가 수정됐고 기존 30 trial은
      이 스크립트로 cleanup 완료. 미래 annotation 실행 시 중복 emit이 재발할
      가능성 없음. 향후 외부 구 데이터 import 시 safety net으로 보관.

Background
----------
Pre-fix orchestrator.py L358 emitted a parent stub for nested_exception
criteria even though the criterion's target loop had already produced the
parent record. This caused 110 duplicate criterion entries across 30
trials, all with parent_role=nested_exception_parent.

After the orchestrator fix (L358 now restricted to composite_split /
macro_aggregate), future runs are clean. This script repairs existing
JSON files in pipeline/output/ without re-running the LLM pipeline.

Dedup rule
----------
For each pair of duplicates sharing the same criterion_id:
  1. Merge `relations` lists (deduplicate by (relation_type,
     target_preferred_name, target_text_span))
  2. Keep the first record's other fields (they should be identical
     since prompt 1 ran once per criterion)
  3. Drop the second record

After this script, every trial JSON should have unique criterion_id.

Usage
-----
  python pipeline/_archive_dedup_nested_exception.py                # all trials
  python pipeline/_archive_dedup_nested_exception.py --trial NCT04334759
  python pipeline/_archive_dedup_nested_exception.py --dry-run      # report only
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
logger = logging.getLogger("dedup")


def _rel_key(rel: dict) -> tuple:
    return (
        rel.get("relation_type"),
        rel.get("target_preferred_name"),
        rel.get("target_text_span"),
    )


def dedup_trial(json_path: Path, dry_run: bool = False) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    criteria = data.get("criteria") or []
    if not criteria:
        return {"trial_id": data.get("trial_id", "?"), "skipped": True}

    seen: dict[str, dict] = {}  # criterion_id → kept record
    n_dup = 0
    n_rel_merged = 0
    order: list[str] = []  # preserve original order

    for crit in criteria:
        cid = crit["criterion_id"]
        if cid not in seen:
            seen[cid] = crit
            order.append(cid)
            continue

        # Duplicate found — merge relations into the first occurrence
        n_dup += 1
        keep = seen[cid]
        existing_keys = {_rel_key(r) for r in (keep.get("relations") or [])}
        for r in crit.get("relations") or []:
            if _rel_key(r) not in existing_keys:
                keep.setdefault("relations", []).append(r)
                existing_keys.add(_rel_key(r))
                n_rel_merged += 1

    if n_dup == 0:
        return {
            "trial_id": data["trial_id"],
            "total_before": len(criteria),
            "duplicates": 0,
            "rel_merged": 0,
            "modified": False,
        }

    deduped = [seen[cid] for cid in order]
    data["criteria"] = deduped

    if not dry_run:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "trial_id": data["trial_id"],
        "total_before": len(criteria),
        "total_after": len(deduped),
        "duplicates": n_dup,
        "rel_merged": n_rel_merged,
        "modified": not dry_run,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", "-i", type=Path,
        default=Path(__file__).parent / "output",
    )
    parser.add_argument("--trial", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing")
    args = parser.parse_args()

    json_files = sorted(args.input.glob("*_annotation.json"))
    json_files = [f for f in json_files if "_backup" not in f.name]
    if args.trial:
        json_files = [f for f in json_files if args.trial in f.name]
    if not json_files:
        print(f"No annotation JSONs in {args.input}", file=sys.stderr)
        sys.exit(1)

    grand_dup = 0
    grand_rel = 0
    affected_trials = 0

    for jf in json_files:
        r = dedup_trial(jf, dry_run=args.dry_run)
        if r.get("skipped"):
            continue
        if r["duplicates"] > 0:
            affected_trials += 1
            grand_dup += r["duplicates"]
            grand_rel += r["rel_merged"]
            logger.info(
                "  %s %s: %d→%d criteria  (%d dup, %d relations merged)",
                "DRY" if args.dry_run else "✓ ",
                r["trial_id"],
                r["total_before"],
                r.get("total_after", r["total_before"]),
                r["duplicates"],
                r["rel_merged"],
            )

    print("\n" + "═" * 70)
    print(f"DEDUP SUMMARY ({len(json_files)} trial files)")
    print("═" * 70)
    print(f"  Trials affected   : {affected_trials}/{len(json_files)}")
    print(f"  Duplicate entries : {grand_dup}")
    print(f"  Relations merged  : {grand_rel}")
    if args.dry_run:
        print("  (dry-run — no files modified)")


if __name__ == "__main__":
    main()
