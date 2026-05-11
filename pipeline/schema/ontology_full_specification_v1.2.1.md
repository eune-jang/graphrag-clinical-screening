# 4-Layer Clinical Trial Screening Ontology — v1.2.1 Micro-Update Patch

**Version**: 1.2.1 (micro-update patch)
**Base version**: v1.2 (`ontology_full_specification_v1.2.md`)
**Change date**: 2026-05-05
**Change motivation**: 6-trial schema stress test (47 criteria, 58 patterns, 47 issues identified) revealed concentrated representational gaps in 6 areas. This micro-update addresses high-severity bottleneck issues while preserving full backward compatibility with v1.2 instances.

**Scope**: 6 schema additions (4 new properties, 2 enum extensions). All other v1.2 specifications unchanged. Backward compatibility: all v1.2 annotations are valid v1.2.1 annotations without modification.

**Out-of-scope**: 12 additional issues identified during stress test are deferred to guideline conventions (`annotation_guideline_v0.1.md`) or v1.3 schema iteration. See Section 4 for deferred items.

---

## Changelog (v1.2 → v1.2.1)

This patch adds 6 schema elements to address bottleneck issues identified during the 6-trial stress test. Each addition is justified by **observed occurrences** across multiple trials, not anticipated patterns.

| # | Issue ID | Element | Type | Affected stages | Occurrences |
|---|---|---|---|---|---|
| 1 | I006 | `Criterion.child_logic` | New property | Stage B (Splitting) | 4 |
| 2 | I008+I016+I037 | `Concept:Biomarker.variant_type` enum + `variant_notation` enum | New properties + enums | Stages F, G | 5 |
| 3 | I022 | `HAS_TEMPORAL.anchor_type` distinction | New property | Stage J | 4 |
| 4 | I030 | `strictness` property (multi-relation) | New property | Stages I, J, all REQUIRES_* | 6 |
| 5 | I036 | `Criterion.cohort_scope` | New property | Stage B (Splitting) | 5 |
| 6 | I040 | `INCLUDES_EXCEPTION.exception_type` enum extension (`requirement_waiver`) | Enum extension | Stage E | 2 |

All changes are **additive and optional**. Existing v1.2 annotations remain valid without modification.

---

## 1. New Property: `Criterion.child_logic`

### 1.1 Motivation

Composite-split criteria (parent_role: composite_split) involve a parent criterion with 2 or more child sub-criteria. The semantics of how children combine — AND (all children must hold) vs OR (any child sufficient) — was not explicitly representable in v1.2.

The default rule from v1.2 guideline convention was:
- `inclusion` criterion → AND default
- `exclusion` criterion → OR default

However, 4 cases observed during stress test violate this default:

| Case | Default | Actual | Source |
|---|---|---|---|
| SEQUOIA I1 | AND (inclusion) | OR (3 alternative confirmation paths) | NCT02923921_I1 |
| ALEX E3 | OR (exclusion) | OR — but explicit (3 alternative liver disease patterns) | NCT02075840_E3 |
| ALEX E7 | OR (exclusion) | OR — explicit | NCT02075840_E7 |
| AURA3 E1 | OR (exclusion) | OR — explicit (7 sub-treatments) | NCT02151981_E1 |

The first case (SEQUOIA I1) is a genuine counterexample to the default rule: an inclusion criterion with OR-semantics children. The remaining 3 are exclusion criteria with explicit OR — non-violating but where explicit specification removes ambiguity for downstream reasoning.

### 1.2 Specification

```
Criterion {
  ...existing v1.2 properties...,
  child_logic?: enum  // NEW (optional)
}
```

**Enum values**:
- `AND` — All children must hold (parent satisfied iff all children satisfied)
- `OR` — Any child sufficient (parent satisfied iff any child satisfied)
- `XOR` — Exactly one child holds (rare, included for completeness)

