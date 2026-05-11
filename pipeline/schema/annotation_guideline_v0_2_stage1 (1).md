# 임상시험 환자 적격성 기준 어노테이션 가이드라인 (v0.2, Stage 1)

**Schema 버전**: v1.2.2 (`ontology_full_specification_unified_v1_2_2_ko.md`)
**도구**: INCEpTION
**Reference annotation**: KEYNOTE-671 v2 (primary), SEQUOIA v2 (supplementary)
**작성일**: 2026-05-07
**문서 단계**: Stage 1 (operational sections — 어노테이터 작업 시작 전 필독)

**v0.1 → v0.2 주요 변경** (Schema v1.2.1 → v1.2.2 반영):
- `strictness` 4-enum 제거 (v1.3으로 연기)
- `anchor_type`: 4-way → 3-way (`procedure_event` 제거, `patient_event`로 통합)
- `variant_notation`: annotator-facing에서 제거 (LLM auto-fill, read-only suggested)
- `requirement_waiver`: `exception_type` enum에서 제거 → `exception_qualifier` free-text로 흡수
- `t/n/m_descriptor`: 제거 → Layer 3에서 AJCC staging table로 자동 생성
- `original_text` → `text`로 필드명 변경 (pipeline JSON ↔ spec 정렬)

**가이드라인 scope**: 본 문서는 **어노테이터의 판단이 필요한 영역**만 다룹니다. Criterion text 분리, numeric value 추출, span offset 계산 등은 Python 파이프라인이 자동 처리하며 어노테이터는 INCEpTION에서 결과만 검수합니다. 자동화 경계는 Appendix B 참조.

---

## 1. Introduction & Scope

### 1.1 본 가이드라인의 목적

본 가이드라인은 임상시험 적격성 기준(eligibility criteria)을 4-Layer Clinical Trial Screening Ontology (Schema v1.2.2)에 따라 **두 명의 어노테이터가 일관되게 어노테이션**하기 위한 룰 집합입니다.

워크플로우는 LLM-assisted annotation: LLM이 1차 어노테이션을 생성하고, 어노테이터 두 명이 INCEpTION에서 독립적으로 검수/수정한 후, adjudicator가 불일치를 해소합니다.

### 1.2 어노테이터의 역할

LLM이 1차 처리한 후 어노테이터가 검수해야 할 영역은 다음과 같습니다 (자동화 경계 분석 결과 기반):

| 어노테이터 작업 영역 | LLM 신뢰도 | 검수 강도 |
|---|---|---|
| **Splitting 결정** (composite/macro/nested) | 보통 | 전수 검수 |
| **Semantic_category 결정** | 높음 | Sample 검수 + flagged exception |
| **Relation type 결정** | 높음 | Sample 검수 + flagged exception |
| **Target subtype 결정** | 매우 높음 | Sample 검수만 |
| **Preferred_name 추출** | 보통 | 약어/추상 클래스만 검수 |
| **Non-standard HAS_TEMPORAL** (anchor_type, formula) | 낮음 | 전수 검수 |
| **alternative_constraint 표현** | 매우 낮음 | **전수 검수, 직접 작성 우선** |

자동 처리되는 영역 (어노테이터가 판단할 필요 없음):
- Criterion text 분리
- HAS_VALUE의 표준 numeric pattern (operator, value, unit)
- HAS_TEMPORAL의 표준 시간 표현 (직접 명시된 numeric + anchor)
- Span offset 계산
- INCEpTION JSON export
- Schema 위반 검출

### 1.3 적용 범위

- **대상 도큐먼트**: ClinicalTrials.gov 등록 임상시험 프로토콜의 inclusion/exclusion criteria 섹션
- **대상 도메인**: NSCLC (primary), PDAC (supplementary)
- **단계**: Phase 1 (ontology 및 알고리즘 개발 단계)
- **언어**: 영어 원문 어노테이션. 한국어 EMR 매핑은 별도 작업.

### 1.4 산출물

각 criterion에 대해 INCEpTION에 다음 정보를 입력합니다:
1. CriterionSpan (criterion text 전체 또는 sub-criterion 단위)
2. ConceptMention (criterion text 내 entity surface forms)
3. CriterionSpan ↔ ConceptMention 사이의 typed relations
4. 각 relation의 properties

---

## 2. Annotation Workflow

### 2.1 LLM-assisted annotation pipeline

3단계 워크플로우:

**Stage A — LLM pre-annotation**
- 사전 정의된 multi-stage 프롬프트로 LLM이 1차 어노테이션 생성
- 출력은 INCEpTION import 가능한 JSON 형식
- 어노테이터에게 노출되기 전 자동 schema validation 통과

**Stage B — Independent dual annotation**
- 어노테이터 A와 B가 **서로의 작업을 보지 않고** 각각 LLM 출력을 검수/수정
- 두 어노테이터는 **같은 LLM 출력**을 입력으로 받음
- 작업 단위: 한 trial 단위 (criterion이 아닌 trial 단위로 배정)

**Stage C — Adjudication**
- 두 어노테이터의 결과를 INCEpTION의 curation mode에서 비교
- 불일치 항목을 adjudicator(Eunhye)가 검토하여 합의 또는 결정
- 임상적 판단이 필요한 케이스는 oncologist 자문

### 2.2 Anchoring bias 통제 — Blind subset

LLM-assisted annotation의 가장 큰 위험은 **anchoring bias** (어노테이터가 LLM 출력에 동조). 이를 통제하기 위해:

- 전체 trial의 **15-20%를 blind subset**으로 선정
- Blind subset에 대해서는 LLM 출력 없이 **from scratch annotation** 수행
- 두 어노테이터가 동일 trial을 from scratch로 어노테이션
- LLM-assisted 결과와 blind 결과를 비교하여 systematic bias 측정 및 보고

Blind subset 선정 시점: 본 어노테이션 작업 시작 전 무작위 추출. 어노테이터는 어느 trial이 blind set인지 사전에 모름. Adjudicator만 식별 가능.

### 2.3 Calibration phase (작업 시작 전 필수)

본격 작업 전 calibration:
1. 어노테이터 두 명이 reference annotation의 11개 criterion (KEYNOTE-671 calibration subset) 학습
2. 동일 11개 criterion을 from scratch로 작성 (LLM 출력 없이, reference 직접 보지 않고)
3. Reference와 비교하여 calibration kappa 측정
4. **κ ≥ 0.7 도달 시 본 작업 시작**, 미달 시 가이드라인 재학습 및 재시도

### 2.4 IAA 측정 시점

- **Calibration kappa**: 본 작업 전 (κ ≥ 0.7 gating)
- **Working IAA**: 본 작업 중 매 5 trial마다 중간 측정 (drift 감지)
- **Final IAA**: 모든 작업 완료 후 (paper에 보고)

### 2.5 INCEpTION 작업 환경

각 어노테이터에게 부여된 작업:
1. INCEpTION에 로그인
2. 배정된 trial 열기 — LLM 1차 어노테이션이 미리 적재되어 있음
3. Document 화면에서 LLM 출력을 criterion 단위로 검수
4. 잘못된 어노테이션은 수정/삭제, 누락된 어노테이션은 추가
5. 작업 완료 후 status를 "Annotation complete"으로 변경
6. INCEpTION 자동 schema validation 통과 확인

---

## 3. Schema Quick Reference (어노테이터용 cheat sheet)

본 섹션은 어노테이터가 작업 중 빠르게 참조할 수 있는 schema 요약입니다. 상세 정의는 `ontology_full_specification_unified_v1_2_2_ko.md` 참조.

### 3.1 Semantic Category 10개

각 criterion은 정확히 1개의 semantic_category에 속합니다 (sub-criterion으로 분해된 경우 각각).

| Category | 정의 | 대표 키워드 | 예시 |
|---|---|---|---|
| `condition` | 진단/질환 요구 또는 배제 | "diagnosis of", "history of", "with X disease" | "Metastatic PDAC", "NSCLC" |
| `treatment_history` | 과거 치료 이력 (drug 기준) | "prior therapy", "previously treated", "received" | "Prior gemcitabine" |
| `lab_value` | 정량 검사 수치 요구 | "ANC ≥", "bilirubin ≤", lab name + numeric | "Platelets ≥ 100×10⁹/L" |
| `performance_status` | 활동 능력 평가 | "ECOG", "Karnofsky" | "ECOG 0-1" |
| `biomarker` | 분자/유전자 marker 상태 | gene name, mutation, expression level | "EGFR Ex19del", "PD-L1+" |
| `comorbidity` | 동반 질환 (배제 위주) | "history of X", "active X infection" | "Active autoimmune disease" |
| `demographic` | 인구학적 특성 | "age", "male/female", "weight" | "Age ≥ 18" |
| `imaging` | 영상 검사 / RECIST / irRC | "RECIST", "irRC", "CT", "MRI", "measurable disease" | "Measurable disease per RECIST" |
| `comedication` | 동시 복용 약물 | "concurrent", "concomitant", "currently taking" | "On Coumadin" |
| `procedural_fitness` | 시술/수술 적격성 | "able to undergo", "fit for surgery", "operable" | "Able to undergo surgery" |

