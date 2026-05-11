# 4-Layer Clinical Trial Screening Ontology — Complete Specification (통합본 v1.1~v1.2.2, 한국어)

**Base 버전**: v1.1 (전체 schema 설계도)
**누적 변경 포함**: v1.2 (KEYNOTE-671 + SEQUOIA reference annotation 보강), v1.2.1 (6-trial schema stress test 보강), v1.2.2 (self-correction patch)
**Latest version**: v1.2.2
**문서 작성일**: 2026-05-05

---

## 변경 표시 범례

본 문서에서 사용하는 인라인 마킹:

- 🆕 **v1.2** — v1.2에서 신규 도입
- ✨ **v1.2.1** — v1.2.1에서 신규 도입
- 🔁 **v1.2 변경** — v1.1 대비 v1.2에서 enum 확장 또는 property 보강
- 🔁 **v1.2.1 변경** — v1.2 대비 v1.2.1에서 enum 확장 또는 property 보강
- ❌ **v1.2.2 제거** — v1.2 또는 v1.2.1에서 도입됐으나 v1.2.2에서 design integrity 위반으로 제거
- 🔁 **v1.2.2 축소** — v1.2.1에서 도입됐으나 v1.2.2에서 unused enum value 정리

표시 없는 항목은 v1.1 그대로 유지됨.

---

## Overview

본 문서는 Neo4j에 Labeled Property Graph (LPG)로 구현된 4-layer medical ontology를 기술함. 본 ontology는 small language model을 활용한 GraphRAG 기반 자동 임상시험 환자 적격성 스크리닝을 위해 설계됨. Primary domain은 oncology (NSCLC/PDAC).

---

## Architecture: 4-Layer Structure

```
Layer 1: Protocol KG    — Clinical trial eligibility criteria as structured rules
Layer 2: Terminology KG — Standard code identifiers (SNOMED CT, RxNorm, LOINC)
Layer 3: Domain KG      — Clinical semantic concepts and their relationships
Layer 4: Lexical KG     — All surface expressions (multilingual synonyms, abbreviations)
```

### Information Flow

```
[Inference direction: bottom-up]

Layer 4 (Lexical)      "췌관선암종" (Korean EMR text)
        │ REFERS_TO
        ▼
Layer 3 (Domain)       Concept:Condition {name: "PDAC"}
        │ MAPPED_TO                    ▲ REQUIRES_CONDITION
        ▼                             │
Layer 2 (Terminology)  StandardCode {SNOMED:372142002}
                                      │
Layer 1 (Protocol)     Criterion {text: "Metastatic PDAC"} ← Trial: NCT02923921
```

---

## Three Core Design Principles

### Principle 1: Layer Separation by Information Lifecycle

각 layer는 distinct change cycle과 authority를 갖는 정보를 캡슐화함:
- Layer 1 (Protocol): Ad hoc 변경 (신규 trial, amendment) — sponsor/IRB 관리
- Layer 2 (Terminology): 연 1회 변경 (SNOMED/RxNorm release) — 표준 단체 관리
- Layer 3 (Domain): Months-years 단위 변경 (가이드라인 업데이트) — 의학 학회 관리
- Layer 4 (Lexical): Daily 변경 (의료진 documentation 스타일) — 개별 institution 관리

Cross-layer edge가 유일한 coupling point. 한 layer 수정이 다른 layer로 전파되지 않음.

**❌ v1.2.2 retroactive fix**: v1.2의 Concept:Stage TNM descriptor가 본 원칙 위반으로 제거됨. AJCC TNM combo는 Layer 3 정보이며 Layer 1 Concept property에 저장하지 않음.

### Principle 2: Three-Dimensional Relationship Typing

모든 relationship type은 3개 orthogonal dimension으로 분류:
- **Structural**: Document-level 조직 (HAS_INCLUSION, HAS_EXCLUSION, CONTAINS)
- **Semantic**: Clinical 의미 (REQUIRES_CONDITION, EXCLUDES_TREATMENT 등)
- **Constraint**: Quantitative/temporal 조건 (HAS_VALUE, HAS_TEMPORAL)

### Principle 3: Hub-Centric Architecture

3개 node type — Condition, Drug, Criterion — 이 대다수 edge를 집중. 임의 두 hub 사이 거리는 최대 1 hop. LLM context window를 위한 subgraph retrieval 최적화.

---

## Complete Schema Definition

### Layer 1: Protocol KG

#### Node: Trial

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| nct_id | string (unique) | ✓ | ClinicalTrials.gov identifier |
| title | string | ✓ | Official trial name |
| short_title | string | | Abbreviated name for display |
| acronym | string | | Trial alias (예: SEQUOIA) |
| phase | string | ✓ | "Phase 1" / "Phase 2" / "Phase 3" / "Phase 4" |
| status | string | ✓ | "Recruiting" / "Active" / "Completed" / "Terminated" |
| sponsor | string | | Sponsor organization |
| condition | string | ✓ | Target disease (original text) |
| intervention | string | | Primary intervention |
| enrollment | integer | | Target enrollment number |
| start_date | date | | Trial start date |
| primary_endpoint | string | | Primary outcome measure |
| version | string | | Protocol version |
| source_url | string | | Original source URL |
| ✨ **cohorts** (v1.2.1) | array of {id, description} | | Multi-cohort/basket trial cohort registry |

#### Node: CriterionGroup

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| group_id | string (unique) | ✓ | Group identifier |
| type | string | ✓ | "inclusion" or "exclusion" |
| logic | string | ✓ | "AND" or "OR" |
| description | string | | Human-readable description |

Convention: Inclusion group은 AND 사용 (모두 충족 필요); Exclusion group은 OR 사용 (하나라도 충족 시 disqualify).

#### Node: Criterion

