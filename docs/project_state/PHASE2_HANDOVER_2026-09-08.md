# PHASE 2 인계 요약 — Phase 3 설계 입력

> **작성일**: 2026-09-08
> **저장소**: graphrag-clinical-screening
> **브랜치**: `feat/adjudication-prep` (main 미병합, origin 백업 완료)
> **커밋**: `7f7fb7e` (docs) → `a27b0f0` (chore) · 직전 동결 `80f0f28` + tag `stage1-adjudication-complete-2026-09-08`
> **목적**: Phase 3 설계에 필요한 5개 항목을 한 문서로 전달

요청된 5개 항목의 위치:

| 요청 항목 | 이 문서의 절 |
|---|---|
| 최종 repo tree | §2 |
| 실제로 archive/move한 파일 목록 | §3 |
| 남아 있는 QUESTIONS FOR HUMAN DECISION | §4 |
| `docs/repository/SOURCE_OF_TRUTH.md` | §6 (전문) |
| `docs/CURRENT_STATUS.md` | §7 (전문) |

§6·§7은 저장소의 실제 파일을 **그대로 복사**한 것이다(요약 아님).

---

## 1. Phase 2 결론

**semantic 변경 0건.** ontology / guideline / prompt / validators / orchestrator / gold / R1·R2 / adjudication queue를 하나도 건드리지 않았다.

Phase 2가 실제로 해결한 문제는 "파일이 잘못된 위치에 있다"가 아니라 **"어느 파일이 authoritative한지 파일명으로 알 수 없다"** 였다. 구체적으로:

- v1.2.2 annotation guideline의 정본이 `_notion` 접미사를 달고 있고 그것이 **유일본**이다
- `ontology_v1.2.1.json`은 정본처럼 보이지만 `config.py`가 읽지 않는 **dead reference**다
- `docs/amia_stage1_numbers.md`는 이름에 버전이 없는데 내용은 **74-item** 기준이다

그래서 **이동보다 index 우선** 원칙을 적용했고, 실제 이동은 참조 0곳이 grep으로 확인된 파일 **1개**에 그쳤다.

### 검증 결과

```
evidence SHA256SUMS                     64/64 OK, FAILED 0
113 manifest 해시 대조                   bb0960577ce876b1… / c3e498bee0ef5ba5…  일치
frozen tracked 파일 변경 (80f0f28..HEAD) 0건
live iaa_workspace + queue (PHASE 1 기준선)  104/104 OK
tests/test_iaa_metrics.py               44/44 PASS
tests/test_adjudication.py              50/50 PASS
artifact discovery smoke test           newest_export → STAGE1_GOLD_113items_2026-09-07
상대 링크 검증 (신규·수정 10문서)         36개 중 깨진 링크 0
secret / PHI scan                       무검출
```

---

## 2. 최종 repo tree

