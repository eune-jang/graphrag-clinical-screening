"""
Stages B-N — 5-Stage LLM Annotation Pipeline
=============================================
위치: pipeline/02_llm_annotation.py

01_criteria_extraction.py의 출력(input_trials.json)을 받아
5-prompt 순차 LLM annotation을 수행합니다.

입력:
  - pipeline/output/input_trials.json (from 01_criteria_extraction.py)

출력:
  - pipeline/output/{NCT_ID}_annotation.json (per trial)
  - pipeline/output/batch_summary.json

사용법 (프로젝트 루트에서):
  python -m pipeline.02_llm_annotation

  # 또는 직접 경로 지정:
  python -m pipeline.02_llm_annotation --input pipeline/output/input_trials.json

사전 준비:
  pip install anthropic
  export ANTHROPIC_API_KEY="sk-ant-..."

파이프라인 단계:
  Prompt 1 (Sonnet 4.5) → Splitting + cohort_scope
  Prompt 2 (Sonnet 4.5) → Category / Relation / Target subtype
  Prompt 3 (Sonnet 4.5) → Preferred name normalization
  Regex I/J + Prompt 4 (Sonnet 4.5) → HAS_VALUE / HAS_TEMPORAL
  Prompt 5 (Opus 4.7*) → alternative_constraint / exception

  *현재 Sonnet 4.5 사용. config.py에서 모델 변경 가능.

변경 이력:
  - v1 (2026-05): 초기 작성
"""
from __future__ import annotations
import json
import logging
import os
import sys
from pathlib import Path

# ── Load .env file (API keys) ─────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and value and key not in os.environ:
                os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("02_llm_annotation")


def main():
    import argparse

    _this_dir = Path(__file__).parent
    _default_input = _this_dir / "output" / "input_trials.json"
    _default_output = _this_dir / "output"

    parser = argparse.ArgumentParser(
        description="Stages B-N: 5-stage LLM annotation pipeline"
    )
    parser.add_argument("--input", "-i", type=Path, default=_default_input,
                        help=f"Input trials JSON (default: {_default_input})")
    parser.add_argument("--output", "-o", type=Path, default=_default_output,
                        help=f"Output directory (default: {_default_output})")
    parser.add_argument("--trial", type=str, default=None,
                        help="Process single trial by NCT ID (for debugging)")
    parser.add_argument("--no-resume", action="store_true",
                        help="Re-process all trials even if output exists")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds to wait between trials (default: 2.0)")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}")
        print(f"  Run 01_criteria_extraction.py first.")
        sys.exit(1)

    # Import pipeline modules (relative imports work via -m execution)
    from .orchestrator import process_batch, process_trial, TrialInput

    # Load input
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    trials = [
        TrialInput(
            trial_id=t["trial_id"],
            trial_acronym=t.get("trial_acronym"),
            disease_domain=t.get("disease_domain"),
            cohorts=t.get("cohorts"),
            criteria=t.get("criteria", []),
        )
        for t in raw
    ]

    # Filter if --trial specified
    if args.trial:
        trials = [t for t in trials if t.trial_id == args.trial]
        if not trials:
            print(f"Error: trial {args.trial} not found in input")
            sys.exit(1)

    logger.info(f"Loaded {len(trials)} trials from {args.input}")

    # Run pipeline
    process_batch(
        trials,
        args.output,
        resume=not args.no_resume,
        inter_trial_delay=args.delay,
    )


if __name__ == "__main__":
    main()