| Property | Type | Required | Description | 변경 |
|----------|------|----------|-------------|------|
| criterion_id | string (unique, immutable) | ✓ | Permanent identifier | unchanged |
| text | string | ✓ | 원본 프로토콜 텍스트 | unchanged |
| normalized_text | string | | NER-normalized 버전 | unchanged |
| short_label | string | | Display label (<5 단어) | unchanged |
| type | string | ✓ | "inclusion" or "exclusion" | unchanged |
| order | integer | ✓ | Group 내 위치 | unchanged |
| semantic_category | string | | enum (10 values) | 🔁 **v1.2 변경** (procedural_fitness 추가) |
| 🆕 **parent_role** (v1.2) | enum | | IS_PART_OF parent role | 🆕 v1.2 |
| ✨ **child_logic** (v1.2.1) | enum (AND/OR) | | composite_split 자녀 결합 logic | ✨ v1.2.1, 🔁 **v1.2.2 축소** (XOR 제거) |
| ✨ **cohort_scope** (v1.2.1) | array of strings | | Multi-cohort trial 적용 cohort | ✨ v1.2.1 |

**`semantic_category` 전체 enum** (v1.2.2 기준, 10개):
- `condition`
- `treatment_history`
- `observation`
- `performance_status`
- `biomarker`
- `comorbidity`
- `demographic`
- `imaging`
- `comedication`
- 🆕 **`procedural_fitness`** (v1.2 추가)

**🆕 `parent_role` enum** (v1.2):
- `macro_aggregate` — organ function 같은 묶음
- `nested_exception_parent` — carve-out 부모
- `composite_split` — 복합 의미 분해 부모

**✨ `child_logic` enum** (v1.2.2 active, 2개):
- `AND` — 모든 자녀 충족 필요 (inclusion default)
- `OR` — 자녀 하나만 충족 (exclusion default)
- ❌ **v1.2.2 제거**: ~~XOR~~ — stress test 0 occurrence, normalized_text 보존

`child_logic`은 default와 다른 semantics일 때만 명시 (예: SEQUOIA I1의 inclusion-OR).

**✨ `cohort_scope` 사용** (v1.2.1):
- Cohort identifier array (예: `["F-1"]`, `["F-2", "F-3"]`)
- 빈 array 또는 생략 시 모든 cohort 적용
- 예: KEYNOTE-001 I1_F1: `cohort_scope: ["F-1"]`

#### Layer 1 Relationships (Structural + Intra-layer)

| Relationship | From → To | Properties | 변경 |
|-------------|-----------|------------|------|
| HAS_INCLUSION | Trial → CriterionGroup | — | unchanged |
| HAS_EXCLUSION | Trial → CriterionGroup | — | unchanged |
| CONTAINS | CriterionGroup → Criterion | order: integer | unchanged |
| 🆕 **IS_PART_OF** | Criterion → Criterion | sub_order, parent_role | 🆕 **v1.2** |

**🆕 IS_PART_OF 사용 규칙** (v1.2):
- 부모 criterion은 macro-statement (예: "adequate organ function as defined in Table 1")
- 자녀 criterion은 sub-rule (예: "ANC ≥ 1500/µL")
- 자녀 criterion은 부모와 다른 `semantic_category` 가능
- Group logic은 AND가 default. ✨ v1.2.1부터 `Criterion.child_logic` property로 명시

---

### Layer 2: Terminology KG

(v1.1 그대로 — v1.2/v1.2.1/v1.2.2 변경 없음)

#### Node: StandardCode

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| code_id | string (unique) | ✓ | Combined identifier |
| code | string | ✓ | Code value |
| system | string | ✓ | "SNOMED CT" / "RxNorm" / "LOINC" / "NCI Thesaurus" |
| version | string | ✓ | Terminology version |
| display_name | string | ✓ | Standard display name |

#### Node: SemanticType

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| tui | string (unique) | ✓ | UMLS Type Unique Identifier |
| name | string | ✓ | Type name |

#### Layer 2 Relationships

| Relationship | From → To | Properties | Description |
|-------------|-----------|------------|-------------|
| HAS_SEMANTIC_TYPE | StandardCode → SemanticType | — | UMLS semantic 분류 |
| PARENT_OF | StandardCode → StandardCode | distance: integer | Terminology hierarchy |

---

### Layer 3: Domain KG

#### Node: Concept (parent label)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| concept_id | string (unique) | ✓ | Domain-internal identifier |
| preferred_name | string | ✓ | Standard name |
| semantic_type | string | ✓ | UMLS semantic type name |
| category | string | ✓ | "Condition" / "Drug" / "Observation" / "Procedure" / "Biomarker" / "Stage" |

#### Concept Subtypes (multi-label)

| Labels | Domain | Additional Properties | 변경 |
|--------|--------|----------------------|------|
| Concept:Condition | Diseases/diagnoses | icd10_code, snomed_code | unchanged |
| Concept:Drug | Medications/treatments | rxnorm_code, atc_code, investigational_name, alt_name | unchanged |
| Concept:Observation | Lab tests, clinical measurements, demographic values | loinc_code, value_range, unit | v1.2.2: LabTest → Observation 명칭 변경 |
| Concept:Procedure | Clinical procedures | cpt_code | unchanged |
| Concept:Biomarker | Molecular markers | gene_symbol, variant, assay_type, ✨ **variant_type**, ✨ **variant_notation** | ✨ v1.2.1 |
| Concept:Stage | Disease staging | system, value | ❌ **v1.2.2 제거**: ~~t_descriptor, n_descriptor, m_descriptor~~ (v1.2 도입 → v1.2.2 retroactive removal) |

#### ✨ Concept:Biomarker (v1.2.1, 🔁 v1.2.2 enum 축소)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| concept_id | string (unique) | ✓ | Domain identifier |
| preferred_name | string | ✓ | Standard name |
| gene_symbol | string | | HUGO gene symbol (예: "EGFR", "ALK") |
| variant | string | | Specific variant (예: "T790M", "Ex19del") |
| assay_type | string | | Assay 종류 |
| ✨ **variant_type** | enum (6 values) | | v1.2.1 도입, 🔁 v1.2.2 축소 |
| ✨ **variant_notation** | enum (5 values) | | v1.2.1 도입, 🔁 v1.2.2 축소 + LLM auto-fill |

