"""
[ARCHIVED] Post-process: Rename lab_value → observation, LabTest → Observation.

상태: ⚠️ ARCHIVED — orchestrator.py:320,330 소스 버그가 수정되어 새 annotation은
      LabTest를 emit하지 않음. 기존 30 trial은 이 스크립트로 cleanup 완료.
      향후 외부 구 데이터 import 시 safety net으로 보관.

LLM 재호출 없이 기존 annotation JSON의 값을 일괄 치환합니다.

사용법:
  python pipeline/_archive_rename_observation.py

  # 단일 trial
  python pipeline/_archive_rename_observation.py --trial NCT03425643

  # 경로 지정
  python pipeline/_archive_rename_observation.py --input pipeline/output
"""
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("_archive_rename_observation")

REPLACEMENTS = {
    "semantic_category": {"lab_value": "observation"},
    "target_subtype": {"LabTest": "Observation"},
}


def process_file(json_path: Path) -> dict:
    """Rename lab_value/LabTest in a single annotation JSON."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("criteria"):
        return {"trial_id": data.get("trial_id", "?"), "changes": 0}

    changes = 0

    for crit in data["criteria"]:
        # semantic_category: lab_value → observation
        if crit.get("semantic_category") == "lab_value":
            crit["semantic_category"] = "observation"
            changes += 1

        for rel in crit.get("relations", []):
            # target_subtype: LabTest → Observation
            if rel.get("target_subtype") == "LabTest":
                rel["target_subtype"] = "Observation"
                changes += 1

    # Write back
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"trial_id": data["trial_id"], "changes": changes}


def main():
    import argparse

    _this_dir = Path(__file__).parent
    _default_input = _this_dir / "output"

    parser = argparse.ArgumentParser(
        description="Rename lab_value → observation, LabTest → Observation"
    )
    parser.add_argument("--input", "-i", type=Path, default=_default_input)
    parser.add_argument("--trial", type=str, default=None)
    args = parser.parse_args()

    json_files = sorted(args.input.glob("*_annotation.json"))
    if args.trial:
        json_files = [f for f in json_files if args.trial in f.name]

    if not json_files:
        print(f"No annotation JSONs found in {args.input}")
        sys.exit(1)

    total_changes = 0
    for json_path in json_files:
        result = process_file(json_path)
        total_changes += result["changes"]
        if result["changes"] > 0:
            logger.info(f"  ✓ {result['trial_id']}: {result['changes']} replacements")
        else:
            logger.info(f"  - {result['trial_id']}: no changes needed")

    logger.info(
        f"\n{'═' * 60}\n"
        f"Rename complete: {total_changes} total replacements across {len(json_files)} files\n"
        f"  lab_value → observation\n"
        f"  LabTest → Observation\n"
        f"\n(legacy: 03_inception_export 스크립트는 더 이상 존재하지 않음)\n"
        f"{'═' * 60}"
    )


if __name__ == "__main__":
    main()