**판단 룰**: 한 criterion이 복수 category에 걸치면 **분해(splitting)** 우선 검토 (Section 4.1). 분해 어려우면 **dominant category** 선택. 모호하면 adjudicator 표시.

### 3.2 Cross-layer Relation 결정 트리

**Step 1**: criterion type 확인 (inclusion vs exclusion)

**Step 2**: 의미 유형 결정

```
inclusion criterion:
├── 진단 요구            → REQUIRES_CONDITION
├── 치료 이력 요구        → REQUIRES_TREATMENT
├── biomarker 상태 요구   → REQUIRES_BIOMARKER
├── 검사 결과 status 요구 → REQUIRES_STATUS
└── 절차 evidence 요구    → REQUIRES_PROCEDURE

exclusion criterion:
├── 진단 배제            → EXCLUDES_CONDITION
├── 치료 이력 배제        → EXCLUDES_TREATMENT
├── 절차 이력 배제        → EXCLUDES_PROCEDURE
├── 병용약물 배제        → EXCLUDES_COMEDICATION
└── 상태 배제            → EXCLUDES_STATUS

constraint (inclusion/exclusion 공통):
├── 수치 제약            → HAS_VALUE
├── 시간 제약            → HAS_TEMPORAL
└── 예외 carve-out       → INCLUDES_EXCEPTION
```

**Step 3**: 한 criterion에 여러 relations이 동시 적용 가능 (예: REQUIRES_TREATMENT + HAS_TEMPORAL).

### 3.3 Schema v1.2.2 properties (필수 숙지)

v1.2.2에서 어노테이터가 직접 적용해야 할 elements:

| Property | 위치 | 사용 시기 |
|---|---|---|
| `Criterion.child_logic` | composite_split 부모 criterion | AND/OR 명시가 필요할 때 (특히 inclusion-OR 또는 명시적 "or" 연결) |
| `Concept:Biomarker.variant_type` | biomarker 노드 | 모든 biomarker criterion에 명시 (mutation/rearrangement/expression 등) |
| `HAS_TEMPORAL.anchor_type` | 시간 anchor | trial_event / patient_event / unspecified 3-way 구분 |
| `Criterion.cohort_scope` | 모든 Criterion (basket trial) | multi-cohort trial에서 cohort-specific criterion |
| `INCLUDES_EXCEPTION.exception_type` | INCLUDES_EXCEPTION | 4-enum: condition_carveout / procedure_carveout / drug_carveout / status_carveout |

**v1.2.2에서 제거된 elements** (어노테이터가 입력할 필요 없음):
- ~~`strictness`~~: v1.3으로 연기. 30개 trial annotation 후 실제 사용 빈도로 재검토.
- ~~`variant_notation`~~: LLM이 자동 할당. INCEpTION에서 read-only suggested로 표시. 어노테이터는 검수만.
- ~~`requirement_waiver`~~: `exception_qualifier` free-text에 `"applies_when: ..., waiver_type: requirement_exempt"`로 기록.
- ~~`t/n/m_descriptor`~~: Layer 3 구축 시 AJCC staging table로 자동 생성. Annotation 단계에서 불필요.

### 3.4 INCEpTION Layer/Feature 매핑 요약

| 작업 | INCEpTION 작업 |
|---|---|
| Criterion 마킹 | CriterionSpan으로 텍스트 범위 선택 + features 입력 |
| Sub-criterion 부모-자녀 관계 | IS_PART_OF relation (CriterionSpan → CriterionSpan) |
| Entity surface form 마킹 | ConceptMention으로 텍스트 범위 선택 + KB lookup |
| Cross-layer relation 그리기 | CriterionSpan → ConceptMention으로 typed relation 그리기 + properties 입력 |
| Exception relation | INCLUDES_EXCEPTION으로 carve-out 또는 waiver 표현 |

---

## 4. Annotation Decision Rules

본 섹션은 가이드라인의 핵심입니다. 어노테이터가 LLM 출력 검수 또는 from-scratch annotation 시 따라야 할 결정 룰입니다.

### 4.1 Splitting Policy (가장 중요)

가장 빈번한 결정 지점이며, IAA에 가장 큰 영향을 줍니다. **3가지 splitting 패턴** 중 어느 것을 적용할지 결정합니다.

#### 4.1.1 Composite Split (복합 의미 분해)

**언제 적용**:
- 한 criterion이 복수의 독립된 의미를 결합하고 있을 때
- 각 의미가 다른 semantic_category 또는 다른 relation_type을 사용할 때
- 의미적으로 분리해도 임상적 정합성이 유지될 때

**적용 방법**:
- 부모 CriterionSpan: 원문 전체 범위, `parent_role: composite_split`
- 자녀 CriterionSpan: 의미 단위로 분할, IS_PART_OF로 부모와 연결
- 자녀들의 group logic: `Criterion.child_logic` property로 명시

**child_logic 결정 룰** (v1.2.2):
- inclusion criterion + 명시적 "or" 또는 "either" → `child_logic: OR`
- inclusion criterion + 일반 나열 → `child_logic: AND` (default, 생략 가능)
- exclusion criterion + 명시적 "or" 또는 sub-bullet 다중 → `child_logic: OR` (default, 생략 가능)
- exclusion criterion + AND 결합 (드뭄) → `child_logic: AND` (명시 필수)

**적용 예시**:

KEYNOTE-671 I1: "Male/female participants ≥18 yrs with previously untreated and pathologically confirmed resectable Stage II/IIIA/IIIB(N2) NSCLC"
→ 4개 자녀로 분해, child_logic 생략 (AND default):
- I1a: NSCLC diagnosis (condition)
- I1b: Resectable Stage II/IIIA/IIIB(N2) (condition)
- I1c: Previously untreated (treatment_history)
- I1d: Age ≥ 18 (demographic)

SEQUOIA I1: "Metastatic PDAC + 1 of: (a) Histological dx, OR (b) Pathologist-confirmed adenocarcinoma + (i) pancreatic mass OR (ii) history of PDAC"
→ 3개 자녀, **child_logic: OR 명시 필수** (inclusion이지만 OR semantics)

**적용하지 않는 경우**:
- 모든 sub-elements가 동일 semantic_category이고 동일 relation에 매핑될 때 (단순 multi-target fan-out으로 처리)
- 예: KEYNOTE-671 E1 "superior sulcus + LCNEC + sarcomatoid" — 모두 condition, 모두 EXCLUDES_CONDITION → 단일 criterion + multi-target

#### 4.1.2 Macro Aggregate (macro-criterion 분해)

**언제 적용**:
- 원문에 "as defined in the following table" 또는 sub-bullet으로 명시된 다중 lab values
- "Adequate organ function", "adequate hematologic function" 등의 macro-statement

**적용 방법**:
- 부모 CriterionSpan: macro-statement 원문, `parent_role: macro_aggregate`
- 자녀 CriterionSpan: 각 lab value를 별도 CriterionSpan으로, IS_PART_OF
- child_logic: AND default (모든 lab value 충족 필요)
- 부모에는 전체에 적용되는 시간 제약(specimen window) 등 부착 가능

**적용 예시**:

KEYNOTE-671 I5: "Adequate organ function as defined in Table 1, specimens within 10 days prior to study treatment"
→ 부모 + 8개 자녀 (ANC, Platelets, Hgb, CrCl/GFR, Total bilirubin, AST/ALT, TSH, INR)
→ 부모에 HAS_TEMPORAL (10 days specimen window) 부착

#### 4.1.3 Nested Exception (carve-out 표현)

**언제 적용**:
- 원문에 "except for", "with the exception of", "Note: X are not excluded" 등 명시적 carve-out
- 부모 EXCLUDES가 broad target을 갖고, 그 안에서 specific items가 carve-out될 때

**적용 방법**:
- 단일 CriterionSpan 사용 (IS_PART_OF 사용하지 않음 — exception은 cross-layer 관계)
- 부모 relation: EXCLUDES_CONDITION (또는 다른 EXCLUDES_*) → broad target
- 자녀 relation: INCLUDES_EXCEPTION → carve-out targets
- `parent_role: nested_exception_parent`
- `INCLUDES_EXCEPTION.exception_type`:
  - `condition_carveout` (broad EXCLUDES_CONDITION에서 carve-out)
  - `procedure_carveout`
  - `drug_carveout`
  - `status_carveout`

> **v1.2.2 변경**: ~~`requirement_waiver`~~는 exception_type enum에서 제거. 대신 exception_qualifier free-text에 `{applies_when: "...", waiver_type: "requirement_exempt"}`로 기록.