**✨ `variant_type` enum** (v1.2.2 active, 6개):
- `mutation` — point mutation
- `rearrangement` — chromosomal rearrangement
- `fusion` — specific gene fusion product
- `deletion` — deletion variant
- `insertion` — insertion variant
- `expression` — gene/protein expression level (PD-L1 등)

❌ **v1.2.2 제거**:
- ~~`amplification`~~ — NSCLC stress test 미관찰. v1.3에서 HER2/MET 등장 시 재도입
- ~~`methylation`~~ — Glioblastoma 영역
- ~~`unknown`~~ — null로 처리 (property 자체 생략)

**✨ `variant_notation` enum** (v1.2.2 active, 5개):
- `protein` — protein-level (예: "L858R")
- `cdna` — cDNA-level (예: "c.2369C>T")
- `genomic` — genomic-level
- `exon_level` — exon-level macro-class (예: "Ex19del")
- `wildcard` — position-pattern with wildcard (예: "G719X")

❌ **v1.2.2 제거**:
- ~~`class_level`~~ — 명확한 사례 부재. preferred_name 자연어로 충분

🔁 **v1.2.2 처리 변경**: variant_notation은 schema-level metadata. INCEpTION에서 read-only suggested feature로 표시. LLM Pre-annotation Pipeline의 Prompt 3 (preferred_name)에서 자동 채움. Annotator 검수만 수행.

#### ❌ Concept:Stage TNM descriptor 제거 (v1.2 → v1.2.2 retroactive)

v1.2에서 도입됐던 t_descriptor, n_descriptor, m_descriptor properties는 v1.2.2에서 **제거됨**. 이유: Layer Separation 원칙 (Principle 1) 위반.

**Concept:Stage v1.2.2 properties** (TNM descriptor 제거 후):

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| concept_id | string (unique) | ✓ | Domain identifier |
| preferred_name | string | ✓ | Standard name (예: "Stage IIIB", "Stage IIIB N2-subset") |
| system | string | ✓ | Staging system (예: "AJCC 8th") |
| value | string | ✓ | Stage value (예: "Stage IIIB") |

**KEYNOTE-671 "Stage IIIB (N2)" 같은 restricted stage 처리** (v1.2.2 권장 옵션):

별도 sub-stage Concept으로 분리:
```
Concept:Stage {
  concept_id: "STAGE_IIIB_N2",
  preferred_name: "Stage IIIB N2-subset",
  value: "Stage IIIB (N2)"
}
(Stage IIIB N2-subset) -[:IS_A]-> (Stage IIIB)
```

AJCC TNM 조합은 Layer 3 Domain KG 구축 시 별도 import (`HAS_TNM_COMBO` edges).

#### Node: Mapping

(v1.1 그대로)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| system | string | ✓ (composite key) | Code system name ("KCD-8", "SMC_local") |
| code | string | ✓ (composite key) | Code value |
| version | string | | System version |
| display | string | | Source language display name |

#### Layer 3 Relationships (Intra-layer)

(v1.1 그대로)

| Relationship | From → To | Properties | Description |
|-------------|-----------|------------|-------------|
| IS_A | Concept → Concept | depth: integer | Subsumption hierarchy |
| TREATS | Drug → Condition | line_of_therapy: string | Drug treats condition |
| ASSESSED_BY | Condition → Observation/Procedure | purpose: string | Condition 평가 방법 |
| HAS_STAGE | Condition → Stage | staging_system: string | Disease staging |
| CONTAINS_DRUG | Drug → Drug | — | Combination regimen 구성 |
| HAS_ALTERNATIVE | Drug → Drug | context: string | Therapeutic alternatives |
| HAS_MAPPING | Concept → Mapping | — | External code system 연결 |

---

### Layer 4: Lexical KG

(v1.1 그대로 — v1.2/v1.2.1/v1.2.2 변경 없음)

#### Node: Mention

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| mention_id | string (unique) | ✓ | Identifier |
| surface_form | string | ✓ | 원본 텍스트 토큰 |
| language | string | ✓ | "ko" / "en" |
| source_type | string | | "EMR" / "trial" / "literature" |
| frequency | integer | | Corpus 출현 빈도 |

#### Node: SynonymGroup

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| group_id | string (unique) | ✓ | Group identifier |
| canonical_form | string | ✓ | Preferred representative expression |
| semantic_category | string | | Category |

#### Layer 4 Relationships

| Relationship | From → To | Properties | Description |
|-------------|-----------|------------|-------------|
| BELONGS_TO | Mention → SynonymGroup | — | Synonym group member |
| VARIANT_OF | Mention → Mention | variant_type: string | Variant 관계 |

---

### Cross-Layer Relationships

#### Layer 4 → Layer 3: REFERS_TO

| Relationship | From → To | Properties |
|-------------|-----------|------------|
| REFERS_TO | SynonymGroup → Concept | confidence: float, mapping_method: string |

#### Layer 3 → Layer 2: MAPPED_TO

| Relationship | From → To | Properties |
|-------------|-----------|------------|
| MAPPED_TO | Concept → StandardCode | confidence: float, mapping_type: string |

#### Layer 1 → Layer 3: Semantic Relationships

