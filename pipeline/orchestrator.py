"""
Pipeline Orchestrator — LLM-assisted annotation for 30 clinical trial protocols.

Implements the 5-stage sequential pipeline from llm_pre_annotation_prompts_design.md:
  Stage A  → Python: criterion text extraction (input parsing)
  Prompt 1 → LLM: splitting decision + cohort_scope
  Prompt 2 → LLM: semantic_category + relation_type + target_subtype
  Prompt 3 → LLM: preferred_name normalization
  Stage I/J → Python regex + Prompt 4 fallback: HAS_VALUE / HAS_TEMPORAL
  Prompt 5 → LLM (frontier): alternative_constraint / exception_qualifier
  Stage N  → Python: final validation

All alignment gaps from schema review are handled inline (see comments prefixed GAP FIX).
"""
from __future__ import annotations
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import OUTPUT_DIR, RELATION_TYPES
from .llm_client import call_llm
from .regex_extractor import extract_constraints
from .transforms import (
    strip_nested,
    fanout_additional_targets,
    normalize_alternative_constraint_keys,
    assemble_criterion_record,
    assemble_relation,
)
from .validators import (
    validate_full_annotation,
    validate_relation_properties,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")


# ── Data structures ────────────────────────────────────────────────────

@dataclass
class TrialInput:
    """Input for a single trial to annotate."""
    trial_id: str                          # e.g. "NCT03425643"
    trial_acronym: str | None = None       # e.g. "KEYNOTE-671"
    disease_domain: str | None = None
    cohorts: list[dict] | None = None      # for basket/multi-cohort trials
    criteria: list[dict] = field(default_factory=list)
    # Each criterion: {"id": str, "type": "inclusion"|"exclusion",
    #                   "text": str, "protocol_ref": str}


@dataclass
class PipelineResult:
    """Result for a single criterion."""
    criterion_id: str
    success: bool
    annotation: dict | None = None
    errors: list[str] = field(default_factory=list)
    needs_human_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    stage_outputs: dict[str, Any] = field(default_factory=dict)  # debug


# ── Alternative / exception detection ─────────────────────────────────

_ALT_KEYWORDS = re.compile(
    r"\b(?:except|exception|unless|provided\s+that|note:\s*\w+\s*(?:are|is)\s+not\s+excluded|"
    r"not\s+required|if\s+(?:available|technically|liver)|or\s+(?:baseline|direct)|"
    r"whichever|±|alternative|waive[dr]?)\b",
    re.IGNORECASE,
)


def _has_alternative_or_exception(
    text: str,
    p1_output: dict,
    relations: list[dict],
) -> bool:
    """Detect whether Prompt 5 is needed."""
    # Nested exception always needs Prompt 5
    if p1_output.get("splitting_decision") == "nested_exception":
        return True
    # Keyword detection
    if _ALT_KEYWORDS.search(text):
        return True
    # Check if any relation has partial alternative_constraint from regex
    for rel in relations:
        props = rel.get("properties", {})
        if props.get("alternative_constraint"):
            return True
    return False


def _extract_alternative_text(text: str) -> str:
    """Extract the alternative/exception portion from criterion text."""
    # Look for common delimiters
    for pattern in [
        r"(?:except|unless|provided\s+that|note:).+",
        r"(?:or\s+direct|or\s+baseline|or\s+recovered).+",
        r"(?:if\s+liver|if\s+available|if\s+technically).+",
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(0).strip()
    return text  # fallback: send full text


# ── Per-criterion processing ──────────────────────────────────────────

def process_criterion(
    criterion_id: str,
    criterion_type: str,
    criterion_text: str,
    trial_metadata: dict,
) -> PipelineResult:
    """
    Process a single criterion through the 5-stage pipeline.
    Returns PipelineResult with annotation or errors.
    """
    result = PipelineResult(criterion_id=criterion_id, success=False)

    # ── Prompt 1: Splitting ────────────────────────────────────────
    try:
        p1 = call_llm("prompt_1", {
            "criterion_text": criterion_text,
            "cohort_list_or_null": trial_metadata.get("cohorts"),
        })
        p1 = strip_nested(p1)
        result.stage_outputs["prompt_1"] = p1
    except RuntimeError as e:
        result.errors.append(f"Prompt 1 failed: {e}")
        result.needs_human_review = True
        result.review_reasons.append("Splitting decision failed — manual splitting required")
        # Fallback: treat as single criterion
        p1 = {"splitting_decision": "none", "sub_criteria": [], "cohort_scope": None}
        result.stage_outputs["prompt_1"] = p1

    # Determine processing targets
    sd = p1.get("splitting_decision", "none")
    if sd == "none":
        targets = [{"child_id": None, "text": criterion_text}]
    elif sd in ("composite_split", "macro_aggregate"):
        targets = [
            {"child_id": sub["child_id"], "text": sub["text_span"]}
            for sub in p1.get("sub_criteria", [])
        ]
        if not targets:
            targets = [{"child_id": None, "text": criterion_text}]
    elif sd == "nested_exception":
        # Process as single unit; exception handled in Prompt 5
        targets = [{"child_id": None, "text": criterion_text}]
    else:
        targets = [{"child_id": None, "text": criterion_text}]

    # ── Process each target through Prompts 2-4 ───────────────────
    all_criteria_records: list[dict] = []
    all_relations_flat: list[dict] = []

    for target in targets:
        target_text = target["text"]
        child_id = target["child_id"]
        sub_criterion_id = (
            f"{criterion_id}{child_id}" if child_id else criterion_id
        )

        # ── Prompt 2: Category / Relation / Target ────────────────
        try:
            p2 = call_llm("prompt_2", {
                "criterion_text": target_text,
                "inclusion_or_exclusion": criterion_type,
                "parent_id_and_role_or_null": (
                    json.dumps({"parent_id": criterion_id, "parent_role": sd})
                    if child_id else "null"
                ),
            })
            p2 = strip_nested(p2)
            result.stage_outputs[f"prompt_2_{sub_criterion_id}"] = p2
        except RuntimeError as e:
            result.errors.append(f"Prompt 2 failed for {sub_criterion_id}: {e}")
            result.needs_human_review = True
            result.review_reasons.append(
                f"Category/relation extraction failed for {sub_criterion_id}"
            )
            continue

        # ── Prompt 3: Preferred name (per relation) ───────────────
        assembled_relations: list[dict] = []

        for rel_raw in p2.get("relations", []):
            try:
                p3 = call_llm("prompt_3", {
                    "target_text_span": rel_raw.get("target_text_span", ""),
                    "target_subtype": rel_raw.get("target_subtype", ""),
                    "full_criterion_text": target_text,
                })
                p3 = strip_nested(p3)
            except RuntimeError as e:
                result.errors.append(
                    f"Prompt 3 failed for {sub_criterion_id}/{rel_raw.get('relation_id')}: {e}"
                )
                result.needs_human_review = True
                # Use text_span as fallback preferred_name
                p3 = {"preferred_name": rel_raw.get("target_text_span", "UNKNOWN")}

            # ── GAP FIX #5: fan-out additional_targets ────────────
            additional = fanout_additional_targets(p3)
            for add_target in additional:
                add_rel = assemble_relation(
                    relation_type=rel_raw.get("relation_type", ""),
                    target_subtype=rel_raw.get("target_subtype", ""),
                    target_preferred_name=add_target.get("preferred_name", ""),
                    target_text_span=rel_raw.get("target_text_span", ""),
                    properties={
                        k: v for k, v in add_target.items()
                        if k not in ("preferred_name", "alternate_names")
                    },
                )
                assembled_relations.append(add_rel)

            # Biomarker details assembly
            biomarker_details = None
            if rel_raw.get("target_subtype") == "Biomarker":
                biomarker_details = {
                    "gene_symbol": p3.get("gene_symbol")
                    or (p3.get("variants", [{}])[0].get("gene_symbol")
                        if p3.get("variants") else None),
                }
                if p3.get("variants"):
                    biomarker_details["variants"] = p3["variants"]
                if p3.get("status"):
                    biomarker_details["status"] = p3["status"]

            # Build primary relation
            primary_rel = assemble_relation(
                relation_type=rel_raw.get("relation_type", ""),
                target_subtype=rel_raw.get("target_subtype", ""),
                target_preferred_name=p3.get("preferred_name", ""),
                target_text_span=rel_raw.get("target_text_span", ""),
                biomarker_details=biomarker_details,
            )
            assembled_relations.append(primary_rel)

        # ── Stages I/J: Regex + Prompt 4 fallback ─────────────────
        # Decision: use regex output when the specific relation type has a
        # match AND extraction is complete (no non-standard keywords). Fall
        # back to Prompt 4 in any other case — including the previously
        # silent "regex found nothing for this type" case which dropped
        # ~114 HAS_VALUE relations to empty properties across 30 trials.
        for rel in assembled_relations:
            rt = rel.get("relation_type", "")
            if rt not in ("HAS_VALUE", "HAS_TEMPORAL"):
                continue

            # Run regex on the relation's specific span when available,
            # falling back to the broader target_text. Span-scoped regex
            # avoids cross-talk when multiple HAS_VALUE relations share a
            # criterion (e.g., I4 organ function with ANC + Hb + Plt).
            scope_text = rel.get("target_text_span") or target_text
            regex_result = extract_constraints(scope_text)
            result.stage_outputs[f"regex_{sub_criterion_id}"] = {
                "has_value": regex_result.has_value,
                "has_temporal": regex_result.has_temporal,
                "is_complete": regex_result.is_complete,
            }

            extracted = (
                regex_result.has_value if rt == "HAS_VALUE"
                else regex_result.has_temporal
            )
            if extracted and regex_result.is_complete:
                rel["properties"] = extracted[0]
                continue

            # Prompt 4 fallback (covers: empty extraction, non-standard
            # keywords, natural language operators, corrupted unicode)
            try:
                p4 = call_llm("prompt_4", {
                    "criterion_text": target_text,
                    "regex_output_or_null": json.dumps({
                        "has_value": regex_result.has_value,
                        "has_temporal": regex_result.has_temporal,
                    }) if (regex_result.has_value or regex_result.has_temporal) else "null",
                })
                p4 = strip_nested(p4)
                result.stage_outputs[f"prompt_4_{sub_criterion_id}"] = p4

                if rt == "HAS_VALUE" and p4.get("has_value_constraints"):
                    rel["properties"] = p4["has_value_constraints"][0]
                elif rt == "HAS_TEMPORAL" and p4.get("has_temporal_constraints"):
                    rel["properties"] = p4["has_temporal_constraints"][0]

                if p4.get("needs_human_review"):
                    result.needs_human_review = True
                    result.review_reasons.append(
                        f"Prompt 4 flagged for review: {p4.get('review_reason', 'unspecified')}"
                    )
            except RuntimeError as e:
                result.errors.append(f"Prompt 4 failed for {sub_criterion_id}: {e}")

        # Also extract HAS_VALUE/HAS_TEMPORAL as separate relations
        # when the main relation is REQUIRES_*/EXCLUDES_* but criterion has
        # numeric or temporal constraints
        regex_check = extract_constraints(target_text)
        existing_types = {r.get("relation_type") for r in assembled_relations}

        if regex_check.has_value and "HAS_VALUE" not in existing_types:
            for hv in regex_check.has_value:
                hv_clean = {k: v for k, v in hv.items() if not k.startswith("_")}
                assembled_relations.append(assemble_relation(
                    relation_type="HAS_VALUE",
                    target_subtype="Observation",
                    target_preferred_name=hv.get("_test_name_hint", ""),
                    target_text_span=target_text,
                    properties=hv_clean,
                ))

        if regex_check.has_temporal and "HAS_TEMPORAL" not in existing_types:
            for ht in regex_check.has_temporal:
                assembled_relations.append(assemble_relation(
                    relation_type="HAS_TEMPORAL",
                    target_subtype="Observation",
                    target_preferred_name="",
                    target_text_span=target_text,
                    properties=ht,
                ))

        # ── GAP FIX #1: validate relation-property whitelist ──────
        for rel in assembled_relations:
            rt = rel.get("relation_type", "")
            props = rel.get("properties", {})
            if props and rt:
                prop_errors = validate_relation_properties(rt, props)
                if prop_errors:
                    logger.warning(
                        f"[{sub_criterion_id}] stripping invalid properties: {prop_errors}"
                    )
                    from .config import RELATION_PROPERTY_WHITELIST
                    allowed = RELATION_PROPERTY_WHITELIST.get(rt, set())
                    rel["properties"] = {k: v for k, v in props.items() if k in allowed}

        all_relations_flat.extend(assembled_relations)

        # Build criterion record
        parent_id = criterion_id if child_id else None
        crit_record = assemble_criterion_record(
            criterion_id=sub_criterion_id,
            criterion_type=criterion_type,
            text=target_text,
            prompt1_output=p1,
            prompt2_output=p2,
            relations_assembled=assembled_relations,
            parent_criterion_id=parent_id,
        )
        all_criteria_records.append(crit_record)

    # ── Add parent record for split criteria ──────────────────────
    # Only composite_split / macro_aggregate produce children with child_id
    # suffixes and thus need a separate parent stub. nested_exception is
    # processed as a single criterion (its target loop already emits the
    # record with parent_role=nested_exception_parent), so adding a parent
    # stub here would duplicate the criterion_id.
    if sd in ("composite_split", "macro_aggregate") and targets:
        parent_record = assemble_criterion_record(
            criterion_id=criterion_id,
            criterion_type=criterion_type,
            text=criterion_text,
            prompt1_output=p1,
            prompt2_output={"semantic_category": all_criteria_records[0].get("semantic_category")
                            if all_criteria_records else None},
            relations_assembled=[],
            parent_criterion_id=None,
        )
        all_criteria_records.insert(0, parent_record)

    # ── Prompt 5: alternative_constraint (if needed) ──────────────
    if _has_alternative_or_exception(criterion_text, p1, all_relations_flat):
        try:
            # Build primary constraint summary for prompt 5 input
            primary_constraints = []
            for rel in all_relations_flat:
                if rel.get("relation_type") in ("HAS_VALUE", "HAS_TEMPORAL") or \
                   rel.get("relation_type", "").startswith(("REQUIRES_", "EXCLUDES_")):
                    primary_constraints.append({
                        "relation_type": rel.get("relation_type"),
                        "target": rel.get("target_preferred_name"),
                        **(rel.get("properties", {})),
                    })

            alt_text = _extract_alternative_text(criterion_text)

            p5 = call_llm("prompt_5", {
                "criterion_text": criterion_text,
                "primary_constraint_from_earlier_stages": json.dumps(
                    primary_constraints, ensure_ascii=False
                ),
                "alternative_or_exception_text": alt_text,
            })
            p5 = strip_nested(p5)
            result.stage_outputs["prompt_5"] = p5

            # Apply Prompt 5 output
            if "alternative_constraint" in p5:
                ac = p5["alternative_constraint"]
                # GAP FIX #2: normalize keys
                if isinstance(ac, dict):
                    ac = normalize_alternative_constraint_keys(ac)
                # Attach to the first HAS_VALUE or HAS_TEMPORAL relation
                for rel in all_relations_flat:
                    if rel.get("relation_type") in ("HAS_VALUE", "HAS_TEMPORAL"):
                        if "properties" not in rel:
                            rel["properties"] = {}
                        rel["properties"]["alternative_constraint"] = ac
                        break

            if "exception_type" in p5:
                # Build INCLUDES_EXCEPTION relation
                exc_rel = assemble_relation(
                    relation_type="INCLUDES_EXCEPTION",
                    target_subtype=all_relations_flat[0].get("target_subtype", "Condition")
                    if all_relations_flat else "Condition",
                    target_preferred_name=alt_text[:100],
                    target_text_span=alt_text,
                    properties={
                        "exception_type": p5["exception_type"],
                        "exception_qualifier": p5.get("exception_qualifier"),
                    },
                )
                # Add to all criterion records that need it
                for crit in all_criteria_records:
                    if crit.get("parent_role") in ("nested_exception_parent", None):
                        crit.setdefault("relations", []).append(exc_rel)
                        break

            if p5.get("needs_human_review"):
                result.needs_human_review = True
                result.review_reasons.append(
                    f"Prompt 5: {p5.get('review_reason', 'alternative_constraint flagged')}"
                )

        except RuntimeError as e:
            result.errors.append(f"Prompt 5 failed: {e}")
            result.needs_human_review = True
            result.review_reasons.append("alternative_constraint extraction failed")

    # ── Assemble final annotation ─────────────────────────────────
    result.annotation = {
        "criteria": all_criteria_records,
        "_pipeline_metadata": {
            "needs_human_review": result.needs_human_review,
            "review_reasons": result.review_reasons,
            "errors": result.errors,
        },
    }
    result.success = len(result.errors) == 0
    return result


# ── Trial-level processing ─────────────────────────────────────────────

def process_trial(trial: TrialInput) -> dict:
    """
    Process all criteria in a single trial.
    Returns the full trial annotation (schema-compliant Trial object).
    """
    logger.info(f"═══ Processing trial {trial.trial_id} ({trial.trial_acronym}) ═══")

    all_criteria: list[dict] = []
    summary = {"total": 0, "success": 0, "human_review": 0, "errors": 0}

    for crit_input in trial.criteria:
        summary["total"] += 1
        result = process_criterion(
            criterion_id=crit_input["id"],
            criterion_type=crit_input["type"],
            criterion_text=crit_input["text"],
            trial_metadata={
                "trial_id": trial.trial_id,
                "cohorts": trial.cohorts,
                "disease_domain": trial.disease_domain,
            },
        )

        if result.success:
            summary["success"] += 1
        else:
            summary["errors"] += 1

        if result.needs_human_review:
            summary["human_review"] += 1

        if result.annotation:
            all_criteria.extend(result.annotation.get("criteria", []))

        logger.info(
            f"  {result.criterion_id}: "
            f"{'✓' if result.success else '✗'} "
            f"{'[REVIEW]' if result.needs_human_review else ''} "
            f"{result.errors if result.errors else ''}"
        )

    # Assemble trial-level annotation
    trial_annotation = {
        "trial_id": trial.trial_id,
        "trial_acronym": trial.trial_acronym,
        "disease_domain": trial.disease_domain,
        "criteria": all_criteria,
    }
    if trial.cohorts:
        trial_annotation["cohorts"] = trial.cohorts

    # ── Stage N: Final validation ─────────────────────────────────
    validation_errors = validate_full_annotation(trial_annotation)
    if validation_errors:
        logger.warning(
            f"Final validation for {trial.trial_id}: {len(validation_errors)} errors"
        )
        for err in validation_errors[:10]:
            logger.warning(f"  {err}")
        trial_annotation["_validation_errors"] = validation_errors

    trial_annotation["_pipeline_summary"] = summary
    logger.info(
        f"═══ {trial.trial_id} complete: "
        f"{summary['success']}/{summary['total']} success, "
        f"{summary['human_review']} need review, "
        f"{summary['errors']} errors ═══"
    )

    return trial_annotation


# ── Batch processing ──────────────────────────────────────────────────

def process_batch(
    trials: list[TrialInput],
    output_dir: Path | None = None,
    resume: bool = True,
    inter_trial_delay: float = 2.0,
) -> list[dict]:
    """
    Process multiple trials. Save each trial annotation as a separate JSON file.

    Args:
        trials: List of trial inputs to process.
        output_dir: Output directory for annotation JSONs.
        resume: If True, skip trials whose output JSON already exists.
        inter_trial_delay: Seconds to wait between trials (rate limit buffer).
    """
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    skipped = 0

    total = len(trials)
    for idx, trial in enumerate(trials, 1):
        out_path = output_dir / f"{trial.trial_id}_annotation.json"

        # Resume: skip already-completed trials
        if resume and out_path.exists():
            try:
                existing = json.loads(out_path.read_text(encoding="utf-8"))
                summary = existing.get("_pipeline_summary", {})
                if summary.get("errors", 0) == 0 and summary.get("success", 0) > 0:
                    logger.info(
                        f"[{idx}/{total}] Skipping {trial.trial_id} "
                        f"(already completed: {summary.get('success')}/{summary.get('total')} success)"
                    )
                    results.append(existing)
                    skipped += 1
                    continue
            except (json.JSONDecodeError, KeyError):
                pass  # Re-process if file is corrupted

        # Process trial
        logger.info(f"[{idx}/{total}] Processing {trial.trial_id}...")
        try:
            annotation = process_trial(trial)
            results.append(annotation)

            # Save individual trial output
            out_path.write_text(
                json.dumps(annotation, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary = annotation.get("_pipeline_summary", {})
            logger.info(
                f"[{idx}/{total}] ✓ {trial.trial_id} saved — "
                f"{summary.get('success', 0)}/{summary.get('total', 0)} success, "
                f"{summary.get('errors', 0)} errors"
            )

        except Exception as e:
            logger.error(f"[{idx}/{total}] ✗ {trial.trial_id} failed: {e}")
            # Save partial result so we don't lose progress
            error_result = {
                "trial_id": trial.trial_id,
                "criteria": [],
                "_pipeline_summary": {"total": 0, "success": 0, "errors": 1,
                                       "fatal_error": str(e)},
            }
            results.append(error_result)
            out_path.write_text(
                json.dumps(error_result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # Rate limit buffer between trials
        if idx < total:
            time.sleep(inter_trial_delay)

    # Save batch summary
    summary_path = output_dir / "batch_summary.json"
    batch_summary = {
        "total_trials": len(trials),
        "processed": len(trials) - skipped,
        "skipped_resume": skipped,
        "per_trial": [
            {
                "trial_id": a.get("trial_id", "?"),
                "summary": a.get("_pipeline_summary", {}),
                "validation_errors": len(a.get("_validation_errors", [])),
            }
            for a in results
        ],
    }
    summary_path.write_text(
        json.dumps(batch_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"Batch summary saved: {summary_path}")

    # Print final summary
    total_success = sum(
        a.get("_pipeline_summary", {}).get("success", 0) for a in results
    )
    total_errors = sum(
        a.get("_pipeline_summary", {}).get("errors", 0) for a in results
    )
    total_criteria = sum(
        a.get("_pipeline_summary", {}).get("total", 0) for a in results
    )
    logger.info(
        f"\n{'═' * 60}\n"
        f"BATCH COMPLETE: {len(trials)} trials\n"
        f"  Criteria: {total_success}/{total_criteria} success, {total_errors} errors\n"
        f"  Skipped (resume): {skipped}\n"
        f"  Output: {output_dir}\n"
        f"{'═' * 60}"
    )

    return results


# ── CLI entry point ───────────────────────────────────────────────────

def main():
    """
    CLI entry point: process trials from a JSON input file.

    Usage:
        python orchestrator.py input_trials.json [output_dir]

    Input JSON format:
    [
      {
        "trial_id": "NCT03425643",
        "trial_acronym": "KEYNOTE-671",
        "disease_domain": "NSCLC",
        "cohorts": null,
        "criteria": [
          {"id": "NCT03425643_I1", "type": "inclusion", "text": "...", "protocol_ref": "Inclusion #1"},
          ...
        ]
      },
      ...
    ]
    """
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <input_trials.json> [output_dir]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT_DIR

    raw = json.loads(input_path.read_text(encoding="utf-8"))
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

    logger.info(f"Loaded {len(trials)} trials from {input_path}")
    process_batch(trials, output_path)


if __name__ == "__main__":
    main()