**적용 예시 (carve-out)**:

KEYNOTE-671 E5: "Has additional malignancy... except basal cell carcinoma, squamous cell carcinoma, noninvasive bladder, carcinoma in situ that have undergone potentially curative therapy"
→ exception_type: condition_carveout

**적용 예시 (waiver — v1.2.2에서 exception_qualifier로 변경)**:

KEYNOTE-001 I1_F (squamous histology waiver): "For F-1/F-2/F-3, squamous histology → molecular testing for EGFR/ALK NOT required"
→ exception_type: requirement_waiver
→ exception_qualifier: {applies_when: "predominantly_squamous_histology"}

**carve-out vs waiver 구분**:
- **carve-out**: EXCLUDES target 집합에서 일부 빼냄 ("X 배제, 단 Y 제외")
- **waiver**: REQUIRES 요구 자체를 면제 ("X 요구, 단 Y context에서는 요구 안 함")

#### 4.1.4 Splitting 결정 트리 — 빠른 판단

```
원문이 "as defined in Table" 또는 sub-bullet 다중 lab values?
└── YES → Macro Aggregate

원문에 명시적 "except / Note: X are not excluded / not required if Y"?
└── YES → Nested Exception (waiver 또는 carve-out 결정)

원문이 복수 의미를 결합 (다른 semantic_category 또는 relation)?
└── YES → Composite Split (child_logic 결정)

위 모두 NO?
└── 단일 criterion으로 처리 (분해 없음)
```

#### 4.1.5 Cohort_scope 적용 (basket trial)

**언제 적용**:
- Multi-cohort/basket trial (Part A/B/C/D, F-1/F-2/F-3 등)
- Criterion이 특정 cohort/sub-cohort에만 적용

**적용 방법**:
- `Criterion.cohort_scope: ["F-1"]` 또는 `["F-2", "F-3"]` 등
- Trial node에 cohort registry 사전 정의 (별도 작업)
- criterion_id에 cohort suffix 권장 (예: `NCT01295827_I1_F1`)

**적용 예시**: KEYNOTE-001 — 6개 targeted criterion 모두 cohort_scope 명시

### 4.2 Semantic Category 결정 우선순위

한 criterion이 복수 category에 걸칠 때:

1. **Splitting 우선 검토** (4.1 참조). Composite Split 적용 가능하면 분해.
2. 분해 어려우면 **dominant category** 선택. 우선순위:
   - Numeric constraint이 있는 lab → `lab_value`
   - Drug/treatment 언급이 핵심 → `treatment_history`
   - Disease/diagnosis 언급이 핵심 → `condition`
   - 그 외 → relation type에 매핑되는 category
3. 모호한 경우 **adjudicator 검토** (INCEpTION comment에 reasoning 추가).

### 4.3 Relation Type 결정 트리

3.2의 결정 트리를 그대로 사용. 추가 룰:

- **REQUIRES_STATUS vs REQUIRES_PROCEDURE 구분**:
  - `status`가 평가의 결과 (e.g., "measurable disease per RECIST") → REQUIRES_STATUS
  - `procedure`가 평가의 수단 (e.g., "CT scan within 28 days") → REQUIRES_PROCEDURE
  - 모호하면 status 우선

- **EXCLUDES_TREATMENT vs EXCLUDES_PROCEDURE 구분**:
  - drug 또는 systemic therapy → EXCLUDES_TREATMENT
  - surgery, radiation, transplant → EXCLUDES_PROCEDURE
  - drug + procedure 결합 (예: chemo + radiation) → 두 개 별도 relations

- **HAS_VALUE는 lab/numeric value, HAS_TEMPORAL은 시간**:
  - 둘 다 한 criterion에 동시 적용 가능 (예: ECOG ≤ 1 within 10 days → HAS_VALUE + HAS_TEMPORAL)

### 4.4 Cross-layer Mapping (target_subtype + preferred_name)

어노테이터는 Layer 3의 concept_id를 직접 부여하지 않습니다. 대신:

1. **target_subtype 결정** (6개 중 1개): Condition / Drug / LabTest / Procedure / Biomarker / Stage
2. **target_preferred_name 입력**: 자연어 standard name (Layer 3 concept matching의 입력)
3. INCEpTION의 KB integration이 활성화되어 있으면 KB lookup으로 concept_id link
4. KB lookup이 안 되거나 새로운 concept이면 preferred_name만 입력 (normalization 단계에서 별도 처리)

**Preferred name 작성 룰**:
- 약물: international non-proprietary name (INN) 우선 (예: "Pegilodecakin", not "AM0010")
- 약물 brand name이 원문에 있어도 preferred_name은 INN
- 질환: SNOMED CT preferred term 우선 (예: "Pancreatic ductal adenocarcinoma", not "PDAC")
- 약어/symbol을 풀어서 작성

### 4.5 Biomarker 어노테이션 (v1.2.2)

Biomarker criterion은 v1.2에서 정형화되었습니다. 모든 biomarker 어노테이션은 다음 properties를 명시합니다.

#### 4.5.1 Concept:Biomarker properties

```
Concept:Biomarker {
  gene_symbol: <gene name>,           // 예: "EGFR", "ALK", "BRAF", "PD-L1"
  variant: <criterion-specific variant>, // 예: "T790M", "Ex19del", "G719X", "rearrangement"
  variant_type: <enum>,               // 4.5.2 참조
  variant_notation: <enum>            // 4.5.3 참조
}
```

#### 4.5.2 variant_type enum 결정

| Enum value | 적용 시기 | 예시 |
|---|---|---|
| `mutation` | Point mutation, single nucleotide/amino acid 치환 | T790M, L858R, V600E |
| `rearrangement` | Chromosomal rearrangement, gene fusion | ALK rearrangement, ROS1 |
| `fusion` | Specific gene fusion product | EML4-ALK |
| `deletion` | 삭제 변이 (genomic, exon, amino acid) | Ex19del, exon 19 deletion |
| `insertion` | 삽입 변이 | Exon 20 insertion |
| `amplification` | Copy number amplification | HER2 amplification, MET amplification |
| `expression` | 유전자/단백 발현 수준 | PD-L1 expression, HER2 expression |
| `methylation` | Epigenetic methylation | MGMT methylation |
| `unknown` | 명시 안 됨 | (rare) |

#### 4.5.3 variant_notation (LLM auto-fill, 어노테이터 검수만)

> **v1.2.2 변경**: `variant_notation`은 LLM이 자동으로 할당합니다. INCEpTION에서 read-only suggested feature로 표시됩니다. 어노테이터는 명백한 오류만 수정하고, 능동적으로 판단할 필요 없습니다.

참고용 enum 값 (검수 시):

| Enum value | 의미 | 예시 |
|---|---|---|
| `protein` | Protein-level 치환 | "L858R" |
| `cdna` | cDNA-level | "c.2369C>T" |
| `genomic` | Genomic-level | "g.55259515T>G" |
| `exon_level` | Exon-level macro-class | "Ex19del" |
| `wildcard` | Position-pattern with wildcard | "G719X" |
| `class_level` | Broad variant class | "any sensitizing mutation" |

#### 4.5.4 REQUIRES_BIOMARKER properties

```
REQUIRES_BIOMARKER {
  status: <enum>,                     // positive / negative / wild_type / unknown / equivocal
  assay_method: <string>,             // 예: "Ventana IHC", "central lab FISH", "22C3 IHC"
  clinical_category: <string>         // 예: "TKI-sensitive", "TKI-resistance", "anti-PD1 predictive"
}
```

