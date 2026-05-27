"""Command-line interface for stage runners.

Usage:
    python -m iaa_pipeline.cli stage1 <input.json> --output-dir <dir> [options]
    python -m iaa_pipeline.cli stage1 --help

Examples:
    # Run Stage 1 on KEYNOTE-671 with caching
    python -m iaa_pipeline.cli stage1 examples/keynote_671_input.json \\
        --output-dir output/ \\
        --cache-dir cache/

    # Run with a specific model
    python -m iaa_pipeline.cli stage1 examples/keynote_671_input.json \\
        --output-dir output/ \\
        --model gpt-4.1-mini
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .stage_runner import run_stage1_splitting, STAGE_RUNNERS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="IAA Pipeline stage runners",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="stage", required=True)

    # ── Stage 1 ────────────────────────────────────────────────────────
    p1 = subparsers.add_parser("stage1", help="Run Stage 1 (splitting)")
    p1.add_argument(
        "input_file",
        type=Path,
        help="Path to Stage 1 input JSON file (Stage1Input schema)",
    )
    p1.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output root directory. File written to {out}/{trial_id}/stage1/llm_output.json",
    )
    p1.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="LLM response cache directory (recommended)",
    )
    p1.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override default model from pipeline.config.MODELS['prompt_1']",
    )
    p1.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )

    # ── Stages 2-5: stubs ───────────────────────────────────────────────
    for stage_num in [2, 3, 4, 5]:
        sp = subparsers.add_parser(f"stage{stage_num}", help=f"Run Stage {stage_num} (not yet implemented)")
        sp.add_argument("--placeholder", help="Stage not yet implemented")

    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.stage == "stage1":
        if not args.input_file.exists():
            print(f"ERROR: Input file not found: {args.input_file}", file=sys.stderr)
            return 1
        try:
            out_path = run_stage1_splitting(
                trial_input=args.input_file,
                output_dir=args.output_dir,
                cache_dir=args.cache_dir,
                model_override=args.model,
            )
            print(f"✓ Output: {out_path}")
            return 0
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 2
    else:
        print(f"Stage {args.stage} not yet implemented.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