| Relationship | From → To | Properties | 변경 |
|-------------|-----------|------------|------|
| REQUIRES_CONDITION | Criterion → Condition | certainty | unchanged (❌ v1.2.2: ~~strictness~~ 제거) |
| REQUIRES_TREATMENT | Criterion → Drug | temporal, status, line_of_therapy, 🆕 **alternative_constraint** | 🆕 v1.2 (alt_const). ❌ v1.2.2: ~~strictness~~ |
| REQUIRES_BIOMARKER | Criterion → Biomarker | variant, status, assay_method | unchanged (❌ v1.2.2: ~~strictness~~) |
| REQUIRES_STATUS | Criterion → Observation | status, version, 🆕 **alternative_constraint** | 🆕 v1.2. ❌ v1.2.2: ~~strictness~~ |
| REQUIRES_PROCEDURE | Criterion → Procedure | role | unchanged (❌ v1.2.2: ~~strictness~~) |
| EXCLUDES_CONDITION | Criterion → Condition | negation, 🆕 **condition_qualifier** | 🆕 v1.2 |
| EXCLUDES_TREATMENT | Criterion → Drug | temporal, drug_class_basis, 🆕 **drug_class_type** | 🆕 v1.2 |
| EXCLUDES_COMEDICATION | Criterion → Drug | condition, alternatives, 🆕 **alternative_constraint** | 🆕 v1.2 |
| EXCLUDES_STATUS | Criterion → Concept | status | unchanged |
| 🆕 **EXCLUDES_PROCEDURE** | Criterion → Procedure | temporal, scope | 🆕 **v1.2** |
| 🆕 **INCLUDES_EXCEPTION** | Criterion → Concept | exception_qualifier, exception_type (4 enum) | 🆕 **v1.2**. ❌ v1.2.2: ~~requirement_waiver enum value 제거~~ |

❌ **v1.2.2 제거**: `strictness` property는 모든 REQUIRES_* relation에서 제거됨. 1 trial concentration (PACIFIC만 6 occurrences). v1.3로 연기.

#### Layer 1 → Layer 3: Constraint Relationships

| Relationship | From → To | Properties | 변경 |
|-------------|-----------|------------|------|
| HAS_VALUE | Criterion → Observation/Concept | operator, value, unit, scale, 🆕 **alternative_constraint** | 🆕 v1.2. ❌ v1.2.2: ~~strictness~~ |
| HAS_TEMPORAL | Criterion → Drug/Concept | operator, value, unit, anchor, 🆕 **direction**, ✨ **anchor_type** (3 enum) | 🆕 v1.2 (direction), ✨ v1.2.1 (anchor_type), 🔁 v1.2.2 (procedure_event 제거). ❌ v1.2.2: ~~strictness~~ |

---

### v1.2/v1.2.1/v1.2.2 신규 Cross-layer Relations 상세 정의

#### 🆕 EXCLUDES_PROCEDURE (v1.2 NEW)

**From → To**: Criterion → Procedure (Concept:Procedure)

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| temporal | string | ✓ | "any_prior" / "within_X_days" / "during_screening" |
| scope | string | | Procedure scope qualifier |

**Examples**:
- KEYNOTE-671 E5: "Has had an allogenic tissue/solid organ transplant" → EXCLUDES_PROCEDURE → Allogenic transplant, temporal=`any_prior`
- KEYNOTE-671 E16: "prior radiotherapy within 2 weeks" → EXCLUDES_PROCEDURE → Radiotherapy + HAS_TEMPORAL
- SEQUOIA E#17: "Major surgery within 28 days" → EXCLUDES_PROCEDURE, scope=`major_surgery`

#### 🆕 INCLUDES_EXCEPTION (v1.2 NEW, 🔁 v1.2.2 수정)

**From → To**: Criterion → Concept (Concept:Condition / Concept:Drug / Concept:Procedure)

**Semantics**: 부모 criterion이 broad EXCLUDES_*로 정의되어 있을 때 명시적으로 carve-out되는 exception.

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| exception_qualifier | string \| object | | Exception 적용 추가 조건 |
| exception_type | enum | ✓ | 4 values (v1.2.2 active) |

**`exception_type` enum** (v1.2.2 active, 4개):
- `condition_carveout`
- `procedure_carveout`
- `drug_carveout`
- `status_carveout`

❌ **v1.2.2 제거**: ~~`requirement_waiver`~~ — 1개 패턴 (KEYNOTE-001 squamous histology)에서 도입. exception_qualifier free-text로 동등 표현 가능.

**Examples**:

v1.2 condition_carveout (KEYNOTE-671 E20):
- 부모: "additional malignancy that is progressing or requires active treatment within 5 years" → EXCLUDES_CONDITION
- 자녀들: INCLUDES_EXCEPTION → BCC, SCC, noninvasive bladder carcinoma, carcinoma in situ
- exception_type=`condition_carveout`, exception_qualifier=`"undergone potentially curative therapy"`

🔁 **v1.2.2 변경**: KEYNOTE-001 histology waiver 처리 변경:
```
부모: REQUIRES_BIOMARKER → "EGFR/ALK molecular testing"
자녀: INCLUDES_EXCEPTION
  exception_type: "condition_carveout"  ← requirement_waiver 대신 재사용
  exception_qualifier: {
    applies_when: "predominantly_squamous_histology OR known_KRAS_mutation",
    waiver_type: "requirement_exempt",   ← free-text로 보존
    rationale: "not_standard_of_care_for_squamous"
  }
```

---

### v1.2/v1.2.1/v1.2.2 Property 상세 정의

#### 🆕 `alternative_constraint` (v1.2)

**적용 relations**: REQUIRES_TREATMENT, REQUIRES_STATUS, EXCLUDES_COMEDICATION, HAS_VALUE

**Type**: string | object (optional)

**Examples**:
- KEYNOTE-671 I4c: primary `{operator: "≥", value: 9.0, unit: "g/dL"}`, alternative_constraint: `{operator: "≥", value: 5.6, unit: "mmol/L"}`
- KEYNOTE-671 I4e: primary `{operator: "≤", value: 1.5, unit: "× ULN"}`, alternative_constraint: `"direct bilirubin within normal limits if total bilirubin > 1.5 × ULN"`
- SEQUOIA E2: alternative_constraint: `{alternatives: ["LMWH", "DOAC"], sub_constraint: "t½ < 24 hours"}`