**Default behavior**:
- If `child_logic` omitted, apply v1.2 default rule (inclusion=AND, exclusion=OR)
- If `child_logic` specified, override default

**Applicability**: Only meaningful when `parent_role` ∈ {`composite_split`, `macro_aggregate`}. For `nested_exception_parent`, child_logic is irrelevant (exception relations are unidirectional carve-outs from parent target).

### 1.3 Annotator guidance

Annotators should explicitly specify `child_logic` when:
- The semantics deviate from the default (e.g., SEQUOIA I1 inclusion-OR)
- The protocol text contains explicit "or" / "either" / "any of the following" connectives between children
- Ambiguity exists that would benefit downstream reasoning clarity

Annotators may omit `child_logic` when:
- Default behavior matches intent (most macro_aggregate cases — adequate organ function = AND)
- A single child criterion exists (no logic decision needed)

---

## 2. New Properties: `Concept:Biomarker.variant_type` and `variant_notation`

### 2.1 Motivation

The first specific biomarker-driven inclusion criteria appeared in ALEX (ALK rearrangement) and AURA3 (EGFR T790M, L858R, L861Q, G719X, Ex19del). These exposed three distinct dimensions of variant representation that v1.2 conflates:

1. **Molecular variant type**: mutation, rearrangement, fusion, expression, amplification, deletion, etc.
2. **Notation level**: protein-level (L858R), cDNA (c.2369C>T), genomic (g.55259515T>G), exon-level (Ex19del), wildcard (G719X)
3. **Clinical category**: TKI-sensitive, TKI-resistant, response-predictive (separate from variant_type)

The third dimension (clinical category) is deferred to guideline convention (Section 4). The first two are formalized here.

### 2.2 Specification

Concept:Biomarker (Layer 3) gains two enum properties:

```
Concept:Biomarker {
  ...existing v1.2 properties...,
  variant_type?: enum,        // NEW
  variant_notation?: enum     // NEW
}
```

**`variant_type` enum**:
- `mutation` — point mutation (single nucleotide / amino acid substitution)
- `rearrangement` — chromosomal rearrangement (gene fusion partners or translocation)
- `fusion` — specific gene fusion product (subset of rearrangement)
- `deletion` — deletion variant (genomic, exon-level, or amino acid)
- `insertion` — insertion variant
- `amplification` — copy number amplification
- `expression` — gene/protein expression level (for biomarkers like PD-L1)
- `methylation` — epigenetic methylation status
- `unknown` — type not specified in protocol

**`variant_notation` enum** (level at which variant is expressed in protocol text):
- `protein` — protein-level (e.g., "L858R", "p.Leu858Arg")
- `cdna` — cDNA-level (e.g., "c.2369C>T")
- `genomic` — genomic-level (e.g., "g.55259515T>G")
- `exon_level` — exon-level macro-class (e.g., "Ex19del", "exon 19 deletion")
- `wildcard` — position-pattern with any-residue wildcard (e.g., "G719X")
- `class_level` — broad variant class (e.g., "any sensitizing mutation")

### 2.3 Cross-reference to relation properties

**`REQUIRES_BIOMARKER.variant`** (existing v1.2 property) holds the criterion-specific variant string. The new `Concept:Biomarker.variant_type` and `variant_notation` properties belong to the Biomarker concept node and describe the variant's molecular and notational characteristics.

For protocols expressing the same biomarker at multiple notation levels (e.g., AURA3 I7 enumerates four EGFR variants at three different notation levels), each variant maps to a separate Concept:Biomarker node with its own `variant_type` + `variant_notation` properties.

### 2.4 Wildcard and macro-class examples

Wildcard variants (e.g., "G719X" denoting any amino acid at position 719):
```
Concept:Biomarker {
  gene_symbol: "EGFR",
  variant: "G719X",
  variant_type: "mutation",
  variant_notation: "wildcard"
}
```
Downstream EMR matching expands wildcard to specific instances (G719A, G719S, G719C) via Layer 4 lexical resources.

