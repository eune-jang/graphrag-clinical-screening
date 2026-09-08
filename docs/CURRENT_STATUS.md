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