```text
graphrag-clinical-screening/
│
├── docs/                                    ← PHASE 2에서 재편
│   ├── adjudication/README.md
│   ├── amia_stage1_numbers.md
│   ├── amia_stage1_trajectories.md
│   ├── amia2027_gold_freeze_2026-09-02.md
│   ├── amia2027_gold_freeze_2026-09-03.md
│   ├── amia2027_work_summary.md
│   ├── audit_reference/app_phase1.py
│   ├── audit_reference/app_phase2.py
│   ├── audit_reference/README (2).md
│   ├── audit_reference/test_workspace.py
│   ├── audit_reference/workspace.py
│   ├── CURRENT_STATUS.md
│   ├── decisions/README.md
│   ├── guidelines/stage1/CURRENT.md
│   ├── hosting_guide.md
│   ├── methods/architecture.md
│   ├── papers/amia2027/README.md
│   ├── project_state/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md
│   ├── project_state/PHASE1_WORK_SUMMARY_2026-09-08.txt
│   ├── repository/SOURCE_OF_TRUTH.md
│
├── evidence/                                ← PHASE 1 신설, append-only
│   ├── README.md
│   └── stage1/adjudication_v1_2_2_2026-09-07/
│       ├── README.md
│       ├── SHA256SUMS                       (64 payload)
│       ├── gold/       5 files
│       ├── queue/      3 files
│       └── envelopes/  56 files  (8 trials × R1/R2/GOLD/input/llm_output)
│
├── pipeline/
│   ├── __init__.py
│   ├── _archive_dedup_nested_exception.py
│   ├── _archive_labelstudio_export.py
│   ├── _archive_rename_observation.py
│   ├── 01_criteria_extraction.py
│   ├── 02_llm_annotation.py
│   ├── 03_recover_has_value.py
│   ├── 04_correct_relation_type.py
│   ├── 05_reextract_constraints.py
│   ├── 06_validate_annotation.py
│   ├── 07_neo4j_ingest.py
│   ├── 08_review_queries.py
│   ├── config.py
│   ├── HANDOFF.md
│   ├── llm_client.py
│   ├── nct_ids.txt
│   ├── orchestrator.py
│   ├── PIPELINE.md
│   ├── regex_extractor.py
│   ├── REVIEW_notion.md
│   ├── review_queries.cypher
│   ├── review_session.py
│   ├── REVIEW.md
│   ├── transforms.py
│   ├── validators.py
│   ├── prompts/
│   │   ├── examples.json
│   │   ├── prompt_1_splitting.txt
│   │   ├── prompt_2_category_relation_target.txt
│   │   ├── prompt_3_preferred_name.txt
│   │   ├── prompt_4_constraint_fallback.txt
│   │   ├── prompt_5_alternative_constraint.txt
│   └── schema/                              ← 이동하지 않음 (frozen basis)
│       ├── annotation_guideline_v0_2_stage1 (1).md
│       ├── annotation_guideline_v1_2_1.md
│       ├── annotation_guideline_v1_2_2_notion.md
│       ├── cohort_standard_unit_proposal_v0.md
│       ├── ontology_full_specification_unified_v1_2_2_ko.md
│       ├── ontology_full_specification_v1.2.1.md
│       ├── ontology_spec_v1_2_3_patch.md
│       ├── ontology_v1.2.1.json
│       ├── stage1_iaa_review_and_guideline_v1_1.md
│
├── iaa_pipeline/
│   ├── __init__.py
│   ├── adjudication.py
│   ├── aligners.py
│   ├── cache.py
│   ├── cli.py
│   ├── metrics.py
│   ├── stage_runner.py
│   ├── stage_schemas.py
│   ├── streamlit_app.py
├── iaa_pipeline_spec/
│   ├── 03_json_schemas.md
│   ├── 04_stage_runners.md
│   ├── adjudication_guide_v2_notion.md
│   ├── adjudication_guide_v2_over_v1.md
│   ├── adjudication_handover.md
│   ├── audit_streamlit_v1.md
│   ├── iaa_8trials_selection.md
│   ├── iaa_8trials.txt
│   ├── README.md
│   ├── streamlit_status_and_gaps_2026-08-25.md
├── scripts/
│   ├── amia_stage1_numbers.py
│   ├── amia_stage1_trajectories.py
│   ├── build_adjudication_queue.py
│   ├── compare_rounds.py
│   ├── compute_iaa.py
│   ├── convert_production_to_iaa.py
│   ├── export_adjudicated_dataset.py
│   ├── reorder_adjudication_queue.py
│   ├── run_iaa_ui.sh
│   ├── tier0_check.py
├── tests/
│   ├── test_adjudication.py
│   ├── test_iaa_metrics.py
```

루트 레벨(위 tree에 미포함):

