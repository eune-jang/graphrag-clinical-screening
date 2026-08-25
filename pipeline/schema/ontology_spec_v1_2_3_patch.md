# 온톨로지 스펙 v1.2.3 패치 (변경 지시서)

**대상 문서**: `ontology_full_specification_unified_v1_2_2_ko.md`
**작성일**: 2026-08-10
**변경 동기**: Annotation guideline v1.2 정합성 검토 + LLM 파이프라인 검증 가능성 검토 (Stage 1 IAA 후속)
**변경 규모**: property 추가/삭제 없음. 사용 규칙 4건 수정, relation 정의 1건 확장, pipeline JSON convention 2건, 미해결 항목 1건 추가

---

## 변경 요약

| # | 대상 | 변경 유형 | 한 줄 요약 |
| --- | --- | --- | --- |
| 1 | Criterion.child_logic 사용 규칙 | 규칙 변경 | default 생략 규칙 폐지 → parent 구조(composite/macro)에서 항상 명시 |
| 2 | IS_PART_OF 사용 규칙 | 규칙 변경 | #1과 동일 취지의 문장 정리 |
| 3 | INCLUDES_EXCEPTION semantics | 정의 확장 | EXCLUDES_* 한정 → REQUIRES_*/EXCLUDES_* 무관 (자체 예시 KEYNOTE-001과 정합화) |
| 4 | parent_role.nested_exception_parent | 정의 명확화 | IS_PART_OF child 없이 INCLUDES_EXCEPTION 보유 표시용임을 명시 |
| 5 | REQUIRES_STATUS From→To | 정의 확장 | Criterion → Observation / **Stage** (파이프라인 prompt 2와 정렬) |
| 6 | Pipeline JSON: sub_criteria.text_span | convention 변경 | string → array of strings (연속 세그먼트, substring 검증 전제) |
| 7 | cohort_scope 빈 값 convention | convention 통일 | "빈 array 또는 생략" → 생략으로 통일 |
| 8 | 미해결 항목 #20 신규 | v1.3 이관 | Criterion → Concept:Stage 연결 정식 정의 + resectability 표현 방식 |

---

## 변경 상세

### 1. Criterion.child_logic — default 생략 규칙 폐지

**위치**: Layer 1 > Node: Criterion > `child_logic` enum 설명부

**현행**:

> - `AND` — 모든 자녀 충족 필요 (inclusion default)
> - `OR` — 자녀 하나만 충족 (exclusion default)
>
> `child_logic`은 default와 다른 semantics일 때만 명시 (예: SEQUOIA I1의 inclusion-OR).

**변경**:

> - `AND` — 모든 자녀 충족 필요
> - `OR` — 자녀 하나만 충족
>
> 🔁 **v1.2.3 변경**: `child_logic`은 parent 구조(composite_split·macro_aggregate)에서 **항상 명시**. default 생략 규칙 폐지 — 생략 시 "의도적 default"와 "누락"을 구분할 수 없어 IAA·validation 모두에서 판별 불가. 판정은 표면 접속사가 아니라 실제 의미(모든 child 충족 필요 → AND / 하나만 → OR)로 함. inclusion/exclusion 여부는 default를 결정하지 않음.

**사유**: Stage 1 IAA Round 2에서 default 추종(DYK)과 의미 판정(EHJ)이 갈린 핵심 지점. 항상 명시가 annotation guideline v1.2에 반영되었으므로 스펙 정렬. macro_aggregate도 "at least one of the following" 구조(KEYNOTE-671 I3)에서 OR가 가능하므로 "macro는 항상 AND" 전제를 두지 않음.

---

### 2. IS_PART_OF 사용 규칙 — 동일 취지 정리

**위치**: Layer 1 Relationships > IS_PART_OF 사용 규칙

**현행**:

> - Group logic은 AND가 default. ✨ v1.2.1부터 `Criterion.child_logic` property로 명시

**변경**:

> - Group logic은 `Criterion.child_logic` property로 **항상 명시** (🔁 v1.2.3: default 생략 폐지, macro_aggregate 포함)

