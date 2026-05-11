"""
Per-stage validators.

Each validator checks LLM output against schema enums and structural
rules BEFORE passing to the next stage. On failure, returns a list of error
strings so the orchestrator can decide whether to retry or flag for human review.

v1.2.1 → pruned: strictness, variant_notation, procedure_event, requirement_waiver, t/n/m_descriptor deferred to v1.3
"""
from __future__ import annotations
from typing import Any

from .config import (
    SPLITTING_DECISIONS, CHILD_LOGIC, SEMANTIC_CATEGORIES,
    RELATION_TYPES, CONCEPT_SUBTYPES, VARIANT_TYPES,
    OPERATORS, DIRECTIONS, ANCHOR_TYPES, EXCEPTION_TYPES,
    BIOMARKER_STATUSES, DRUG_CLASS_TYPES, RELATION_PROPERTY_WHITELIST,
)


def _check_enum(value: Any, allowed: set[str], field_name: str) -> list[str]:
    if value is None:
        return []
    if value not in allowed:
        return [f"{field_name}='{value}' not in {sorted(allowed)}"]
    return []


# ── Prompt 1: Splitting ────────────────────────────────────────────────

def validate_prompt1(output: dict) -> list[str]:
    """Validate splitting decision output."""
    errors: list[str] = []

    sd = output.get("splitting_decision")
    errors += _check_enum(sd, SPLITTING_DECISIONS, "splitting_decision")

    cl = output.get("child_logic")
    if cl is not None:
        errors += _check_enum(cl, CHILD_LOGIC, "child_logic")

    # structural checks
    if sd in ("composite_split", "macro_aggregate"):
        subs = output.get("sub_criteria", [])
        if len(subs) < 2:
            errors.append(f"splitting_decision={sd} requires ≥2 sub_criteria, got {len(subs)}")
        for i, sub in enumerate(subs):
            if not sub.get("text_span"):
                errors.append(f"sub_criteria[{i}] missing text_span")

    if sd == "nested_exception":
        subs = output.get("sub_criteria", [])
        if len(subs) < 2:
            errors.append(f"nested_exception requires ≥2 sub_criteria (main+exception), got {len(subs)}")

    if sd == "none":
        subs = output.get("sub_criteria", [])
        if subs:
            errors.append(f"splitting_decision=none but sub_criteria is non-empty ({len(subs)} items)")

    # cohort_scope type check
    cs = output.get("cohort_scope")
    if cs is not None and not isinstance(cs, list):
        errors.append(f"cohort_scope must be list or null, got {type(cs).__name__}")

    return errors


# ── Prompt 2: Category / Relation / Target ─────────────────────────────

def validate_prompt2(output: dict) -> list[str]:
    """Validate semantic category + relations output."""
    errors: list[str] = []

    errors += _check_enum(
        output.get("semantic_category"), SEMANTIC_CATEGORIES, "semantic_category"
    )

    relations = output.get("relations", [])
    if not relations:
        errors.append("relations array is empty")

    for i, rel in enumerate(relations):
        prefix = f"relations[{i}]"
        errors += _check_enum(rel.get("relation_type"), RELATION_TYPES,
                              f"{prefix}.relation_type")
        errors += _check_enum(rel.get("target_subtype"), CONCEPT_SUBTYPES,
                              f"{prefix}.target_subtype")
        if not rel.get("target_text_span"):
            errors.append(f"{prefix}.target_text_span is missing")

    return errors


# ── Prompt 3: Preferred Name ───────────────────────────────────────────

def validate_prompt3(output: dict) -> list[str]:
    """Validate preferred name extraction output."""
    errors: list[str] = []

    errors += _check_enum(
        output.get("concept_subtype"), CONCEPT_SUBTYPES, "concept_subtype"
    )

    if not output.get("preferred_name"):
        errors.append("preferred_name is missing or empty")

    # Biomarker variant checks
    variants = output.get("variants", [])
    for i, v in enumerate(variants):
        prefix = f"variants[{i}]"
        errors += _check_enum(v.get("variant_type"), VARIANT_TYPES,
                              f"{prefix}.variant_type")
        # variant_notation: deferred to v1.3 (auto-assigned, not validated)
        if not v.get("gene_symbol"):
            errors.append(f"{prefix}.gene_symbol is missing")
        if not v.get("variant"):
            errors.append(f"{prefix}.variant is missing")

    # Drug class checks
    if output.get("is_drug_class"):
        errors += _check_enum(output.get("drug_class_type"), DRUG_CLASS_TYPES,
                              "drug_class_type")

    return errors


# ── Prompt 4: Constraint Fallback ──────────────────────────────────────