```text
CLAUDE.md                                    운영 지침 (문서 포인터 2곳 추가)
AGENTS.md                                    ⚠️ 훼손된 미러, 여전히 미추적
AMIA_ABSTRACT_EVIDENCE_PACK.md               추적, 무변경
STAGE1_GOLD_113items_2026-09-07/             113 gold — artifact discovery 경로 (§3 참조)
AMIA_2027_STAGE1_GOLD_61items_2026-09-01/    60 gold + 1 gap (선행본)
AMIA_2027_STAGE1_GOLD_61items_2026-09-02/    61 gold
AMIA_2027_STAGE1_GOLD_74items_2026-09-03/    74 gold — AMIA 제출본
iaa_workspace/                               gitignored, live source
results/                                     gitignored (README만 추적)
data/external/aact/                          gitignored, 15GB 공개 덤프
gpt_context_package/ + .zip                  PHASE 2에서 gitignore 추가
streamlit_apps/ configs/ notebooks/ src/     무변경
```

---

## 3. 실제로 move / archive 한 파일 목록

### 3.1 이동 (git mv) — 1건

```
docs/architecture.md  →  docs/methods/architecture.md
```
grep으로 inbound 참조 **0곳** 확인 후 이동. 이동 후 잔존 참조 0.

### 3.2 추적 전환 (기존 미추적 파일의 배치) — 2건

```
docs/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md  →  docs/project_state/…
WORK_SUMMARY_2026-09-08.txt                    →  docs/project_state/PHASE1_WORK_SUMMARY_2026-09-08.txt
```
둘 다 Phase 1에서는 커밋 제외했던 파일. Phase 2 제외 목록에 없고 `CURRENT_STATUS.md`가 참조하므로 추적으로 전환. **핸드오프 문서는 v1.3 설계를 서술할 뿐 구현이 아니다.** (§4 질문 1)

### 3.3 archive — **0건**

archive 후보 전부가 rule A(active 코드/문서가 참조)에 걸렸다. 대신 `SOURCE_OF_TRUTH.md` §2에 지위를 기록했다.

| 후보 | 분류 | 사유 |
|---|---|---|
| `pipeline/schema/ontology_v1.2.1.json` | **KEEP ACTIVE** | `config.py:21` `SCHEMA_PATH`가 경로를 참조(호출부 0). rule A |
| `pipeline/schema/ontology_full_specification_v1.2.1.md` | **KEEP ACTIVE** | **immutable v1.2.2 본문**이 링크 → 이동 시 고칠 수 없는 링크가 깨짐 |
| `pipeline/schema/annotation_guideline_v0_2_stage1 (1).md` | **DEFER** | `REVIEW.md:368`/`REVIEW_notion.md:433`이 "현재 stage 1"로 참조 — stale pointer 해소가 선행 (§4 질문 2) |
| `pipeline/schema/cohort_standard_unit_proposal_v0.md` | **DEFER** | 참조 0이나 DEFERRED 결정문 → `docs/decisions/` 이관이 자연스러움 |
| `pipeline/_archive_*.py` 3종 | **KEEP ACTIVE** | PIPELINE/HANDOFF/REVIEW 4문서가 "구 데이터 import safety net"으로 참조 |
| `docs/audit_reference/` | **DEFER** | `adjudication_handover.md`가 **감사 시점 검증 기록**("참조 0") 안에서 경로를 인용 → 옮기면 그 기록이 자기 날짜에 대해 부정확해짐 |
| `src/graphrag_screening/` | **DEFER** | superseded가 아니라 **미래 작업용 scaffold**. `pyproject.toml` packages 미포함 |
| `docs/hosting_guide.md` | **KEEP ACTIVE** | `streamlit_apps/stage1_app.py:24,598` 사용자 노출 문자열 포함 6곳 참조 |

### 3.4 삭제 — **0건**

### 3.5 신규 문서 — 7건