---

### 3. INCLUDES_EXCEPTION — semantics 문장 확장

**위치**: Cross-layer Relations 상세 정의 > INCLUDES_EXCEPTION > Semantics

**현행**:

> **Semantics**: 부모 criterion이 broad EXCLUDES_*로 정의되어 있을 때 명시적으로 carve-out되는 exception.

**변경**:

> **Semantics**: 부모 criterion이 broad rule(EXCLUDES_* 또는 REQUIRES_*)로 정의되어 있을 때 명시적으로 carve-out 또는 waive되는 exception. inclusion/exclusion 구분 없이 구조적 패턴으로 적용.

**사유**: v1.2.2 문서 내 자기모순 해소 — KEYNOTE-001 histology waiver 예시가 이미 REQUIRES_BIOMARKER 부모에 INCLUDES_EXCEPTION을 부여하고 있으나 semantics 문장은 EXCLUDES_* 한정으로 서술됨. Annotation guideline의 nested_exception 정의("inclusion/exclusion criteria 구분없이 구조적 패턴으로 판단") 및 트리거 `not required if ~`와 정렬.

---

### 4. parent_role.nested_exception_parent — 정의 명확화

**위치**: Layer 1 > Node: Criterion > `parent_role` enum

**현행**:

> - `nested_exception_parent` — carve-out 부모

**변경**:

> - `nested_exception_parent` — INCLUDES_EXCEPTION relation을 보유한 Criterion 표시용. 🔁 **v1.2.3 명확화**: nested_exception은 별도 child Criterion 노드와 IS_PART_OF edge를 생성하지 않음. Annotation JSON의 예외 조각(exception span)은 Neo4j ingest 시 단일 Criterion 노드의 INCLUDES_EXCEPTION relation으로 변환됨. 따라서 이 값은 IS_PART_OF의 parent_role property로는 사용되지 않고, Criterion node property로만 사용됨.

**사유**: "parent"라는 명칭이 IS_PART_OF children의 존재를 암시하나, 실제 그래프 구조 결정(nested_exception은 child 노드 미생성)과 어긋남. enum 값 자체는 유지하되(하위 호환), 용도를 명시. Annotation guideline v1.2의 "예외 조각(exception span)" 용어 도입과 세트.

---

### 5. REQUIRES_STATUS — From→To 확장

**위치**: Layer 1 → Layer 3 Semantic Relationships 표

**현행**:

> | REQUIRES_STATUS | Criterion → Observation | status, version, alternative_constraint |

**변경**:

> | REQUIRES_STATUS | Criterion → Observation **/ Stage** | status, version, alternative_constraint | 🔁 v1.2.3: target에 Concept:Stage 추가 |

**사유**: 파이프라인 `prompt_2`의 target_subtype 표는 이미 "Stage | Disease stage classifications (REQUIRES_STATUS for stage)"로 운용 중이나 스펙 표에는 Stage target이 없어 스펙-파이프라인 불일치 상태. 최소 변경으로 현행 파이프라인을 스펙에 반영. 단, Stage 연결의 정식 설계(전용 relation 신설 여부, resectability 표현)는 미해결 항목 #20으로 이관 (→ 변경 8).

---

### 6. Pipeline JSON — sub_criteria.text_span 배열화

**위치**: INCEpTION Layer/Feature Mapping > Property Name Mapping (또는 신규 소절 "Stage 1 sub_criteria convention")

**추가 서술**:

> 🔁 **v1.2.3**: Stage 1 출력의 `sub_criteria[].text_span`은 **array of strings** (세그먼트 배열)로 기록. 각 세그먼트는 원문 criterion text의 연속 부분 문자열이어야 하며, validator가 `segment in text` 검사로 기계 검증함.
>
> - 일반 케이스: 세그먼트 1개 — `["previously untreated"]`
> - 원문 어순상 떨어진 동일 판정 단위: 세그먼트 복수 — `["locally advanced", "Stage III"]` (이어붙인 단일 문자열은 원문에 없는 조합이므로 무효)
> - 시점·수치·조건 제약 표현: 적용되는 모든 child의 배열에 동일 세그먼트 추가
>
> 기존 string 형식 gold set은 1개짜리 배열로 감싸는 일괄 마이그레이션. `target_text_span`(Stage 2)의 배열화 여부는 Stage 2 gold set 착수 전 검토 항목으로 보류.