**status="wild_type"** vs **status="negative"** 구분 (Convention #5.18):
- `wild_type`: mutation testing 결과 mutation 없음 (KEYNOTE-001 EGFR wild-type)
- `negative`: marker 자체가 없음 또는 negative (KEYNOTE-001 ALK translocation 없음)
- 임상적 의미 동일하지만 source data interpretation 다름

### 4.6 Constraint Properties (HAS_VALUE, HAS_TEMPORAL)

**중요**: 표준 numeric pattern (e.g., "ANC ≥ 1500/µL", "within 10 days of randomization")은 LLM/Python이 자동 추출합니다. 어노테이터는 비표준 패턴만 검수합니다.

#### 4.6.1 HAS_VALUE properties

| Property | 입력 형식 | 예시 |
|---|---|---|
| operator | enum: `≤` `<` `=` `≥` `>` `within` | "≥" |
| value | string (numeric 또는 enum) | "100", "1.5", "normal_limits" |
| unit | string | "g/dL", "× ULN", "mg/dL" |
| scale | string (시스템명) | "ECOG", "CTCAE", "RECIST v1.1", "irRC" |
| alternative_constraint | string 또는 nested object | (Section 4.7 참조) |

#### 4.6.2 HAS_TEMPORAL properties

| Property | 입력 형식 | 예시 |
|---|---|---|
| operator | enum: `≤` `<` `=` `≥` `>` `within` | "≤" |
| value | numeric 또는 string | "28", "2" |
| unit | string | "days", "weeks", "months", "years" |
| anchor | string | "Randomization", "first_dose", "informed_consent" |
| direction | enum: `before` `after` `within` `since` | "before" |
| **anchor_type** (v1.2.2) | enum | `trial_event` / `patient_event` / `unspecified` |

**anchor_type 결정 룰** (v1.2.2, 3-way):

| Anchor 예시 | anchor_type |
|---|---|
| "Randomization" | trial_event |
| "first_dose_of_IP" | trial_event |
| "informed_consent" | trial_event |
| "study_treatment_start" | trial_event |
| "first_EGFR_TKI_treatment_start" | patient_event |
| "documented_PD_on_1L_EGFR_TKI" | patient_event |
| "completion_of_concurrent_CRT" | patient_event |
| "completion_of_most_recent_therapy" | patient_event |
| "screening_biopsy" | patient_event |
| "thoracic_radiation_completion" | patient_event |

> **v1.2.2 변경**: ~~`procedure_event`~~ 제거. "screening_biopsy", "thoracic_radiation_completion" 등은 `patient_event`로 통합 — EMR query path가 동일하므로 구분 불필요.

**Direction 결정 룰**:
- "prior to / before X" → `before`
- "after / following X" → `after`
- "within X days/weeks of Y" (양방향 또는 모호) → `within`
- "since X" (X 시점부터 현재까지) → `since`
- 명시되지 않으면 default `before`

### 4.7 alternative_constraint 표현 (가장 어려운 영역)

자동화 분석에서 38% MANUAL로 식별된 가장 어려운 stage입니다. **LLM 출력을 신뢰하지 말고 어노테이터가 직접 작성하는 것이 더 효율적**입니다.

#### 4.7.1 alternative_constraint object schema

`alternative_constraint`는 string 또는 object 둘 다 허용합니다.

**Object 형식**:
```
alternative_constraint: {
  condition: <when applies>,
  operator: <comparison>,
  value: <threshold>,
  unit: <unit>,
  // 또는 free-form keys
}
```

**Object 형식 사용 시기** (구조화 가능한 경우):

KEYNOTE-671 I5e bilirubin: `alternative_constraint: "direct bilirubin within normal limits if total bilirubin > 1.5 × ULN"`

→ structured form:
```
alternative_constraint: {
  condition: "if total bilirubin > 1.5 × ULN",
  alternative_test: "direct bilirubin",
  alternative_value: "within normal limits"
}
```

**String 형식 사용 시기** (자연어 보존 필요):

AURA3 E1b mathematical washout: `alternative_constraint: "max(8 days, 5 × half-life) — whichever longer applies"`

복잡한 자연어는 string으로 보존. EMR matching 시 사람이 검토.

#### 4.7.2 Compound exception_qualifier convention

INCLUDES_EXCEPTION에서 compound 조건이 있을 때:

```
INCLUDES_EXCEPTION {
  exception_type: "status_carveout",
  exception_qualifier: {
    conditions: ["asymptomatic", "stable", "no_steroid_dependency"],
    logic: "AND",
    temporal: {operator: "≥", value: 4, unit: "weeks", anchor: "study_treatment_start"},
    applies_to: "no_steroid_dependency"
  }
}
```

(AURA3 E3 brain mets carve-out 적용)

#### 4.7.3 alternative_constraint 작성 결정 트리

```
조건이 단일 numeric threshold + 조건문?
└── YES → object 형식 (condition + operator + value + unit)

조건이 mathematical formula 또는 외부 reference (baseline, t½ 등)?
└── YES → string 형식 (자연어 보존)

조건이 compound (AND/OR + temporal 등)?
└── YES → INCLUDES_EXCEPTION + compound exception_qualifier object

조건이 sponsor/medical monitor 협의 등 subjective?
└── YES → string 형식 + INCEpTION comment에 자연어 보존
```

---

## 5. Convention Rules (schema에서 위임된 항목)

본 섹션은 schema에서 명시적으로 정의되지 않은 표현 패턴의 처리 룰입니다. 32개 issue가 가이드라인 convention으로 처리됩니다. **이 룰들은 IAA에 직접 영향을 주므로 어노테이터는 모두 숙지해야 합니다.**

### 5.1 Confirmation Rule (sub-stage별 evidence 차이)

**문제**: 동일 stage 내에서 sub-stage별 evidence 요구가 다른 경우.

**예시**: KEYNOTE-671 I1 — "lymph node disease requires pathologic confirmation, while T3 (rib destruction) disease requires only radiographic documentation"

**처리**:
- Stage sub-staging은 preferred_name에 명시 (예: "Stage IIIB (N2)")
- confirmation rule은 INCEpTION annotation comment에 자연어 보존

> **v1.2.2 변경**: ~~`t/n/m_descriptor`~~ property 제거. TNM 조합은 Layer 3 구축 시 AJCC staging table에서 자동 생성. Annotation 단계에서는 preferred_name에 "(N2)" 등을 명시하는 것으로 충분.

### 5.2 Equivalent Tests OR vs AND

**문제**: "Cr clearance OR GFR" (OR) vs "AST AND ALT" (AND).

**처리**:
- **OR semantics**: 두 개의 평행 HAS_VALUE relation + 동일한 `equivalence_group_id` (string feature)로 묶음
- **AND semantics**: equivalence_group_id 사용하지 않음. 두 개의 평행 HAS_VALUE만 부착, 또는 별도 자녀 sub-criterion으로 분해

**판단 기준**:
- 원문에 "OR" 또는 "either" → OR
- 원문에 항목 나열 (콤마, 줄바꿈) + AND default → AND
- 임상적 의미로 판단 (예: AST와 ALT는 둘 다 정상이어야 간기능 정상 → AND)

### 5.3 "× ULN" 단위 처리

**문제**: "≤ 1.5 × ULN" institution-specific value의 multiple.

**처리**:
- unit field에 `"× ULN"` 그대로 기록
- value field는 숫자만 (예: 1.5)
- EMR matching 단계에서 institution-specific ULN value lookup 필요

### 5.4 "Previously Untreated" Universal-Scope

**문제**: "previously untreated"는 모든 prior therapy의 부재.

**처리**:
- relation: EXCLUDES_TREATMENT
- target_preferred_name: "any prior systemic anticancer therapy"
- properties: `temporal: "any_prior"`, `drug_class_basis: true`, `drug_class_type: "open_mechanism_class"`

### 5.5 "Clinical Progression" 분류

**문제**: "clinical progression"이 procedure 평가인지 status 평가인지 모호.

**처리**: **status로 분류**. REQUIRES_STATUS 사용. evidence_methods property에 "clinical_progression" 명시.

### 5.6 Range Expression Normalization

**문제**: "ECOG 0-1" range로 표현된 값.

**처리**:
- Lower bound가 자명한 scale (ECOG, Karnofsky 등 0부터) → **upper bound만** 정규화 → `operator: "≤", value: 1`
- Lower bound가 자명하지 않으면 **두 개의 relations** 부착 → `operator: "≥", value: lower` + `operator: "≤", value: upper`

### 5.7 "Baseline" 비교 기준

**문제**: "recovered to Grade 1 or baseline" 환자별 가변 reference.

**처리**:
- primary value: `operator: "≤", value: 1, scale: "CTCAE"`
- alternative_constraint: `"recovered to baseline (patient-specific reference)"` (자연어 string)

### 5.8 광의 카테고리 ("non-X") 처리

**문제**: "non-adenocarcinoma" abstract category에 명시 examples.

**처리**:
- **명시된 examples만 target** (예: "non-adenocarcinoma (ie, lymphoma, sarcoma)" → target은 lymphoma, sarcoma만)
- abstract category 자체는 condition_qualifier 또는 normalized_text에 자연어 보존

### 5.9 HAS_VALUE의 condition_qualifier 표현

**문제**: "Hgb ≥ 9.0 g/dL **without erythropoietin dependency**".

**처리**: alternative_constraint를 nested object 형식으로 사용:
```
alternative_constraint: {
  condition: "without erythropoietin dependency AND no pRBC transfusion within 2 weeks"
}
```

### 5.10 HAS_TEMPORAL "at" 시점 표현

**문제**: "at the day of informed consent" point-in-time.

**처리**: `direction: "since"` + `value: 0, unit: "days"` 정규화.

### 5.11 HAS_TEMPORAL Forward-looking

**문제**: "anticipated surgery during study period" 미래 시점.

**처리**:
- direction enum `after` 사용
- anchor: 적절한 시점 (e.g., "study_period_start")
- 자연어 nuance는 normalized_text 보존

### 5.12 EXCLUDES_STATUS Operational Definition

**문제**: "intolerance" 같은 status에 operational definition (e.g., "unable to receive ≥ 8 weeks").

**처리**:
- status property에 핵심 status 키워드 (e.g., `"intolerance"`)
- alternative_constraint 또는 normalized_text에 operational definition 보존

### 5.13 procedural_fitness Target Subtype

**문제**: "able to undergo surgery" 임상의 평가의 target Concept 모호.

**처리**:
- target_subtype: `LabTest`로 분류 (broader interpretation: "정량 lab 또는 임상 평가")
- target_preferred_name: 평가 항목명 (예: "Surgical fitness assessment")
- value field에 status string

### 5.14 Stage Resectability Qualifier

**문제**: "Stage IIIB not amenable for multimodality treatment".

**처리**:
- Concept:Stage의 standard properties (system, value)
- resectability qualifier는 normalized_text 또는 별도 property로 자연어 보존
- 향후 occurrences 누적 시 v1.3에서 정형화 검토

### 5.15 Numeric Exception Qualifier

**문제**: Carve-out에 numeric threshold (예: corticosteroids ≤ 20mg/day).

**처리**:
- INCLUDES_EXCEPTION의 exception_qualifier object에 명시:
```
exception_qualifier: {
  threshold: "≤ 20 mg/day",
  drug_form: "prednisolone equivalent"
}
```

### 5.16 Lab Value Reproducibility

**문제**: "Confirmed on two consecutive measurements".

**처리**: HAS_VALUE에 자연어 보존 (normalized_text 또는 alternative_constraint string).

### 5.17 line_of_therapy enum

**Convention enum** (relation property):
- `first_line` — 1L therapy
- `second_line` — 2L specific
- `second_line_or_later` — 2L+ (e.g., AURA3 E1a "more than one prior line")
- `third_line_or_later`
- `any_line` (default if not specified)
- `n_prior_lines: {operator: ">", value: 1}` — count-based 표현

### 5.18 Biomarker status enum 확장

**Convention enum**:
- `positive` — biomarker 양성
- `negative` — biomarker 음성
- `wild_type` — mutation testing 결과 mutation 없음
- `unknown` — 검사 결과 미상
- `equivocal` — 중간/모호 결과 (IHC 등에서)

### 5.19 Status Negation Expansion

**문제**: "not progressed" 같은 negated status.

**처리**:
- status property: 핵심 키워드 (e.g., "not_progressed")
- equivalent_status array: positive 형태 expansion (e.g., `["CR", "PR", "SD"]`)

### 5.20 Specialized Notation (V20, V45 등)

**처리**: Concept:LabTest의 extensibility 활용. preferred_name에 정확한 metric name (e.g., "Lung V20", "Heart V45").

### 5.21 Direction "before_or_concurrent"

**문제**: "final chemo ≤ final RT".

**처리**: direction=before + value=0, 또는 normalized_text 보존.

### 5.22 requires_consultation Qualifier

**문제**: Sponsor/medical monitor 협의 필요한 carve-out.

**처리**:
- INCLUDES_EXCEPTION의 exception_qualifier에 자연어 보존:
```
exception_qualifier: {
  conditions: [...],
  requires_consultation: "AstraZeneca/MedImmune medical monitor"
}
```

### 5.23 Treatment_modality enum

**Convention enum** (relation property):
- `concurrent_with_chemotherapy`
- `sequential_chemoradiation`
- `neoadjuvant`
- `adjuvant`
- `consolidation`
- `induction`
- `maintenance`

### 5.24 Drug Regimen Partner

**문제**: "Platinum + companion drug from {etoposide, ...}".

**처리**: 두 sibling REQUIRES_TREATMENT relations로 표현. EMR matching 시 same treatment cycle window 내 두 약물 병기 확인.

### 5.25 Range Temporal Value

**문제**: "1 to 42 days prior".

**처리**: 두 평행 HAS_TEMPORAL relations:
- HAS_TEMPORAL #1: `{operator: "≥", value: 1, unit: "days", direction: "before"}`
- HAS_TEMPORAL #2: `{operator: "≤", value: 42, unit: "days", direction: "before"}`

### 5.26 Value Tolerance

**문제**: "60 Gy ±10% (54-66 Gy)".

**처리**:
- HAS_VALUE primary: `operator: "=", value: 60, unit: "Gy"`
- alternative_constraint: `{tolerance: "±10%", value_range: [54, 66]}`

### 5.27 2-perpendicular Measurement Method

**문제**: irRC requires 2-perpendicular diameters (RECIST는 single longest).

**처리**: HAS_VALUE에 `measurement_method` property:
- enum values: `longest_diameter` / `2_perpendicular_diameters` / `short_axis`
- scale property로 RECIST vs irRC 구분

### 5.28 Mathematical Formula Temporal

**문제**: AURA3 E1b "8 days OR 5×half-life, whichever longer".

**처리**: 두 평행 HAS_TEMPORAL + equivalence_group + group_logic="MAX":
- HAS_TEMPORAL #1: `{operator: ">", value: 8, unit: "days"}`
- HAS_TEMPORAL #2: `{operator: ">", value: 5, unit: "× half_life", value_type: "computed"}`
- Both: `equivalence_group_id: "egfr_tki_washout_aura3", group_logic: "MAX"`

### 5.29 Imaging-parameter-dependent Threshold

**문제**: KEYNOTE-001 I2 "≥10mm OR 2×slice_thickness if >5mm".

**처리**: alternative_constraint에 자연어 보존 (mathematical formula 5.28과 유사 패턴).

### 5.30 Biomarker-conditional Mandatory Treatment

**문제**: KEYNOTE-001 BRAF V600+ → mandatory BRAF/MEK inhibitor.

**처리**: composite_split with applies_when convention:
- 부모: composite_split, child_logic: AND
- 자녀 1: REQUIRES_BIOMARKER (BRAF V600)
- 자녀 2: REQUIRES_TREATMENT (BRAF/MEK inhibitor) with `applies_when: "BRAF V600 mutation present"` (alternative_constraint property에 명시)

### 5.31 Histology-specific Applicability

**문제**: KEYNOTE-001 squamous histology → testing 면제.

**처리**: 5.4 (requirement_waiver) + condition_qualifier 또는 INCEpTION population_qualifier comment에 자연어 보존.

### 5.32 Order-independence Qualifier

**문제**: "No preferred order, both required".

**처리**: condition_qualifier에 자연어:
```
condition_qualifier: "two_treatments_required_no_preferred_order"
```

또는 INCEpTION comment에 보존.

---

## 6. Worked Examples

본 섹션은 가이드라인의 모든 decision rules을 실제 적용한 worked examples를 제공합니다. 어노테이터는 본격 작업 시작 전 본 섹션의 examples를 충분히 학습해야 합니다.

### 6.1 Reference Annotation 문서

상세한 worked example은 두 reference annotation 문서를 참조합니다:

**Primary reference (NSCLC main worked example)**:
- `NCT03425643_KEYNOTE671_reference_annotation_v2.md` — 11 calibration criteria, schema v1.2 적용
- 적용 패턴: composite_split (4-way), macro_aggregate (8 sub), nested_exception, condition_qualifier, EXCLUDES_PROCEDURE, drug_class_type=open_mechanism_class, TNM substaging

**Supplementary reference (PDAC, multi-domain validation)**:
- `NCT02923921_SEQUOIA_reference_annotation_v2.md` — 11 criteria
- 적용 패턴: composite_split (3-path OR), macro_aggregate (9 sub), alternative_constraint nested object, drug_class_type=closed_class, EXCLUDES_PROCEDURE, EXCLUDES_STATUS with operational definition

**Calibration set 학습 절차**:
1. KEYNOTE-671 reference annotation을 처음부터 끝까지 읽음
2. SEQUOIA reference annotation을 학습
3. 11 criterion을 from-scratch로 다시 어노테이션 (reference 직접 보지 않음)
4. Adjudicator와 비교하여 calibration kappa 측정
5. **κ ≥ 0.7 도달 시 본 작업 시작**

### 6.2 v1.2.2 패턴 적용 예시

KEYNOTE-671/SEQUOIA reference에는 v1.2.2 patterns이 적용되지 않았으므로, 본 섹션에서 4개 stress test trial의 핵심 예시를 정리합니다.

#### 6.2.1 child_logic=OR 명시 (composite_split)

**원문 (SEQUOIA I1)**:
> The presence of metastatic pancreatic adenocarcinoma plus 1 of the following:
> a. Histological diagnosis of pancreatic adenocarcinoma confirmed pathologically, OR
> b. Pathologist-confirmed diagnosis... + (i) pancreatic mass, OR (ii) history of PDAC

**어노테이션**:
- Criterion: parent_role=composite_split, **child_logic=OR** (inclusion이지만 OR semantics — 명시 필수)
- 자녀 3개: I1a, I1b, I1c (각각 다른 confirmation path)

**핵심 결정**: inclusion criterion은 default AND이므로 OR semantics를 명시적으로 표현해야 합니다.

#### 6.2.2 Biomarker variant_type/notation 적용

**원문 (AURA3 I7)**:
> Documented EGFR mutation known to be associated with EGFR TKI sensitivity (including G719X, exon 19 deletion, L858R, L861Q).

**어노테이션 (multi-target fan-out)**:

| Target | gene_symbol | variant | variant_type | variant_notation |
|---|---|---|---|---|
| Concept:Biomarker #1 | EGFR | G719X | mutation | wildcard |
| Concept:Biomarker #2 | EGFR | exon 19 deletion | deletion | exon_level |
| Concept:Biomarker #3 | EGFR | L858R | mutation | protein |
| Concept:Biomarker #4 | EGFR | L861Q | mutation | protein |

**REQUIRES_BIOMARKER properties**:
- status: positive
- clinical_category: "EGFR_TKI_sensitive"
- temporal: "any_time_since_NSCLC_diagnosis"

**핵심 결정**: 4개 variants가 다른 notation level이므로 각각 별도 Concept:Biomarker 노드. notation level 구분이 EMR matching에서 wildcard expansion (G719X → G719A/G719S/G719C 등)을 가능하게 합니다.

#### 6.2.3 Specific point mutation (T790M)

**원문 (AURA3 I8)**:
> Subjects must have central confirmation of tumour T790M+ mutation status from a tissue biopsy sample taken after documented disease progression on first line treatment with an approved, EGFR tyrosine kinase inhibitor.

**어노테이션 (composite_split)**:
- 부모: composite_split, child_logic=AND
- 자녀 I8a: T790M biomarker
  - Concept:Biomarker: gene_symbol="EGFR", variant="T790M", **variant_type="mutation"**, **variant_notation="protein"**, hgvs_p="p.Thr790Met"
  - REQUIRES_BIOMARKER: status="positive", clinical_category="EGFR_TKI_resistance"
- 자녀 I8b: REQUIRES_PROCEDURE (Central laboratory mutation testing)
- 자녀 I8c: REQUIRES_PROCEDURE (Tumor tissue biopsy)
- 자녀 I8d: HAS_TEMPORAL — anchor_type="patient_event"

#### 6.2.4 anchor_type 적용 (HAS_TEMPORAL v1.2.2)

**원문 (AURA3 I8d)**:
> ...biopsy sample taken after documented disease progression on first line treatment with an approved, EGFR tyrosine kinase inhibitor.

**어노테이션**:
```
HAS_TEMPORAL {
  operator: ">",
  value: 0,
  unit: "days",
  anchor: "documented_PD_on_1L_EGFR_TKI",
  direction: "after",
  anchor_type: "patient_event"     ← v1.2.2
}
```

**대조 예시 (trial_event)**:

KEYNOTE-671 I4: "ECOG within 10 days of randomization"
```
HAS_TEMPORAL {
  operator: "≤",
  value: 10,
  unit: "days",
  anchor: "Randomization",
  direction: "before",
  anchor_type: "trial_event"        ← 표준 trial event
}
```

**핵심 결정**: anchor가 protocol에서 정의된 표준 event (Randomization, first_dose 등)이면 trial_event. 환자별 chart-level 조회가 필요한 historical event이면 patient_event.

#### 6.2.5 ~~strictness~~ (v1.2.2에서 제거 — 참고용만)

> **v1.2.2 변경**: `strictness`는 v1.3으로 연기되었습니다. 아래 예시는 참고용으로만 보존합니다. 30개 trial annotation 후 실제 hedging 표현 빈도에 따라 재도입 여부를 결정합니다.

**원문 (PACIFIC I4g)**:
> Patients must have received a total dose of radiation of 60 Gy ±10% (54 Gy to 66 Gy). Sites are encouraged to adhere to mean organ radiation dosing as follows:

**v1.2.2 처리**: "Sites are encouraged..." 같은 hedging 표현은 INCEpTION comment에 `"hedging: encouraged"` 태그로 보존. `strictness` property는 사용하지 않음.

#### 6.2.6 cohort_scope 적용 (KEYNOTE-001)

**원문 (KEYNOTE-001 I1_F1)**:
> In Part F of the study, patients must have a histologically-confirmed diagnosis of NSCLC. Under Amendments 07 and beyond, patients in F must have a known EGFR mutation and ALK translocation status. Patients in F-1 must be EGFR wild type and without ALK translocation. Patients in F-1 must be naive to systemic treatment for NSCLC and have Stage IV disease.

**어노테이션**:
- criterion_id: NCT01295827_I1_F1
- **cohort_scope: ["F-1"]**
- (이하 inclusion 조건들)

대조: NCT01295827_I2_irRC는 Part B/C/D/F에 적용
- **cohort_scope: ["B", "C", "D", "F"]**

**핵심 결정**: 모든 KEYNOTE-001 criterion에 cohort_scope 명시. Single-cohort trial (KEYNOTE-671, SEQUOIA, ALEX, AURA3, PACIFIC)에서는 cohort_scope 생략.

#### 6.2.7 Requirement waiver 표현 (v1.2.2 변경)

> **v1.2.2 변경**: ~~`exception_type: "requirement_waiver"`~~는 enum에서 제거. 대신 기존 4개 exception_type 중 가장 적합한 것을 사용하고, `exception_qualifier` free-text에 waiver 정보를 기록합니다.

**원문 (KEYNOTE-001 histology waiver)**:
> For patients enrolled in F-1, F-2, or F-3, who are known to have a tumor of predominantly squamous histology, molecular testing for EGFR mutation and ALK translocation will not be required as this is not standard of care.

**어노테이션 (v1.2.2)**:
- 부모 criterion: REQUIRES_BIOMARKER (EGFR/ALK testing) — F-1/F-2/F-3 cohort에 적용
- INCLUDES_EXCEPTION:
  - **exception_type: "status_carveout"** (squamous histology라는 status에 의한 면제)
  - exception_qualifier:
    ```
    {
      applies_when: "predominantly_squamous_histology",
      waiver_type: "requirement_exempt",
      rationale: "not_standard_of_care_for_squamous"
    }
    ```

**핵심 결정**: waiver는 exception_qualifier의 `waiver_type` key로 표현. Schema enum 복잡도를 줄이면서 동일한 정보를 보존.

---

## 7. Edge Cases & FAQ

본 섹션은 어노테이션 작업 중 자주 마주칠 문제 패턴들을 다룹니다.

### 7.1 동일 criterion이 inclusion+exclusion에 동시 등장

**문제**: 일부 protocol에서 동일 medical condition이 inclusion (요구) + exclusion (다른 측면 배제)에 모두 등장.

**예시**: KEYNOTE-671 — "Stage II/IIIA/IIIB(N2) NSCLC" inclusion, but "superior sulcus NSCLC" exclusion (둘 다 NSCLC subtype).

**처리**:
- 별개 criterion으로 어노테이션 (inclusion 1개, exclusion 1개)
- 충돌 아님 — inclusion은 broad target, exclusion은 specific subtype

### 7.2 Sub-criterion에서만 등장하는 cross-layer relation

**문제**: 부모 criterion은 단순 EXCLUDES_CONDITION이지만 자녀에서는 다른 relation type 등장.

**예시**: AURA3 E1 (parent: composite_split, OR) — 자녀들이 EXCLUDES_TREATMENT, EXCLUDES_PROCEDURE, INCLUDES_EXCEPTION 모두 사용.

**처리**:
- 부모 criterion은 cross-layer relation 직접 부착하지 않음 (semantic_category만 dominant 분류)
- 각 자녀 criterion이 자신의 relation 직접 부착
- 부모-자녀 IS_PART_OF만 부착

### 7.3 같은 lab name이 inclusion에 있는 macro와 exclusion에 있는 단독 criterion에 등장

**문제**: 예) KEYNOTE-671 I5 macro에 "AST/ALT ≤ 2.5×ULN" inclusion, ALEX E3에 "ALT/AST > 3×ULN" exclusion.