```
docs/CURRENT_STATUS.md               entry point           (§7 전문)
docs/repository/SOURCE_OF_TRUTH.md   권위 표                (§6 전문)
docs/guidelines/stage1/CURRENT.md    Stage 1 규범 precedence index
docs/papers/amia2027/README.md       AMIA 제출본 ↔ post-AMIA 113 분리 index
docs/adjudication/README.md          판정 문서 index (실제 문서는 iaa_pipeline_spec/에 유지)
docs/decisions/README.md             ADR 규약 (아직 비어 있음)
evidence/README.md                   append-only 영역 규약
```

### 3.6 수정 — 3건 (경로/문서만)

```
CLAUDE.md          문서 포인터 2곳 추가 (methodology 무변경)
results/README.md  재작성 — 존재하지 않는 scripts/run_evaluation.py 를 가리키고 있었음.
                   artifact별 실제 재생성 명령 + "queue는 generated이나 재생성 불가" 경고
.gitignore         gpt_context_package/ + .zip 추가 (generated LLM context snapshot)
```

### 3.7 DELETE CANDIDATE — 없음 (중요)

`STAGE1_GOLD_113items_2026-09-07/` 루트 사본을 지시대로 조사한 결과 **삭제 후보가 아니다**:

- `scripts/amia_stage1_numbers.py` / `amia_stage1_trajectories.py`의 `newest_export(REPO_ROOT)`가
  저장소 루트에서 `*GOLD_*items_*`를 glob하고 **trailing date로 정렬**한다
- 루트에서 113-item을 지우면 다음 후보인 `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/`이 선택되어
  **74-item으로 조용히 회귀**한다
- discovery를 evidence 쪽으로 옮기는 변경은 산출물 선택 우선순위를 바꿀 위험이 있어 **DEFER**
- smoke test로 현재 113-item이 선택됨을 확인했다

따라서 gold payload는 두 곳에 의도적으로 중복 보관된다. `SOURCE_OF_TRUTH.md` §5에 명시했고, 두 사본이
갈라지면 `SHA256SUMS`로 검출된다.

---

## 4. 남아 있는 QUESTIONS FOR HUMAN DECISION

| # | 질문 | 왜 자동 결정하지 않았는가 |
|---|---|---|
| 1 | `docs/project_state/` 2개 파일 추적 전환을 유지할지 | Phase 1에서 명시적으로 제외했던 파일이다 |
| 2 | ~~stale pointer 해소~~ — **2026-09-08 해결.** `pipeline/REVIEW.md` / `REVIEW_notion.md`의 "현재 Stage 1" 라벨을 v1.2.2로 교정(쌍으로), v0.2는 superseded로 보존 | — |
| 3 | `AGENTS.md` — 실제 Codex consumer가 있는가 | 없으면 삭제, 있으면 find/replace 미러가 아닌 관리 정책 필요 |
| 4 | `AMIA_2027_ABSTRACT_REVIEW_BUNDLE_2026-08-24.zip` gitignore 추가 여부 | 논문 산출물인지 generated인지 판단 필요 |
| 5 | 로컬 전용 태그 2개 push 여부 (`adjudication-freeze-20260825`, `amia2027-stage1-gold-74items-20260903`) | Phase 1에서 "위 tag만" 지시받음 |
| 6 | `docs/audit_reference/` · `cohort_standard_unit_proposal_v0.md` archive 이동 승인 | §3.3 사유 참조 |
| 7 | `docs/amia_stage1_*.md`를 113 기준으로 재생성할지 | 재생성하면 AMIA 제출 당시 74-item 숫자가 사라진다 |
| 8 | `pipeline/prompts/prompt_1_splitting.txt` 등 v1.2.3 드리프트 처리 시점 | semantic 변경 — 연구 측 판단 사항 |

---

## 5. Phase 3 설계 관련 확인

### 5.1 guideline / ontology 문서를 이동하지 않은 것 — 의도대로 수행됨

`pipeline/schema/`의 아래 4개는 **원래 위치 그대로**다.

