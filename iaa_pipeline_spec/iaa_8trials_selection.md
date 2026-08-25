# IAA Evaluation Trials (n=8)

Selected from the 30 final candidates in `nsclc_protocol_candidates_selected.xlsx`,
following stratified purposive sampling across stage, line of therapy, biomarker,
modality, and special structural features (cohort, basket).

> **⚠️ 2026-08-24 정정 — 측정 대상 8건은 아래 표의 8건과 다르다.**
>
> **KEYNOTE-671(NCT03425643)은 측정에서 제외됐다.** 이 trial은 어노테이션 워크플로우의
> **파일럿·캘리브레이션**에 사용되어 EHJ/DYK 양쪽이 이미 노출된 상태였고, blind 조건이
> 성립하지 않으므로 **사전 노출 편향을 피하기 위해 의도적으로 IAA 측정에서 뺐다.**
> 이는 3라운드 설계 원칙(기존 trial 재측정 금지 → held-out trial 사용)과 동일한 논리다.
>
> 비게 된 **Perioperative 셀은 AEGEAN(NCT03800134)으로 대체**했다 (2026-06-04, commit
> `e0da99c`). AEGEAN은 8,520건 sampling frame에는 포함돼 있었으나 47건 후보 추출 시
> 뽑히지 않았던 trial로, criteria는 AACT `eligibilities.txt` + `design_groups.txt`에서
> 직접 추출했다. 두 trial의 frame 속성은 아래와 같이 거의 일치하여 셀 수준 층화가 보존된다:
>
> | 속성 | KEYNOTE-671 (제외) | AEGEAN (대체) |
> |---|---|---|
> | Phase | PHASE3 | PHASE3 |
> | Enrollment | 797 | 825 |
> | Stage | Early (I-II) / Perioperative | Early (I-II) / LocAdv (III) / Perioperative |
> | Modality | Chemo + IO + Radiation | Chemo + IO + Radiation + Surgery |
> | Biomarker | PD-L1 | EGFR, ALK, PD-L1 |
> | Sponsor type | INDUSTRY (Merck) | INDUSTRY (AstraZeneca) |
> | Line | Mixed (1L + 2L+) | 1L (Treatment-naïve) |
>
> **실제 측정 8건** (round1/round2 각 2인 committed envelope 전수 확인, 172 aligned pairs):
> PACIFIC · GEMSTONE-301 · ALEX · KEYNOTE-001 · ASTRIS · GFH925 · eNRGy · **AEGEAN**.
> KEYNOTE-671 envelope는 0건.
>
> `iaa_8trials.txt`는 9줄(위 8건 표 + AEGEAN)이며 hosted app 드롭다운 필터용 **작업 목록**이다.
> 분석 표본과 혼동하지 말 것. 아래 표는 최초 선정 시점의 기록으로 보존한다.
> 상세·초록용 Methods 문장은 `docs/amia2027_work_summary.md` §2.3 참조.

## Selected trials

| # | NCT ID | Short name | Selection cell | Rationale |
|---|---|---|---|---|
| 1 | ~~NCT03425643~~ | ~~KEYNOTE-671~~ | Perioperative | **파일럿으로 사용 → 측정 제외** (위 정정 참조). macro_aggregate + nested_exception rich. → AEGEAN으로 대체 |
| 2 | NCT02125461 | PACIFIC | ChemoRT 1L | patient_event anchor (CRT completion) — core Stage 4 test. |
| 3 | NCT03728556 | GEMSTONE-301 | Consolidation | Maint/Consol line representation. Modern PHASE3. |
| 4 | NCT02075840 | ALEX | Metastatic 1L | ALK rearrangement — variant_type=rearrangement. TKI modality. |
| 5 | NCT01295827 | KEYNOTE-001 | Metastatic 2L+ | Multi-cohort PHASE1 — cohort_scope detection (Part F-1 etc.). |
| 6 | NCT02474355 | ASTRIS | Metastatic 2L+ | EGFR T790M — variant_notation=protein. Real-world. |
| 7 | NCT05756153 | GFH925+cetuximab | Advanced 1L | KRAS G12C — modern driver. N=47 small-trial baseline. |
| 8 | NCT02912949 | eNRGy | Driver: NRG1 | Basket trial (is_basket=1). NRG1 fusion. Bispecific Ab. |
| 9 | NCT03800134 | AEGEAN | Perioperative | **추가 2026-06-04** — KEYNOTE-671 대체. Perioperative durvalumab+chemo, PHASE3/N=825로 평행 구조. sampling frame 내, 47건 후보에는 미포함이었음. |

## Stratification

- **Stage**: Early 1 · LocAdv 2 · Advanced 1 · Metastatic 4
- **Line**: 1L 4 · 2L+ 2 · Maint/Consol 1 · Not specified 1
- **Biomarker**: PD-L1 4 · EGFR 1 · ALK 1 · KRAS 1 · NRG1 1
- **Modality**: Chemo+IO 4 · TKI 1 · Surgery 1 · Bispecific 1 · ChemoRT/Surgery 1
- **Phase**: PHASE1 1 · PHASE1/2 1 · PHASE2 1 · PHASE3 5
- **Enrollment range**: 47 – 3,017 (median 547)
- **Basket trials**: 1

> **위 분포는 KEYNOTE-671 → AEGEAN 대체 후에도 그대로 유효하다** (2026-08-24 재확인).
> 두 trial 모두 PHASE3 · Early/Perioperative · PD-L1 · Surgery 포함 · INDUSTRY이며,
> enrollment만 797 → 825로 바뀌어 range(47–3,017)와 median(547) 모두 불변이다.

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
