"""One-shot converter: production pipeline output → IAA Stage 1 workspace.

Reads:
    pipeline/output/input_trials.json         (30 trials, criteria list)
    pipeline/output/NCT*_annotation.json      (per-trial production output)

Writes (per trial):
    {workspace}/{trial_id}/stage1/input.json        (Stage1Input)
    {workspace}/{trial_id}/stage1/llm_output.json   (Stage1 envelope, source="llm")

The llm_output is extracted directly from the production annotation's existing
parent_role / child_logic / sub-criterion records — no LLM call is made.

This lets the IAA Streamlit UI compare new annotator gold against the
already-paid-for production Prompt 1 output.

Usage:
    python scripts/convert_production_to_iaa.py                       # default workspace
    python scripts/convert_production_to_iaa.py --workspace foo/      # custom workspace
    python scripts/convert_production_to_iaa.py --trial NCT03425643   # one trial only
    python scripts/convert_production_to_iaa.py --dry-run             # preview only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_OUTPUT = PROJECT_ROOT / "pipeline" / "output"
DEFAULT_WORKSPACE = PROJECT_ROOT / "iaa_workspace"
DEFAULT_MODEL_NAME = "production-pipeline-v1.2.1"  # production output isn't keyed by model


# ──────────────────────────────────────────────────────────────────────
# Input conversion (input_trials.json → per-trial Stage1Input)
# ──────────────────────────────────────────────────────────────────────

def convert_trial_input(production_trial: dict) -> dict:
    """Convert one trial entry from input_trials.json to Stage1Input format.

    Field renames:
      criteria[].id  →  criteria[].criterion_id
      cohorts[].id   →  cohorts[].cohort_id  (when present)
    """
    out: dict[str, Any] = {
        "trial_id": production_trial["trial_id"],
        "criteria": [
            {
                "criterion_id": c["id"],
                "type": c["type"],
                "text": c["text"],
                **({"protocol_ref": c["protocol_ref"]} if c.get("protocol_ref") else {}),
            }
            for c in production_trial.get("criteria", [])
        ],
    }
    if production_trial.get("trial_acronym"):
        out["trial_acronym"] = production_trial["trial_acronym"]
    if production_trial.get("disease_domain"):
        out["disease_domain"] = production_trial["disease_domain"]
    cohorts = production_trial.get("cohorts") or []
    if cohorts:
        out["cohorts"] = [
            {
                "cohort_id": c.get("id", c.get("cohort_id", "")),
                **{k: v for k, v in c.items() if k not in ("id", "cohort_id")},
            }
            for c in cohorts
        ]
    return out


# ──────────────────────────────────────────────────────────────────────
# Production annotation → Stage 1 envelope
# ──────────────────────────────────────────────────────────────────────

VALID_DECISIONS = {"composite_split", "macro_aggregate", "nested_exception", "none"}


def extract_stage1_envelope(production_annotation: dict) -> dict:
    """Build a Stage 1 envelope (`source="llm"`) from production annotation.

    Production annotation has top-level criterion records (which may be
    parents) and sub-criterion records (with parent_criterion_id). We
    invert that to Stage 1's parent-centric representation:
      - splitting_decision: from parent's parent_role (default "none")
      - child_logic: from parent
      - sub_criteria: list of {child_id, text_span} from kids
    """
    trial_id = production_annotation["trial_id"]
    criteria = production_annotation.get("criteria", [])

    # Group kids by parent_criterion_id
    kids_by_parent: dict[str, list[dict]] = {}
    for c in criteria:
        pid = c.get("parent_criterion_id")
        if pid:
            kids_by_parent.setdefault(pid, []).append(c)

    records: list[dict] = []
    for c in criteria:
        if c.get("parent_criterion_id"):
            continue  # this is a child; will be folded into its parent's sub_criteria

        crit_id = c["criterion_id"]
        decision = c.get("parent_role") or "none"
        if decision not in VALID_DECISIONS:
            # Unknown role — fall back to "none" with a note
            decision = "none"

        sub_criteria = []
        for kid in sorted(kids_by_parent.get(crit_id, []), key=lambda k: k["criterion_id"]):
            child_id = _derive_child_id(kid["criterion_id"], parent_id=crit_id)
            sub_criteria.append({
                "child_id": child_id,
                "text_span": kid.get("text", ""),
            })

        rec: dict[str, Any] = {
            "criterion_id": crit_id,
            "splitting_decision": decision,
            "sub_criteria": sub_criteria,
        }
        if c.get("child_logic"):
            rec["child_logic"] = c["child_logic"]
        # cohort_scope: production doesn't track this at Stage 1 granularity;
        # leave absent (Stage 1 spec: optional field)
        records.append(rec)

    envelope = {
        "trial_id": trial_id,
        "stage": 1,
        "source": "llm",
        "model": DEFAULT_MODEL_NAME,
        "created_at": _utc_now_iso(),
        "records": records,
        "notes": (
            "Extracted from production pipeline output "
            "(pipeline/output/NCT*_annotation.json) — Prompt 1 results were "
            "already embedded as parent_role / child_logic. No new LLM call."
        ),
    }
    return envelope


def _derive_child_id(child_criterion_id: str, *, parent_id: str) -> str:
    """Pull the child suffix (e.g., 'I1a' with parent 'I1' → 'a')."""
    if child_criterion_id.startswith(parent_id):
        suffix = child_criterion_id[len(parent_id):]
        if suffix:
            return suffix
    # Fallback: last character
    return child_criterion_id[-1] if child_criterion_id else "?"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ──────────────────────────────────────────────────────────────────────
# Main driver
# ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help=f"Output workspace directory (default: {DEFAULT_WORKSPACE})",
    )
    parser.add_argument(
        "--production-output",
        type=Path,
        default=PRODUCTION_OUTPUT,
        help=f"Production pipeline output directory (default: {PRODUCTION_OUTPUT})",
    )
    parser.add_argument(
        "--trial",
        type=str,
        default=None,
        help="Convert only one trial by NCT id (default: all 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written, don't actually write",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in workspace",
    )
    args = parser.parse_args(argv)

    input_trials_path = args.production_output / "input_trials.json"
    if not input_trials_path.exists():
        print(f"ERROR: not found: {input_trials_path}", file=sys.stderr)
        return 1

    all_trials = json.loads(input_trials_path.read_text(encoding="utf-8"))
    if args.trial:
        all_trials = [t for t in all_trials if t["trial_id"] == args.trial]
        if not all_trials:
            print(f"ERROR: trial {args.trial} not found in input_trials.json", file=sys.stderr)
            return 1

    print(f"Converting {len(all_trials)} trial(s) → {args.workspace}")
    n_input_written = 0
    n_llm_written = 0
    n_llm_skipped = 0
    for trial in all_trials:
        trial_id = trial["trial_id"]
        stage_dir = args.workspace / trial_id / "stage1"

        # 1. Stage 1 input
        input_data = convert_trial_input(trial)
        input_path = stage_dir / "input.json"
        if _write_json(input_path, input_data, dry_run=args.dry_run, force=args.force):
            n_input_written += 1

        # 2. Stage 1 LLM envelope (from production annotation)
        prod_path = args.production_output / f"{trial_id}_annotation.json"
        if not prod_path.exists():
            print(f"  [skip llm_output] {trial_id}: no production annotation at {prod_path}")
            n_llm_skipped += 1
            continue
        prod_data = json.loads(prod_path.read_text(encoding="utf-8"))
        envelope = extract_stage1_envelope(prod_data)
        llm_path = stage_dir / "llm_output.json"
        if _write_json(llm_path, envelope, dry_run=args.dry_run, force=args.force):
            n_llm_written += 1

    print(f"\nSummary:")
    print(f"  input.json written:       {n_input_written}/{len(all_trials)}")
    print(f"  llm_output.json written:  {n_llm_written}/{len(all_trials)}")
    if n_llm_skipped:
        print(f"  llm_output.json skipped:  {n_llm_skipped} (missing production data)")
    if args.dry_run:
        print(f"  (dry-run — no files actually written)")
    print(f"\nNext: bash scripts/run_iaa_ui.sh  → pick a trial in the sidebar.")
    return 0


def _write_json(path: Path, data: dict, *, dry_run: bool, force: bool) -> bool:
    if path.exists() and not force:
        print(f"  [skip exists] {path}")
        return False
    if dry_run:
        print(f"  [dry] would write {path} ({len(json.dumps(data))} chars)")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ wrote {path}")
    return True


if __name__ == "__main__":
    sys.exit(main())