```
ontology_full_specification_unified_v1_2_2_ko.md    (v1.2.2 본문)
ontology_spec_v1_2_3_patch.md                       (v1.2.3, 본문 미병합)
annotation_guideline_v1_2_2_notion.md               (v1.2.2 판정 동결본, 규칙 ID 출처)
annotation_guideline_v1_2_1.md                      (superseded)
```

`docs/guidelines/stage1/CURRENT.md`는 **index 전용**으로 만들었고 이 파일들을 상대 경로로 가리킬 뿐,
어떤 파일도 옮기지 않았다. 따라서 Phase 3에서 `docs/guidelines/stage1/`의 최종 version layout을
한 번에 정하는 데 제약이 없다.

### 5.2 Phase 3이 분리해야 할 세 층 — 현재 상태

| 층 | 현재 저장소 상태 |
|---|---|
| **v1.2.2 historical adjudication basis** | ✅ 존재. `pipeline/schema/` 4개 문서 + `evidence/stage1/adjudication_v1_2_2_2026-09-07/` (113 gold, 해시 검증됨). `docs/guidelines/stage1/CURRENT.md` §1이 이 조합을 기준표준으로 고정 |
| **v1.3.0 current normative core** | ⛔ **저장소에 없음** |
| **v1.3.1 DEV executable prompt** | ⛔ **저장소에 없음** |

v1.3 부재의 근거(파일명 검색 0건, `primary_rule_id`/`supporting_rule_ids`/`recursion_targets`/
`TARGET_SEGMENTS`/`ROOT_CRITERION_TEXT`/`PARENT_CONTEXT` 전부 0 파일, H0–H6 언급이 핸드오프 문서에만
존재)는 `CURRENT_STATUS.md` §5에 검증 방법과 함께 기록되어 있다.

### 5.3 Phase 3이 이미 갖고 시작할 수 있는 것

- **경계 선언이 문서로 존재한다**: `docs/guidelines/stage1/CURRENT.md` §3이
  "113-item set은 v1.3-harmonized gold가 아니다 / v1.3.0·v1.3.1 미반입 / historical record를 다시 쓰지 않는다"를
  이미 명시. Phase 3은 이 문장을 갱신하는 형태로 세 층을 채우면 된다.
- **동결 증거가 해시로 고정되어 있다**: v1.3 도입이 historical record를 건드리지 않았음을
  `SHA256SUMS`로 증명 가능.
- **known drift가 목록화되어 있다**: `CURRENT_STATUS.md` §6의 7개 항목이 v1.3 프롬프트 구현 시
  실제로 손대야 할 지점과 정확히 겹친다 (text_span 배열, child_logic 필수, inclusion/exclusion 기본값,
  NEIGHBORING_CRITERIA span 출처 금지).
- **ADR 자리가 준비되어 있다**: `docs/decisions/` — 규범(normative) 변경과 구현 변경을 구분해 기록하는
  형식이 정의되어 있다. v1.3의 H/X 규칙 결정을 여기에 남기면 "기존 규칙으로 해소된 항목"과
  "v1.3이 새로 추가한 규칙으로 해소된 항목"을 구분할 수 있다.

### 5.4 Phase 3 착수 blocker

**v1.3.0 Canonical Core와 v1.3.1 DEV prompt의 저장소 반입.** 추정해서 생성하지 않았다.

---

## 6. `docs/repository/SOURCE_OF_TRUTH.md` — 전문

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

---

## 7. `docs/CURRENT_STATUS.md` — 전문

# CURRENT STATUS

> **최종 갱신**: 2026-09-08
> **활성 브랜치**: `feat/adjudication-prep` (main 미병합)
> **동결 checkpoint**: commit `80f0f28` / tag `stage1-adjudication-complete-2026-09-08`
> **Phase 2**: 완료 (`7f7fb7e` → `a27b0f0`) · **Phase 3**: 대기 — 착수 blocker는 §5
> 이 문서는 **빠르게 변하는 연구 진행 상태**의 entry point다.
> 무엇을 authoritative하게 읽어야 하는지는 [`repository/SOURCE_OF_TRUTH.md`](repository/SOURCE_OF_TRUTH.md)를 본다.

