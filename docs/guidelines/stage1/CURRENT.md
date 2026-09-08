# Stage 1 — 규범 문서 index / precedence

> **최종 갱신**: 2026-09-08 (v1.3 방법론 반입 후)
> 이 문서는 **index**다. v1.2.2 계열 가이드라인·스펙 파일은 원래 위치(`pipeline/schema/`)에 그대로 있다.
> 여기서는 "무엇이 어떤 지위인가"만 정의한다.

---

## 0. 네 개의 층 — 한눈에

```
LAYER 1  HISTORICAL REFERENCE / REPRODUCIBILITY
         Stage 1 guideline v1.2.2 + ontology v1.2.2 + v1.2.3 patch
         + 113-item frozen evidence
         + historical implementation @ tag stage1-adjudication-complete-2026-09-08
                 │  immutable
                 ▼
LAYER 2  CURRENT NORMATIVE METHOD
         docs/guidelines/stage1/canonical_core_v1_3_0.md
                 │  implemented by
                 ▼
LAYER 3  DEVELOPMENT PROMPT ARTIFACT (non-normative)
         pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt
                 │  not yet wired
                 ▼
LAYER 4  CURRENT RUNTIME IMPLEMENTATION
         ⚠️ 아직 v1.3을 따르지 않는다
         pipeline/prompts/prompt_1_splitting.txt (구 프로덕션 프롬프트, 변경 없음)
```

| | |
|---|---|
| **CURRENT NORMATIVE** | [`canonical_core_v1_3_0.md`](canonical_core_v1_3_0.md) |
| **DEVELOPMENT PROMPT** | [`pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt`](../../../pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt) |
| **HISTORICAL ADJUDICATION BASIS** | guideline v1.2.2 + ontology v1.2.2 + v1.2.3 patch |
| **HISTORICAL EVIDENCE** | [113-item frozen adjudication set](../../../evidence/stage1/adjudication_v1_2_2_2026-09-07/) |
| **HISTORICAL IMPLEMENTATION** | `iaa_pipeline/adjudication.py` **@ tag `stage1-adjudication-complete-2026-09-08`** |
| **CURRENT RUNTIME** | **not yet v1.3 conformant** |

---

## 1. LAYER 2 — 현행 규범 방법론

**[`canonical_core_v1_3_0.md`](canonical_core_v1_3_0.md)** — Stage 1 Canonical Core **v1.3.0 (FROZEN)**

H0–H6 결정 계층, X1–X7 cross-cutting 규칙, 라벨 의미, split/merge 경계, child-logic 의미,
criterion-locality가 v1.3.0으로 동결되어 있다.

**이 파일이 저장소에 있다는 사실이 런타임이 v1.3을 구현한다는 뜻은 아니다.**
현행 규범은 "무엇이 구현되어야 하는가"를 말하고, 코드는 "무엇이 실제로 돌아가는가"를 말한다.
둘의 격차는 [`../../project_state/stage1_v1_3_implementation_gap.md`](../../project_state/stage1_v1_3_implementation_gap.md)에 재고 조사되어 있다.

반입 기록: [`../../decisions/0001-stage1-v1-3-method-import.md`](../../decisions/0001-stage1-v1-3-method-import.md)

### 버전 정책 (canonical이 스스로 규정)

- **v1.3.x** — 비규범 구현 패치. 문구·예시·중복 DO/DO NOT·JSON 검증 세부.
  **동작이 바뀌지 않을 때만** 허용.
- **v1.4** — 규범 변경. H/X 의미, 규칙 우선순위, 구조 라벨 의미, split/merge 경계,
  exception 경계, child-logic 동작, criterion-local 범위가 바뀌면 필수.

---

## 2. LAYER 3 — 개발용 프롬프트 (비규범)

**[`pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt`](../../../pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt)**

Canonical Core v1.3.0을 프롬프트로 구현한 **v1.3.1 개발 아티팩트**다.

이것은 다음이 **아니다**:
- 현행 프로덕션 프롬프트
- 최종 동결 프롬프트
- 런타임이 v1.3을 따른다는 증거

프로덕션 로더는 이 파일을 읽지 않는다 — `pipeline/llm_client.py`와 `iaa_pipeline/stage_runner.py`는
모두 **명시적 파일명**으로만 프롬프트를 찾고 디렉터리를 glob하지 않는다.
**development artifact imported; runtime activation deferred to Phase 4.**

---

## 3. LAYER 1 — Historical adjudication normative basis

113-item Stage 1 판정은 **아래 셋을 기준으로** 수행되었다. 이 조합이 판정의 기준표준이다.

