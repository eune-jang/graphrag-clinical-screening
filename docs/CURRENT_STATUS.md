# CURRENT STATUS

> **최종 갱신**: 2026-09-08
> **활성 브랜치**: `feat/adjudication-prep` (main 미병합)
> **동결 checkpoint**: commit `80f0f28` / tag `stage1-adjudication-complete-2026-09-08`
> **Phase 2**: 완료 (`7f7fb7e` → `a27b0f0`) · **Phase 3**: 완료 (v1.3 방법론 반입) · **Phase 4**: 대기
> 이 문서는 **빠르게 변하는 연구 진행 상태**의 entry point다.
> 무엇을 authoritative하게 읽어야 하는지는 [`repository/SOURCE_OF_TRUTH.md`](repository/SOURCE_OF_TRUTH.md)를 본다.

---

## 1. 한 문단 요약

Stage 1(적격성 기준 구조 분해) 연구 트랙은 **어노테이션 2라운드 → IAA → 판정(adjudication) → gold 증거집합**까지
완료되었다. 판정 큐 113건이 전건 해소되어 **gold 113건 / 미해결 gap 0건**이 되었고, 해시가 찍힌 동결
export와 함께 Git에 보존·원격 백업되었다. 저장소 구조가 안정화되었고, 후속 방법론 **v1.3.0(현행 규범)** 과
**v1.3.1 개발 프롬프트(비규범)** 가 반입되었다. **다만 런타임은 아직 v1.3을 구현하지 않는다** — 다음 단계다.

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
| v1.3 방법론 반입 (PHASE 3) | ✅ **완료** — canonical core v1.3.0 + 개발 프롬프트 v1.3.1 반입, 4층 governance 정의 (§5) |
| v1.3 런타임 구현 (PHASE 4) | ⏸️ **대기** — 런타임은 아직 v1.3 비준수 (§6) |
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

## 5. v1.3 — 반입 완료, 런타임 미구현

2026-09-08에 두 외부 아티팩트를 **바이트 동일 사본**으로 반입했다.
반입 기록(외부 파일명 ↔ 저장소 파일명 매핑, 해시, provenance): [`decisions/0001-stage1-v1-3-method-import.md`](decisions/0001-stage1-v1-3-method-import.md)

| 층 | 경로 | 지위 |
|---|---|---|
| **현행 규범** | [`guidelines/stage1/canonical_core_v1_3_0.md`](guidelines/stage1/canonical_core_v1_3_0.md) | **NORMATIVE** — Stage 1 Canonical Core v1.3.0 (FROZEN) |
| **개발 프롬프트** | `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` | **NON-NORMATIVE** 개발 아티팩트 |

```
sha256  canonical_core_v1_3_0.md      16e56569b7570acea8b50aaab82d31292d7421c8fe650fdbe960be1f09f0f0fe
sha256  stage1_prompt_v1_3_1.txt      dfce30245473b8f69627d5030cb772be3ef84f8e23957b09d170e6ac288590f9
```

### 네 개의 층

```
LAYER 1  HISTORICAL  v1.2.2 guideline + ontology v1.2.2/v1.2.3 + 113-item evidence
                     + iaa_pipeline/adjudication.py @ tag stage1-adjudication-complete-2026-09-08
LAYER 2  NORMATIVE   canonical_core_v1_3_0.md
LAYER 3  DEV PROMPT  stage1_prompt_v1_3_1.txt  (비규범)
LAYER 4  RUNTIME     ⚠️ 아직 v1.3 비준수
```

전체 정의: [`guidelines/stage1/CURRENT.md`](guidelines/stage1/CURRENT.md) §0

> **v1.3.0이 현행 규범이지만, 완전히 v1.3을 따르는 런타임 구현은 아직 없다.**
> canonical core가 저장소에 있다는 사실은 런타임 준수의 증거가 **아니다**.
> 개발 프롬프트는 프로덕션 로더가 읽지 않는다 —
> **development artifact imported; runtime activation deferred to Phase 4.**

---

## 6. Known implementation gap — 기준은 v1.3.0

런타임이 현행 규범 v1.3.0을 따르지 않는다. 비교 기준은 더 이상 v1.2.3 패치가 아니라 **canonical core v1.3.0**이다.

**이 격차는 113 gold의 유효성에 영향을 주지 않는다** — gold는 판정 트랙
(`iaa_pipeline/adjudication.py` @ tag `stage1-adjudication-complete-2026-09-08`)으로 생성되었고
프로덕션 프롬프트를 거치지 않았다. 실제로 gold의 sub_criteria 123/123은 이미 `text_span` 배열이다.

재고 요약: **conformant 5 / partial 8 / missing 12 / incompatible 6 / historical-only 4**

