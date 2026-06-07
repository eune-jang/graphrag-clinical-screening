# 03 · JSON Schemas (Contract)

This file defines the JSON contracts between pipeline stages. Every module
(stage runners, UI, IAA metrics) reads/writes these schemas.

**Implement these schemas in `iaa_pipeline/stage_schemas.py` as `TypedDict`
classes.** This gives static type checking and lets the UI infer field types.

## Source of truth for enums

All enum values come from `pipeline.config`. Do NOT redefine them here.

```python
from pipeline.config import (
    SEMANTIC_CATEGORIES,    # 10 values
    RELATION_TYPES,         # 13 values
    CONCEPT_SUBTYPES,       # 6 values
    SPLITTING_DECISIONS,    # 4 values
    CHILD_LOGIC,            # 3 values
    OPERATORS,              # 6 values
    DIRECTIONS,             # 4 values
    ANCHOR_TYPES,           # 3 values
    VARIANT_TYPES,          # 9 values
    EXCEPTION_TYPES,        # 4 values
    BIOMARKER_STATUSES,     # 5 values
    DRUG_CLASS_TYPES,       # 3 values
)
```

## Universal envelope

Every stage output file follows this top-level structure:

```python
class StageOutputEnvelope(TypedDict):
    trial_id: str                       # "NCT03425643"
    stage: Literal[1, 2, 3, 4, 5]
    source: Literal["llm", "annotator", "gold"]
    annotator: NotRequired[str]         # required when source == "annotator"
    model: NotRequired[str]             # required when source == "llm"
    created_at: str                     # ISO 8601 UTC
    records: list                       # type depends on stage (see below)
    notes: NotRequired[str]
```

## Stage 1 — Splitting

### Input
```python
class Stage1Input(TypedDict):
    trial_id: str
    criteria: list[CriterionInput]

class CriterionInput(TypedDict):
    criterion_id: str                   # "NCT03425643_I1"
    type: Literal["inclusion", "exclusion"]
    text: str                           # raw criterion text from protocol
    protocol_ref: NotRequired[str]      # e.g. "Inclusion #1"
    cohort_list: NotRequired[list[str]] # for multi-cohort trials
    neighboring_criteria: NotRequired[list[CriterionInput]]
```

### Output records
```python
class Stage1Record(TypedDict):
    criterion_id: str                   # parent criterion ID
    splitting_decision: str             # one of SPLITTING_DECISIONS
    child_logic: NotRequired[str | None]  # "AND" | "OR" | "XOR" | None
    cohort_scope: NotRequired[list[str] | None]  # record-level scope; used only
                                                 #   for non-split ("none"). Split
                                                 #   criteria scope per child below.
    sub_criteria: list[Stage1SubCriterion]
    confidence: NotRequired[Literal["high", "medium", "low"]]
    notes: NotRequired[str]

class Stage1SubCriterion(TypedDict):
    child_id: str                       # "a" | "b" | "c" ...
    text_span: str                      # exact text from parent
    cohort_scope: NotRequired[list[str] | None]  # cohorts this child applies to
    rationale: NotRequired[str]
```

> **cohort_scope placement.** For split criteria (`composite_split`,
> `macro_aggregate`, `nested_exception`) cohort_scope is set **per child**
> inside each `sub_criteria` entry, because different children may apply to
> different cohorts. For non-split criteria (`none`) there are no children, so
> cohort_scope stays at the record level. Drafts created before this change
> stored a single record-level cohort_scope shared by all children; importers
> copy that legacy value to every child.

### Example

```json
{
  "trial_id": "NCT03425643",
  "stage": 1,
  "source": "annotator",
  "annotator": "EHJ",
  "created_at": "2026-05-28T10:30:00Z",
  "records": [
    {
      "criterion_id": "NCT03425643_I1",
      "splitting_decision": "composite_split",
      "child_logic": "AND",
      "sub_criteria": [
        {"child_id": "a", "text_span": "Male/female ≥18 years", "cohort_scope": null},
        {"child_id": "b", "text_span": "previously untreated NSCLC", "cohort_scope": null},
        {"child_id": "c", "text_span": "ECOG ≤1", "cohort_scope": null}
      ]
    }
  ]
}
```

