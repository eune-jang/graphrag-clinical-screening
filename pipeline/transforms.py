"""
Transform utilities for bridging LLM output → schema-compliant annotation.
Handles all alignment gaps identified in schema review.
"""
from __future__ import annotations
from typing import Any
from .config import LLM_OUTPUT_STRIP_FIELDS


def strip_nonschema_fields(obj: dict, extra_strip: set[str] | None = None) -> dict:
    """
    Gap fix #4, #6: Remove fields that exist in LLM prompt output
    but are NOT in the final schema (is_negation, value_type, etc.).

    Returns a new dict with stripped fields. Does not mutate input.
    """
    to_strip = LLM_OUTPUT_STRIP_FIELDS | (extra_strip or set())
    return {k: v for k, v in obj.items() if k not in to_strip}


def strip_nested(obj: Any) -> Any:
    """Recursively strip non-schema fields from nested dicts/lists."""
    if isinstance(obj, dict):
        cleaned = strip_nonschema_fields(obj)
        return {k: strip_nested(v) for k, v in cleaned.items()}
    elif isinstance(obj, list):
        return [strip_nested(item) for item in obj]
    return obj


def fanout_additional_targets(prompt3_output: dict) -> list[dict]:
    """
    Gap fix #5: When prompt_3 returns additional_targets[], each entry
    becomes a separate Relation-level record that the orchestrator must
    create as a new relation on the same criterion.

    Returns list of additional relation seeds (each with preferred_name,
    drug_class info, etc.) that the orchestrator appends to the criterion.

    Example input (from examples.json prompt_3, AZD9291):
    {
      "preferred_name": "Osimertinib",
      "additional_targets": [
        {"preferred_name": "3rd generation EGFR TKI class",
         "is_drug_class": true, "drug_class_type": "open_mechanism_class",
         "class_members": ["Osimertinib"]}
      ]
    }

    Returns:
    [{"preferred_name": "3rd generation EGFR TKI class",
      "is_drug_class": true, "drug_class_type": "open_mechanism_class", ...}]
    """
    return prompt3_output.get("additional_targets", [])


def normalize_alternative_constraint_keys(ac: dict) -> dict:
    """
    Gap fix #2 (partial): Normalize common key variants in
    alternative_constraint objects that LLM might produce.

    e.g. "if" → "condition", "when" → "condition",
         "applies_when" → "condition" (for consistency at relation level)
    """
    key_aliases = {
        "if": "condition",
        "when": "condition",
        "applies_when": "condition",
        "alt_test": "alternative_test",
        "alt_value": "alternative_value",
        "alt_baseline": "alternative_baseline",
    }
    return {key_aliases.get(k, k): v for k, v in ac.items()}


def cohort_scope_to_csv(cohort_scope: list[str] | None) -> str | None:
    """
    Gap fix #8 (INCEpTION): Convert array to comma-separated string
    for INCEpTION export (UIMA String field doesn't support arrays).
    """
    if not cohort_scope:
        return None
    return ",".join(cohort_scope)


def array_to_csv(arr: list[str] | None) -> str | None:
    """Generic array-to-CSV for equivalent_status, evidence_methods."""
    if not arr:
        return None
    return ",".join(arr)


def assemble_criterion_record(
    criterion_id: str,
    criterion_type: str,
    text: str,
    prompt1_output: dict,
    prompt2_output: dict,
    relations_assembled: list[dict],
    parent_criterion_id: str | None = None,
    child_cohort_scope: list[str] | None = None,
) -> dict:
    """
    Assemble a single Criterion record from pipeline stage outputs.
    This is the final schema-compliant structure.

    `child_cohort_scope` is the cohort_scope of the specific sub-criterion
    this record represents (split criteria carry cohort_scope per child). It
    takes precedence over the parent's record-level `cohort_scope`, which is
    used as a fallback for non-split criteria (and legacy data).
    """
    record: dict[str, Any] = {
        "criterion_id": criterion_id,
        "type": criterion_type,
        "semantic_category": prompt2_output.get("semantic_category"),
        "text": text,
        "relations": relations_assembled,
    }

    # Splitting metadata
    sd = prompt1_output.get("splitting_decision")
    if sd and sd != "none":
        if parent_criterion_id is None:
            # This is a parent record
            role_map = {
                "composite_split": "composite_split",
                "macro_aggregate": "macro_aggregate",
                "nested_exception": "nested_exception_parent",
            }
            record["parent_role"] = role_map.get(sd, sd)
            cl = prompt1_output.get("child_logic")
            if cl:
                record["child_logic"] = cl
        else:
            # This is a child record
            record["parent_criterion_id"] = parent_criterion_id

    # Cohort scope: prefer the per-child scope; fall back to the parent's
    # record-level scope (non-split criteria and legacy data).
    cs = child_cohort_scope if child_cohort_scope else prompt1_output.get("cohort_scope")
    if cs:
        record["cohort_scope"] = cs

    return record


# def _assign_review_tier(record: dict) -> str:
#     """
#     Assign review tier based on annotation guideline v0.2 Appendix B.

#     Tier 3 (전수 검수): splitting, alternative_constraint, 비표준 temporal
#     Tier 2 (빠르게 확인): category, relation type, preferred_name
#     Tier 1 (spot-check): 순수 numeric value, span offset
#     """
#     # Tier 3 triggers
#     if record.get("parent_role"):
#         return "tier3_full_review"

#     for rel in record.get("relations", []):
#         # alternative_constraint present
#         props = rel.get("properties", {})
#         if isinstance(props, dict) and props.get("alternative_constraint"):
#             return "tier3_full_review"

#         # Non-standard temporal (patient_event anchor)
#         if isinstance(props, dict) and props.get("anchor_type") == "patient_event":
#             return "tier3_full_review"

#         # INCLUDES_EXCEPTION
#         if rel.get("relation_type") == "INCLUDES_EXCEPTION":
#             return "tier3_full_review"

#     # Tier 1 triggers — pure numeric-only criteria
#     rel_types = {r.get("relation_type") for r in record.get("relations", [])}
#     if rel_types and rel_types <= {"HAS_VALUE", "HAS_TEMPORAL"}:
#         # Only value/temporal constraints, no semantic relations
#         return "tier1_spot_check"

#     # Default: Tier 2
#     return "tier2_quick_scan"


def assemble_relation(
    relation_type: str,
    target_subtype: str,
    target_preferred_name: str,
    target_text_span: str,
    properties: dict | None = None,
    biomarker_details: dict | None = None,
) -> dict:
    """Assemble a single Relation record."""
    rel: dict[str, Any] = {
        "relation_type": relation_type,
        "target_subtype": target_subtype,
        "target_preferred_name": target_preferred_name,
        "target_text_span": target_text_span,
    }

    if properties:
        # Strip non-schema fields from properties
        rel["properties"] = strip_nonschema_fields(properties)

    if biomarker_details:
        rel["biomarker_details"] = biomarker_details

    return rel