# SOURCE OF TRUTH

> **최종 갱신**: 2026-09-08
> 사람 / Claude Code / 외부 LLM이 **무엇을 authoritative하게 읽어야 하는지** 정의한다.
> 진행 상태 요약은 [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).

두 가지 원칙:

1. **파일명이 최신처럼 보인다고 최신이 아니다.** 아래 표에 없는 경로는 authoritative가 아니다.
2. **frozen은 append-only다.** 재직렬화·공백 정규화·개행 변경도 수정으로 간주한다.

---

## 1. 목적별 권위 (authority by purpose)

**권위는 하나의 사다리가 아니다.** 질문의 목적에 따라 authoritative한 문서가 달라진다.
v1.3 반입 이후에는 특히 다음을 구분해야 한다.

> **코드는 무엇이 *실행되는가*를 말한다. Canonical Core는 무엇이 *구현되어야 하는가*를 말한다.**
> 현행 규범 의미(normative semantics)에 관해서는 **구현 코드가 v1.3.0보다 우위에 있지 않다.**

### 1-A. Normative Stage 1 semantics — "규칙이 무엇인가"

| 순위 | 경로 | Status | Mutability |
|---|---|---|---|
| 1 | `docs/guidelines/stage1/canonical_core_v1_3_0.md` | **CURRENT NORMATIVE (v1.3.0 FROZEN)** | ❌ v1.4 없이는 불변 |

H0–H6, X1–X7, 라벨 의미, split/merge 경계, child-logic 의미, criterion-locality의 **유일한 규범 출처**.
런타임이 아직 이를 구현하지 않는다는 사실은 규범 지위를 낮추지 않는다.

### 1-B. Current implementation contracts — "지금 무엇이 실행되는가"

| 순위 | 경로 | Status | Mutability | Notes |
|---|---|---|---|---|
| 1 | `pipeline/config.py` | active | **mutable** | v1.2.2 enum 정본. `SEMANTIC_CATEGORIES`·`RELATION_TYPES`·`CONCEPT_SUBTYPES`·`SPLITTING_DECISIONS`·`CHILD_LOGIC`·`RELATION_PROPERTY_WHITELIST`. `CHILD_LOGIC`에서 XOR 제거(`:94`) |
| 2 | `iaa_pipeline/stage_schemas.py` | active | **mutable** | envelope/record 저장 계약. `text_span: list[str] \| str`은 **의도적 관대함** — R1/R2 문자열 저장분을 읽어야 한다 |
| 3 | 실행 코드 전반 (`orchestrator.py`, `validators.py`, `llm_client.py`, `stage_runner.py`, `pipeline/prompts/prompt_1_splitting.txt`) | active | **mutable** | **v1.3 비준수.** 격차는 §7 |

이 계층은 "현재 동작"의 근거이지 **규범의 근거가 아니다.**
구현이 canonical과 다르면 그것은 canonical이 틀린 것이 아니라 **구현 격차**다.

### 1-C. Development prompt — 비규범

| 순위 | 경로 | Status | Mutability |
|---|---|---|---|
| 1 | `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` | **NON-NORMATIVE 개발 아티팩트** | mutable (v1.3.x 패치, 동작 불변 조건) |

v1.3.0을 프롬프트로 구현한 것. 현행 프로덕션 프롬프트도, 최종 동결 프롬프트도, 런타임 준수 증거도 **아니다**.
프로덕션 로더가 읽지 않는다(§5-B).

### 1-C-2. Development execution path — 비규범

| 순위 | 경로 | Status | Mutability |
|---|---|---|---|
| 1 | `pipeline/stage1_v13/` | **개발 실행 경로 (LAYER 3.5)** | mutable |

canonical v1.3.0을 실제로 실행해 보기 위한 병렬 런타임. 2026-09-08(PHASE 4) 신설.
**프로덕션 경로를 대체하지 않는다** — `pipeline/orchestrator.py`, `pipeline/validators.py`,
`pipeline/prompts/prompt_1_splitting.txt`는 무변경이다.