#### 🆕 HAS_TEMPORAL.`direction` (v1.2)

**Enum values**: `before` / `after` / `within` / `since`

**Default**: `before`

#### 🆕 EXCLUDES_TREATMENT.`drug_class_type` (v1.2)

**Enum values**: `explicit_list` / `closed_class` / `open_mechanism_class`

**Examples**:
- `explicit_list`: SEQUOIA E4 — "5-FU and oxaliplatin"
- `closed_class`: "platinum-containing regimen"
- `open_mechanism_class`: KEYNOTE-671 E14 — "any coinhibitory T-cell receptor agent"

#### 🆕 EXCLUDES_CONDITION.`condition_qualifier` (v1.2)

**Examples**:
- KEYNOTE-671 E3: pneumonitis/ILD `condition_qualifier: "required_or_requires_steroid_treatment"`
- KEYNOTE-671 E4: infection `condition_qualifier: "active_AND_requiring_systemic_therapy"`

#### ✨ HAS_TEMPORAL.`anchor_type` (v1.2.1, 🔁 v1.2.2 축소)

**Enum values** (v1.2.2 active, 3개):
- `trial_event` — Trial-level standard event (Randomization, first_dose 등)
- `patient_event` — Patient-specific historical event (procedure events 포함)
- `unspecified` — 분류 불가 (default)

❌ **v1.2.2 제거**: ~~`procedure_event`~~ — patient_event와 EMR query path 동일. 분리 정당화 부족. 이전 procedure_event 케이스는 patient_event로 통합.

**Examples**:
- KEYNOTE-671 I4: "within 10 days of randomization" → anchor_type=`trial_event`
- AURA3 I8d: "biopsy after documented disease progression on first line EGFR TKI" → anchor_type=`patient_event`
- PACIFIC I5: "not progressed following CRT" → anchor_type=`patient_event`

#### ❌ `strictness` (v1.2.1 도입 → v1.2.2 제거)

v1.2.1에서 HAS_VALUE, HAS_TEMPORAL, REQUIRES_* 7개 relation에 도입됐으나 v1.2.2에서 **제거됨**.

**제거 사유**: 1 trial concentration. PACIFIC에서만 6 occurrences (I4g 5 + I6b 1). 6 trial 중 5 trial은 strictness 사용 0회. Frequency-justified addition 원칙에 어긋남.

**대체 처리**: 마이그레이션 시 `required` strictness는 단순 삭제 (default). `encouraged`/`optional`/`discretionary`는 normalized_text에 자연어 보존:
```
Criterion.normalized_text += " [strictness: encouraged]"
```

**v1.3 trigger**: Phase 2 SMC validation에서 ≥3 trial occurrence 시 재도입 검토.

---

## 🆕 INCEpTION Layer/Feature Mapping (v1.2 신규 섹션, 🔁 v1.2.2 갱신)

### Span Layers

| INCEpTION Layer | 매핑 schema entity | Features |
|---|---|---|
| `CriterionSpan` | Layer 1 Criterion | criterion_id, type, semantic_category (10 values), short_label, normalized_text, parent_criterion_id, parent_role, ✨ child_logic (2 values, v1.2.2), ✨ cohort_scope |
| `ConceptMention` | Layer 1 → Layer 3 매핑 surface | target_subtype, target_preferred_name, kb_link, ✨ variant_type (6 values, v1.2.2), ✨ variant_notation (5 values, v1.2.2, **read-only suggested**) |

### Relation Layers (v1.2.2 갱신)

| INCEpTION Relation | From → To | Features |
|---|---|---|
| `IS_PART_OF` | CriterionSpan → CriterionSpan | sub_order, parent_role |
| `REQUIRES_CONDITION` | CriterionSpan → ConceptMention | certainty |
| `REQUIRES_TREATMENT` | CriterionSpan → ConceptMention | temporal, status, line_of_therapy, alternative_constraint |
| `REQUIRES_BIOMARKER` | CriterionSpan → ConceptMention | variant, status, assay_method |
| `REQUIRES_STATUS` | CriterionSpan → ConceptMention | status, version, alternative_constraint |
| `REQUIRES_PROCEDURE` | CriterionSpan → ConceptMention | role |
| `EXCLUDES_CONDITION` | CriterionSpan → ConceptMention | negation, condition_qualifier |
| `EXCLUDES_TREATMENT` | CriterionSpan → ConceptMention | temporal, drug_class_basis, drug_class_type |
| `EXCLUDES_COMEDICATION` | CriterionSpan → ConceptMention | condition, alternatives, alternative_constraint |
| `EXCLUDES_STATUS` | CriterionSpan → ConceptMention | status |
| `EXCLUDES_PROCEDURE` | CriterionSpan → ConceptMention | temporal, scope |
| `INCLUDES_EXCEPTION` | CriterionSpan → ConceptMention | exception_qualifier, exception_type (4 values, v1.2.2) |
| `HAS_VALUE` | CriterionSpan → ConceptMention | operator, value, unit, scale, alternative_constraint |
| `HAS_TEMPORAL` | CriterionSpan → ConceptMention | operator, value, unit, anchor, direction, ✨ anchor_type (3 values, v1.2.2) |

❌ **v1.2.2 제거 features**: 모든 relation에서 `strictness` 제거.

### Property Name Mapping: Ontology Schema ↔ INCEpTION Feature ↔ Pipeline JSON

INCEpTION feature 이름은 annotation 문맥에서의 명확성을 위해 ontology schema property와 다를 수 있음. Pipeline JSON은 INCEpTION feature 이름과 동일하게 유지하여 Stage M (INCEpTION export) 시 1:1 매핑.

#### CriterionSpan features