**처리**:
- 같은 LabTest concept (Concept:LabTest "AST", "ALT") 재사용
- 각 criterion은 자신의 HAS_VALUE relation으로 다른 operator/value 표현
- ConceptMention (surface form)은 각 criterion text에서 별도로 마킹

### 7.4 Splitting을 적용했을 때 자녀가 1개만 나옴

**문제**: composite_split 시도했는데 의미 단위가 사실상 1개.

**처리**:
- Splitting 적용하지 않음 (단일 criterion으로)
- parent_role 부여하지 않음
- 자녀 1개만 있는 IS_PART_OF는 schema validation에서 reject

### 7.5 LLM 출력에 schema에 없는 property 포함

**문제**: LLM이 hallucinated property 또는 v1.2 이전 버전 property 사용.

**처리**:
- 모르는 property는 무시 (어노테이션 작업 중 제거)
- INCEpTION schema validation이 자동 reject할 것
- 빈번한 hallucination 발견 시 adjudicator에게 보고 (LLM prompt 개선)

### 7.6 LLM 출력의 target_preferred_name이 INN/SNOMED standard와 다름

**문제**: LLM이 "AZD9291" (development code) 사용, 올바른 INN은 "Osimertinib".

**처리**:
- 어노테이터가 직접 INN으로 수정
- Brand name → INN 변환 (Section 4.4 룰)
- 약어 → full name (PDAC → Pancreatic ductal adenocarcinoma)