이 패키지가 존재한다는 사실은 **런타임이 v1.3을 따른다는 뜻이 아니다**. 1-B가 여전히 실행 계약이다.
상세: [`../methods/stage1_v1_3_runtime.md`](../methods/stage1_v1_3_runtime.md)

### 1-D. Historical adjudication semantics — "113건은 무엇을 근거로 판정됐나"

| 순위 | 경로 | Status | Mutability |
|---|---|---|---|
| 1 | `pipeline/schema/annotation_guideline_v1_2_2_notion.md` | **frozen** | ❌ immutable |
| 2 | `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md` | **frozen** | ❌ immutable |
| 3 | `pipeline/schema/ontology_spec_v1_2_3_patch.md` | **frozen** | ❌ immutable · 본문 **미병합**, #2와 함께 읽는다 |

`§1-1`/`§T2-3`/`§C1-1` 규칙 ID의 출처는 위 #1(부록 3이 색인)이며, **`_notion` 접미사가 붙었지만 v1.2.2 정본이자 유일본**이다.

### 1-E. Historical adjudication implementation — "그 판정을 어떻게 재현하나"

| 순위 | 경로 | Status |
|---|---|---|
| 1 | `iaa_pipeline/adjudication.py` **@ tag `stage1-adjudication-complete-2026-09-08`** | **frozen anchor** |

⚠️ **"오늘의 `adjudication.py`"가 아니다.** 작업 트리 파일은 Phase 4 이후 진화할 수 있으므로
영구 불변으로 선언하지 않는다. 불변인 것은 **태그가 가리키는 그 시점의 내용**이다.

```bash
git show stage1-adjudication-complete-2026-09-08:iaa_pipeline/adjudication.py
```

### 1-F. Historical evidence — "결과가 무엇인가"

| 순위 | 경로 | Status | Mutability |
|---|---|---|---|
| 1 | `evidence/stage1/adjudication_v1_2_2_2026-09-07/` | **frozen** | ❌ append-only |

113 gold / 0 gap / 8 trials + exact queue + R1/R2/GOLD 불변 사본. `SHA256SUMS` 보유.
**113-item historical gold ≠ v1.3-harmonized gold.**

### 1-G. Working annotations / generated output

| 경로 | Status | Mutability | Notes |
|---|---|---|---|
| `iaa_workspace/*/stage1/round{1,2}/` | live source | ⚠️ **git 미추적** | 판정 UI가 쓰는 live 파일. 불변 사본은 1-F |
| `results/**`, `pipeline/output/**`, `docs/amia_stage1_*.md` | **generated** | 재생성 가능 | source of truth **아님**. §3 |
| `gpt_context_package/` + `.zip` | **generated** | 재생성 가능 | source of truth **아님**. §4 |

### 충돌 시 판단 순서

```
질문이 "규칙이 무엇인가"       → 1-A (canonical v1.3.0)
질문이 "지금 무엇이 도는가"     → 1-B (config / stage_schemas / 프로덕션 실행 코드)
질문이 "v1.3을 어떻게 돌려보나" → 1-C-2 (개발 실행 경로, 프로덕션 아님)
질문이 "113건 판정 근거"        → 1-D + 1-E (v1.2.2 기준 + 태그 앵커)
질문이 "결과 수치"             → 1-F (동결 증거)
1-A와 1-B가 다르면            → 구현 격차. 조용히 고치지 말고 gap inventory에 기록
```

불일치를 발견하면 **조용히 고치지 말고 보고**한다.

---

## 2. Source of truth가 **아닌** 것 — 자주 오인되는 파일

