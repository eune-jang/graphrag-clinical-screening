# SOURCE OF TRUTH

> **최종 갱신**: 2026-09-08
> 사람 / Claude Code / 외부 LLM이 **무엇을 authoritative하게 읽어야 하는지** 정의한다.
> 진행 상태 요약은 [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).

두 가지 원칙:

1. **파일명이 최신처럼 보인다고 최신이 아니다.** 아래 표에 없는 경로는 authoritative가 아니다.
2. **frozen은 append-only다.** 재직렬화·공백 정규화·개행 변경도 수정으로 간주한다.

---

## 1. 권위 우선순위 표

| # | Category | Authoritative path | Status | Mutability | Notes |
|---|---|---|---|---|---|
| 1 | implementation enums / config | `pipeline/config.py` | active | **mutable** | v1.2.2 enum 정본. `SEMANTIC_CATEGORIES`·`RELATION_TYPES`·`CONCEPT_SUBTYPES`·`SPLITTING_DECISIONS`·`CHILD_LOGIC`·`RELATION_PROPERTY_WHITELIST`·`LLM_OUTPUT_STRIP_FIELDS`. `CHILD_LOGIC`에서 XOR 제거됨(`:94`) |
| 2 | Stage-1 storage contract | `iaa_pipeline/stage_schemas.py` | active | **mutable** | envelope/record 계약. `text_span: list[str] \| str`은 **의도적 관대함** — R1/R2 문자열 저장분을 읽어야 하기 때문 |
| 3 | adjudication behavior | `iaa_pipeline/adjudication.py` | active | **mutable** | **v1.2.3 준수**: `child_logic` 양방향 필수(`:271-281`), `normalize_text_span`(`:137`). 113 gold를 생성한 코드 |
| 4 | historical adjudication ontology basis | `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md` | **frozen** | ❌ immutable | v1.2.2 본문 |
| 5 | 〃 (alignment patch) | `pipeline/schema/ontology_spec_v1_2_3_patch.md` | **frozen** | ❌ immutable | 본문에 **미병합**. #4와 **반드시 함께** 읽는다 |
| 6 | historical adjudication guideline basis | `pipeline/schema/annotation_guideline_v1_2_2_notion.md` | **frozen** | ❌ immutable | `§1-1`/`§T2-3`/`§C1-1` 규칙 ID의 출처(부록 3이 색인). **`_notion` 접미사이지만 이것이 v1.2.2 정본이며 유일본**이다 |
| 7 | frozen evidence (최신) | `evidence/stage1/adjudication_v1_2_2_2026-09-07/` | **frozen** | ❌ append-only | 113 gold / 0 gap / 8 trials + exact queue + R1/R2/GOLD 불변 사본. `SHA256SUMS` 보유 |
| 8 | working annotations | `iaa_workspace/*/stage1/round{1,2}/` | live source | ⚠️ **git 미추적** | 판정 UI가 쓰는 live 파일. 불변 사본은 #7에 있다 |
| 9 | generated reports | `results/**`, `pipeline/output/**`, `docs/amia_stage1_*.md` | **generated** | 재생성 가능 | source of truth **아님**. §3 참조 |
| 10 | LLM context snapshot | `gpt_context_package/`, `gpt_context_package.zip` | **generated** | 재생성 가능 | source of truth **아님**. §4 참조 |

### 코드 권위 순서 (충돌 시)

```
1. pipeline/config.py                    실행되는 구현 계약
2. iaa_pipeline/stage_schemas.py         Stage별 저장 계약
   iaa_pipeline/adjudication.py          판정 동작
3. ontology v1.2.2 + v1.2.3 패치         현행 온톨로지 설계
4. annotation guideline v1.2.2           판정에 쓰인 동결 가이드라인
5. evidence/stage1/.../ + MANIFEST       동결 증거·해시
6. (v1.3 core / dev prompt)              ⛔ 아직 저장소에 없음
7. 그 밖의 historical/superseded 산출물   lineage 용도
```

불일치를 발견하면 **조용히 고치지 말고 보고**한다.

---

## 2. Source of truth가 **아닌** 것 — 자주 오인되는 파일