| 지위 | 문서 | 비고 |
|---|---|---|
| ontology base | [`pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md`](../../../pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md) | **v1.2.2** 본문 |
| ontology alignment patch | [`pipeline/schema/ontology_spec_v1_2_3_patch.md`](../../../pipeline/schema/ontology_spec_v1_2_3_patch.md) | **v1.2.3**. 본문에 **미병합** — 위 문서와 **반드시 함께** 읽는다 |
| Stage 1 annotation guideline | [`pipeline/schema/annotation_guideline_v1_2_2_notion.md`](../../../pipeline/schema/annotation_guideline_v1_2_2_notion.md) | **v1.2.2 판정 동결본**. 규칙 ID(`§1-1`, `§T2-3`, `§C1-1` …)의 출처, 부록 3이 색인 |

세 문서 모두 **immutable**이다. 판정 중 발견된 개정 필요 사항은 문서를 고치는 대신
판정 기록의 `rule_status=conflict` / `gap`으로 남겼다.

### Historical evidence

**113-item Stage 1 adjudication set** — [`evidence/stage1/adjudication_v1_2_2_2026-09-07/`](../../../evidence/stage1/adjudication_v1_2_2_2026-09-07/)

113 gold / 0 gap / 8 trials. 수치와 해시는 [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) §3.

### Historical implementation — 앵커는 태그다

historical 판정 동작의 정의는 **"오늘의 `iaa_pipeline/adjudication.py`"가 아니다.**

> historical 113-item 판정 동작을 재현하려면
> **tag `stage1-adjudication-complete-2026-09-08` 시점의 `iaa_pipeline/adjudication.py`** 를 쓴다.

작업 트리의 해당 파일은 Phase 4 이후 진화할 수 있다. 그 파일을 영구 불변으로 선언하지 않는다.
불변인 것은 **태그가 가리키는 그 시점의 내용**이다.

```bash
git show stage1-adjudication-complete-2026-09-08:iaa_pipeline/adjudication.py
```

---

## 4. LAYER 4 — 현재 런타임

> **v1.3.0이 현행 규범이지만, 완전히 v1.3을 따르는 런타임 구현은 아직 없다.**

- `pipeline/prompts/prompt_1_splitting.txt`는 **이번 단계에서 변경하지 않았다.**
  구 프로덕션 시대 프롬프트이며, 새 개발 프롬프트가 생겼다는 이유만으로 **v1.3으로 재라벨하지 않는다.**
- 확인된 비준수 6건이 `incompatible` 상태다 — `nested_exception` sub_criteria 규약, `text_span` 문자열 소비,
  inclusion/exclusion child_logic 기본값, 인접 criterion span 도입, Table 위임 → `macro_aggregate`,
  `nested_exception`의 cohort_scope 위치.
- 전체 목록: [`../../project_state/stage1_v1_3_implementation_gap.md`](../../project_state/stage1_v1_3_implementation_gap.md)

---

## 5. 반드시 지켜야 할 경계

> - **113-item historical gold ≠ v1.3-harmonized gold.**
> - **향후 v1.3 구현이 historical record를 다시 쓰지 않는다.**
> - v1.3-harmonized reference set이 필요해지면 **별도 버전으로 새로 만든다.**

canonical 자신도 같은 경계를 긋는다:

> The frozen 113-item v1.2.2 evidence set should remain unchanged;
> any later v1.3-harmonized reference set should be versioned separately.

이 경계가 중요한 이유: 기존 규칙으로 해소된 항목과 v1.3이 새로 추가한 규칙으로 해소된 항목이
구분 가능해야 한다. historical record를 v1.3으로 마이그레이션하면 그 구분이 사라지고,
"v1.3이 무엇을 개선했는가"를 증거로 말할 수 없게 된다.

v1.3 기반 평가 결과가 나오면 **새 날짜의 별도 evidence 디렉터리**를 만든다.

### legacy rule ID 매핑표 사용법

canonical의 `v1.2.2 rule → v1.3 family` 매핑표는 **분석·provenance recoding용**이다.
historical record의 `rule_id`를 다시 쓰기 위한 것이 **아니다**.
원래 `rule_id`는 보존하고, 비교가 필요하면 파생 필드(`canonical_rule_family`)를 별도로 붙인다.

---

## 6. 버전 계보 — 무엇을 인용할 것인가