| 경로 | 실제 지위 | 근거 |
|---|---|---|
| `pipeline/schema/ontology_v1.2.1.json` | **dead reference** | `pipeline/config.py:21`이 `SCHEMA_PATH`로 대입하지만 **호출부 0곳**이며 코드 주석이 "presently unused"라고 명시. v1.2.2 enum 정본은 `config.py`다. 이동하지 않는다 — active 코드가 경로를 참조하기 때문 |
| `pipeline/schema/ontology_full_specification_v1.2.1.md` | superseded | v1.2.2 통합본이 대체. **v1.2.2 본문이 링크하므로 제자리 유지** |
| `pipeline/schema/annotation_guideline_v1_2_1.md` | superseded | 규칙 내용은 v1.2.2와 동일, 규칙 ID가 없다. 인용은 v1.2.2로 |
| `pipeline/schema/annotation_guideline_v0_2_stage1 (1).md` | **legacy (v0.2)** | 인용하지 않는다. historical Stage 1 가이드라인은 1-D의 v1.2.2이고, 현행 규범은 1-A의 v1.3.0이다. `pipeline/REVIEW.md` / `REVIEW_notion.md`가 이 파일을 "현재 stage 1"로 가리키던 stale pointer는 2026-09-08에 #6으로 교정되었고, v0.2 링크는 superseded로 표시해 보존한다 |
| `pipeline/schema/stage1_iaa_review_and_guideline_v1_1.md` | 검토 기록 | 가이드라인 본문 아님 |
| `pipeline/schema/cohort_standard_unit_proposal_v0.md` | DEFERRED 결정문 | 2026-06-07 미채택. cohort_scope는 표면형 유지 |
| `AGENTS.md` | 훼손된 미러 | CLAUDE.md의 find/replace 사본이며 문자열이 깨져 있다(예: `Codex-*`가 Anthropic으로 라우팅된다는 잘못된 서술). **CLAUDE.md가 authoritative**. 현재 git 미추적 |
| `pipeline/prompts/prompt_1_splitting.txt` | **구 프로덕션 프롬프트** | ⚠️ v1.3 프롬프트가 아니다. 개발용 v1.3.1이 반입됐다는 이유로 재라벨하지 않는다. 현행 규범 대비 비준수 4건(§7) |
| `docs/project_state/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md` | 외부 설계 핸드오프 | v1.3 설계를 서술한 문서. **규범 출처가 아니다** — 규범은 1-A의 canonical core다. 2026-09-08 이후 v1.3 산출물은 저장소에 반입되어 있다 |
| `docs/audit_reference/` | 참조 구현 | blinding 위반 방지 설계 예시. 실행 코드 아님 |

---

## 3. Generated / rebuildable — 절대 승격 금지

아래는 **재생성 가능한 산출물**이다. 수치의 근거로 인용하지 말고, 항상 #1–#7에서 다시 읽는다.

| 경로 | 재생성 방법 | git |
|---|---|---|
| `results/iaa/**` | `scripts/compute_iaa.py` | 미추적 |
| `results/adjudication/adjudication_queue.{json,csv}` | ⚠️ **재생성 불가** — 아래 경고 | 미추적 |
| `results/*.xlsx`, `results/review_log_*.xlsx` | `notebooks/`, `pipeline/review_session.py` | 미추적 |
| `pipeline/output/**` | `python -m pipeline.02_llm_annotation` | 미추적 |
| `docs/amia_stage1_numbers.md` | `scripts/amia_stage1_numbers.py` | 추적 (74-item 기준, **stale**) |
| `docs/amia_stage1_trajectories.md` | `scripts/amia_stage1_trajectories.py` | 추적 (74-item 기준, **stale**) |
| `STAGE1_GOLD_113items_2026-09-07/` | `scripts/export_adjudicated_dataset.py` | 추적 — §5 참조 |

