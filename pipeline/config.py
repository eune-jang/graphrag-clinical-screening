"""
Pipeline configuration.
Model assignments, schema paths, enum definitions, and gap-handling rules.

Path convention:
  This file lives at:  <project_root>/pipeline/config.py
  AACT data at:        <project_root>/data/external/aact/
  Results output at:   <project_root>/pipeline/output/
  Prompts at:          <project_root>/pipeline/prompts/
  Schema at:           <project_root>/pipeline/schema/
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
PIPELINE_DIR = Path(__file__).parent
PROJECT_ROOT = PIPELINE_DIR.parent
# NOTE: SCHEMA_PATH is presently unused (grep shows zero call sites). The
# v1.2.1 JSON is kept as a historical reference; the v1.2.2 enum source of
# truth lives in this file (config.py). A canonical v1.2.2 JSON will be
# generated when Stage 3 IAA work needs JSON Schema validation downstream.
SCHEMA_PATH = PIPELINE_DIR / "schema" / "ontology_v1.2.1.json"
PROMPTS_DIR = PIPELINE_DIR / "prompts"
OUTPUT_DIR = PIPELINE_DIR / "output"
EXAMPLES_PATH = PROMPTS_DIR / "examples.json"
AACT_DIR = PROJECT_ROOT / "data" / "external" / "aact"

# ── Model assignments ──────────────────────────────────────────────────
# Provider is auto-detected from model name prefix:
#   "gpt-*" or "o3*" → OpenAI
#   "claude-*"       → Anthropic
#
# Presets: switch by uncommenting one block.

# ── Preset A: GPT-4.1 hybrid (cost-optimized, ~$4-5 sync / ~$2-3 batch)
MODELS = {
    "prompt_1": "gpt-4.1-mini",       # Splitting — pattern matching, Mini 충분
    "prompt_2": "gpt-4.1-mini",       # Category/Relation — enum classification
    "prompt_3": "gpt-4.1",            # Preferred name — 도메인 지식 필요
    "prompt_4": "gpt-4.1-mini",       # Constraint — 숫자/시간 추출
    "prompt_5": "gpt-4.1",            # alternative_constraint — 복합 구조
}

# ── Preset B: GPT-4.1 전체 (~$10 sync / ~$5 batch)
# MODELS = {
#     "prompt_1": "gpt-4.1",
#     "prompt_2": "gpt-4.1",
#     "prompt_3": "gpt-4.1",
#     "prompt_4": "gpt-4.1",
#     "prompt_5": "gpt-4.1",
# }

# ── Preset C: Claude Sonnet 전체 (~$36 sync / ~$18 batch)
# MODELS = {
#     "prompt_1": "claude-sonnet-4-5-20250514",
#     "prompt_2": "claude-sonnet-4-5-20250514",
#     "prompt_3": "claude-sonnet-4-5-20250514",
#     "prompt_4": "claude-sonnet-4-5-20250514",
#     "prompt_5": "claude-sonnet-4-5-20250514",
# }

# ── Preset D: Claude Sonnet + Opus P5 (~$38 sync / ~$19 batch)
# MODELS = {
#     "prompt_1": "claude-sonnet-4-5-20250514",
#     "prompt_2": "claude-sonnet-4-5-20250514",
#     "prompt_3": "claude-sonnet-4-5-20250514",
#     "prompt_4": "claude-sonnet-4-5-20250514",
#     "prompt_5": "claude-opus-4-6-20250414",
# }

MAX_RETRIES = 2          # per-prompt LLM retry on validation failure
LLM_TEMPERATURE = 0.0   # deterministic for annotation reproducibility
LLM_MAX_TOKENS = 4096

# ── Schema enum definitions (single source of truth) ──────────────────

SEMANTIC_CATEGORIES = {
    "condition", "treatment_history", "observation", "performance_status",
    "biomarker", "comorbidity", "demographic", "imaging",
    "comedication", "procedural_fitness",
}

RELATION_TYPES = {
    "REQUIRES_CONDITION", "REQUIRES_TREATMENT", "REQUIRES_BIOMARKER",
    "REQUIRES_STATUS", "REQUIRES_PROCEDURE",
    "EXCLUDES_CONDITION", "EXCLUDES_TREATMENT", "EXCLUDES_PROCEDURE",
    "EXCLUDES_COMEDICATION", "EXCLUDES_STATUS",
    "HAS_VALUE", "HAS_TEMPORAL", "INCLUDES_EXCEPTION",
}

CONCEPT_SUBTYPES = {"Condition", "Drug", "Observation", "Procedure", "Biomarker", "Stage"}

SPLITTING_DECISIONS = {"composite_split", "macro_aggregate", "nested_exception", "none"}

CHILD_LOGIC = {"AND", "OR"}  # v1.2.2: XOR removed (stress test 0 occurrence in 30 trials)

VARIANT_TYPES = {
    "mutation", "rearrangement", "fusion", "deletion", "insertion", "expression",
}
# v1.2.2 removed: amplification, methylation, unknown
# Affected production cases (5 total, all in non-IAA trials):
#   NCT01884285 — amplification 1, unknown 3
#   NCT03219268 — amplification 1
# Reprocess when those trials enter scope (e.g., 22 follow-up corpus).

## variant_notation: kept stripped (v1.2.2 spec activates it with 5 enum values
## protein/cdna/genomic/exon_level/wildcard; revisit when Stage 3 IAA work begins).

OPERATORS = {"≤", "<", "=", "≥", ">", "within"}

DIRECTIONS = {"before", "after", "within", "since"}

ANCHOR_TYPES = {"trial_event", "patient_event", "unspecified"}

## strictness: deferred to v1.3 (insufficient real-world usage across 30 trials)

EXCEPTION_TYPES = {
    "condition_carveout", "procedure_carveout", "drug_carveout",
    "status_carveout",
}

BIOMARKER_STATUSES = {"positive", "negative", "wild_type", "unknown", "equivocal"}

DRUG_CLASS_TYPES = {"explicit_list", "closed_class", "open_mechanism_class"}

# ── Gap-handling: relation_type → allowed RelationProperties whitelist ─

RELATION_PROPERTY_WHITELIST: dict[str, set[str]] = {
    "REQUIRES_CONDITION":  {"certainty", "temporal", "condition_qualifier"},
    "REQUIRES_TREATMENT":  {"temporal", "drug_class_basis", "drug_class_type", "line_of_therapy",
                            "treatment_setting", "treatment_modality"},
    "REQUIRES_BIOMARKER":  {"status", "assay_method", "clinical_category", "temporal"},
    "REQUIRES_STATUS":     {"status", "equivalent_status", "evidence_methods", "scale",
                            "anchor_event", "operational_definition"},
    "REQUIRES_PROCEDURE":  {"role", "scope", "scope_qualifier", "treatment_modality"},
    "EXCLUDES_CONDITION":  {"certainty", "temporal", "condition_qualifier"},
    "EXCLUDES_TREATMENT":  {"temporal", "drug_class_basis", "drug_class_type", "line_of_therapy",
                            "treatment_setting", "treatment_modality"},
    "EXCLUDES_PROCEDURE":  {"temporal", "scope", "scope_qualifier"},
    "EXCLUDES_COMEDICATION": {"condition_qualifier", "drug_class_basis"},
    "EXCLUDES_STATUS":     {"status", "operational_definition", "anchor_event"},
    "HAS_VALUE":           {"operator", "value", "unit", "scale", "measurement_method",
                            "equivalence_group_id", "equivalence_group_logic",
                            "alternative_constraint"},
    "HAS_TEMPORAL":        {"operator", "value", "unit", "anchor", "direction", "anchor_type",
                            "forward_extending", "equivalence_group_id", "equivalence_group_logic",
                            "alternative_constraint"},
    "INCLUDES_EXCEPTION":  {"exception_type", "exception_qualifier"},
}

# ── Gap-handling: fields to strip from LLM output ─
LLM_OUTPUT_STRIP_FIELDS = {
    "is_negation",       # issue #4: prompt_2 output, not in schema
    "value_type",        # issue #6: prompt_4 "computed", not in schema
    "rationale",         # prompt-internal reasoning, not stored
    "confidence",        # prompt-level confidence, stored on CriterionSpan only
    "notes",             # prompt-level notes, not in schema Relation
    "review_reason",     # pipeline-internal, not in schema
    "needs_human_review",# pipeline-internal flag
    "strictness",        # deferred to v1.3: insufficient real-world usage
    "variant_notation",  # v1.2.2 activates it, but kept stripped here until Stage 3 IAA work
    "t_descriptor",      # deferred to v1.3: belongs in Layer 3, not annotation
    "n_descriptor",      # deferred to v1.3: belongs in Layer 3, not annotation
    "m_descriptor",      # deferred to v1.3: belongs in Layer 3, not annotation
}