| 문서 | 지위 | 인용 |
|---|---|---|
| `docs/guidelines/stage1/canonical_core_v1_3_0.md` | **현행 규범 (v1.3.0 FROZEN)** | ✅ **현행 Stage 1 방법론은 이것을 인용한다** |
| `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` | 비규범 개발 아티팩트 | ⚠️ 규범 근거로 인용하지 않는다 |
| `annotation_guideline_v1_2_2_notion.md` | **historical 판정 동결본** | ✅ 113건 판정 근거를 말할 때 |
| `annotation_guideline_v1_2_1.md` | superseded (2026-08-25 동결) | 규칙 내용 동일, **규칙 ID 없음** → v1.2.2로 인용 |
| `annotation_guideline_v0_2_stage1 (1).md` | legacy v0.2 (2026-05-11) | ❌ 인용 금지 (§8 참조) |
| `stage1_iaa_review_and_guideline_v1_1.md` | Round 2 IAA 검토 기록 | 가이드라인 본문 **아님** |
| `ontology_full_specification_unified_v1_2_2_ko.md` | historical 온톨로지 본문 | ✅ v1.2.3 패치와 **함께** |
| `ontology_spec_v1_2_3_patch.md` | historical 정합성 패치 | ✅ 위와 함께 |
| `ontology_full_specification_v1.2.1.md` | superseded | lineage 용도 |
| `ontology_v1.2.1.json` | **dead reference** | ❌ authoritative 아님 — enum 정본은 `pipeline/config.py` |

> ⚠️ **파일명 함정**: v1.2.2 가이드라인의 정본은 `_notion` 접미사가 붙은 파일이 **유일본**이다.
> "Notion 사본이니 부차적"이라고 오해하지 말 것. 접미사 제거 rename은 참조 스캔 없이 하지 않는다.

> ⚠️ **반입 파일명 규약**: 외부 원본은 `..._FROZEN_2026-09-07.md` / `..._DEV_2026-09-08_CORRECTED.txt`였다.
> 저장소 파일명은 **버전만 유지하고 lifecycle 상태 접미사를 뺐다** — 상태는 변하고, 파일명이 변하면 참조가 깨진다.
> 원본 파일명 ↔ 저장소 파일명 매핑은 ADR 0001에 기록되어 있다.

---

## 7. 판정 방법 — 보존해야 할 것

판정은 다수결도 어노테이터 합의도 아니다. 증거 위계에 근거한 **정오 판단**이다.

```
Tier 0  온톨로지/스펙의 구조적 제약만으로 결정
Tier 1  외부 임상 권위
Tier 2  CRC / 운영 스크리닝 로직
Tier 3  미해결 → gap ticket (억지로 gold로 만들지 않는다)
```

- 어노테이터 일치가 정답을 뜻하지 않는다. 둘 다 틀릴 수 있다 → 일치 항목도 감사했다.
- 113-item set에는 Tier-3 gap이 **0건** 남았다.
- 판정은 **단일 blind pass**로 수행되었다([`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) §3).

v1.3은 tier를 **primary decisive rule에서 파생**하도록 제안한다(H2-A → Tier 0, H2-B → Tier 1, 나머지 → Tier 2).
현재 구현은 사람이 tier를 직접 부여한다 — 격차는 gap inventory §4에 있다.

---

## 8. 해소된 stale pointer (2026-09-08)

`pipeline/REVIEW.md`와 `pipeline/REVIEW_notion.md`의 "관련 문서" 목록이
`schema/annotation_guideline_v0_2_stage1 (1).md`를 **"annotation guideline (현재 stage 1)"** 으로
가리키고 있었다. v0.2는 현재 Stage 1 가이드라인이 아니다 — §3의 v1.2.2가 historical 기준이고,
현행 규범은 §1의 v1.3.0이다.

두 파일을 **쌍으로** 교정해 "현재 Stage 1" 라벨을
`schema/annotation_guideline_v1_2_2_notion.md`로 옮겼고, v0.2 링크는 `(구) v0.2, superseded`로
표시해 보존했다. 규칙 내용은 건드리지 않았다.

`iaa_pipeline_spec/streamlit_status_and_gaps_2026-08-25.md`는 이 파일을 "⛔ 구버전(v0.2), 혼동 위험"으로
이미 표시하고 있었다 — 그 판단이 옳았다.

---

## 9. 관련 문서

- [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) — 진행 상태, 최신 수치
- [`../../repository/SOURCE_OF_TRUTH.md`](../../repository/SOURCE_OF_TRUTH.md) — 목적별 권위 표
- [`../../project_state/stage1_v1_3_implementation_gap.md`](../../project_state/stage1_v1_3_implementation_gap.md) — v1.3 구현 격차 재고
- [`../../decisions/0001-stage1-v1-3-method-import.md`](../../decisions/0001-stage1-v1-3-method-import.md) — v1.3 반입 기록
- [`iaa_pipeline_spec/adjudication_guide_v2_over_v1.md`](../../../iaa_pipeline_spec/adjudication_guide_v2_over_v1.md) §2-0 — 판정자용 기준표준 정의
- [`iaa_pipeline_spec/adjudication_handover.md`](../../../iaa_pipeline_spec/adjudication_handover.md) — 판정 설계 근거