> ⚠️ **`adjudication_queue.json`은 generated이지만 재생성 불가다.**
> `scripts/build_adjudication_queue.py`는 실행할 때마다 **S4 감사표본을 재추첨**한다.
> 시드는 고정이지만 표본틀은 고정이 아니고, 이 표본은 논문 Methods에 보고된다.
> 그래서 exact 사본이 `evidence/stage1/adjudication_v1_2_2_2026-09-07/queue/`에 동결되어 있다.
> 작업 순서만 바꾸려면 `scripts/reorder_adjudication_queue.py`를 쓴다(행 집합 불변을 assert).

---

## 4. LLM context snapshot 정책

```
gpt_context_package/  =  generated LLM context snapshot; never a source of truth
```

- 현재 스냅샷은 **2026-09-01 / `version: "0.1.0-example"`** 이며 61·74·113 freeze가 모두 **미반영된 stale** 상태다.
- 이번 단계에서 **재생성하지 않는다.** 재생성은 저장소 source-of-truth 안정화가 끝난 뒤다.
- 갱신이 필요하면 **스냅샷을 손으로 고치지 말고 원본을 고친 다음 다시 빌드**한다.
- 향후 canonical 위치 제안: `dist/gpt_context_package/` 또는 `artifacts/context/` (이번 단계에서 이동하지 않음).
- 재생성 시점: 판정/gold freeze 직후, Stage 1 v1.3 최종 프롬프트 동결, held-out 평가, Stage 2–5 마일스톤.

`.env`, API key, Neo4j 자격증명, PHI, 병원 원자료는 **추적되는 컨텍스트 패키지에 절대 넣지 않는다.**

---

## 5. 경로 주의사항

### 5-A. Gold payload 이중 보관 — 의도된 중복

동일 payload가 두 곳에 있다.

| 경로 | 역할 |
|---|---|
| `evidence/stage1/adjudication_v1_2_2_2026-09-07/gold/` | **canonical frozen evidence.** 장기 보존 위치, `SHA256SUMS` 적용 |
| `STAGE1_GOLD_113items_2026-09-07/` (저장소 루트) | **artifact discovery 경로.** `scripts/amia_stage1_numbers.py`·`amia_stage1_trajectories.py`의 `newest_export(REPO_ROOT)`가 루트에서 `*GOLD_*items_*`를 glob한다 |

두 사본은 바이트 동일하며, 갈라지면 `SHA256SUMS`로 즉시 검출된다.

> **루트 디렉터리를 지우면 안 된다.** glob이 trailing date 기준으로 정렬하므로, 루트에서 113-item이
> 사라지면 다음 후보인 `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/`이 선택되어 **74-item으로 조용히
> 회귀**한다. discovery 경로를 evidence 쪽으로 옮기는 변경은 산출물 선택 우선순위를 바꿀 수 있어
> **보류(DEFER)** 상태다.

---

### 5-B. 프롬프트 디렉터리 — 프로덕션 로더는 development/ 를 읽지 않는다

`pipeline/prompts/` 아래에 개발용 서브트리가 생겼다.

| 경로 | 로더가 읽는가 |
|---|---|
| `pipeline/prompts/prompt_{1..5}_*.txt` | ✅ `llm_client.py:86-93`의 명시적 `filename_map` |
| `pipeline/prompts/examples.json` | ✅ `config.py:24` `EXAMPLES_PATH` |
| `pipeline/prompts/development/**` | ❌ **어떤 코드도 참조하지 않음** |

두 로더(`pipeline/llm_client.py`, `iaa_pipeline/stage_runner.py:107-112`) 모두 **명시적 파일명**만 쓰고
디렉터리를 glob하지 않는다. 따라서 `development/` 하위에 파일을 두어도 런타임에 들어가지 않는다.

**development artifact imported; runtime activation deferred to Phase 4.**
로더 매핑을 바꾸거나 프로덕션 실행을 DEV 프롬프트로 돌리는 것은 Phase 4 작업이다.

---

## 6. 로컬 절대경로 정책

`evidence/.../queue/adjudication_queue.json`의 `workspace` 필드에
`/Users/jang-eunhye/graphrag-clinical-screening/iaa_workspace`가 들어 있다.