### IAA fields (which fields go into agreement computation)

| Field | Type | IAA treatment |
|---|---|---|
| `splitting_decision` | 4-class | Cohen's κ (primary) |
| `child_logic` | 3-class + null | Cohen's κ (only for `composite_split`) |
| `cohort_scope` | list (per-child for splits, record-level for `none`) | exact set match over normalized `(child_id, cohort)` pairs |
| `sub_criteria.text_span` | string | **NOT direct IAA** — used for downstream alignment only |
| `confidence`, `notes`, `rationale` | various | excluded from IAA |

## Stage 2 — Semantic Category + Relation + Subtype

### Input
```python
class Stage2Input(TypedDict):
    trial_id: str
    sub_criteria: list[Stage2SubCriterionInput]  # from Stage 1 gold

class Stage2SubCriterionInput(TypedDict):
    sub_criterion_id: str               # "NCT03425643_I1a" or "NCT03425643_I2" if no split
    parent_criterion_id: str            # "NCT03425643_I1"
    parent_role: str                    # value of splitting_decision from Stage 1
    type: Literal["inclusion", "exclusion"]
    text_span: str                      # text of this sub-criterion
```

### Output records
```python
class Stage2Record(TypedDict):
    sub_criterion_id: str
    semantic_category: str              # one of SEMANTIC_CATEGORIES
    relations: list[Stage2Relation]

class Stage2Relation(TypedDict):
    relation_id: str                    # "r1", "r2", ... unique within sub_criterion
    relation_type: str                  # one of RELATION_TYPES
    target_subtype: str                 # one of CONCEPT_SUBTYPES
    target_text_span: str               # exact text identifying target entity
    rationale: NotRequired[str]
```

### Example
```json
{
  "records": [
    {
      "sub_criterion_id": "NCT03425643_I4",
      "semantic_category": "performance_status",
      "relations": [
        {
          "relation_id": "r1",
          "relation_type": "HAS_VALUE",
          "target_subtype": "Observation",
          "target_text_span": "ECOG"
        },
        {
          "relation_id": "r2",
          "relation_type": "HAS_TEMPORAL",
          "target_subtype": "Observation",
          "target_text_span": "within 10 days of randomization"
        }
      ]
    }
  ]
}
```

### IAA fields

| Field | Type | IAA treatment |
|---|---|---|
| `semantic_category` | 10-class | Cohen's κ |
| `relations` (presence count) | int | absolute match rate |
| `relation_type` | 13-class | Cohen's κ (computed over aligned relations) |
| `target_subtype` | 6-class | Cohen's κ (computed over aligned relations) |
| `target_text_span` | string | **NOT direct IAA** — used for alignment |
| `rationale` | string | excluded |

### Relation alignment problem (CRITICAL)

Two annotators may produce different numbers of relations for the same
sub_criterion. To compute relation-level IAA, relations must be **aligned**:

- Primary key for alignment: `target_text_span` (or fuzzy match if non-identical)
- If annotator A has 3 relations and B has 2, the unmatched relation
  contributes to "presence disagreement" but is excluded from
  relation_type/target_subtype kappa computation.

The aligner lives in `iaa_pipeline/aligners.py` (see `05_iaa_metrics.md`).

## Stage 3 — Preferred Name

### Input
```python
class Stage3Input(TypedDict):
    trial_id: str
    relations: list[Stage3RelationInput]  # from Stage 2 gold

class Stage3RelationInput(TypedDict):
    sub_criterion_id: str
    relation_id: str
    target_subtype: str
    target_text_span: str
    full_criterion_text: str            # context for the LLM
```