| INCEpTION Feature | Ontology Schema Property | Pipeline JSON Key | 비고 |
|---|---|---|---|
| criterion_id | Criterion.criterion_id | criterion_id | 동일 |
| type | Criterion.type | type | 동일 |
| semantic_category | Criterion.semantic_category | semantic_category | 동일 |
| text | Criterion.text | text | 동일 (v1.2.2에서 original_text → text 수정) |
| short_label | Criterion.short_label | short_label | 동일 |
| normalized_text | Criterion.normalized_text | normalized_text | 동일 |
| parent_criterion_id | IS_PART_OF edge target | parent_criterion_id | Relation을 node property로 flatten |
| parent_role | Criterion.parent_role | parent_role | 동일 |
| child_logic | Criterion.child_logic | child_logic | 동일 |
| cohort_scope | Criterion.cohort_scope | cohort_scope | 동일 |

#### ConceptMention features

| INCEpTION Feature | Ontology Schema Property | Pipeline JSON Key | 비고 |
|---|---|---|---|
| target_subtype | Concept.category | target_subtype | `target_` prefix: relation의 target을 가리킴. Concept 노드 자체에서는 `category` |
| target_preferred_name | Concept.preferred_name | target_preferred_name | `target_` prefix: 동상. Concept 노드 자체에서는 `preferred_name` |
| target_text_span | Mention.surface_form (Layer 4) | target_text_span | ConceptMention의 span 범위. Layer 4 surface_form에 대응 |
| kb_link | Concept.concept_id → StandardCode | kb_link | INCEpTION KB lookup으로 채움 |
| variant_type | Concept:Biomarker.variant_type | biomarker_details.variant_type | Pipeline에서는 biomarker_details object 내부에 중첩 |
| variant_notation | Concept:Biomarker.variant_notation | biomarker_details.variant_notation | LLM auto-fill, annotator 검수만 수행 |

#### Relation properties

| INCEpTION Feature | Ontology Schema Property | Pipeline JSON Key | 비고 |
|---|---|---|---|
| operator | HAS_VALUE.operator / HAS_TEMPORAL.operator | properties.operator | Pipeline에서는 properties object 내부에 중첩 |
| value | HAS_VALUE.value / HAS_TEMPORAL.value | properties.value | 동상 |
| unit | HAS_VALUE.unit / HAS_TEMPORAL.unit | properties.unit | 동상 |
| anchor | HAS_TEMPORAL.anchor | properties.anchor | 동상 |
| direction | HAS_TEMPORAL.direction | properties.direction | 동상 |
| anchor_type | HAS_TEMPORAL.anchor_type | properties.anchor_type | 동상 |
| alternative_constraint | (각 relation).alternative_constraint | properties.alternative_constraint | 동상 |
| (기타 semantic relation properties) | 각 relation 정의 참조 | properties.{key} | 동상 |

**설계 원칙**: INCEpTION feature에서 `target_` prefix가 붙는 이유는 annotation 문맥에서 "이 relation의 target concept"를 명시하기 위함. Ontology schema의 Concept 노드에서는 자기 자신의 property이므로 prefix 없이 `category`, `preferred_name`을 사용. Pipeline JSON은 INCEpTION과 1:1 정렬하여 export 변환 불필요.

### KB Integration

`ConceptMention.kb_link`는 INCEpTION의 Knowledge Base 기능 활용:
- 외부 KB로 SNOMED CT, RxNorm, LOINC, NCI Thesaurus 통합
- 본 프로젝트 Layer 3 ontology를 자체 KB로 import

### 어노테이션 워크플로우

1. Criterion text 전체를 `CriterionSpan`으로 마킹
2. Macro-criterion이면 sub-criterion들을 별도 CriterionSpan + IS_PART_OF
3. Entity surface form을 `ConceptMention`으로 마킹 + KB lookup
4. CriterionSpan → ConceptMention 사이에 cross-layer relation + features
5. Nested exception이 있으면 INCLUDES_EXCEPTION으로 carve-out

🔁 **v1.2.2 변경**: variant_notation은 LLM auto-fill로 처리. Annotator는 검수만 수행.

---

## Reference Instances

### Primary Reference: NCT03425643 (KEYNOTE-671) — 🆕 v1.2

NSCLC primary domain의 main reference instance.

**Trial Summary**:
- NCT ID: NCT03425643 (KEYNOTE-671)
- Phase: Phase 3
- Intervention: Pembrolizumab + platinum doublet, neoadjuvant + adjuvant
- Condition: Resectable Stage II/IIIA/IIIB(N2) NSCLC
- Enrollment: 797

🔁 **v1.2.2 영향**: 원래 reference에서 "Stage IIIB (T3-4N2)"의 TNM descriptor는 별도 sub-stage Concept으로 마이그레이션됨. 어노테이션 텍스트 자체는 영향 없음.

### Supplementary Reference: NCT02923921 (SEQUOIA)

PDAC schema validation 보조 reference.

### ✨ Stress Test References (v1.2.1)

| Trial | NCT | 핵심 stress test 가치 |
|---|---|---|
| ALEX | NCT02075840 | ALK rearrangement biomarker |
| AURA3 | NCT02151981 | EGFR T790M, mathematical washout |
| PACIFIC | NCT02125461 | Concurrent CRT, treatment_modality (v1.3 후보) |
| KEYNOTE-001 | NCT01295827 | Multi-cohort basket trial, cohort_scope |

🔁 **v1.2.2 영향**: PACIFIC strictness 어노테이션은 normalized_text로 마이그레이션. KEYNOTE-001 requirement_waiver는 condition_carveout + exception_qualifier free-text로 마이그레이션.

---

## Naming Conventions

(v1.1 그대로)

| Element | Convention | Examples |
|---------|-----------|----------|
| Node labels | PascalCase | Trial, Criterion, Concept |
| Relationship types | UPPER_SNAKE_CASE | HAS_INCLUSION, REQUIRES_CONDITION |
| Properties | lower_snake_case | nct_id, criterion_id |
| ID format | {nct_id}_{type}{num} | NCT02923921_I3 |