Macro-class variants (e.g., "Ex19del" covering multiple specific deletions):
```
Concept:Biomarker {
  gene_symbol: "EGFR",
  variant: "Exon 19 deletion",
  variant_type: "deletion",
  variant_notation: "exon_level"
}
```

EMR matching identifies specific HGVS deletions (c.2235_2249del, c.2236_2250del, etc.) as members of this macro-class via curated equivalence tables.

---

## 3. New Property: `HAS_TEMPORAL.anchor_type`

### 3.1 Motivation

HAS_TEMPORAL.anchor (existing v1.2 property) is treated as a free-form string. Stress test revealed two distinct types of anchor with different downstream semantics:

| Anchor type | Examples | Resolution |
|---|---|---|
| Trial-level standard event | "Randomization", "first_dose", "informed_consent", "study_treatment_start" | Same anchor for all patients in the trial |
| Patient-specific historical event | "first_EGFR_TKI_treatment_start" (AURA3 E1e), "documented_PD_on_1L_EGFR_TKI" (AURA3 I8d), "completion_of_concurrent_CRT" (PACIFIC I5), "completion_of_most_recent_therapy" (PACIFIC I6b) | Resolved per-patient from EMR chart |

The semantic distinction matters for EMR matching strategy:
- Trial-level events: deterministic (e.g., randomization date is recorded in the trial system)
- Patient-specific events: require chart parsing or structured data lookup, may be unavailable

### 3.2 Specification

```
HAS_TEMPORAL {
  ...existing v1.2 properties (operator, value, unit, anchor, direction)...,
  anchor_type?: enum   // NEW
}
```

**`anchor_type` enum**:
- `trial_event` — Trial-level standard event (Randomization, first_dose, etc.)
- `patient_event` — Patient-specific historical event requiring chart resolution
- `procedure_event` — Specific procedure event (e.g., "screening_biopsy", "thoracic_radiation_completion")
- `unspecified` — Anchor type not classified (default if omitted)

**Default behavior**: If `anchor_type` omitted, downstream consumers should default to `unspecified` and not assume `trial_event`. This is intentional — it surfaces the ambiguity rather than silently assuming the safer interpretation.

### 3.3 Annotator guidance

Annotators should specify `anchor_type` when:
- The anchor refers to a patient-specific event that requires chart-level resolution
- The anchor refers to a procedure-specific event distinct from the trial schedule

Annotators may omit `anchor_type` when:
- The anchor is a standard trial-level event listed above
- A simpler temporal pattern applies (e.g., "within 14 days of randomization" — anchor=Randomization is implicitly trial_event)

### 3.4 Cross-reference to issue I047 (dose-dependent conditional washout)

Some anchors involve a precondition on prior treatment dose (e.g., KEYNOTE-001 I1_F1f: "if prior thoracic RT > 30 Gy, then ≥26 weeks washout from RT completion"). These remain represented via `composite_split` with `applies_when` qualifier (guideline convention). The `anchor_type=procedure_event` value applies to the temporal anchor itself, not the conditional structure.

---

## 4. New Property: `strictness`

### 4.1 Motivation

The strictness of an inclusion or exclusion requirement was implicit in v1.2 (all criteria assumed strict). PACIFIC stress test revealed three distinct strictness levels in protocol text:

| Level | Example | Source |
|---|---|---|
| Required (default) | All standard inclusion/exclusion criteria | v1.2 default |
| Encouraged | "Sites are encouraged to adhere to mean lung dose <20Gy" | PACIFIC I4g (5 organ-dose constraints) |
| Optional | "Recent biopsy is an optional requirement" | PACIFIC I6b |

These map to different eligibility-decision behaviors:
- Required: violation → exclusion
- Encouraged: violation → not exclusion, but flag for site adherence monitoring
- Optional: not specified → not violation; specified → use as enrichment data

### 4.2 Specification