def validate_prompt4(output: dict) -> list[str]:
    """Validate HAS_VALUE + HAS_TEMPORAL constraint output."""
    errors: list[str] = []

    for i, hv in enumerate(output.get("has_value_constraints", [])):
        prefix = f"has_value_constraints[{i}]"
        errors += _check_enum(hv.get("operator"), OPERATORS, f"{prefix}.operator")
        if hv.get("value") is None:
            errors.append(f"{prefix}.value is missing")
        # strictness: deferred to v1.3

    for i, ht in enumerate(output.get("has_temporal_constraints", [])):
        prefix = f"has_temporal_constraints[{i}]"
        errors += _check_enum(ht.get("operator"), OPERATORS, f"{prefix}.operator")
        errors += _check_enum(ht.get("direction"), DIRECTIONS, f"{prefix}.direction")
        errors += _check_enum(ht.get("anchor_type"), ANCHOR_TYPES, f"{prefix}.anchor_type")
        if ht.get("value") is None:
            errors.append(f"{prefix}.value is missing")
        if not ht.get("anchor"):
            errors.append(f"{prefix}.anchor is missing")

    return errors


# ── Prompt 5: alternative_constraint / exception ──────────────────────

def validate_prompt5(output: dict) -> list[str]:
    """Validate alternative_constraint or exception output."""
    errors: list[str] = []

    # May be alternative_constraint or exception_type output
    if "exception_type" in output:
        errors += _check_enum(output["exception_type"], EXCEPTION_TYPES, "exception_type")

    # alternative_constraint can be string or object — both valid
    ac = output.get("alternative_constraint")
    if ac is not None and not isinstance(ac, (str, dict)):
        errors.append(f"alternative_constraint must be string or object, got {type(ac).__name__}")

    eq = output.get("exception_qualifier")
    if eq is not None and not isinstance(eq, (str, dict)):
        errors.append(f"exception_qualifier must be string or object, got {type(eq).__name__}")

    return errors


# ── Final annotation validation ────────────────────────────────────────

def validate_relation_properties(relation_type: str, properties: dict) -> list[str]:
    """
    Gap fix #1: Check that relation properties only contain fields
    allowed for the given relation_type.
    """
    errors: list[str] = []
    allowed = RELATION_PROPERTY_WHITELIST.get(relation_type)
    if allowed is None:
        errors.append(f"Unknown relation_type '{relation_type}' — no property whitelist defined")
        return errors

    for key in properties:
        if key not in allowed:
            errors.append(
                f"relation_type={relation_type}: property '{key}' not in allowed set "
                f"{sorted(allowed)}"
            )

    return errors


def validate_full_annotation(annotation: dict) -> list[str]:
    """
    Final validation of assembled annotation before output.
    Checks structural integrity, enum compliance, and relation-property consistency.
    """
    errors: list[str] = []

    # Trial-level
    trial_id = annotation.get("trial_id", "")
    if not trial_id:
        errors.append("trial_id is missing")

    criteria = annotation.get("criteria", [])
    if not criteria:
        errors.append("criteria array is empty")

    seen_ids = set()
    for ci, crit in enumerate(criteria):
        cid = crit.get("criterion_id", "")
        prefix = f"criteria[{ci}] ({cid})"

        if not cid:
            errors.append(f"{prefix}: criterion_id missing")
        if cid in seen_ids:
            errors.append(f"{prefix}: duplicate criterion_id")
        seen_ids.add(cid)

        errors += _check_enum(crit.get("type"), {"inclusion", "exclusion"},
                              f"{prefix}.type")
        errors += _check_enum(crit.get("semantic_category"), SEMANTIC_CATEGORIES,
                              f"{prefix}.semantic_category")

        # parent_role check
        pr = crit.get("parent_role")
        if pr is not None:
            errors += _check_enum(pr,
                                  {"composite_split", "macro_aggregate", "nested_exception_parent"},
                                  f"{prefix}.parent_role")

        # Relations
        for ri, rel in enumerate(crit.get("relations", [])):
            rprefix = f"{prefix}.relations[{ri}]"
            rt = rel.get("relation_type", "")
            errors += _check_enum(rt, RELATION_TYPES, f"{rprefix}.relation_type")
            errors += _check_enum(rel.get("target_subtype"), CONCEPT_SUBTYPES,
                                  f"{rprefix}.target_subtype")

            # relation-property whitelist (gap fix #1)
            props = rel.get("properties", {})
            if props and rt:
                errors += validate_relation_properties(rt, props)

            # biomarker_details required for REQUIRES_BIOMARKER
            if rt == "REQUIRES_BIOMARKER" and not rel.get("biomarker_details"):
                errors.append(f"{rprefix}: REQUIRES_BIOMARKER missing biomarker_details")

    return errors


# ── Convenience: validator dispatch ────────────────────────────────────

VALIDATORS = {
    "prompt_1": validate_prompt1,
    "prompt_2": validate_prompt2,
    "prompt_3": validate_prompt3,
    "prompt_4": validate_prompt4,
    "prompt_5": validate_prompt5,
}