| 경로 | 실제 지위 | 근거 |
|---|---|---|
| `pipeline/schema/ontology_v1.2.1.json` | **dead reference** | `pipeline/config.py:21`이 `SCHEMA_PATH`로 대입하지만 **호출부 0곳**이며 코드 주석이 "presently unused"라고 명시. v1.2.2 enum 정본은 `config.py`다. 이동하지 않는다 — active 코드가 경로를 참조하기 때문 |
| `pipeline/schema/ontology_full_specification_v1.2.1.md` | superseded | v1.2.2 통합본이 대체. **v1.2.2 본문이 링크하므로 제자리 유지** |
| `pipeline/schema/annotation_guideline_v1_2_1.md` | superseded | 규칙 내용은 v1.2.2와 동일, 규칙 ID가 없다. 인용은 v1.2.2로 |
| `pipeline/schema/annotation_guideline_v0_2_stage1 (1).md` | **legacy (v0.2)** | 인용하지 않는다. 현재 Stage 1 가이드라인은 #6(v1.2.2)이다. `pipeline/REVIEW.md` / `REVIEW_notion.md`가 이 파일을 "현재 stage 1"로 가리키던 stale pointer는 2026-09-08에 #6으로 교정되었고, v0.2 링크는 superseded로 표시해 보존한다 |
| `pipeline/schema/stage1_iaa_review_and_guideline_v1_1.md` | 검토 기록 | 가이드라인 본문 아님 |
| `pipeline/schema/cohort_standard_unit_proposal_v0.md` | DEFERRED 결정문 | 2026-06-07 미채택. cohort_scope는 표면형 유지 |
| `AGENTS.md` | 훼손된 미러 | CLAUDE.md의 find/replace 사본이며 문자열이 깨져 있다(예: `Codex-*`가 Anthropic으로 라우팅된다는 잘못된 서술). **CLAUDE.md가 authoritative**. 현재 git 미추적 |
| `docs/project_state/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md` | 외부 설계 핸드오프 | v1.3 설계를 서술하지만 **그 v1.3 산출물은 저장소에 없다**([`../CURRENT_STATUS.md`](../CURRENT_STATUS.md) §5) |
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

## 5. Gold payload 이중 보관 — 의도된 중복

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

## 6. 로컬 절대경로 정책

`evidence/.../queue/adjudication_queue.json`의 `workspace` 필드에
`/Users/jang-eunhye/graphrag-clinical-screening/iaa_workspace`가 들어 있다.

- **secret이 아니다.** **PHI가 아니다.**
- **바이트 보존 동결** 때문에 그대로 둔다. 한 글자만 바꿔도 해시가 깨지고 exact historical artifact가 아니게 된다.
- 같은 문자열은 이미 추적 중인 `pipeline/HANDOFF.md`, `iaa_pipeline_spec/adjudication_guide_v2_over_v1.md`에도 있다.
- 향후 공개 배포가 필요하면 **동결 원본을 수정하지 말고**, sanitized derived artifact를 별도로 생성한다.

---

## 7. Known deferred implementation drift

프로덕션 어노테이션 트랙이 ontology v1.2.3 패치를 **아직 반영하지 않았다**.
목록과 상세는 [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md) §6.

**113 gold의 유효성에는 영향이 없다** — gold는 v1.2.3을 준수하는 판정 트랙(#3)으로 생성되었고
프로덕션 프롬프트를 거치지 않았다.

이 항목들은 Stage 1 semantic 계약을 건드리므로 **연구 측 판단 없이 수정하지 않는다.**

---

## 8. 변경 시 지켜야 할 것

- annotation schema를 바꿀 때: `pipeline/config.py` enum을 고치고 `iaa_pipeline/stage_schemas.py`
  docstring을 동기화한다. `SCHEMA_PATH` JSON은 authoritative가 아니다.
- `pipeline/REVIEW.md`와 `REVIEW_notion.md`는 **쌍으로 유지**한다(둘 다 수정).
- 리뷰 발견을 `validators.py` 규칙으로 승격하는 것은 같은 패턴이 **3개 trial 이상**에서 나올 때만.
- abstract에 들어가는 숫자는 **생성하고, 옮겨 적지 않는다**.
- frozen freeze는 **새 날짜 디렉터리**를 만든다. 기존 디렉터리를 수정하지 않는다.