---

## 1. 한 문단 요약

Stage 1(적격성 기준 구조 분해) 연구 트랙은 **어노테이션 2라운드 → IAA → 판정(adjudication) → gold 증거집합**까지
완료되었다. 판정 큐 113건이 전건 해소되어 **gold 113건 / 미해결 gap 0건**이 되었고, 해시가 찍힌 동결
export와 함께 Git에 보존·원격 백업되었다. 다음 단계는 **저장소 구조 안정화**이며, v1.3 방법론 파일은
아직 이 저장소에 반입되지 않았다.

이 저장소를 "검증된 환자 수준 GraphRAG 스크리닝 에이전트"로 읽지 말 것.
현재 방법론적으로 성숙한 부분은 **Protocol KG / Stage 1 어노테이션 방법론**에 한정된다.

---

## 2. 진행 상태

| 단계 | 상태 |
|---|---|
| Stage 1 Round 1 어노테이션 | ✅ 완료 (2026-06-11 동결) |
| Stage 1 Round 2 어노테이션 | ✅ 완료 (2026-06-26 동결) |
| Stage 1 IAA 산출 | ✅ 완료 |
| Stage 1 판정 (adjudication) | ✅ **전건 완료** — 큐 113건 = gold 113건 |
| 판정 증거 동결 + 원격 백업 | ✅ 완료 (PHASE 1, commit `80f0f28`) |
| 저장소 구조 안정화 | ✅ **완료 (PHASE 2)** — source / frozen evidence / historical / generated 경계 문서화 |
| v1.3 방법론 반입 (PHASE 3) | ⏸️ **대기 — 파일이 저장소에 없음** (§5) |
| Stage 2–5 IAA | ⛔ 미착수 (stage_runner에서 `NotImplementedError`) |
| Neo4j 온톨로지 / RAG 에이전트 | ⛔ scaffold만 존재 |

---

## 3. 최신 증거집합 — 113 gold / 0 gap / 8 trials

**canonical 위치**: [`evidence/stage1/adjudication_v1_2_2_2026-09-07/`](../evidence/stage1/adjudication_v1_2_2_2026-09-07/)

아래 수치는 그 디렉터리의 `gold/STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl`에서
**재계산한 값**이며, 서술에서 옮겨 적은 것이 아니다.

| 항목 | 값 |
|---|---|
| total lines / gold / tier-3 gap ticket | 113 / **113** / **0** |
| trials | 8 |
| unique criterion ID / 중복 | 113 / 0 |
| criterion type | exclusion 62 · inclusion 51 |
| queue stratum | S1 49 · S2 35 · S3 4 · S4 25 |
| evidence tier | 0 → 10 · 1 → 2 · 2 → 101 |
| splitting_decision | none 59 · composite_split 42 · nested_exception 10 · macro_aggregate 2 |
| rule_status | existing 99 · new 12 · conflict 2 |
| adjudication pass | blind 113 |
| `escalate_pi=true` | 7 |
| `needs_recursion=true` | 8 |
| text_span 축자 위반 | 0 |

sha256
```
STAGE1_ADJUDICATED_113items_2026-09-07.jsonl (+.txt)
  bb0960577ce876b108cd04485ff60353d1e3f6aa8cf44e338c9884db29062865
STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl (+.txt)
  c3e498bee0ef5ba5479c51005a80d375731fd4b1f6272ce68a34bed0a6be9a7f
adjudication_queue.json
  a42b471c36c5f155d28e64b65b8e768c3e74c71e43edba03d61e1a27a2f427c8
```

### 판정 provenance — 단일 blind pass