---

## Relationship to Prior Work

- **Criteria2Query (Yuan et al., JAMIA 2019)**: 🆕 v1.2 (direction, alternative_constraint), ✨ v1.2.1 (anchor_type)
- **CTKG (Hao et al., Sci Rep 2022)**: 🆕 v1.2 (EXCLUDES_PROCEDURE, INCLUDES_EXCEPTION)
- **n2c2 2018 Track 1**: 🆕 v1.2 (IS_PART_OF)
- **🆕 INCEpTION (Klie et al., COLING 2018)** (v1.2 추가)

---

## Implementation

- **Graph database**: Neo4j (LPG)
- **🆕 Annotation tool** (v1.2): INCEpTION
- **Current scale**:
  - v1.1: ~65 nodes, ~90 relationships (SEQUOIA single)
  - 🆕 v1.2: ~75 nodes, ~110 relationships (KEYNOTE-671 + SEQUOIA dual)
  - ✨ v1.2.1: 47 criteria, 58 patterns, 6 trial stress test
  - 🔁 v1.2.2: v1.2.1 동일 + design integrity cleanup
- **Target scale**: 200-500 domain concepts, 50-100 trials
- **Primary use case**: GraphRAG-based eligibility screening with small LLMs

---

## Schema-level Findings 미해결 항목

### v1.2 가이드라인 input

1. `Concept:Stage` confirmation_rule
2. `equivalent_tests` grouping (Cr clearance OR GFR)
3. "× ULN" units EMR matching
4. "Previously untreated" universal-scope EXCLUDES_TREATMENT
5. "clinical progression" status 분류
6. Range expression "0–1" lower-bound
7. "Baseline" 비교 기준
8. "non-adenocarcinoma" 광의 카테고리

### ✨ v1.2.1 추가 (변경 없음)

9. Status negation expression (not_progressed → CR/PR/SD)
10. 2-perpendicular measurement_method
11. Drug-class-specific washout
12. Order-independence qualifier
13. Mathematical formula temporal

### 🔁 v1.2.2 추가 (self-correction defer)

14. **`strictness` re-introduction** — Phase 2 SMC validation에서 ≥3 trial occurrence 시 재도입
15. **Requirement waiver enum** — 30 trial 후 ≥3 패턴 재발 시 enum 승격
16. **`child_logic.XOR`** — NSCLC 외 도메인 확장 시 재검토
17. **`variant_type.amplification/methylation/unknown`** — 도메인 확장 시 재도입
18. **`anchor_type.procedure_event`** — patient_event 병합 유지
19. **`Concept:Stage` TNM descriptor** — Layer 3 Domain KG construction에서 처리

---

# 변경대비표 (v1.0 → v1.1 → v1.2 → v1.2.1 → v1.2.2)

## Layer 1 (Protocol KG) 변경

| 요소 | v1.0 | v1.1 | v1.2 | v1.2.1 | v1.2.2 |
|---|---|---|---|---|---|
| Trial.cohorts | — | — | — | ✨ NEW | unchanged |
| Criterion.semantic_category | 9 enum | 9 enum | 🔁 10 enum | 10 enum | 10 enum |
| Criterion.parent_role | — | — | 🆕 NEW | unchanged | unchanged |
| Criterion.child_logic | — | — | — | ✨ NEW (3 values) | 🔁 **2 values** (XOR 제거) |
| Criterion.cohort_scope | — | — | — | ✨ NEW | unchanged |
| IS_PART_OF relation | — | — | 🆕 NEW | unchanged | unchanged |

## Layer 3 (Domain KG) 변경

| 요소 | v1.0 | v1.1 | v1.2 | v1.2.1 | v1.2.2 |
|---|---|---|---|---|---|
| Concept:Stage.t_descriptor | — | — | 🆕 NEW | unchanged | ❌ **제거** (Layer separation 위반) |
| Concept:Stage.n_descriptor | — | — | 🆕 NEW | unchanged | ❌ **제거** |
| Concept:Stage.m_descriptor | — | — | 🆕 NEW | unchanged | ❌ **제거** |
| Concept:Biomarker.variant_type | — | — | — | ✨ NEW (9 enum) | 🔁 **6 enum** (3개 제거) |
| Concept:Biomarker.variant_notation | — | — | — | ✨ NEW (6 enum) | 🔁 **5 enum** (1개 제거) + LLM auto-fill |

## Cross-layer Semantic Relations 변경

| Relation | v1.0 | v1.1 | v1.2 | v1.2.1 | v1.2.2 |
|---|---|---|---|---|---|
| REQUIRES_CONDITION | exists | exists | exists | 🔁 +strictness | ❌ ~~strictness~~ 제거 |
| REQUIRES_TREATMENT | exists | exists | 🔁 +alternative_constraint | 🔁 +strictness | ❌ ~~strictness~~ |
| REQUIRES_BIOMARKER | exists | exists | exists | 🔁 +strictness | ❌ ~~strictness~~ |
| REQUIRES_STATUS | exists | exists | 🔁 +alternative_constraint | 🔁 +strictness | ❌ ~~strictness~~ |
| REQUIRES_PROCEDURE | exists | exists | exists | 🔁 +strictness | ❌ ~~strictness~~ |
| EXCLUDES_CONDITION | exists | exists | 🔁 +condition_qualifier | unchanged | unchanged |
| EXCLUDES_TREATMENT | exists | exists | 🔁 +drug_class_type | unchanged | unchanged |
| EXCLUDES_COMEDICATION | exists | exists | 🔁 +alternative_constraint | unchanged | unchanged |
| EXCLUDES_STATUS | exists | exists | exists | unchanged | unchanged |
| EXCLUDES_PROCEDURE | — | — | 🆕 NEW | unchanged | unchanged |
| INCLUDES_EXCEPTION | — | — | 🆕 NEW (4 enum) | 🔁 **5 enum** (+requirement_waiver) | ❌ **4 enum** (waiver 제거) |