- **secret이 아니다.** **PHI가 아니다.**
- **바이트 보존 동결** 때문에 그대로 둔다. 한 글자만 바꿔도 해시가 깨지고 exact historical artifact가 아니게 된다.
- 같은 문자열은 이미 추적 중인 `pipeline/HANDOFF.md`, `iaa_pipeline_spec/adjudication_guide_v2_over_v1.md`에도 있다.
- 향후 공개 배포가 필요하면 **동결 원본을 수정하지 말고**, sanitized derived artifact를 별도로 생성한다.

---

## 7. Known implementation gap — 기준은 v1.3.0

현재 런타임은 **현행 규범 v1.3.0을 따르지 않는다.** (이전 기록은 v1.2.3 기준이었으나 v1.3.0이 forward 목표다.)

> **v1.3.0이 현행 규범이지만, 완전히 v1.3을 따르는 런타임 구현은 아직 없다.**

`incompatible` 6건(고치면 기존 출력이 바뀜):

| canonical family | 위치 | 어긋난 동작 |
|---|---|---|
| **H4** | `validators.py:59-61` | `nested_exception`에 `≥2 sub_criteria` 강제 — v1.3은 exception span만(1개도 유효). **historical gold 10건 중 9건을 거부** |
| **X1** | `orchestrator.py:155` | `sub["text_span"]`을 문자열로 소비 — v1.3은 배열 |
| **H5** | `prompt_1_splitting.txt` | inclusion=AND / exclusion=OR 암묵 기본값 — v1.3은 criterion type·표면 연결어에서 추론 금지 |
| **X7** | 〃 | 인접 criterion 텍스트를 자식 span 출처로 **명시 지시** |
| **X5** | 〃 | "as defined in Table" 위임을 `macro_aggregate`로 — v1.3은 `none` + delegation note |
| **X4** | 〃 | `nested_exception`의 cohort_scope를 자식에 배치 — v1.3은 현재 Criterion에 부착 가능 |

전체 재고(conformant 5 / partial 8 / missing 12 / incompatible 6 / historical-only 4),
저장·실행 계약 재고, ontology vs pipeline metadata 경계:
[`../project_state/stage1_v1_3_implementation_gap.md`](../project_state/stage1_v1_3_implementation_gap.md)

**113 gold의 유효성에는 영향이 없다** — gold는 판정 트랙(1-E)으로 생성되었고 프로덕션 프롬프트를 거치지 않았다.
실제로 gold의 sub_criteria 123/123은 이미 `text_span` 배열이다.

> PHASE 4의 개발 런타임(1-C-2)은 이 규칙들을 **자기 경로 안에서** 올바르게 구현한다.
> 위 표는 **레거시 프로덕션 경로**의 상태이며 PHASE 4에서 바뀌지 않았다.

이 항목들은 Stage 1 semantic 계약을 건드리므로 **연구 측 판단 없이 수정하지 않는다.**
v1.2.3 중간 상태를 따로 만들지 않고 **v1.3에서 한 번에 해소**한다.

---

## 8. 변경 시 지켜야 할 것

- annotation schema를 바꿀 때: `pipeline/config.py` enum을 고치고 `iaa_pipeline/stage_schemas.py`
  docstring을 동기화한다. `SCHEMA_PATH` JSON은 authoritative가 아니다.
- `pipeline/REVIEW.md`와 `REVIEW_notion.md`는 **쌍으로 유지**한다(둘 다 수정).
- 리뷰 발견을 `validators.py` 규칙으로 승격하는 것은 같은 패턴이 **3개 trial 이상**에서 나올 때만.
- abstract에 들어가는 숫자는 **생성하고, 옮겨 적지 않는다**.
- frozen freeze는 **새 날짜 디렉터리**를 만든다. 기존 디렉터리를 수정하지 않는다.