### 7.7 Cross-criterion temporal anchor (AURA3 I8d 같은 패턴)

**문제**: 한 criterion의 temporal anchor가 다른 criterion의 status event를 참조.

**예시**: AURA3 I8d biopsy timing이 I5의 progression event를 anchor로 사용.

**처리**:
- I8d의 anchor에 자연어 표현 ("documented_PD_on_1L_EGFR_TKI")
- anchor_type=patient_event 명시
- INCEpTION comment에 cross-reference 자연어 보존: "anchor refers to event documented in I5"
- 별도 cross-criterion link relation은 사용 안 함 (v1.3 검토 사항)

### 7.8 Subjective catch-all criterion

**문제**: KEYNOTE-671 E12, ALEX E14 등 "investigator judgment" 또는 "clinically significant disease" 같은 catch-all.

**처리**:
- Schema 표현 한계 (paper limitation으로 보고됨)
- 단일 EXCLUDES_CONDITION → abstract Concept:Condition ("any clinically significant disease")
- condition_qualifier에 자연어 보존
- INCEpTION comment에 "subjective_catch_all" 태그

### 7.9 동일 의미를 가진 reverse-direction criterion

**문제**: PACIFIC I5 "must have not progressed"는 negation status. 양성 표현으로 바꾸면 "achieved CR/PR/SD".