**사유**: Annotation guideline v1.2 Text_span 대원칙(연속 substring + 세그먼트 배열)의 스키마 반영. 상세 근거는 guideline v1.2 변경 요약 #3·#4 참조.

**연동 수정 필요 (스펙 외)**: `prompt_1`(text_span 배열 형식·경계 규칙 반영, macro=AND 고정 문구 삭제), `prompt_2`(PARENT_TEXT 입력 필드 추가), `validators.py`(substring·배열 타입 검사 추가).

---

### 7. cohort_scope 빈 값 — 생략으로 통일

**위치**: Layer 1 > Node: Criterion > `cohort_scope` 사용

**현행**:

> - 빈 array 또는 생략 시 모든 cohort 적용

**변경**:

> - 모든 cohort에 적용되는 경우 property를 기록하지 않음(생략). 🔁 v1.2.3: null·빈 array 표기는 사용하지 않음 (JSON 검증 일관성)

---

### 8. 미해결 항목 #20 신규 등록

**위치**: Schema-level Findings 미해결 항목 > v1.2.3 추가 (신규 소절)

**추가**:

> ### 🔁 v1.2.3 추가
>
> 20. **Criterion → Concept:Stage 연결 정식 정의** — 현행은 REQUIRES_STATUS의 target 확장(변경 5)으로 임시 운용. v1.3에서 결정할 사항: (a) 전용 relation(예: REQUIRES_STAGE) 신설 여부, (b) resectability의 표현 위치 — Concept:Stage property 추가 vs 별도 Concept vs relation property, (c) Annotation guideline 6)의 "stage·resectability Stage 2 재결합" 규칙과의 정합. NCCN상 resectability는 TNM과 독립 축이므로 property 추가 시 Layer Separation 원칙 재검토 필요.

---

## 변경대비표 갱신 (v1.2.2 → v1.2.3 열 추가)

| 요소 | v1.2.2 | v1.2.3 |
| --- | --- | --- |
| Criterion.child_logic 명시 규칙 | default와 다를 때만 | 🔁 parent 구조에서 항상 명시 |
| parent_role.nested_exception_parent | "carve-out 부모" | 🔁 정의 명확화 (IS_PART_OF 미사용, node property 전용) |
| INCLUDES_EXCEPTION semantics | EXCLUDES_* 부모 한정 서술 | 🔁 REQUIRES_*/EXCLUDES_* 무관으로 확장 |
| REQUIRES_STATUS target | Observation | 🔁 Observation / Stage |
| sub_criteria.text_span (pipeline) | string | 🔁 array of strings (연속 세그먼트) |
| cohort_scope 빈 값 | 빈 array 또는 생략 | 🔁 생략으로 통일 |

**변경 성격**: v1.2.3은 property·relation·enum의 추가/삭제가 없는 **정합화 패치** (사용 규칙·정의 서술·pipeline convention). Frequency-justified addition 원칙과 무관하며, v1.2.2 self-correction 계보의 연장선 — 문서 내 자기모순(변경 3)과 스펙-파이프라인 불일치(변경 5)의 해소가 중심.

---

## Paper Methods 반영 메모

v1.2.2 self-correction narrative에 이어붙일 수 있는 문장:

> "A subsequent alignment patch (v1.2.3) resolved documentation-level inconsistencies identified during inter-annotator calibration: the INCLUDES_EXCEPTION semantics were generalized to cover waivers on inclusion-side rules (consistent with the schema's own KEYNOTE-001 reference annotation), the child_logic default-omission convention was replaced with mandatory explicit annotation after IAA analysis showed default-following behavior to be a systematic disagreement source, and the Stage-1 text_span format was changed to verbatim contiguous segments to enable automated substring validation of LLM outputs."