## Cross-layer Constraint Relations 변경

| Relation | v1.0 | v1.1 | v1.2 | v1.2.1 | v1.2.2 |
|---|---|---|---|---|---|
| HAS_VALUE | exists | exists | 🔁 +alternative_constraint | 🔁 +strictness, +measurement_method | ❌ ~~strictness~~ 제거 |
| HAS_TEMPORAL | exists | exists | 🔁 +direction | 🔁 +anchor_type (4 enum), +strictness | 🔁 **anchor_type 3 enum**, ❌ ~~strictness~~ |

## 누적 변경 통계

| 버전 | 변경 동기 | 신규 relation | Property 추가 | Enum 추가 | 누적 reference |
|---|---|---|---|---|---|
| v1.1 | Schema 정형화 (initial) | 13 cross-layer | — | — | SEQUOIA (1 trial) |
| v1.2 | Schema validation | +EXCLUDES_PROCEDURE +INCLUDES_EXCEPTION (2개) | +6 properties (alt_constraint, direction, drug_class_type, condition_qualifier, t/n/m_descriptor, parent_role) | procedural_fitness | KEYNOTE-671 + SEQUOIA (2 trial) |
| v1.2.1 | 6-trial stress test | — | +4 properties (child_logic, cohort_scope, anchor_type, strictness) | variant_type, variant_notation, requirement_waiver | + ALEX, AURA3, PACIFIC, KEYNOTE-001 (6 trial) |
| **v1.2.2** | **Self-correction patch** | — | **−2 properties** (~~strictness~~, ~~t/n/m_descriptor~~) | **−1 enum value** (~~requirement_waiver~~) + 다수 enum value 정리 | 6 trial 동일, design integrity cleanup |

## v1.2.2 active 추가 항목 (v1.1 대비 누적)

| Category | Active count |
|---|---|
| New relations | 3 (EXCLUDES_PROCEDURE, INCLUDES_EXCEPTION, IS_PART_OF) |
| New properties | 9 (parent_role, alternative_constraint, direction, drug_class_type, condition_qualifier, child_logic, cohort_scope, anchor_type, variant_type+variant_notation) |
| Enum extensions | 1 (semantic_category +procedural_fitness) |
| Trial-level | 1 (cohorts) |

**비교**: v1.2.1에서는 13 properties + 4 enum values 추가 → v1.2.2에서 design integrity 검토 후 9 properties + 1 enum 확장으로 압축 (4 properties + 3 enum values 제거).

## v1.3 예정 변경 (참고용)

(v1.2.2에서 v1.3로 연기된 항목)

**v1.2.1 → v1.2.2에서 새로 v1.3로 연기**:
- `strictness` re-introduction (Phase 2 데이터 trigger)
- `requirement_waiver` enum 승격 (30 trial 후 ≥3 패턴 trigger)
- `child_logic.XOR` (도메인 확장 trigger)
- `variant_type.amplification/methylation` (도메인 확장 trigger)
- `anchor_type.procedure_event` (병합 유지)
- `Concept:Stage` TNM descriptor (Layer 3 KB construction)

**기존 v1.2.1 deferred 유지**:
- General conditional inclusion mechanism
- Drug class strength + generation 통합 (class_qualifier object)
- Concept:Biomarker.clinical_category formal enum
- Procedure.scope_qualifier object schema
- Concept:Stage.system_version property

v1.3는 Phase 2 SMC validation 후 도입 예정.

---

## Self-Correction Disclosure (Paper Methods 입력)

본 통합본은 **schema iteration의 transparency** 사례를 보여줌. v1.2.1 release 후 design integrity 검토에서 다음 사항이 식별됨:

1. **Frequency-justified addition 원칙 위반**: v1.2.1의 일부 element는 1-2 trial occurrence에서 도입되어 stress test 정당화 기준 약화
2. **Layer Separation 원칙 위반 (retroactive)**: v1.2의 TNM descriptor는 Principle 1 위반

v1.2.2는 이 두 비판에 대한 self-correction patch. Paper Methods 활용 narrative:

> "Schema v1.2.1 was followed by a self-correction patch (v1.2.2) after design integrity review. Five elements introduced in v1.2.1 — `strictness`, `requirement_waiver`, and unused enum values in `child_logic`, `variant_type`, `variant_notation`, `anchor_type` — were identified as either insufficiently justified by stress-test frequency or violating layer separation principles. The Concept:Stage TNM descriptor introduced in v1.2 was retroactively removed for the same layer separation violation. This iterative self-correction reflects the methodology's commitment to frequency-justified schema additions and clean layer boundaries, deferring premature generalizations to v1.3 pending Phase 2 validation data."

이는 schema design의 정직한 보고이며, reviewer rigor 검토에서 강점이 됨.

---

## Appendix: Document Lineage

- **v1.0** (initial): Pre-stress-test, basic 4-layer 구조
- **v1.1** (`ontology_full_specification.md`): Schema 정형화 + SEQUOIA reference instance
- **v1.2** (`ontology_full_specification_v1.2.md`): KEYNOTE-671 + SEQUOIA reference annotation 보강 (9개 추가). ❌ TNM descriptor는 v1.2.2에서 retroactive 제거
- **v1.2.1** (`ontology_full_specification_v1.2.1.md`): 6-trial schema stress test 보강 (6개 추가). ❌ strictness, requirement_waiver, 일부 enum value는 v1.2.2에서 retroactive cleanup
- **v1.2.2** (`ontology_full_specification_v1.2.2_ko.md`): Self-correction patch. v1.2/v1.2.1 design integrity 위반 항목 정리. 본 통합본 (`ontology_full_specification_unified_v1.2.2_ko.md`)이 latest active spec.
- **v1.3** (향후): Phase 2 SMC validation 후 도입.