**처리**:
- status property: 핵심 키워드 그대로 (e.g., "not_progressed")
- equivalent_status: positive expansion array (e.g., ["CR", "PR", "SD"])
- Section 5.19 convention 적용

### 7.10 Concept:Drug에 발현되지 않은 drug class (예: "any cytotoxic chemo")

**문제**: "any chemotherapy" 같은 abstract drug class — Concept:Drug 노드 명세 어려움.

**처리**:
- Concept:Drug 노드: preferred_name="Cytotoxic chemotherapy class" (abstract concept)
- relation properties: drug_class_basis=true, drug_class_type="open_mechanism_class"
- EMR matching 시 drug_class lookup table 필요 (Layer 4 lexical)

### 7.11 Patient population qualifier vs criterion-level scope

**문제**: KEYNOTE-001 ipilimumab-refractory 같은 "patient population" 한정 criterion.

**처리**:
- cohort_scope에 명시 (예: cohort_scope=["Ipilimumab-refractory MEL"])
- 또는 criterion text에 자연어 보존 (single cohort trial일 경우)

### 7.12 Optional vs strictly required 모호한 표현

**문제**: "Where possible", "should be", "is recommended" 같은 미묘한 hedging.

**처리 (v1.2.2)**:
- `strictness` property는 v1.3으로 연기되어 사용하지 않음
- hedging 표현은 INCEpTION comment에 태그로 보존:
  - "Sites are encouraged to" → comment: `hedging: encouraged`
  - "Is recommended" → comment: `hedging: recommended`
  - "Is optional" / "if available" → comment: `hedging: optional`
- 어노테이터는 hedging 여부를 판단하되, property로 입력하지 않음

### 7.13 Multi-protocol amendment의 criterion 변경

**문제**: AURA3 protocol처럼 여러 amendment가 누적된 PDF에서 criterion이 시간에 따라 변화.

**처리**:
- 가장 최신 amendment의 criterion text 사용
- Amendment history는 INCEpTION metadata에 보존 (별도 작업)
- 어노테이션 시점에 latest version으로 일관 처리

### 7.14 ConceptMention surface form이 criterion text에 명시되지 않음

**문제**: Criterion이 "treatment-naive"라고만 표현하고 specific drug name 없음.

**처리**:
- ConceptMention 마킹할 surface form이 없으면 ConceptMention 생성하지 않음
- Cross-layer relation은 CriterionSpan에 직접 부착 (target은 conceptual)
- LLM prompt에서 abstract concept 처리 룰 명시

### 7.15 단일 protocol에 매우 많은 criterion (50개+)

**문제**: 일부 protocol은 50개+ criterion을 가져 작업 부담 큼.

**처리**:
- Targeted annotation 적용 (5-8개 핵심 criterion만)
- 나머지는 LLM 1차 출력만 사용 (어노테이터 검수 없이)
- Paper에서 "targeted stress test methodology"로 보고

---

## 8. Disagreement Resolution Protocol

### 8.1 Disagreement Taxonomy

두 어노테이터의 결과가 불일치할 때, 다음 6가지 유형으로 분류합니다 (paper reporting 시에도 동일 분류 사용):

| 유형 | 정의 | 예시 |
|---|---|---|
| **Scope** | criterion 분해 여부 또는 범위 차이 | A는 단일 criterion, B는 composite_split으로 분해 |
| **Category** | semantic_category 차이 | A는 `condition`, B는 `comorbidity` |
| **Relation** | relation_type 차이 | A는 REQUIRES_STATUS, B는 REQUIRES_PROCEDURE |
| **Target** | cross-layer target_preferred_name 차이 | A는 "PDAC", B는 "Pancreatic ductal adenocarcinoma" |
| **Property** | relation properties 차이 | A는 `temporal: "prior"`, B는 `temporal: "any_prior"` |
| **Span** | CriterionSpan 또는 ConceptMention 텍스트 범위 차이 | A는 "Stage IIIB (N2)" 전체, B는 "Stage IIIB"만 |

### 8.2 Adjudication 절차

1. INCEpTION의 curation mode에서 두 어노테이터 결과를 동시 표시
2. 불일치 항목별로:
   - **Type 분류** (위 6개 중 1개)
   - **Adjudicator 판단** (가이드라인 룰 적용)
   - 룰로 결정 불가능하면 **임상 판단 필요 케이스**로 분류
3. Adjudicated annotation을 INCEpTION에 저장 (curation 결과)
4. Adjudication log: 각 결정의 근거를 문서화 (별도 spreadsheet)

### 8.3 Adjudication Decision Hierarchy

불일치 해소 시 다음 우선순위로 판단:

1. **Schema rule 위반인가?**: v1.2.2 schema에 명시된 룰 위반 시 자동 reject
2. **가이드라인 convention 적용 가능한가?**: Section 5의 convention 적용
3. **Reference annotation에 동일/유사 사례 있는가?**: KEYNOTE-671 v2 또는 SEQUOIA v2 참조
4. **임상적 판단 필요한가?**: Oncologist 자문 (third adjudicator)
5. **위 모두 결정 불가**: Adjudicator 판단으로 처리 + 가이드라인 v0.2 입력

### 8.4 Third Adjudicator 시점

다음 케이스는 oncologist (third adjudicator)에게 자문:
- 임상적 판단이 필요한 케이스 (e.g., "is X disease equivalent to Y in this trial context?")
- 가이드라인 룰로 결정 불가능한 schema-level 모호성
- 두 어노테이터가 합의에 이르지 못하는 케이스
- Subjective catch-all criterion의 처리 일관성

Third adjudicator 자문 결과는 가이드라인 v0.2의 입력으로 활용 (가이드라인은 living document).

### 8.5 Adjudication 빈도 관리

- 매 trial 단위 adjudication 수행
- 평균 disagreement rate 추적 (per criterion type, per stage)
- Disagreement rate가 특정 stage에서 급증 시 가이드라인 v0.2에 해당 stage 룰 보강

---

## 9. Quality Metrics

### 9.1 Inter-Annotator Agreement (IAA)

본 작업에서 측정할 IAA 지표:

#### 9.1.1 Span-level F1 (CriterionSpan, ConceptMention)

CriterionSpan과 ConceptMention의 텍스트 범위 일치도:
- Exact match: 정확히 동일 offset
- Partial overlap: 50% 이상 겹침
- Strict F1 (exact match) + Lenient F1 (partial overlap) 둘 다 보고

#### 9.1.2 Cohen's kappa (categorical decisions)

다음 categorical 결정에 대해 Cohen's kappa 측정:
- semantic_category (10-enum)
- relation_type (cross-layer relations)
- target_subtype (6-enum)
- splitting_decision (composite/macro/nested/none)
- child_logic (AND/OR)
- exception_type (4-enum)
- anchor_type (3-enum)
- variant_type (9-enum)