A new optional property `strictness` is added to the following relations:
- HAS_VALUE
- HAS_TEMPORAL
- REQUIRES_CONDITION, REQUIRES_TREATMENT, REQUIRES_PROCEDURE, REQUIRES_BIOMARKER, REQUIRES_STATUS

```
HAS_VALUE / HAS_TEMPORAL / REQUIRES_* {
  ...existing v1.2 properties...,
  strictness?: enum   // NEW
}
```

**`strictness` enum**:
- `required` — Standard requirement, violation excludes patient (default if omitted)
- `encouraged` — Site/operational guidance, violation does not exclude
- `optional` — Specified-if-available, absence does not exclude
- `discretionary` — Investigator judgment determines applicability

**Default behavior**: If `strictness` omitted, treat as `required`. This preserves backward compatibility (v1.2 annotations without strictness are correctly interpreted as required).

### 4.3 Applicability to EXCLUDES_* relations

EXCLUDES_* relations are inherently strict (an exclusion is by definition required). Adding `strictness` to EXCLUDES_* relations is semantically incoherent — there is no "encouraged exclusion." Therefore strictness applies only to REQUIRES_* and constraint relations (HAS_VALUE, HAS_TEMPORAL).

### 4.4 Annotator guidance

Annotators should specify `strictness` when:
- Protocol text contains explicit hedging ("encouraged", "where possible", "should be", "is preferred")
- An "optional" or "if available" language modifies a requirement
- The criterion is part of guidance (e.g., NCCN/ESMO adherence) rather than strict eligibility

Annotators may omit `strictness` when:
- Standard inclusion/exclusion language ("must have", "patients with", "exclude if")
- No hedging or optionality marker present

### 4.5 Cross-reference to NCCN/ESMO adherence

PACIFIC I4 includes "Where possible, chemotherapy regimens should be given according to NCCN Guidelines or ESMO Guidelines." This is `strictness=encouraged` rather than `required` — sites are guided but not strictly required.

---

## 5. New Property: `Criterion.cohort_scope`

### 5.1 Motivation

KEYNOTE-001 introduced multi-cohort/basket trial structure where the same trial contains multiple sub-cohorts (Part A, B, C, D, F-1, F-2, F-3) with cohort-specific inclusion criteria. v1.2 had no mechanism to express which cohort a criterion applies to.

Observed cases (5 of 5 KEYNOTE-001 targeted criteria):
- I1_F1: applies to Part F-1 only
- I1_F2F3: applies to Parts F-2 and F-3
- I1_Ipi_BRAF: applies to Ipilimumab-refractory cohort only
- I1_F_HistologyWaiver: applies to Parts F-1, F-2, F-3
- I2_irRC: applies to Parts B, C, D, F (not Part A)

Multi-cohort/basket trials are increasingly common in modern precision oncology. v1.2 representation forced annotators to encode cohort information in criterion_id suffixes (e.g., `NCT01295827_I1_F1`), losing structured queryability.

### 5.2 Specification

```
Criterion {
  ...existing v1.2 properties (criterion_id, type, semantic_category, parent_role, ...)...,
  cohort_scope?: array of strings   // NEW
}
```

**`cohort_scope` value**: Array of cohort identifiers. Empty array or omitted property indicates the criterion applies to all cohorts in the trial.

**Examples**:
```
Criterion (NCT01295827_I1_F1) {
  cohort_scope: ["F-1"]
}

Criterion (NCT01295827_I1_F2F3) {
  cohort_scope: ["F-2", "F-3"]
}

Criterion (NCT01295827_I1_F_HistologyWaiver) {
  cohort_scope: ["F-1", "F-2", "F-3"]
}

Criterion (NCT01295827_I2_irRC) {
  cohort_scope: ["B", "C", "D", "F"]
}
```

### 5.3 Trial-level cohort registry

Each Trial node may specify a registry of valid cohort identifiers:

```
Trial {
  ...existing properties...,
  cohorts?: array of {id: string, description: string}   // NEW (optional)
}

Example:
Trial (NCT01295827) {
  cohorts: [
    {id: "A", description: "Dose escalation, MEL or any carcinoma"},
    {id: "B", description: "MEL ipilimumab-naive or refractory"},
    {id: "C", description: "NSCLC after 2 prior systemic regimens"},
    {id: "D", description: "MEL ipilimumab-naive expansion"},
    {id: "F", description: "NSCLC PD-L1+ subgroups (F-1, F-2, F-3)"},
    {id: "F-1", description: "NSCLC treatment-naive Stage IV PD-L1+ EGFR/ALK wild"},
    {id: "F-2", description: "NSCLC PD-L1+ ≥1 prior or PD-L1- ≥2 prior"},
    {id: "F-3", description: "NSCLC PD-L1+ ≥1 prior platinum doublet"}
  ]
}
```

This is **strictly optional**. Single-cohort trials can omit both `cohort_scope` (on Criterion) and `cohorts` (on Trial).

### 5.4 Annotator guidance

Annotators should specify `cohort_scope` when:
- Protocol explicitly defines named cohorts/parts/arms with different inclusion criteria
- A criterion applies to a strict subset of trial cohorts

Annotators may omit `cohort_scope` when:
- Trial has a single cohort (most pre-2010 trials)
- Criterion applies universally to all cohorts

For backward compatibility, criterion_id suffix conventions (e.g., `_F1`, `_F2F3`) remain acceptable as redundant encoding alongside `cohort_scope`.

---

## 6. Enum Extension: `INCLUDES_EXCEPTION.exception_type`

### 6.1 Motivation

v1.2 introduced INCLUDES_EXCEPTION with three exception types: `condition_carveout`, `procedure_carveout`, `drug_carveout`. KEYNOTE-001 stress test revealed a fourth distinct type: **requirement waiver** — where a condition met by the patient waives an inclusion requirement entirely (rather than carving out a sub-set of the excluded population).

Observed cases:
- KEYNOTE-001 I1_F_HistologyWaiver (squamous): squamous histology → EGFR/ALK molecular testing waived
- KEYNOTE-001 I1_F_HistologyWaiver (KRAS+): KRAS mutation → EGFR/ALK testing waived (mutual exclusivity rationale)

Semantic distinction from carve-outs:
- **Carve-out** (existing): from a broad EXCLUDES target, certain entities are excluded from exclusion (e.g., "additional malignancy except BCC")
- **Requirement waiver** (NEW): in certain patient contexts, a REQUIRES requirement does not apply (e.g., "EGFR testing required, except squamous histology where testing is not required")

### 6.2 Specification

```
INCLUDES_EXCEPTION {
  ...existing v1.2 properties...,
  exception_type: enum   // EXTENDED (added requirement_waiver)
}
```

**Updated `exception_type` enum**:
- `condition_carveout` (existing v1.2)
- `procedure_carveout` (existing v1.2)
- `drug_carveout` (existing v1.2)
- `status_carveout` (existing v1.2 — KEYNOTE-671 E5 ihc)
- `requirement_waiver` (NEW — KEYNOTE-001 I1_F_HistologyWaiver)

### 6.3 Semantic difference at the relation level

Carve-out exceptions modify the target set of the parent relation:
```
EXCLUDES_CONDITION → "additional malignancy"      [parent relation, broad target]
INCLUDES_EXCEPTION → "BCC"                         [carve-out, narrows the EXCLUDES set]
                                                   exception_type: condition_carveout
```

Requirement-waiver exceptions modify the applicability of the parent relation entirely:
```
REQUIRES_BIOMARKER → "EGFR/ALK molecular testing"  [parent relation, requirement]
INCLUDES_EXCEPTION → "squamous histology context"   [waiver, removes applicability]
                                                    exception_type: requirement_waiver
                                                    exception_qualifier: {
                                                      applies_when: "predominantly_squamous_histology"
                                                    }
```