### Output records
```python
class Stage3Record(TypedDict):
    sub_criterion_id: str
    relation_id: str
    target_preferred_name: str          # standardized name
    alternate_names: NotRequired[list[str]]
    kb_link: NotRequired[str]           # e.g. "SNOMED:254637007"

    # Biomarker-specific (when target_subtype == "Biomarker")
    variants: NotRequired[list[Stage3Variant]]

    # Drug-class-specific (when target is a class)
    is_drug_class: NotRequired[bool]
    drug_class_type: NotRequired[str]   # one of DRUG_CLASS_TYPES
    class_members: NotRequired[list[str]]

class Stage3Variant(TypedDict):
    gene_symbol: str                    # HUGO symbol, e.g. "EGFR"
    variant: str                        # e.g. "T790M"
    variant_type: str                   # one of VARIANT_TYPES
    variant_notation: NotRequired[str]
    hgvs_p: NotRequired[str]
```

### IAA fields

| Field | Type | IAA treatment |
|---|---|---|
| `target_preferred_name` | string | **α/β/γ/δ** (LLM-assisted metric, see 05) |
| `alternate_names` | list | not in IAA |
| `kb_link` | string | exact match agreement |
| `variants[].gene_symbol` | string | exact match (for Biomarker) |
| `variants[].variant_type` | 9-class | Cohen's κ (for Biomarker) |

### Special: LLM-assisted IAA

Stage 3 is the first LLM-assisted stage. For each row, four states exist:
- LLM original output
- Annotator A's final value (may equal LLM or be modified)
- Annotator B's final value
- Consensus (after adjudication)

The 4-way metric (α, β, γ, δ) compares these four. See `05_iaa_metrics.md`.

## Stage 4 — Constraints (HAS_VALUE / HAS_TEMPORAL)

### Input
```python
class Stage4Input(TypedDict):
    trial_id: str
    constraints: list[Stage4ConstraintInput]  # from Stage 2 gold (filtered to constraint relations)

class Stage4ConstraintInput(TypedDict):
    sub_criterion_id: str
    relation_id: str
    relation_type: Literal["HAS_VALUE", "HAS_TEMPORAL"]
    target_text_span: str
    full_criterion_text: str
```

### Output records — HAS_VALUE
```python
class Stage4ValueRecord(TypedDict):
    sub_criterion_id: str
    relation_id: str
    relation_type: Literal["HAS_VALUE"]
    operator: str                       # one of OPERATORS
    value: str | float | int            # numeric or string (e.g., "ECOG 1")
    unit: NotRequired[str]
    scale: NotRequired[str]             # "ECOG" | "CTCAE" | "RECIST v1.1" | etc.
    measurement_method: NotRequired[str]
    equivalence_group_id: NotRequired[str]
    equivalence_group_logic: NotRequired[str]  # "MAX" | "MIN" | "AND" | "OR"
    extraction_source: Literal["regex", "llm"]  # tracks which method extracted
```

### Output records — HAS_TEMPORAL
```python
class Stage4TemporalRecord(TypedDict):
    sub_criterion_id: str
    relation_id: str
    relation_type: Literal["HAS_TEMPORAL"]
    operator: str                       # one of OPERATORS
    value: int | float
    unit: Literal["days", "weeks", "months", "years"]
    anchor: str                         # e.g. "randomization", "first_dose"
    direction: str                      # one of DIRECTIONS
    anchor_type: str                    # one of ANCHOR_TYPES
    forward_extending: NotRequired[bool]
    equivalence_group_id: NotRequired[str]
    equivalence_group_logic: NotRequired[str]
    extraction_source: Literal["regex", "llm"]
```

### IAA fields

| Field | IAA treatment |
|---|---|
| `operator` | exact match |
| `value` | exact match (numeric) |
| `unit` | exact match |
| `anchor` | string match (fuzzy allowed) |
| `direction`, `anchor_type` | exact match (categorical) |
| Per-field F1 across all constraints |
| Overall: macro-F1 across fields |

### Stage 4 dual-source design

Stage 4 has two extraction sources: `regex` (in `pipeline/regex_extractor.py`)
and `llm` (Prompt 4 fallback). The `extraction_source` field tracks which
produced each record. Report IAA separately for each:

- Regex-extracted records: typically near-100% agreement (deterministic)
- LLM-extracted records: where annotator disagreement actually concentrates

## Stage 5 — Alternative Constraint / Exception

### Input
```python
class Stage5Input(TypedDict):
    trial_id: str
    candidates: list[Stage5CandidateInput]  # criteria with potential alternatives

class Stage5CandidateInput(TypedDict):
    sub_criterion_id: str
    relation_id: str                    # relation that has alternative
    primary_constraint: dict            # the Stage 4 result (HAS_VALUE or HAS_TEMPORAL)
    full_criterion_text: str
    p1_splitting_decision: str          # from Stage 1, for context
```

### Output records
```python
class Stage5Record(TypedDict):
    sub_criterion_id: str
    relation_id: str
    alternative_constraint: dict | str | None  # see prompt_5 for structure
    exception_qualifier: NotRequired[dict | str]
    exception_type: NotRequired[str]    # one of EXCEPTION_TYPES
    needs_human_review: bool
    review_reason: NotRequired[str]
```

### IAA fields

Stage 5 is the most subjective; primary IAA metric is **consensus rate
after adjudication**:

| Metric | Computation |
|---|---|
| Initial agreement | % of candidates where annotators agree before adjudication |
| Post-adjudication consensus | % where consensus reached |
| Escalation rate | % requiring third reviewer |
| Structure agreement | When both annotators provide structured form, do they agree on shape (keys present)? |

## Error type annotation (cross-cutting)

Each annotator may attach an `error_type` to any record across any stage. This
is meta-annotation about LLM output quality, not the annotation itself.

### Schema
```python
class ErrorTypeAnnotation(TypedDict):
    stage: Literal[1, 2, 3, 4, 5]
    record_locator: dict                # which record (e.g. {"sub_criterion_id": "...", "relation_id": "..."})
    error_type: Literal[
        "PASS",
        "S-SPLIT",          # Stage 1 splitting wrong
        "M-CATEGORY",       # Stage 2 semantic_category wrong
        "M-COHORT",         # Stage 1 cohort_scope wrong
        "M-META",           # other metadata error
        "R-MISSING",        # Stage 2 relation missing
        "R-WRONG",          # Stage 2 relation wrong type
        "P-VALUE",          # Stage 4 value wrong
        "P-QUALIFIER",      # Stage 2 relation qualifier wrong
        "N-NAME",           # Stage 3 preferred_name wrong
    ]
    comment: NotRequired[str]           # free-text reviewer comment
```

### File location

Error type annotations live in a separate file per annotator:
```
workspace/error_types/{trial_id}_{annotator}_errors.jsonl
```

Each line is one `ErrorTypeAnnotation`. JSONL (not JSON array) so it can be
appended during annotation without rewriting the whole file.

### IAA on error_type itself

Error type kappa is computed by aligning entries on `record_locator` and
comparing `error_type` values. Multi-label (comma-separated) values must be
normalized to sets before comparison. See `05_iaa_metrics.md` for details.

## Universal rules

### Identifiers
- `criterion_id` is unique within a trial
- `sub_criterion_id` equals `criterion_id` when `splitting_decision == "none"`,
  otherwise `criterion_id + child_id` (e.g., `"NCT03425643_I1" + "a"` → `"NCT03425643_I1a"`)
- `relation_id` is unique within a `sub_criterion_id`

### Empty / missing values
- Use `None` (becomes `null` in JSON) for genuinely absent values
- Use `""` for "present but empty string" — these are different and treated
  differently in agreement computation
- Do NOT use `"N/A"`, `"none"`, `"-"`, or other sentinel strings

### Field ordering
JSON field order in serialization should match dataclass/TypedDict definition
order. This makes diffs across annotators readable.

### Validation
Every output file must pass `validators.validate_full_annotation()` from the
existing pipeline OR a stage-specific validator (to be added). If validation
fails, the runner writes the file with `"_validation_errors": [...]` key
and emits a warning, but does NOT crash.