`incompatible` 6건 (고치면 기존 출력이 바뀜):

| canonical family | 위치 | 어긋난 동작 |
|---|---|---|
| **H4** | `pipeline/validators.py:59-61` | `nested_exception`에 `≥2 sub_criteria` 강제 — v1.3은 exception span만. **historical gold 10건 중 9건을 거부** |
| **X1** | `pipeline/orchestrator.py:155` | `sub["text_span"]`을 문자열로 소비 — v1.3은 배열 |
| **H5** | `pipeline/prompts/prompt_1_splitting.txt` | inclusion=AND / exclusion=OR 암묵 기본값 |
| **X7** | 〃 | 인접 criterion 텍스트를 자식 span 출처로 명시 지시 |
| **X5** | 〃 | "as defined in Table" 위임을 `macro_aggregate`로 |
| **X4** | 〃 | `nested_exception`의 cohort_scope를 자식에 배치 |

주요 `missing`: H0 role gate · H1-A/H1-B 명제 경계 · H2-B 종양학 축 + confirmation 규칙 · H3 open/closed 목록 ·
H6 재귀 루프 · `recursion_targets` · `primary_rule_id` / `supporting_rule_ids` ·
`ROOT_CRITERION_TEXT` / `TARGET_SEGMENTS` / `PARENT_CONTEXT`

전체 재고(저장·실행 계약, ontology vs pipeline metadata 경계, Phase 4 작업 범주 A–I 포함):
[`project_state/stage1_v1_3_implementation_gap.md`](project_state/stage1_v1_3_implementation_gap.md)

이 항목들은 semantic 변경이므로 **연구 측 판단 없이 고치지 않는다.**
v1.2.3 중간 상태를 따로 만들지 않고 **v1.3에서 한 번에 해소**한다.

---

## 7. 다음 단계

1. ~~저장소 구조 안정화~~ — **완료 (PHASE 2)**. 인계 문서는
   [`project_state/PHASE2_HANDOVER_2026-09-08.md`](project_state/PHASE2_HANDOVER_2026-09-08.md)
2. ~~v1.3 방법론 반입~~ — **완료 (PHASE 3)**. 4층 governance 정의, 구현 격차 재고 작성
3. **(다음) PHASE 4** — v1.3 런타임 구현. H/X 의미를 바꾸지 않는 범위에서 프롬프트 재작성,
   입력 컨텍스트 배선, 출력 계약 확장, 재귀 루프, 검증기 정렬 (§6)
4. 사전 지정 1 frontier + 1 open-weight 모델로 개발 → **최종 Stage 1 프롬프트 동결**
5. 모델 계열 간 비교 평가 (3 frontier + 2 open-weight)
6. 신규 trial 대상 held-out 인간 재현성 평가

> 기존 8개 IAA trial은 held-out Round 3으로 쓸 수 없다.
> 어노테이터가 판정·방법 개선 과정에서 이미 노출되었다.

---

## 8. 미결 — 사람 판단 필요

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
| [`guidelines/stage1/CURRENT.md`](guidelines/stage1/CURRENT.md) | Stage 1 4층 governance + 규범 우선순위 index |
| [`guidelines/stage1/canonical_core_v1_3_0.md`](guidelines/stage1/canonical_core_v1_3_0.md) | **현행 규범** — Stage 1 Canonical Core v1.3.0 |
| [`project_state/stage1_v1_3_implementation_gap.md`](project_state/stage1_v1_3_implementation_gap.md) | v1.3 구현 격차 재고 (Phase 4 입력) |
| [`decisions/0001-stage1-v1-3-method-import.md`](decisions/0001-stage1-v1-3-method-import.md) | v1.3 반입 ADR |
| [`papers/amia2027/README.md`](papers/amia2027/README.md) | AMIA 제출 당시 산출물 vs post-AMIA 113건 분리 |
| [`project_state/PHASE2_HANDOVER_2026-09-08.md`](project_state/PHASE2_HANDOVER_2026-09-08.md) | PHASE 2 인계 — 최종 tree, move/archive 목록, 미결 질문, Phase 3 설계 입력 |
| [`../evidence/stage1/adjudication_v1_2_2_2026-09-07/README.md`](../evidence/stage1/adjudication_v1_2_2_2026-09-07/README.md) | 동결 증거 번들 provenance·재검증 절차 |
| `../CLAUDE.md` | 저장소 운영 지침 (Claude Code) |
| `../pipeline/PIPELINE.md`, `../pipeline/HANDOFF.md` | 프로덕션 파이프라인 |
| `../iaa_pipeline_spec/README.md` | IAA 프레임워크 구현 상태 |
