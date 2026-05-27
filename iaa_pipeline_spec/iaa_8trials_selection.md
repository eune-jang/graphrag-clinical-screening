# IAA Evaluation Trials (n=8)

Selected from the 30 final candidates in `nsclc_protocol_candidates_selected.xlsx`,
following stratified purposive sampling across stage, line of therapy, biomarker,
modality, and special structural features (cohort, basket).

## Selected trials

| # | NCT ID | Short name | Selection cell | Rationale |
|---|---|---|---|---|
| 1 | NCT03425643 | KEYNOTE-671 | Perioperative | Pilot — EHJ/DYK already reviewed. macro_aggregate + nested_exception rich. |
| 2 | NCT02125461 | PACIFIC | ChemoRT 1L | patient_event anchor (CRT completion) — core Stage 4 test. |
| 3 | NCT03728556 | GEMSTONE-301 | Consolidation | Maint/Consol line representation. Modern PHASE3. |
| 4 | NCT02075840 | ALEX | Metastatic 1L | ALK rearrangement — variant_type=rearrangement. TKI modality. |
| 5 | NCT01295827 | KEYNOTE-001 | Metastatic 2L+ | Multi-cohort PHASE1 — cohort_scope detection (Part F-1 etc.). |
| 6 | NCT02474355 | ASTRIS | Metastatic 2L+ | EGFR T790M — variant_notation=protein. Real-world. |
| 7 | NCT05756153 | GFH925+cetuximab | Advanced 1L | KRAS G12C — modern driver. N=47 small-trial baseline. |
| 8 | NCT02912949 | eNRGy | Driver: NRG1 | Basket trial (is_basket=1). NRG1 fusion. Bispecific Ab. |

## Stratification

- **Stage**: Early 1 · LocAdv 2 · Advanced 1 · Metastatic 4
- **Line**: 1L 4 · 2L+ 2 · Maint/Consol 1 · Not specified 1
- **Biomarker**: PD-L1 4 · EGFR 1 · ALK 1 · KRAS 1 · NRG1 1
- **Modality**: Chemo+IO 4 · TKI 1 · Surgery 1 · Bispecific 1 · ChemoRT/Surgery 1
- **Phase**: PHASE1 1 · PHASE1/2 1 · PHASE2 1 · PHASE3 5
- **Enrollment range**: 47 – 3,017 (median 547)
- **Basket trials**: 1

## Stage-by-stage coverage

Each trial is selected to expose specific challenges at specific stages:

| Stage | Trials that stress-test it |
|---|---|
| Stage 1 (Splitting) | KEYNOTE-671 (macro_aggregate, nested_exception), KEYNOTE-001 (cohort_scope), eNRGy (basket) |
| Stage 2 (Category/Relation) | ASTRIS (REQUIRES_BIOMARKER + REQUIRES_TREATMENT), KEYNOTE-671 (E5 EXCLUDES + INCLUDES_EXCEPTION) |
| Stage 3 (Preferred name) | ALEX (ALK rearrangement), ASTRIS (EGFR T790M), GFH925 (KRAS G12C), eNRGy (NRG1 fusion) — **4 variant types covered** |
| Stage 4 (Constraints) | PACIFIC (patient_event anchor), KEYNOTE-001 (cohort-specific timing), KEYNOTE-671 (within X days) |
| Stage 5 (Alternative) | KEYNOTE-671 (E5 carve-out), PACIFIC (CRT timing exceptions) |

## Cross-cutting (9-class error_type)

All 8 trials contribute to error_type κ measurement. Expect highest variation in:
- N-NAME (preferred_name disagreement) — concentrated in ALEX, ASTRIS, GFH925, eNRGy
- P-QUALIFIER (drug_class_type, condition_qualifier) — concentrated in KEYNOTE-671, ASTRIS
- S-SPLIT (splitting decision) — concentrated in KEYNOTE-001, KEYNOTE-671

## Pre-flight checklist

Before annotators begin:

- [ ] Pull eligibility criteria from AACT for all 8 trials
- [ ] Verify each trial has both inclusion and exclusion criteria (some old trials may be sparse)
- [ ] Confirm criterion count per trial (target: 15-40 each; if outliers, reconsider)
- [ ] Build `8trials_input.json` in Stage1Input schema
- [ ] Run Stage 1 LLM pipeline → cache LLM outputs
- [ ] Annotators receive ONLY the criterion texts (no LLM output) for Phase 1 splitting annotation

## Possible substitutions

If issues arise during criterion extraction:

- **ASTRIS too sparse** (real-world study, may have minimal criteria) → swap with NCT00091663 (Tarceva, EGFR, PHASE3, N=5000)
- **GFH925 too narrow** (KRAS G12C specific, small N) → swap with another Advanced 1L candidate from the 30
- **KEYNOTE-001 too complex** (multi-cohort Phase 1, criteria may be very long) → swap with NCT00730639 (nivolumab Phase 1, also multi-cohort)