- `adjudication.pass == "revealed"`인 record가 **0건**이다.
- 113건 전부 `blind_label == gold`이며, 둘이 다른 record는 **0건**이다.
- 따라서 이 데이터셋에는 D-3("blind → revealed 라벨 변경") 표본이 **존재하지 않는다**.
- 이 데이터셋을 **2-pass revealed 판정으로 사후 서술하지 말 것.**

판정은 다수결도 어노테이터 합의도 아니다. 단일 판정자(`GOLD`)가 동결 기준표준에 대해 `rule_id`를
인용하고 증거 `tier`를 부여하는 정오 판단이다. 두 어노테이터가 일치해도 둘 다 틀릴 수 있으므로 일치
항목도 감사 대상에 포함했다.

---

## 4. 판정의 historical 기준표준

113건은 **아래 세 문서를 기준으로** 생성되었다.

- ontology spec **v1.2.2** — `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md`
- ontology alignment patch **v1.2.3** — `pipeline/schema/ontology_spec_v1_2_3_patch.md` (본문 미병합)
- Stage 1 annotation guideline **v1.2.2** — `pipeline/schema/annotation_guideline_v1_2_2_notion.md`

> **113-item set은 v1.3에 맞춰 정렬된 gold가 아니다.**
> 향후 v1.3이 도입되어도 이 기록을 v1.3 기준으로 재라벨하거나 마이그레이션하지 말 것.
> 자세한 우선순위는 [`guidelines/stage1/CURRENT.md`](guidelines/stage1/CURRENT.md).

### IAA 수치

Round 2 어노테이터 간 splitting-decision **Cohen's κ = 0.650 (n = 172, 8 trials)**.
산출물은 `results/iaa/round2/iaa_stage1.md`이며 이 파일은 **generated·git 미추적**이다
(`scripts/compute_iaa.py --stage 1 --round 2`로 재생성). 분모 172는 R1/R2 envelope의 record 수와 일치한다.

> 전체 코퍼스 어노테이터 κ와, 판정으로 강화된 부분집합의 gold 대비 정확도는 **서로 다른 것을 측정한다.**
> 같은 척도처럼 나란히 비교하지 말 것.

---

## 5. v1.3 — 아직 이 저장소에 없다

[`project_state/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md`](project_state/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md)는 **Canonical Core v1.3.0 frozen** 및
**v1.3.1 development prompt**를 전제로 서술하지만, PHASE 1 감사 결과 **두 산출물 모두 이 저장소에
존재하지 않는다**.

확인 방법과 결과:

- 파일명 검색(`*1[._]3*`) — 0건
- `primary_rule_id` / `supporting_rule_ids` / `recursion_targets` / `TARGET_SEGMENTS` /
  `ROOT_CRITERION_TEXT` / `PARENT_CONTEXT` — 핸드오프 문서 자신을 빼면 **0 파일**
- H0–H6 결정 계층 언급 — 핸드오프 문서에만 존재
- 저장소 안의 "v1.3" 문자열은 전부 *deferred to v1.3* 형태의 **미래형 주석**

따라서 v1.3 관련 구현·프롬프트 작업의 **선행조건이 미충족**이다.
v1.3 내용을 추정해서 새로 만들지 말 것.

---

## 6. Known deferred implementation drift — 이번 단계에서 고치지 않음

프로덕션 어노테이션 트랙이 ontology **v1.2.3 패치를 아직 반영하지 않았다**.
**이 드리프트는 113 gold의 유효성에 영향을 주지 않는다** — gold는 판정 트랙
(`iaa_pipeline/adjudication.py`, v1.2.3 준수)으로 생성되었고 프로덕션 프롬프트를 거치지 않았다.