The waiver-style exception_qualifier uses `applies_when` to specify the patient context that triggers the waiver.

### 6.4 Annotator guidance

Annotators should use `requirement_waiver` when:
- Protocol explicitly states a requirement is "not required" in a specific patient context
- The exception removes applicability rather than carving out a sub-set
- "Will not be required if..." or similar language present

Annotators should use existing carve-out types when:
- The exception narrows the EXCLUDES target set ("X is excluded except Y")
- The exception describes specific entities outside the exclusion scope

---

## 7. Out of Scope (Deferred to Guideline or v1.3)

12 issues identified during stress test are deferred from v1.2.1:

### 7.1 Deferred to `annotation_guideline_v0.1.md` (convention-only)

| Issue | Rationale for deferral |
|---|---|
| I001 (HAS_VALUE condition_qualifier) | Low frequency (2 cases), expressible via alternative_constraint nested object |
| I002 (HAS_TEMPORAL "at" point-in-time) | Low frequency (1 case), expressible via since + value=0 |
| I003 (HAS_TEMPORAL forward-looking) | Convention via direction=after + study_period_start anchor |
| I004 (EXCLUDES_STATUS operational definition) | Low frequency (1 case), expressible via normalized_text |
| I005 (procedural_fitness target subtype) | Convention to use Concept:LabTest as broad assessment |
| I007 (equivalence_group OR vs AND) | Convention rule (OR uses equivalence_group_id, AND uses parallel relations) |
| I009 (Biomarker.variant duplication) | Convention clarification (Concept-level vs relation-level redundancy) |
| I013 (INCLUDES_EXCEPTION numeric qualifier) | Expressible via exception_qualifier object with threshold |
| I014 (Lab value reproducibility qualifier) | Convention via normalized_text |
| I024 (Compound exception_qualifier) | Convention via exception_qualifier object schema |
| I025 (line_of_therapy enum) | Convention enum in guideline (low complexity) |
| I031 (Status negation expression) | Convention via equivalent_status array expansion |
| I033 (Specialized radiation notation) | Convention via Concept:LabTest extensibility (V20, V45 as standard concepts) |
| I034 (HAS_TEMPORAL direction "before_or_concurrent") | Convention via direction=before + value=0 |
| I035 (requires_consultation qualifier) | Convention via exception_qualifier free-form |
| I038 (status=wild_type enum) | Convention enum in guideline |
| I042 (irRC scale) | Already covered by Concept:LabTest.scale property |
| I043 (2-perpendicular measurement_method) | Convention enum |
| I045 (drug-class-specific washout) | Already covered by composite_split + EXCLUDES_TREATMENT |
| I046 (order-independence qualifier) | Convention via condition_qualifier free-form |
| I047 (dose-dependent conditional washout) | Convention via composite_split + applies_when |

### 7.2 Deferred to v1.3 (future schema iteration)

| Issue | Rationale |
|---|---|
| I010 (general conditional inclusion) | Currently handled via composite_split + applies_when convention. Schema-level conditional mechanism merits v1.3 design study. |
| I011 (Stage resectability qualifier) | 2 occurrences. Convention sufficient for now. Re-evaluate after Phase 2 expansion. |
| I012 (drug class strength qualifier) | Combines with I021 (generation). Both deferred for unified `class_qualifier` object design in v1.3. |
| I019 (Biomarker clinical_category) | Convention via free-form string for now. Formal enum requires curation effort. |
| I020 (mathematical formula temporal value) | Convention via parallel HAS_TEMPORAL with group_logic=MAX. Formal formula language deferred. |
| I021 (drug generation qualifier) | Combined with I012 in v1.3. |
| I023 (Procedure scope_qualifier) | Object schema requires more examples to formalize. |
| I027 (drug regimen partner) | Convention via sibling relations. Schema-level partner edge deferred. |
| I028 (range temporal value) | Convention via two HAS_TEMPORAL. |
| I029 (HAS_VALUE tolerance) | Convention via alternative_constraint with range. |
| I032 (Concept:Stage system_version) | Pair with system property. Defer until v1.3. |
| I039 (Biomarker-conditional mandatory treatment) | Convention via composite_split + applies_when. |
| I041 (Histology-specific applicability) | Convention via condition_qualifier or population_qualifier. |
| I044 (imaging-parameter-dependent threshold) | Same family as I020. |

