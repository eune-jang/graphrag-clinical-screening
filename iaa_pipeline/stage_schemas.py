"""JSON schemas for the IAA pipeline.

These TypedDict classes are the contract between stage runners, UI, and
IAA metrics. They mirror the JSON file structures defined in
iaa_pipeline_spec/03_json_schemas.md.

Enums are imported from `pipeline.config` (single source of truth) — DO NOT
duplicate enum values here.

This module also provides lightweight validation helpers; full schema
validation is in `iaa_pipeline.validators` (separate file).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict, Literal, Any
from typing_extensions import NotRequired  # for Python < 3.11 compatibility


# ── Make existing pipeline/ importable ────────────────────────────────
# The `pipeline/` directory is a sibling of `iaa_pipeline/`. We add the
# project root to sys.path so `from pipeline.config import ...` works.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Import enums from the existing pipeline ───────────────────────────
try:
    from pipeline.config import (
        SEMANTIC_CATEGORIES,
        RELATION_TYPES,
        CONCEPT_SUBTYPES,
        SPLITTING_DECISIONS,
        CHILD_LOGIC,
        OPERATORS,
        DIRECTIONS,
        ANCHOR_TYPES,
        VARIANT_TYPES,
        EXCEPTION_TYPES,
        BIOMARKER_STATUSES,
        DRUG_CLASS_TYPES,
    )
except ImportError as e:
    raise ImportError(
        f"Could not import enums from pipeline.config. "
        f"Make sure {_PROJECT_ROOT}/pipeline/config.py exists. "
        f"Original error: {e}"
    )


# ──────────────────────────────────────────────────────────────────────
# Universal envelope (top-level structure of every stage output file)
# ──────────────────────────────────────────────────────────────────────

class StageOutputEnvelope(TypedDict, total=False):
    """The top-level structure of every stage output JSON file."""
    trial_id: str                       # required
    stage: int                          # required: 1, 2, 3, 4, or 5
    source: str                         # required: "llm" | "annotator" | "gold"
    annotator: str                      # required if source == "annotator"
    model: str                          # required if source == "llm"
    created_at: str                     # required: ISO 8601 UTC
    records: list[dict[str, Any]]       # required: stage-specific record dicts
    notes: str                          # optional
    _validation_errors: list[str]       # optional, set by validator


# ──────────────────────────────────────────────────────────────────────
# Stage 1 — Splitting
# ──────────────────────────────────────────────────────────────────────

class CriterionInput(TypedDict, total=False):
    """One criterion as input to Stage 1."""
    criterion_id: str                   # required, e.g. "NCT03425643_I1"
    type: Literal["inclusion", "exclusion"]  # required
    text: str                           # required, raw text from protocol
    protocol_ref: str                   # optional, e.g. "Inclusion #1"
    cohort_list: list[str]              # optional, for multi-cohort trials
    neighboring_criteria: list["CriterionInput"]  # optional, for macro_aggregate detection


class Stage1Input(TypedDict):
    """Input to Stage 1 runner."""
    trial_id: str
    trial_acronym: NotRequired[str]
    disease_domain: NotRequired[str]
    cohorts: NotRequired[list[dict[str, Any]]]
    criteria: list[CriterionInput]


class Stage1SubCriterion(TypedDict, total=False):
    """One sub-criterion produced by splitting."""
    child_id: str                       # required: "a", "b", "c", ...
    text_span: str                      # required: exact text from parent
    rationale: str                      # optional


class Stage1Record(TypedDict, total=False):
    """One record in Stage 1 output (one per input criterion)."""
    criterion_id: str                   # required: parent criterion ID
    splitting_decision: str             # required: one of SPLITTING_DECISIONS
    child_logic: str | None             # optional: "AND" | "OR" | "XOR" | None
    cohort_scope: list[str] | None      # optional
    sub_criteria: list[Stage1SubCriterion]  # required (empty list if decision="none")
    confidence: Literal["high", "medium", "low"]  # optional
    notes: str                          # optional
    _error: str                         # optional, set if processing failed
    _traceback: str                     # optional


# ──────────────────────────────────────────────────────────────────────
# Stage 2 — Semantic Category + Relation + Subtype  (stub)
# ──────────────────────────────────────────────────────────────────────

class Stage2SubCriterionInput(TypedDict, total=False):
    sub_criterion_id: str               # required
    parent_criterion_id: str            # required
    parent_role: str                    # required, value of splitting_decision from Stage 1
    type: Literal["inclusion", "exclusion"]
    text_span: str


class Stage2Relation(TypedDict, total=False):
    relation_id: str                    # required, "r1", "r2", ...
    relation_type: str                  # required, one of RELATION_TYPES
    target_subtype: str                 # required, one of CONCEPT_SUBTYPES
    target_text_span: str               # required
    rationale: str                      # optional


class Stage2Record(TypedDict, total=False):
    sub_criterion_id: str               # required
    semantic_category: str              # required
    relations: list[Stage2Relation]     # required


# ──────────────────────────────────────────────────────────────────────
# Stage 3, 4, 5 — full schemas will be added later; only stubs here
# so that Stage 1 module can import the file without missing names.
# ──────────────────────────────────────────────────────────────────────

class Stage3Record(TypedDict, total=False):
    sub_criterion_id: str
    relation_id: str
    target_preferred_name: str


class Stage4ValueRecord(TypedDict, total=False):
    sub_criterion_id: str
    relation_id: str
    relation_type: Literal["HAS_VALUE"]
    operator: str
    value: Any
    unit: str
    extraction_source: Literal["regex", "llm"]


class Stage4TemporalRecord(TypedDict, total=False):
    sub_criterion_id: str
    relation_id: str
    relation_type: Literal["HAS_TEMPORAL"]
    operator: str
    value: Any
    unit: str
    anchor: str
    direction: str
    anchor_type: str
    extraction_source: Literal["regex", "llm"]


class Stage5Record(TypedDict, total=False):
    sub_criterion_id: str
    relation_id: str
    alternative_constraint: Any
    needs_human_review: bool


# ──────────────────────────────────────────────────────────────────────
# Error type annotation (cross-cutting)
# ──────────────────────────────────────────────────────────────────────

ERROR_TYPES = {
    "PASS",
    "S-SPLIT",
    "M-CATEGORY",
    "M-COHORT",
    "M-META",
    "R-MISSING",
    "R-WRONG",
    "P-VALUE",
    "P-QUALIFIER",
    "N-NAME",
}


class ErrorTypeAnnotation(TypedDict, total=False):
    stage: int                          # required: 1-5
    record_locator: dict[str, str]      # required, e.g. {"criterion_id": "..."}
    error_type: str                     # required, one of ERROR_TYPES (or comma-joined)
    comment: str                        # optional
    annotator: str                      # required
    created_at: str                     # required


# ──────────────────────────────────────────────────────────────────────
# Lightweight validation helpers (full validators live elsewhere)
# ──────────────────────────────────────────────────────────────────────

def validate_stage1_record(record: dict) -> list[str]:
    """Returns a list of validation error messages. Empty list = valid."""
    errors = []
    if "_error" in record:
        return []  # error placeholder records are skipped

    if "criterion_id" not in record:
        errors.append("missing criterion_id")
    if "splitting_decision" not in record:
        errors.append("missing splitting_decision")
    elif record["splitting_decision"] not in SPLITTING_DECISIONS:
        errors.append(
            f"invalid splitting_decision: {record['splitting_decision']!r} "
            f"(must be one of {sorted(SPLITTING_DECISIONS)})"
        )

    if "sub_criteria" not in record:
        errors.append("missing sub_criteria (use empty list if no split)")
    elif not isinstance(record["sub_criteria"], list):
        errors.append("sub_criteria must be a list")
    else:
        # For composite_split / macro_aggregate, sub_criteria must be non-empty
        if record.get("splitting_decision") in ("composite_split", "macro_aggregate"):
            if len(record["sub_criteria"]) == 0:
                errors.append(
                    f"sub_criteria must be non-empty for "
                    f"splitting_decision={record['splitting_decision']!r}"
                )
        # For "none", sub_criteria should be empty
        if record.get("splitting_decision") == "none":
            if len(record["sub_criteria"]) > 0:
                errors.append("sub_criteria must be empty when splitting_decision='none'")

    child_logic = record.get("child_logic")
    if child_logic is not None and child_logic not in CHILD_LOGIC:
        errors.append(
            f"invalid child_logic: {child_logic!r} (must be one of {sorted(CHILD_LOGIC)} or null)"
        )

    return errors


def validate_envelope(envelope: dict) -> list[str]:
    """Validate the top-level envelope structure."""
    errors = []
    for required in ("trial_id", "stage", "source", "created_at", "records"):
        if required not in envelope:
            errors.append(f"envelope missing required field: {required}")

    source = envelope.get("source")
    if source not in ("llm", "annotator", "gold"):
        errors.append(f"invalid source: {source!r}")
    elif source == "annotator" and "annotator" not in envelope:
        errors.append("source='annotator' requires 'annotator' field")
    elif source == "llm" and "model" not in envelope:
        errors.append("source='llm' requires 'model' field")

    return errors