| 위치 | 드리프트 | 기준표준이 요구하는 것 |
|---|---|---|
| `pipeline/prompts/prompt_1_splitting.txt` | `text_span`을 **문자열**로 출력 | v1.2.3 변경 6 — 인접 세그먼트 **배열** |
| 〃 | `child_logic` "default, can omit" | v1.2.3 변경 1 — composite/macro 양쪽 **명시 필수** |
| 〃 | macro_aggregate는 항상 AND(omit) | 〃 |
| 〃 | inclusion=AND / exclusion=OR **암묵 기본값** | 표면 and/or·criterion type에서 추론 금지 |
| 〃 | `NEIGHBORING_CRITERIA`의 인접 criterion 텍스트를 자식 span 출처로 지시 | criterion-local 분해 원칙과 충돌 |
| `pipeline/validators.py` | `child_logic` 필수성 미검증 (존재 시 enum만 확인) | v1.2.3 변경 1 |
| `pipeline/orchestrator.py` | `sub["text_span"]`을 문자열로 직접 소비 (`:155`) | v1.2.3 변경 6 |

추가 점검 대상(향후 downstream 재설계 시): v1.2.3 패치가 요구한 **Stage 1 → Stage 2 PARENT_TEXT /
handoff 정합성**.

이 항목들은 semantic 변경이므로 **연구 측 판단 없이 고치지 않는다.**

---

## 7. 다음 단계

1. ~~저장소 구조 안정화~~ — **완료 (PHASE 2)**. 인계 문서는
   [`project_state/PHASE2_HANDOVER_2026-09-08.md`](project_state/PHASE2_HANDOVER_2026-09-08.md)
2. **(현재) PHASE 3** — v1.3.0 Canonical Core + v1.3.1 development prompt **저장소 반입**.
   코드 변경 없는 반입·governance 정렬 단계이며, 선행조건은 §5
3. H/X semantics를 바꾸지 않는 범위에서 v1.3 파이프라인 메커니즘 구현·검증
4. 사전 지정 개발 모델로 테스트 → **최종 Stage 1 프롬프트 동결**
5. 모델 계열 간 비교 평가
6. 신규 trial 대상 held-out 인간 재현성 평가

> 기존 8개 IAA trial은 held-out Round 3으로 쓸 수 없다.
> 어노테이터가 판정·방법 개선 과정에서 이미 노출되었다.

---

## 8. 미결 — 사람 판단 필요

- v1.3.0 / v1.3.1 파일 반입 (§5)
- 로컬 전용 태그 2개 push 여부: `adjudication-freeze-20260825`,
  `amia2027-stage1-gold-74items-20260903`
- `docs/amia_stage1_*.md`를 113 기준으로 재생성할지 여부
  (재생성하면 AMIA 제출 당시 74-item 숫자가 사라진다 — [`papers/amia2027/README.md`](papers/amia2027/README.md) 참조)
- prompt_1 드리프트(§6) 처리 시점

---

## 9. 관련 문서

| 문서 | 역할 |
|---|---|
| [`repository/SOURCE_OF_TRUTH.md`](repository/SOURCE_OF_TRUTH.md) | 무엇을 authoritative하게 읽을 것인가 |
| [`guidelines/stage1/CURRENT.md`](guidelines/stage1/CURRENT.md) | Stage 1 규범 문서 우선순위 index |
| [`papers/amia2027/README.md`](papers/amia2027/README.md) | AMIA 제출 당시 산출물 vs post-AMIA 113건 분리 |
| [`project_state/PHASE2_HANDOVER_2026-09-08.md`](project_state/PHASE2_HANDOVER_2026-09-08.md) | PHASE 2 인계 — 최종 tree, move/archive 목록, 미결 질문, Phase 3 설계 입력 |
| [`../evidence/stage1/adjudication_v1_2_2_2026-09-07/README.md`](../evidence/stage1/adjudication_v1_2_2_2026-09-07/README.md) | 동결 증거 번들 provenance·재검증 절차 |
| `../CLAUDE.md` | 저장소 운영 지침 (Claude Code) |
| `../pipeline/PIPELINE.md`, `../pipeline/HANDOFF.md` | 프로덕션 파이프라인 |
| `../iaa_pipeline_spec/README.md` | IAA 프레임워크 구현 상태 |