The deferred items are not abandoned. Their resolution via convention (annotation guideline) remains traceable; if Phase 2 validation surfaces evidence that convention is insufficient, the items can be elevated to v1.3 schema additions.

---

## 8. Backward Compatibility Statement

All v1.2 annotations are valid v1.2.1 annotations without modification. Specifically:

1. All v1.2.1 new properties are **optional** — omission means default behavior (per Section 1-6 specifications)
2. All v1.2.1 enum extensions are **additive** — existing enum values retain their meaning
3. v1.2.1 introduces no breaking changes to relation cardinality, target_subtype, or layer structure

Tools and pipelines built for v1.2 continue to function on v1.2.1 instances. Tools targeting v1.2.1 should handle absent properties gracefully (default behavior).

---

## 9. Cross-reference: Stress Test Evidence

Each v1.2.1 element's empirical justification:

| Element | Issue | Trials with occurrences | Total occurrences |
|---|---|---|---|
| `Criterion.child_logic` | I006 | KEYNOTE-671, SEQUOIA, ALEX, AURA3 | 4 |
| `Concept:Biomarker.variant_type` + `variant_notation` | I008+I016+I037 | ALEX, AURA3, KEYNOTE-001 | 5 |
| `HAS_TEMPORAL.anchor_type` | I022 | AURA3, PACIFIC | 4 |
| `strictness` | I030 | PACIFIC | 6 (5 organ-dose constraints + 1 optional biopsy) |
| `Criterion.cohort_scope` | I036 | KEYNOTE-001 | 5 |
| `INCLUDES_EXCEPTION.exception_type=requirement_waiver` | I040 | KEYNOTE-001 | 2 |

All 6 elements have ≥2 occurrences across stress-tested trials. Frequency-justified additions only.

---

## 10. Implementation Notes for Pipeline

The 6 v1.2.1 additions affect specific automation pipeline stages:

| Element | Pipeline impact |
|---|---|
| `child_logic` | Stage B (Splitting) — LLM prompt should explicitly elicit child_logic when composite_split detected |
| `variant_type` + `variant_notation` | Stage F (Target subtype) and Stage G (preferred_name) — biomarker entity normalization |
| `anchor_type` | Stage J (HAS_TEMPORAL) — LLM prompt should classify anchors into trial_event vs patient_event |
| `strictness` | Stage I, J, REQUIRES_* — LLM prompt should detect hedging language ("encouraged", "should") |
| `cohort_scope` | Stage B (Splitting) and Stage A (Criterion split) — multi-cohort trials require cohort detection in protocol parsing |
| `exception_type=requirement_waiver` | Stage E (Relation type) — LLM prompt should distinguish carve-out from waiver semantics |

These extensions enable automation but also require LLM prompts to be aware of the new fields. The annotation_guideline_v0.1 (Stage 1 operational sections) will codify the annotator decision rules that the LLM prompts mirror.

---

## Appendix A: Document Lineage

- v1.0 (initial): pre-stress-test
- v1.1 (`ontology_full_specification.md`): incorporated initial KEYNOTE-671 reference work
- v1.2 (`ontology_full_specification_v1.2.md`): 9 additions from KEYNOTE-671 + SEQUOIA reference annotation
- **v1.2.1 (this document)**: 6 additions from 6-trial schema stress test, all backward-compatible
- v1.3 (future): planned for after Phase 2 SMC validation, addressing deferred items in Section 7.2