#### 9.1.3 Relation-level F1

Cross-layer relation 일치도:
- Source span + relation type + target span 모두 동일 시 match
- Strict F1 + Lenient F1 (target span only) 보고

#### 9.1.4 Property-level agreement

각 relation의 properties (operator, value, unit, anchor 등) 정확도:
- Per-property accuracy
- Property-level F1

### 9.2 Calibration kappa (gating threshold)

- **본 작업 시작 조건**: calibration kappa ≥ 0.7 (semantic_category 기준)
- 미달 시 가이드라인 재학습 후 재시도
- Calibration log: 어노테이터별 disagreement 패턴 분석

### 9.3 Working IAA (drift 감지)

- 매 5 trial마다 중간 IAA 측정
- 직전 5 trial 대비 IAA 10% 이상 하락 시 adjudicator 검토 trigger
- Drift 원인 분석 → 가이드라인 보강 또는 재학습

### 9.4 Final IAA (paper reporting)

논문 보고용 final metrics:
- Span F1 (strict + lenient)
- Cohen's kappa per categorical decision (10+ enums)
- Relation F1 (strict + lenient)
- Disagreement type distribution (Section 8.1 6-type taxonomy)

### 9.5 LLM-assisted vs Blind subset 비교

- Blind subset (15-20%)와 LLM-assisted subset의 IAA 비교
- Anchoring bias 정량화: blind에서 IAA 높으면 anchoring bias 우려, 비슷하면 LLM 영향 작음
- Per-stage anchoring bias 분석 (특히 Stage K alternative_constraint)

---

## Appendix A: Schema v1.2.1 → v1.2.2 Changelog (어노테이터 관점)

본 가이드라인 v0.2는 schema v1.2.2를 기준으로 작성됐습니다.

### v1.2.2에서 제거된 elements (어노테이터가 더 이상 입력하지 않음)

| 제거된 element | 이유 | 대체 처리 |
|---|---|---|
| `strictness` (4-enum) | 30개 trial 중 사용 빈도 극소 | v1.3으로 연기. hedging은 INCEpTION comment 태그 |
| `variant_notation` (6-enum) | Annotator 판단 부담 과다 | LLM auto-fill, read-only suggested |
| `requirement_waiver` (exception_type 5번째 값) | 1개 trial에서만 발생 | exception_qualifier free-text로 흡수 |
| `t/n/m_descriptor` | Layer 1에 Layer 3 정보 중복 | Layer 3에서 AJCC table 자동 생성 |
| `procedure_event` (anchor_type 4번째 값) | patient_event와 구분 불필요 | patient_event로 통합 |

### v1.2.2에서 유지/변경된 elements

| Element | 변경 사항 |
|---|---|
| `child_logic` | 유지 (AND/OR) |
| `variant_type` | 유지 (9-enum, annotator 입력) |
| `anchor_type` | 4-way → 3-way (trial_event / patient_event / unspecified) |
| `exception_type` | 5-enum → 4-enum (requirement_waiver 제거) |
| `cohort_scope` | 유지 |

상세 schema 정의는 `ontology_full_specification_unified_v1_2_2_ko.md` 참조.

---

## Appendix B: 자동화 영역 (어노테이터 참조용)

본 가이드라인은 **어노테이터의 판단이 필요한 영역만** 다룹니다. 다음 영역은 Python 파이프라인이 자동 처리하며, 어노테이터는 INCEpTION에서 결과만 검수합니다.

### B.1 완전 자동화 영역 (검수 불필요)

| Stage | 작업 | 자동화율 |
|---|---|---|
| A. Criterion 분리 | 원문에서 #1, #2... 추출 | 91% AUTO_PYTHON |
| F. Target subtype 결정 | 6-enum 분류 | 94% AUTO_LLM |
| I. HAS_VALUE 표준 추출 | numeric (operator, value, unit) | 94% AUTO_PYTHON |
| L. Span offset 계산 | text matching | 100% AUTO_PYTHON |
| M. INCEpTION JSON export | format conversion | 100% AUTO_PYTHON |
| N. Schema validation | enum/property check | 100% AUTO_PYTHON |

### B.2 LLM 자동화 영역 (sample 검수만)

| Stage | 작업 | 자동화율 |
|---|---|---|
| D. Semantic_category | 10-enum 분류 | 77% AUTO_LLM |
| E. Relation type | 결정 트리 적용 | 79% AUTO_LLM |
| J. HAS_TEMPORAL 표준 케이스 | 표준 시간 표현 | 72% AUTO_PYTHON |

### B.3 어노테이터 검수 필수 영역

| Stage | 작업 | 자동화율 |
|---|---|---|
| B. Splitting 결정 | composite/macro/nested + child_logic | 53% AUTO_LLM |
| G. Preferred_name | 약어 풀어쓰기, 추상 클래스 처리 | 66% AUTO_LLM |
| K. alternative_constraint | nested object 또는 자연어 fallback | 34% AUTO (대부분 manual) |
| J. HAS_TEMPORAL 비표준 | patient-specific anchor, formula | (위 72% 외 나머지) |

### B.4 어노테이터의 검수 강도

INCEpTION에서 LLM 출력을 검수할 때:

- **Tier 1 (B.1)**: 5-10% sample만 spot-check. 시스템 신뢰성에 의문이 들 때만 추가 검수.
- **Tier 2 (B.2)**: 모든 criterion 한 번씩 빠르게 확인. 의심 케이스 detail check.
- **Tier 3 (B.3)**: 모든 criterion detail 검수. 특히 Stage K는 LLM 출력을 처음부터 다시 작성하는 게 더 효율적인 경우 많음.

---

## Appendix C: Glossary

본 가이드라인 및 schema에서 사용하는 핵심 용어 정의.

| 용어 | 정의 |
|---|---|
| **Criterion** | 임상시험 적격성의 한 항목 (inclusion 또는 exclusion) |
| **CriterionSpan** | INCEpTION에서 criterion text 범위를 마킹한 span annotation |
| **ConceptMention** | Criterion text 내 entity surface form을 마킹한 span annotation |
| **Cross-layer relation** | Layer 1 (Protocol KG) ↔ Layer 3 (Domain KG) 간 typed relation |
| **REQUIRES_*/EXCLUDES_*** | Cross-layer relations: condition, treatment, biomarker, status, procedure |
| **HAS_VALUE / HAS_TEMPORAL** | 수치/시간 제약 표현 cross-layer relations |
| **INCLUDES_EXCEPTION** | EXCLUDES 또는 REQUIRES에서 carve-out 또는 waiver 표현 |
| **IS_PART_OF** | Layer 1 intra-layer relation: parent criterion ↔ child sub-criterion |
| **Composite split** | 한 criterion을 의미 단위로 분해 (다른 semantic_category, OR/AND 결합) |
| **Macro aggregate** | 다중 lab values 등 macro-statement의 분해 |
| **Nested exception** | EXCLUDES 또는 REQUIRES + INCLUDES_EXCEPTION으로 carve-out 표현 |
| **child_logic** | composite_split 자녀들의 group logic (AND/OR/XOR) |
| **cohort_scope** | Multi-cohort/basket trial에서 criterion이 적용되는 cohort id list |
| **strictness** | ~~v1.3으로 연기~~. hedging 표현은 INCEpTION comment 태그로 보존 |
| **anchor_type** | HAS_TEMPORAL anchor의 종류 (trial_event/patient_event/unspecified, 3-way) |
| **variant_type** | Biomarker variant의 분자 유형 (mutation/rearrangement/expression 등) |
| **variant_notation** | ~~LLM auto-fill, read-only suggested~~. Variant 표현 level (protein/cdna/exon_level 등) |
| **exception_type** | INCLUDES_EXCEPTION의 종류 (carveout 4종). ~~requirement_waiver~~는 exception_qualifier로 흡수 |
| **Calibration kappa** | 본 작업 시작 전 IAA 측정 (κ ≥ 0.7 gating) |
| **Blind subset** | LLM 출력 없이 from-scratch 어노테이션하는 trial 부분 (anchoring bias 통제) |
| **Adjudication** | 두 어노테이터 결과 비교 후 합의 또는 결정 |
| **drug_class_type** | Drug class 추상화 레벨 (explicit_list/closed_class/open_mechanism_class) |
| **equivalence_group_id** | OR semantics 평행 relations 묶음 식별자 |

---

## 문서 끝

본 가이드라인 v0.2 Stage 1은 어노테이터 작업 시작 전 필독 사항입니다. Stage 2 (Reference, edge cases, advanced sections)는 별도 문서로 작성됩니다.

가이드라인은 living document — 어노테이션 작업 진행 중 발견되는 새 패턴과 disagreement 처리 사례는 v0.3으로 누적 보강됩니다.
