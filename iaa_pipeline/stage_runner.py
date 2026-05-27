"""Stage runners for the IAA pipeline.

Each runner wraps the existing pipeline's per-stage LLM call with:
  - explicit JSON envelope output
  - LLM response caching (to avoid re-paying for re-runs)
  - per-criterion error isolation (failures don't crash the whole run)
  - upstream gold validation (Stages 2+ require Stage N-1 gold)

This file currently implements Stage 1 only. Stages 2-5 follow the
same pattern; stubs will be filled in subsequent commits.

See iaa_pipeline_spec/04_stage_runners.md for the full design.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure pipeline/ is importable (stage_schemas.py does this too)
from .stage_schemas import (
    Stage1Input,
    Stage1Record,
    StageOutputEnvelope,
    validate_stage1_record,
    validate_envelope,
)
from .cache import LLMCache

# Existing pipeline imports — paths set up by stage_schemas.py
from pipeline.config import MODELS, PROMPTS_DIR
from pipeline.llm_client import call_llm
from pipeline.transforms import strip_nested

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 with Z suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_input(trial_input: dict | Path) -> dict:
    """Load and lightly validate Stage 1 input."""
    if isinstance(trial_input, (str, Path)):
        path = Path(trial_input)
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = trial_input

    if "trial_id" not in data:
        raise ValueError("Stage 1 input missing 'trial_id'")
    if "criteria" not in data or not isinstance(data["criteria"], list):
        raise ValueError("Stage 1 input must contain 'criteria' as a list")
    if len(data["criteria"]) == 0:
        raise ValueError("Stage 1 input 'criteria' list is empty")

    for crit in data["criteria"]:
        for required in ("criterion_id", "type", "text"):
            if required not in crit:
                raise ValueError(f"Criterion missing required field: {required}")
        if crit["type"] not in ("inclusion", "exclusion"):
            raise ValueError(
                f"Criterion {crit['criterion_id']} has invalid type: {crit['type']!r}"
            )

    return data


def _format_neighboring_criteria(
    current_criterion: dict,
    all_criteria: list[dict],
    window: int = 2,
) -> str:
    """Build the NEIGHBORING_CRITERIA block expected by prompt_1.

    Returns a multi-line string with the current criterion marked
    by '>>> CURRENT >>>'. Uses ±`window` neighbors.
    """
    try:
        idx = next(
            i for i, c in enumerate(all_criteria)
            if c["criterion_id"] == current_criterion["criterion_id"]
        )
    except StopIteration:
        return current_criterion["text"]

    lo = max(0, idx - window)
    hi = min(len(all_criteria), idx + window + 1)
    lines = []
    for i in range(lo, hi):
        c = all_criteria[i]
        marker = ">>> CURRENT >>>" if i == idx else "                "
        lines.append(f"{marker} {c['criterion_id']}: {c['text']}")
    return "\n".join(lines)


def _read_prompt_template(prompt_id: str) -> str:
    """Read the raw prompt template text (for cache key)."""
    path = PROMPTS_DIR / f"{prompt_id}_splitting.txt" if prompt_id == "prompt_1" \
        else PROMPTS_DIR / f"{prompt_id}.txt"
    # The actual file naming may vary; try common patterns
    candidates = [
        PROMPTS_DIR / f"{prompt_id}_splitting.txt",
        PROMPTS_DIR / f"{prompt_id}.txt",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    # Fall back: return the prompt_id itself so cache key still works
    logger.warning(f"Could not find prompt template file for {prompt_id}")
    return prompt_id


# ──────────────────────────────────────────────────────────────────────
# Stage 1 — Splitting
# ──────────────────────────────────────────────────────────────────────

def run_stage1_splitting(
    trial_input: dict | Path,
    *,
    output_dir: Path,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> Path:
    """Run Prompt 1 (splitting) on every criterion in the trial.

    Args:
        trial_input: A Stage1Input dict or a path to a JSON file containing one.
        output_dir: Output root. The file is written to
            {output_dir}/{trial_id}/stage1/llm_output.json
        cache_dir: If provided, LLM responses are cached here. Subsequent
            runs with identical inputs incur zero LLM calls.
        model_override: Override the model defined in pipeline.config.MODELS.

    Returns:
        Path to the written output file.
    """
    data = _load_input(trial_input)
    trial_id = data["trial_id"]
    criteria = data["criteria"]

    model = model_override or MODELS["prompt_1"]
    cache = LLMCache(cache_dir)
    prompt_template = _read_prompt_template("prompt_1")

    logger.info(
        f"[Stage 1] {trial_id}: {len(criteria)} criteria, model={model}, "
        f"cache={'on' if cache.enabled else 'off'}"
    )

    records: list[dict] = []
    n_validation_failed = 0

    for i, criterion in enumerate(criteria, 1):
        criterion_id = criterion["criterion_id"]
        logger.info(f"[Stage 1] [{i}/{len(criteria)}] {criterion_id}")

        try:
            # Build the LLM variables
            variables = {
                "criterion_text": criterion["text"],
                "cohort_list_or_null": criterion.get("cohort_list") or "null",
                "neighboring_criteria": _format_neighboring_criteria(
                    criterion, criteria, window=2
                ),
            }

            # Try cache first
            cached = cache.get(prompt_template, variables, model)
            if cached is not None:
                parsed = cached
                logger.debug(f"[Stage 1] {criterion_id} cache hit")
            else:
                parsed = call_llm("prompt_1", variables, model_override=model)
                cache.put(prompt_template, variables, model, parsed)

            # Normalize: strip_nested handles fenced JSON, nested wrappers, etc.
            parsed = strip_nested(parsed)

            # Build the Stage1Record
            record: dict[str, Any] = {
                "criterion_id": criterion_id,
                "splitting_decision": parsed.get("splitting_decision", "none"),
                "child_logic": parsed.get("child_logic"),
                "cohort_scope": parsed.get("cohort_scope"),
                "sub_criteria": parsed.get("sub_criteria") or [],
            }
            # Include optional fields only if present
            if parsed.get("confidence"):
                record["confidence"] = parsed["confidence"]
            if parsed.get("notes"):
                record["notes"] = parsed["notes"]

            # Validate
            errors = validate_stage1_record(record)
            if errors:
                logger.warning(
                    f"[Stage 1] {criterion_id} validation errors: {errors}"
                )
                record["_validation_errors"] = errors
                n_validation_failed += 1

            records.append(record)

        except Exception as e:
            logger.error(
                f"[Stage 1] {criterion_id} FAILED: {type(e).__name__}: {e}"
            )
            records.append({
                "criterion_id": criterion_id,
                "_error": f"{type(e).__name__}: {e}",
                "_traceback": traceback.format_exc(),
            })

    # Assemble envelope
    envelope: dict[str, Any] = {
        "trial_id": trial_id,
        "stage": 1,
        "source": "llm",
        "model": model,
        "created_at": _utc_now_iso(),
        "records": records,
    }
    if data.get("trial_acronym"):
        envelope["trial_acronym"] = data["trial_acronym"]

    env_errors = validate_envelope(envelope)
    if env_errors:
        envelope["_validation_errors"] = env_errors
        logger.warning(f"Envelope validation errors: {env_errors}")

    # Write output
    out_dir = Path(output_dir) / trial_id / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "llm_output.json"
    out_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Summary
    n_errors = sum(1 for r in records if "_error" in r)
    n_success = len(records) - n_errors
    logger.info(
        f"[Stage 1] {trial_id} complete: "
        f"{n_success}/{len(records)} success, "
        f"{n_errors} errors, "
        f"{n_validation_failed} validation issues. "
        f"Cache: {cache.stats()}. "
        f"Output: {out_path}"
    )

    return out_path


# ──────────────────────────────────────────────────────────────────────
# Stage 2-5 stubs (to be implemented later)
# ──────────────────────────────────────────────────────────────────────

def run_stage2_category_relation(*args, **kwargs):
    raise NotImplementedError(
        "Stage 2 runner not yet implemented. See iaa_pipeline_spec/04_stage_runners.md"
    )


def run_stage3_preferred_name(*args, **kwargs):
    raise NotImplementedError("Stage 3 runner not yet implemented")


def run_stage4_constraints(*args, **kwargs):
    raise NotImplementedError("Stage 4 runner not yet implemented")


def run_stage5_alternatives(*args, **kwargs):
    raise NotImplementedError("Stage 5 runner not yet implemented")


STAGE_RUNNERS = {
    1: run_stage1_splitting,
    2: run_stage2_category_relation,
    3: run_stage3_preferred_name,
    4: run_stage4_constraints,
    5: run_stage5_alternatives,
}
