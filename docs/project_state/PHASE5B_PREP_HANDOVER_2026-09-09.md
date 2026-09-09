# PHASE 5B-prep 인계 — 완료 보고 + 가설 + 개발 세트

> **작성일**: 2026-09-09 · **작업일**: 2026-09-08
> **저장소**: graphrag-clinical-screening · **브랜치**: `feat/adjudication-prep`
> **HEAD**: `ea4d414` (origin 동기화) · **main 미병합** · **신규 태그 없음**
> **유료 API 호출: 0회**

이 문서 하나에 네 가지가 들어 있다. §2–§4는 저장소 파일을 **그대로 복사**한 것이다(요약 아님).

| 요청 항목 | 이 문서의 절 |
|---|---|
| Claude Code completion report 전체 | **§1** |
| `docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md` | **§2** (전문) |
| `experiments/stage1_v13/phase5b_dev/design.md` | **§3** (전문) |
| `experiments/stage1_v13/phase5b_dev/cases.jsonl` | **§4** (전문 34줄) |

---

## 0. 검토자가 집중해서 볼 두 가지 — 먼저 답

리뷰 초점이 두 가지라고 하셨으므로, 근거를 앞에 놓는다.

### 0-1. 프롬프트 가설이 canonical semantics를 몰래 바꾸고 있지 않은가

**바꾸지 않는다.** 구조적으로 세 겹의 장치가 있다.

**첫째, 파일이 물리적으로 안 바뀌었다.** 외부 원본과 바이트 대조로 확인했다.

```
docs/guidelines/stage1/canonical_core_v1_3_0.md              무변경 (외부 원본과 바이트 동일)
pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt 무변경 (외부 원본과 바이트 동일)
v1.3.2                                                       생성하지 않음
```

**둘째, 두 가설 모두 "규칙을 바꾸자"가 아니라 "이미 있는 규칙의 관계를 명시하자"다.**

| 가설 | canonical이 이미 말하는 것 | 가설이 제안하는 것 |
|---|---|---|
| H-X2-1 | `Copy a shared dependent qualifier … into every child it semantically modifies.` | 이 의무와 "문법적 불완전 허용" 절의 **관계를 명시**. 새 의무를 만들지 않는다 |
| H-PR-1 | `Evidence tier should be derived from the primary decisive canonical rule.` / `H2-A validates the H1 proposition boundary` | **"decisive"를 정의**. canonical이 이미 H2-A를 validating rule이라 부르는데, 프롬프트에는 그 구분이 없다 |

두 경우 모두 **canonical에 이미 있는 문장을 근거로** 프롬프트가 말하지 않은 관계를 채우는 것이다.

**셋째, 안전 조건이 가설 안에 명시돼 있다.**

> H-PR-1: **구조 결정 자체(`splitting_decision` / `child_logic`)는 변하지 않을 것.**
> 세 번째가 안전 조건이다. provenance 지침을 손댔는데 라벨이 바뀐다면
> 그것은 프롬프트 명확화가 아니라 **의미 변경**이므로 즉시 중단하고 규범 검토로 넘긴다.

그리고 개발 세트에 **대조군 5건**을 넣어 이 조건을 기계적으로 검사한다 —
Phase 5A에서 이미 옳게 나왔던 유형(H1-A 병합 / 깨끗한 H1-B 분할 / open list / nested_exception /
cohort scope)이 바뀌면 **후보를 기각**한다.

**넷째, escalation 경계가 정의돼 있다.** H-PR-1은 의도적으로 **경계선**에 놓았다:
명확화해도 H2-A 역전이 지속되면 그것은 프롬프트 부족이 아니라
**canonical에 판정 근거가 없다는 증거**이므로 v1.4 규범 사안으로 승격한다.
즉 "프롬프트로 조용히 해결"하는 경로를 미리 차단해 두었다.

**tier 매핑은 건드리지 않는다.** `H2-A → Tier 0` 매핑 자체는 canonical 소관이며,
가설이 다루는 것은 **어떤 규칙이 primary가 되는가**뿐이다. tier 변화는 그 결과다.

> ⚠️ 다만 정직하게: 문구 후보 A안(H2-A·H3를 이름으로 지목)은 **특정 관측에 맞출 위험**이 있다.
> 그래서 이름을 지목하지 않는 B안을 함께 적어 두고 **확정하지 않았다**. 선택은 사람 판단이다.

### 0-2. 개발 세트가 S04 / H2-A 몇 사례에 과적합되지 않았는가

**과적합 방지를 설계에 넣었다.** 네 가지 근거.

**① S04를 고쳐 쓰지 않았다.** qualifier 유형 × 구문 위치를 교차시켰다.

| case | qualifier 유형 | 구문 위치 | 공유 표지 |
|---|---|---|---|
| A1 | 시간 | 두 번째 conjunct 뒤 (S04 형태) | **없음** |
| A2 | 시간 | coordination **앞** | 없음 |
| A3 | 중증도 | 뒤 | `either of` |
| A4 | 수치 | 분배 | `each` |
| A5 | 조건/방법 | 뒤 | `in either case` |
| A8 | 공유 목적어 | 뒤 | 없음 |
| E1 | 방법 + 시간 (2개) | 하나는 비연속 | `in either case` |

**A1·A2에 표지를 일부러 뺐다.** Phase 5A에서 S04(실패)와 S05·S12(성공)의 차이가
표지(`each`, `at screening`의 위치)였을 가능성이 있어, 표지 없는 경우를 독립적으로 확보했다.

**② 음성 대조군이 있다 — 이게 가장 중요하다.**
`A6`(분기 전용 qualifier), `A7`(공유 qualifier 없음)은 **복사하면 안 되는** 케이스다.

> A1–A5·A8에서 복사가 늘고 **A6·A7에서 늘지 않아야** 가설이 지지된다.
> 한쪽만 개선되면 그것은 개선이 아니라 **편향 이동**이다.

음성 대조군이 없으면 "복사를 강화했더니 좋아졌다"가 과잉 복사를 성공으로 오독한다.

**③ H2-A도 같은 조합을 반복하지 않는다.** 서로 다른 semantic 조합 6가지로 흩었다.

```
B3 진단 + 바이오마커        (H2-B가 canonical에서 직접 규정)
B4 진단 + 치료력            (S13 패턴, 다른 도메인)
B5 검사값 + 약물 제한        (S12 패턴, 다른 도메인)
B6 확인(confirmation) 귀속
B7 open list
B8/B9 closed macro list ×2   (동등 구조 쌍)
B10 같은 도메인·다른 기전    (H1-A 병합 실패 → H1-B)
```

**④ B8/B9 쌍이 안정성 자체를 측정한다.** 도메인만 다르고 구조가 같은 `macro_aggregate` 두 건이다.
같은 primary가 나오면 안정, 갈리면 Phase 5A의 S06 vs S07 관측이 재현된 것이다.
이것은 "고칠 수 있는가"가 아니라 **"규칙군 차원의 문제인가"** 를 묻는 설계다.

**⑤ 재귀는 관측 확대가 아니라 커버리지 공백 메우기다.** Phase 5A에서 실모델로 노출된 재귀는
`nested_exception → ["main"]` **1건, depth 1**뿐이었다. C군 7건은 depth 2·3, 복수 target,
형제 분기, macro 아래 재귀, 혼합 논리를 **의도적으로** 겨냥한다.

**규모의 한계는 명시했다**: 34건으로 유병률을 추정하지 않는다.
커버리지는 rule family 기준이며 빈도 기준이 아니다.

---

## 1. Completion report (전문)

### [PHASE 5B-PREP SUMMARY]

관측 가능성 수정 → 환경 재현성 기록 → 가설 사전 등록 → 개발 세트 설계.
프롬프트·canonical·프로덕션 경로는 손대지 않았다.

### [TRACE LOGGING]

**누락됐던 것**: Phase 5A는 **성공한 pass당 1레코드**만 남겨, 파싱/검증 실패 후 재시도된 응답은
흔적이 없었다. 재시도 수도 `api_calls − successful_nodes`로 유추해야 했다. 20개 요구 항목 중 9개 부재.

**attempt 단위 로깅이 실제로 추가됐는가 — 그렇다.**
`pipeline/stage1_v13/tracing.py` 신설. **harness가 아니라 런타임을 계측**했다 —
주입된 LLM callable은 프롬프트 문자열만 볼 뿐 attempt index·parsed JSON·검증 결과·계층 경로·
TARGET_SEGMENTS·PARENT_CONTEXT를 알 수 없기 때문이다.

```
ROOT CASE → PASS (계층 노드) → ATTEMPT (모델 호출 1회)
```

시도가 일어나는 즉시 append-only로 기록하며 **실패도 남긴다.** 덮어쓰지 않는다.
`summarize_attempts`는 재시도를 `is_retry=true` 레코드로 세지, 산술 차이로 유추하지 않는다.
부재도 의미를 유지한다 — 파싱 실패 시 `parsed_json` 없음, 검증 미실행 시 `validation_errors` None.

레코드 필드: `run_id · record_index · case_id · hierarchy_path · depth · pass_id · attempt_id ·
attempt_index · is_retry · model · prompt_sha256 · root_criterion_text · target_segments ·
parent_context · criterion_type · trial_has_cohorts · raw_response · parse_status · parse_error ·
parsed_json · validation_status · validation_errors · latency_s · usage · llm_meta · api_error ·
cache · disposition · recorded_at` + `run_config` 병합분.

**parse 실패 / validator 실패 / retry 성공 테스트가 있는가 — 있다.**

| 테스트 | 검증 내용 |
|---|---|
| `test_parse_failure_then_retry_success_keeps_both` | 파싱 실패 레코드 + 재시도 성공 레코드 **둘 다** 보존, `attempt_index` 0→1, `is_retry` false→true |
| `test_validation_failure_then_retry_success_keeps_both` | 검증 실패 → 재시도 성공, 둘 다 보존 |
| `test_validation_errors_retained_on_validation_failure` | 3회 전부 실패 시 **3레코드 모두** 유지, 각 레코드에 `validation_errors` 보존 |
| `test_api_error_is_recorded_then_propagates` | API 오류도 기록 후 재전파 (러너는 API 오류를 재시도하지 않으며, 그 정책을 관측성 수정에 끼워 넣지 않았다) |
| `test_attempt_order_preserved` | 파싱실패 → 검증실패 → 성공 순서와 `record_index` 1·2·3 보존 |
| `test_retry_inside_a_recursive_child_is_attributed_to_that_child` | `[("root",0), ("root.a",0), ("root.a",1)]` |

**failed raw response가 보존되는가 — 보존된다.**
`test_failed_raw_response_is_retained`가 거부된 응답 본문 자체(`"<<<garbage>>>"`)가
레코드에 남는지 확인한다. 실패 사실만이 아니라 **응답 원문**이 남는다.
`test_parsed_json_absent_on_parse_failure`는 그때 `parsed_json`이 **채워지지 않음**을 확인한다
(플레이스홀더를 넣지 않는다 — 부재가 의미다).

**결과**: 신규 21/21 통과. `tracer` 기본값 `None` → 동작 불변, 기존 85건 그대로 통과
(`test_tracer_is_optional_and_changes_nothing`).

### [SDK / ENVIRONMENT]

```
Python      3.11.5 (CPython, miniconda base) · Darwin arm64
openai SDK  1.6.1                              (PyPI 최신 3.8.0)
부수         httpx 0.26.0 / pydantic 2.5.3 / anyio 4.2.0
model       gpt-5.6-terra
requested_reasoning_effort  medium
max_completion_tokens       8000
전달 방식    extra_body   (1.6.1에 reasoning_effort / max_completion_tokens 명시 파라미터 없음)
```

**어디에 pin/기록했는가**:
`experiments/stage1_v13/environment/requirements-phase5.txt` + 같은 디렉터리 `README.md`.

**`pyproject.toml`에 넣지 않았다.** 저장소 관례는 명확하지만(pyproject = 개발 정본,
extras `dev`/`llm`/`iaa`), `openai==1.6.1`을 공유 extra에 고정하면 **레거시 프로덕션 경로까지
v1.3 실험이 고른 버전에 묶인다** — "SDK 현대화를 이유로 프로덕션 동작 변경" 금지의 거울상이다.
기존 `llm` extra는 로컬 open-weight(transformers/torch)용이라 의미도 섞인다.
`openai` 미선언은 v1.3이 만든 문제가 아니라 **기존 저장소 결손**이다
(프로덕션 `pipeline/llm_client.py`가 이미 import한다). 선언 위치·제약은 **사람 판단**으로 남겼다.

**`reasoning_effort=medium`을 어떻게 기록하는가**:

```
requested_reasoning_effort = "medium"     ← 우리가 보낸 값. 검증 가능
confirmed_reasoning_effort                ← 기록하지 않는다
```

SDK 1.6.1의 `usage`가 노출하는 키는 `prompt_tokens` / `completion_tokens` / `total_tokens` 뿐이고
`reasoning_tokens` 류 필드가 없다 — **응답이 적용을 증명하지 않는다.**
`JsonlTracer(run_config=...)`가 이 dict를 **모든 attempt 레코드에 병합**하므로,
한 번 설정하면 시도 단위로 provenance가 남는다.

**재현성의 실질 위험**: harness가 SDK 1.6.1에 암묵 결합돼 있다. 3.x에서는 `extra_body` 없이
명시 파라미터를 쓰므로 코드가 달라진다.

### [PROMPT HYPOTHESES]

**H-X2-1 (공유 qualifier)** — 프롬프트가
`Repeat a shared dependent qualifier in every child it semantically modifies` 바로 아래
`A child may be grammatically incomplete if ROOT/PARENT context supplies shared meaning`을 두어,
후자가 전자의 예외로 읽힐 여지. 후자는 *문법적* 불완전성 허용이지 *의미적으로 수식하는 qualifier의
생략 허가*가 아니다. 후보 문구 2안(X2 본문 관계 명시 / 자기점검 항목 추가), **미확정**.
기대 효과 3항 중 **2·3항이 핵심** — 누락 감소 + 무효 span 증가 없음 + 분기 전용 qualifier 복사 증가 없음.

**H-PR-1 (`primary_rule_id`)** — canonical도 프롬프트도 **"decisive"를 정의하지 않는다**.
결정을 *만든* 규칙과 *정당화하는* 규칙을 가르는 문장이 없다. canonical은 다른 곳에서
`H2-A validates the H1 proposition boundary`라고 말하는데, 프롬프트에는 그 구분이 없다.
후보 2안(H2-A·H3 명시 / 일반 원칙만), 트레이드오프 기록.
**안전 조건**: 구조 결정이 바뀌면 명확화가 아니라 의미 변경이므로 중단.

**escalation 경계** — 판별 질문: *"모델이 이미 옳게 판단한 것을 기록하는 방식의 문제인가?"*

| 수준 | 기준 |
|---|---|
| **PROMPT** | 모델이 올바른 규칙을 알고 있는데 필드 배정·형식이 불안정 / 프롬프트 지침이 미명시 / 라벨은 옳고 provenance만 흔들림 |
| **NORMATIVE (v1.4)** | canonical을 두 가지로 합리적으로 읽을 수 있고 각각 다른 구조 결정을 함의 / **어떤 규칙이 primary여야 하는지 canonical이 정하지 않음** / 고치면 출력 규율이 아니라 결정 경계가 바뀜 |

H-X2-1은 명백히 PROMPT 수준(모델이 자기 notes로 규칙을 알고 있음을 증명했다).
**H-PR-1은 의도적으로 경계선** — 명확화해도 역전이 지속되면 canonical에 판정 근거가 없다는
증거이므로 v1.4로 승격.

### [DEVELOPMENT SET]

**총 34 케이스** (제안 24–36 범위 내), **미실행**.

| 군 | 건수 | 내역 |
|---|--:|---|
| **X2 공유 qualifier** | **8** | A1–A5, A8, E1, F2 |
| ├ **음성 대조군** | **2** | A6(분기 전용), A7(공유 없음) — 복사 금지 |
| **provenance** | **7** | B3, B4, B5, B6, B8, B9, B10 |
| **recursion** | **7** | C1–C6, E2 |
| ├ **음성 대조군** | **1** | C7(분할했으나 재귀 불필요) |
| **exception 구분** | **4** | D1, D3, D4, D5 |
| **control** | **5** | B1, B2, B7, D2, F1 |

**X1 provenance는 별도 군이 아니라 교차 배치**했다: E1(multi-segment, 비연속 공유 qualifier),
E2(형제 텍스트 누출 금지), A8(문법 불완전하되 의미 완전) — rule_family에 `X1` 3건으로 집계된다.

rule family 커버리지: `H1-B 15 · X2 10 · H4 9 · H6 8 · H3 5 · X1 3 · X3 3 · H5 3 ·
H1-A 2 · H2-A 2 · H2-B 2 · X4 2 · H0 1 · X5 1 · X7 1`

기대 구조: composite_split 20 · nested_exception 5 · none 4 · macro_aggregate 3 · 모호 2
· 재귀 기대 7건 · inclusion 19 / exclusion 15 · cohort 지정 2건

**depth≥2 · 복수 recursion target · 형제 재귀가 설계에 포함됐는가 — 전부 포함됐다.**

| 경로 | 담당 케이스 |
|---|---|
| **depth 2** | C1 (composite → 자식 1개 재귀), C3 (nested_exception → main → composite) |
| **depth 3** | C6 (exception over composite whose child is an OR pair) |
| **복수 `recursion_targets`** | **C2** (자식 2개 동시 재귀) |
| **형제 재귀 분기** | **C2** (같은 레벨 형제 2개가 각각 재귀) |
| macro 아래 재귀 자식 | C4 |
| 혼합 논리 A AND (B1 OR B2) | C5 |
| 형제 텍스트 누출 금지 | E2 |
| 재귀 불필요 (음성 대조) | C7 |

`max_depth` 가드와 `empty_main`은 실모델로 유도하기 어려워(자연스러운 criterion이 depth 5를 넘지 않음)
**mock 테스트가 계속 담당**한다 — 이 점은 design.md에 명시했다.

**중복 검증(프로그램)**: v1.3.1 프롬프트 예제 **0건**, Phase 5A 케이스 **0건**,
historical 113 **0건**, `case_id` 중복 **0건**.

### [NO-CHANGE CONFIRMATION]

```
canonical_core_v1_3_0.md                          무변경 (외부 원본과 바이트 동일)
stage1_prompt_v1_3_1.txt                          무변경 (외부 원본과 바이트 동일)
prompt_1_splitting.txt                            무변경
examples.json                                     무변경
프로덕션 경로 (orchestrator/validators/llm_client) 무변경
v1.3.2                                            생성하지 않음
동결 payload 변경                                  0건
API 호출                                          0회
```

### [TESTS]

```
tests/test_stage1_v13.py          85/85 PASS
tests/test_stage1_v13_tracing.py  21/21 PASS   (신규, 전부 mock, API 호출 0)
tests/test_iaa_metrics.py         44/44 PASS
tests/test_adjudication.py        50/50 PASS
                                  총 200/200
```

### [FROZEN EVIDENCE INTEGRITY]

```
evidence SHA256SUMS               64/64 OK, FAILED 0
live iaa_workspace + queue        104/104 OK
61 / 61' / 74 / 113 스냅샷         무변경
반입 v1.3 아티팩트                 2/2 외부 원본과 바이트 동일
동결 payload 변경 (80f0f28..HEAD)  0건
```

*중간 점검에서 "frozen 1건"이 뜬 것은 Phase 2에서 추가한 `evidence/README.md`(evidence 영역 규약
문서)를 넓은 grep 패턴이 잡은 오탐이며, 정확한 패턴으로는 0건이다.*

### [GIT COMMITS]

```
ea4d414  experiment: add Stage 1 v1.3 Phase 5B development set     5 files, +904/−2
ec31d9c  docs: define Stage 1 v1.3 Phase 5B prompt hypotheses      1 file,  +237
9f802f7  chore: record Phase 5 development environment             2 files, +108
241d8eb  fix: preserve complete Stage 1 v1.3 attempt traces        4 files, +599/−4
```
push `a4ecbf2..ea4d414` → `origin/feat/adjudication-prep` · **태그 생성 없음** · **main 미병합**

### [GIT STATUS]

```
?? AGENTS.md                                        범위 밖 (계속 defer)
?? AMIA_2027_ABSTRACT_REVIEW_BUNDLE_2026-08-24.zip  범위 밖 (계속 defer)

HEAD ea4d414 == origin/feat/adjudication-prep
main 349306d == origin/main   (미병합)
태그 3개 (신규 없음)
```

### [QUESTIONS REQUIRING HUMAN DECISION]

1. **프롬프트 후보 문구 확정** — H-X2-1 A/B안, H-PR-1 A/B안 (또는 제3안)
2. **`openai` 의존성 선언** — 새 extra / 기존 그룹 / 계속 미선언.
   프로덕션도 쓰는 패키지라 v1.3만의 결정이 아니다
3. **호출 상한** — A/B 비교는 34 × 2 = 68 root 호출 + 재귀 + 재시도
4. **A6·A7 과잉 복사 판정 기준** 사전 정의
5. **D5(모호 케이스)** — 지표 제외 vs 별도 보고
6. **API 오류 재시도** — 현재 미지원. 추가할지 (관측성 수정에 끼워 넣지 않았다)

### [READY FOR PHASE 5B EXECUTION]

**YES.**

첫 모델 호출 전에 정해야 할 것은 **1·3번**(프롬프트 후보 문구, 호출 상한)이다.
나머지(2·4·5·6)는 실행 자체를 막지 않지만, **4·5는 결과 해석 전에** 정해져야
사후 기준 변경이 되지 않는다.

v1.3.1 미수정 · v1.3.2 미생성 · 모델 호출 없음 · 프롬프트 비교 없음 ·
113 채점 없음 · 최종 동결 없음.

---

## 2. `docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md` — 전문

# Stage 1 v1.3 — Phase 5B 프롬프트 가설

> **작성일**: 2026-09-08 (PHASE 5B-prep) · **성격**: 사전 등록된 **가설**이다.
> **프롬프트를 수정하지 않았다. canonical core를 수정하지 않았다. v1.3.2를 만들지 않았다.**
> 근거: [`../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md`](../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md)

두 가설 모두 **비규범(non-normative) 프롬프트 명확화 후보**다. canonical 의미를 바꾸지 않는다.
문구는 **확정이 아니다** — 각 가설에 대안 표현을 하나 이상 적어 둔다.

---

## H-X2-1 — 공유 qualifier 복사 누락

### 관측 (S04, 1건)

```
"Women who are pregnant or breastfeeding at the time of screening."

[a] ["Women who are pregnant"]                          ← qualifier 없음
[b] ["breastfeeding at the time of screening"]
notes: "The phrase 'at the time of screening' applies to both coordinated conditions by shared context."
```

모델이 **두 조건 모두에 적용된다고 스스로 서술**하고도 자식 a에 넣지 않았다.
런타임 손실이 아니고(런타임은 `text_span` 내용을 만들지도 바꾸지도 않는다),
능력 문제도 아니다(같은 실행의 S05·S12에서 동일 유형을 정확히 복사했다).

### 프롬프트 원문

```
X2. SHARED EXPRESSIONS / QUALIFIER SCOPE

- Do not duplicate a shared clinical entity solely to make children grammatical.
- Repeat a shared dependent qualifier in every child it semantically modifies.
- A child may be grammatically incomplete if ROOT/PARENT context supplies shared meaning.
```

canonical 원문도 같은 구조다(`Copy a shared dependent qualifier … into every child it
semantically modifies.` / `A child may be grammatically incomplete if root/parent context is
available downstream.`).

### 가설

> **두 번째 불릿(복사 의무)과 세 번째 불릿(문법적 불완전 허용)이 나란히 놓여 있어,
> 세 번째가 두 번째의 예외로 읽힐 수 있다.**
> 세 번째 불릿은 *문법적* 불완전성 허용이지 *의미적으로 수식하는 qualifier의 생략 허가*가 아니다.
> 두 절의 관계를 명시하면 누락이 줄어들 것이다.

### 후보 문구 A (관계 명시)

```
- A child may be grammatically incomplete if ROOT/PARENT context supplies shared meaning.
  This does NOT permit omitting a shared dependent qualifier that X2 requires: if a
  temporal/numeric/conditional/severity qualifier semantically modifies more than one
  child, its exact source span must appear in every child it modifies.
```

### 후보 문구 B (자기 점검으로 이동, 본문 불변)

X2 본문은 그대로 두고 SILENT PRE-OUTPUT CHECK에 한 줄 추가:

```
18. If I concluded that a qualifier applies to more than one child, I copied its exact
    source span into every one of them.
```

B의 장점: 규칙 본문을 건드리지 않아 규범 해석 변경 위험이 더 낮다.
B의 단점: 점검 목록이 이미 17항목이라 희석될 수 있다.

### 기대되는 관측 효과

- 공유 qualifier 누락 **감소**
- **동시에** 무효 span 복사(원문에 없는 텍스트를 만들어 붙이는 것)가 **증가하지 않을 것**
- 분기 전용 qualifier를 잘못 복사하는 사례가 늘지 않을 것 (아래 대조군이 이를 잡는다)

두 번째·세 번째가 핵심이다. "복사하라"를 강화하면 **과잉 복사**로 넘어갈 수 있으므로,
개발 세트에 **복사하면 안 되는 케이스**를 반드시 포함한다.

### 과적합 방지

S04를 여러 번 고쳐 쓰지 않는다. 서로 다른 qualifier 유형(시간/중증도/수치/조건),
서로 다른 구문 위치(coordination 앞 / 두 번째 conjunct 뒤), 그리고 **분기 전용 qualifier**를
독립적으로 작성한 케이스로 검증한다. 확인하려는 것은 문장 하나의 수정 가능성이 아니라
**규칙군(rule family) 차원의 실패 여부**다.

---

## H-PR-1 — `primary_rule_id`가 확인 규칙으로 채워짐

### 관측 (S03·S12·S13, 3건 / S06 vs S07, 1건)

| case | primary | 실제로 경계를 세운 규칙 | tier |
|---|---|---|--:|
| S03 | **H2-A** | H1-B → canonical H2-B가 진단 vs 바이오마커를 직접 규정 | **0** |
| S12 | **H2-A** | H1-B (모델이 supporting에 직접 기재) | **0** |
| S13 | **H2-A** | H1-B (모델이 supporting에 직접 기재) | **0** |
| S06 | H3 | H3 (macro gate) | 2 |
| S07 | **H1-B** | H3 (closed list + umbrella) — S06과 구조 동일한데 선택이 갈림 | 2 |

세 건 모두 **같은 방향의 역전**이다: 결정적 규칙이 `supporting_rule_ids`로 내려가고
확인 규칙이 primary로 올라갔다. tier는 primary에서 파생되므로 **tier 0 주장 3건**이 발생했다.

canonical은 H2-A를 이렇게 규정한다:

> H2-A **validates** the H1 proposition boundary; it should not turn Stage 1 into concept extraction.

그리고 tier 규칙은:

> Evidence tier should be derived from the **primary decisive canonical rule**.

### 프롬프트 원문

```
PROVENANCE

Output one primary decisive rule ID.

Suggested default evidence tier mapping:
- H2-A -> Tier 0
...
For primary_rule_id:
- choose ONE decisive rule
- put secondary rules in supporting_rule_ids
```

"decisive"의 뜻이 정의되어 있지 않다. **"결정을 정당화하는 규칙"과 "결정을 만든 규칙"을
구분하는 문장이 없다.**

### 가설

> **`primary_rule_id`는 Stage 1 구조 결정을 가장 직접적으로 성립시킨 규칙이어야 한다.
> 다른 규칙이 이미 세운 경계를 검증·확인하기만 하는 규칙은 원칙적으로 `supporting_rule_ids`다.**
>
> 구체적으로: H1이 이미 명제 경계를 세운 뒤 H2-A가 leaf 적정성을 확인했을 뿐이라면
> H2-A는 primary가 되지 않는다.
>
> `macro_aggregate`의 경우: 구조를 결정한 것이 H3의 open/closed 판정 또는 umbrella 테스트라면,
> 단지 복수의 독립 자식을 식별했다는 이유로 H1-B를 고르지 말고 **H3를 결정적 규칙으로 본다.**

### 후보 문구 A (PROVENANCE에 정의 추가)

```
For primary_rule_id:
- choose the ONE rule that most directly ESTABLISHED the structural decision
- a rule that only validates or confirms a boundary another rule already established
  belongs in supporting_rule_ids
- in particular, do not select H2-A as primary merely because it validates semantic
  leaf adequacy after an H1 boundary was already established
- for macro_aggregate, if H3's coverage/umbrella test determined the structure,
  H3 is the decisive rule
```

### 후보 문구 B (최소 개입)

두 줄만 추가:

```
- "decisive" = the rule that established the decision, not a rule that confirms it
- if another rule already fixed the boundary, that rule is primary
```

B의 장점: H2-A·H3를 이름으로 지목하지 않아 특정 사례 과적합 위험이 낮다.
B의 단점: 모델이 일반 원칙을 이번 사례에 적용할지 불확실하다.

### 기대되는 관측 효과

- 부적절한 H2-A primary 선택 **감소**
- 구조적으로 동등한 `macro_aggregate` 케이스에서 H3 primary 선택이 **더 안정적**
- **구조 결정 자체(splitting_decision / child_logic)는 변하지 않을 것**

세 번째가 안전 조건이다. provenance 지침을 손댔는데 라벨이 바뀐다면
그것은 프롬프트 명확화가 아니라 **의미 변경**이므로 즉시 중단하고 규범 검토로 넘긴다.

### 과적합 방지

동일한 semantic 조합만 반복하지 않는다. 진단+바이오마커 / 진단+치료력 / 검사값+약물 제한 /
확인(confirmation) 귀속 / open list / closed macro list를 각각 독립 작성해,
**규칙군 차원의 선택 실패인지 특정 조합의 문제인지** 가른다.

### tier 정책은 건드리지 않는다

이 가설은 `H2-A → Tier 0` 매핑 자체를 바꾸자는 것이 **아니다.**
매핑은 canonical 소관이다. 여기서 다루는 것은 **어떤 규칙이 primary가 되는가**뿐이며,
tier 변화는 그 결과로 따라오는 것이다.

---

## 규범 escalation 경계

Phase 5B 관측을 **"프롬프트 명확화"에서 "canonical 방법론 문제"로 올려야 하는 기준**.
이 단계에서 규범 질문을 **해결하지 않는다.** 기준만 정의한다.

### PROMPT 수준 (v1.3.x 비규범 패치로 처리 가능)

- 모델이 올바른 규칙을 알고 있는데 **필드 배정·형식이 불안정**하다
- 프롬프트의 primary vs supporting 지침이 **명시되어 있지 않다**(현재 "decisive" 미정의)
- 공유 qualifier를 **이해하면서도** 모든 자식에 복사하지 않는다
- 같은 규칙을 어떤 케이스에서는 지키고 어떤 케이스에서는 놓친다 → **출력 규율(discipline)** 문제
- 판정 라벨(`splitting_decision` / `child_logic`)은 옳은데 provenance만 흔들린다

**판별 질문**: 모델이 이미 옳게 판단한 것을 *기록하는 방식*의 문제인가?

### NORMATIVE 수준 (v1.4 사안, 사람 판단 필요)

- Canonical Core를 **두 가지로 합리적으로 읽을 수 있고** 각각 다른 구조 결정을 함의한다
- **어떤 규칙이 primary여야 하는지 canonical이 정하지 않는다**
- H2-A와 H1-B의 위계를 **기존 규범 텍스트만으로 해소할 수 없다**
- 고치면 **출력 규율이 아니라 결정 경계가 바뀐다**
- tier 파생 규칙 자체를 바꿔야 한다

**판별 질문**: 고치려면 *무엇이 옳은가*를 새로 정해야 하는가?

### 현재 두 가설의 위치

| 가설 | 현재 판단 | 근거 |
|---|---|---|
| H-X2-1 | **PROMPT 수준** | 모델이 규칙을 알고 있음을 자기 notes로 증명했다. 규범 텍스트에 모순이 없다 |
| H-PR-1 | **경계선** — 프롬프트로 시작하되 규범 검토 대기 | canonical이 "primary decisive rule"을 요구하면서 **decisive를 정의하지 않는다**. 프롬프트 명확화로 개선되면 PROMPT 수준, 개선되지 않으면 NORMATIVE로 승격 |

H-PR-1이 경계선인 것이 중요하다. Phase 5B에서 **후보 문구로도 H2-A 역전이 지속되면**,
그것은 프롬프트가 부족한 것이 아니라 **canonical에 판정 근거가 없다는 증거**다.

---

## 이 문서가 하지 않은 것

- `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` 수정 없음
- `docs/guidelines/stage1/canonical_core_v1_3_0.md` 수정 없음
- v1.3.2 생성 없음 · 문구 확정 없음 · tier 정책 재작성 없음
- 규범 질문 해결 없음 (escalation 기준만 정의)
- 모델 호출 없음

## 관련

- [`../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md`](../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md) — 근거가 된 감사 전문
- [`../../experiments/stage1_v13/phase5b_dev/design.md`](../../experiments/stage1_v13/phase5b_dev/design.md) — 이 가설을 검증할 개발 세트 설계
- [`../methods/stage1_v1_3_runtime.md`](../methods/stage1_v1_3_runtime.md) — 런타임 계약

---

## 3. `experiments/stage1_v13/phase5b_dev/design.md` — 전문

# Phase 5B 개발 세트 — 설계

> **작성일**: 2026-09-08 (PHASE 5B-prep) · **미실행.** 모델을 호출하지 않았다.
> 가설: [`../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md`](../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md)

## 1. 무엇을 위한 세트인가

Phase 5A에서 두 가지 관측이 나왔다 — 공유 qualifier 누락 1건(S04), `primary_rule_id`가 확인 규칙으로
채워진 사례 3건(S03·S12·S13). **각각 1건과 3건이다. 규칙군 차원의 실패인지 알 수 없다.**

이 세트의 목적은 **문장 하나를 고칠 수 있는지 확인하는 것이 아니라,
규칙군 차원의 실패가 존재하는지 판정하는 것**이다.

따라서 설계 원칙은 **유병률 추정이 아니라 규칙군 커버리지**다. 34건으로 비율을 말하지 않는다.

## 2. 구성 — 34 케이스

| role | 건수 | 목적 |
|---|--:|---|
| `x2_hypothesis` | 8 | H-X2-1 검증 |
| `x2_hypothesis_negative_control` | 2 | **복사하면 안 되는** 경우 — 과잉 복사 탐지 |
| `primary_rule_hypothesis` | 7 | H-PR-1 검증 |
| `recursion_coverage` | 7 | Phase 5A 미노출 재귀 경로 |
| `recursion_coverage_negative_control` | 1 | 분할했으나 재귀 불필요 |
| `exception_distinction` | 4 | negative requirement vs exception |
| `control` | 5 | Phase 5A에서 이미 잘 되던 동작의 회귀 방지 |

criterion_type: inclusion 19 / exclusion 15. cohort 지정 2건.

### rule family 커버리지

```
H0 1 · H1-A 2 · H1-B 15 · H2-A 2 · H2-B 2 · H3 5 · H4 9 · H5 3 · H6 8
X1 3 · X2 10 · X3 3 · X4 2 · X5 1 · X7 1
```

## 3. A군 — X2 공유 qualifier (8 + 2 대조군)

S04를 여러 번 고쳐 쓰지 않았다. **qualifier 유형과 구문 위치를 교차**시켰다.

| case | qualifier 유형 | 구문 위치 | 기대 |
|---|---|---|---|
| A1 | 시간 | 두 번째 conjunct **뒤** (S04 형태) | 양쪽 복사 |
| A2 | 시간 | coordination **앞** | 양쪽 복사 |
| A3 | 중증도 | 뒤, `either of` 표지 있음 | 양쪽 복사 |
| A4 | 수치 임계값 | `each`로 분배 | 양쪽 복사 |
| A5 | 조건/방법 | `in either case` 표지 | 양쪽 복사 |
| **A6** | 시간 | **한 분기 안에만** | ❌ **복사 금지** |
| **A7** | 없음 | — | ❌ 복사할 것 없음 |
| A8 | 공유 목적어 | coordination 뒤 | 문법 불완전하되 의미 완전 |
| E1 | 두 개(방법 + 시간) | 하나는 비연속 | multi-segment span |
| F2 | 코호트별 내용 차이 | — | 자식별 scope, top-level null |

**A6·A7이 설계의 핵심이다.** "복사하라"를 강화하면 과잉 복사로 넘어갈 수 있다.
A1–A5·A8에서 복사가 늘고 **A6·A7에서 늘지 않아야** 가설이 지지된다.
한쪽만 개선되면 그것은 개선이 아니라 편향 이동이다.

Phase 5A의 S05·S12는 이미 올바르게 복사했으므로 A군에는 **표지가 없는 경우**(A1, A2)를
의도적으로 넣었다 — S04와 S05/S12의 차이가 표지(`each`, `in either case`)의 유무였기 때문이다.

## 4. B군 — primary_rule_id (7 + 대조 2)

같은 semantic 조합을 반복하지 않았다.

| case | 조합 | 검증 지점 |
|---|---|---|
| B3 | 진단 + 바이오마커 | H2-B가 canonical에서 직접 규정하는 사례. H2-A가 primary가 되면 안 됨 |
| B4 | 진단 + 치료력 | H1-B가 경계를 세움 (S13 패턴, 다른 도메인) |
| B5 | 검사값 + 약물 제한 | H1-B가 경계를 세움 (S12 패턴, 다른 도메인) |
| B6 | 확인 귀속 | confirmation을 분리하면 안 됨 |
| **B8 / B9** | umbrella + closed list **2건** | **동등 구조에서 primary 선택이 안정적인가** |
| B10 | 같은 도메인·다른 기전 | H1-A 병합이 실패하고 H1-B로 넘어가야 함 |
| B1 | 같은 대상, status만 다름 | H1-A 병합 (대조군) |
| B2 | 명백한 독립 요건 2개 | 깨끗한 H1-B (대조군) |
| B7 | open list | H3 (대조군) |

**B8/B9 쌍이 S06 vs S07 관측의 직접 후속이다.** 두 케이스는 도메인만 다르고 구조가 같다.
같은 primary가 나오면 안정적, 갈리면 Phase 5A 관측이 재현된 것이다.

## 5. C군 — 재귀 (7 + 대조 1)

Phase 5A에서 실모델로 **노출되지 않은 경로**를 의도적으로 겨냥한다.

| case | 겨냥한 경로 |
|---|---|
| C1 | composite 자식 1개 재귀 (**depth 2**) — 5A에서 미노출 |
| C2 | **복수 `recursion_targets`** + **형제 재귀 분기** — 둘 다 미노출 |
| C3 | nested_exception → main → composite (**main 재귀 후 분할**) |
| C4 | **macro_aggregate 아래 재귀 자식** — 미노출 |
| C5 | **혼합 논리** A AND (B1 OR B2) — 평탄화 금지 |
| C6 | **depth 3** 목표 — exception over composite whose child is an OR pair |
| E2 | 재귀 시 **형제 텍스트 누출 금지**(X7/X1) |
| **C7** | 분할했으나 자식이 이미 leaf → `needs_recursion=false` (**대조군**) |

`max_depth` 가드와 `empty_main`은 여전히 실모델로 유도하기 어렵다.
자연스러운 criterion으로 depth 5를 넘기기 어렵기 때문이다 — **mock 테스트가 계속 담당**한다.

## 6. D군 — exception 구분 (4 + 대조 1)

| case | 표현 | 기대 |
|---|---|---|
| D1 | `without X` | **negative requirement** — nested_exception 아님 |
| D2 | `unless X` | 진짜 waiver (대조군) |
| D3 | `permitted if X` | 조건부 허용 = waiver |
| D4 | `other than X` | carve-out, trigger 첫 단어부터 span |
| **D5** | `except where … specified in the Study Manual` | **외부 문서 위임** — 실질 carve-out이 아님. X5와 H4가 경합 |

D5는 **의도적으로 모호**하게 두었다. 정답 라벨을 정해 두지 않고,
delegation note가 나오는지, 아니면 실질 없는 exception으로 처리되는지를 관찰한다.

## 7. 대조군 정책 (§12)

프롬프트 명확화가 **이미 잘 되던 동작을 깨뜨리지 않는지** 확인해야 한다.
Phase 5A에서 통과한 유형을 5건 넣었다.

| case | Phase 5A 대응 |
|---|---|
| B1 | S01/S13 (H1-A 병합) |
| B2 | S12 (깨끗한 H1-B 분할) |
| B7 | S08 (open list) |
| D2 | S09 (명확한 nested_exception) |
| F1 | S14 (cohort scope) |

**대조군에서 결정이 바뀌면 그 프롬프트 후보는 기각한다** — 명확화가 아니라 의미 변경이기 때문이다.

## 8. 비교 설계 — 문서만, 실행하지 않음

### Step 1 — 프롬프트 버전 격리 (모델 고정)

모델·케이스·reasoning effort·런타임·SDK 환경을 **모두 고정**하고 프롬프트만 바꾼다.

```
Prompt A : 현행 v1.3.1                (변경 없음)
Prompt B : 비규범 명확화 후보          (아직 작성하지 않음)

고정: model=gpt-5.6-terra · requested_reasoning_effort=medium
      cases=이 34건 · runtime=pipeline/stage1_v13 · SDK=openai 1.6.1
```

비교 지표:

| 지표 | 왜 보는가 |
|---|---|
| 구조 결정 정확성 | **변하면 안 된다** — 변하면 명확화가 아니라 의미 변경 |
| 공유 qualifier 준수 | H-X2-1 주 지표 |
| **과잉 복사** (A6·A7) | H-X2-1 안전 지표 |
| `primary_rule_id` 적절성 | H-PR-1 주 지표 |
| `supporting_rule_ids` 적절성 | 역전이 사라졌는지 |
| B8/B9 primary 일치 | H-PR-1 안정성 지표 |
| validator 첫 시도 통과율 | 형식 규율 |
| 재시도율 | 〃 (이제 attempt 트레이스로 직접 계수) |
| span 위반 | X1 회귀 |
| 재귀 정확성 | C군 |
| 불완전 실행 | `incomplete_reason` |

### Step 2 — 모델 계열 (후보 확정 후)

프롬프트 후보가 안정된 **뒤에만** 동일 후보를 계획된 frontier / open-weight 계열에 적용한다.
**이 단계에서 open-weight 비교를 시작하지 않는다.**

## 9. 실행 전 확정해야 할 것

1. **프롬프트 후보 문구** — 가설 문서의 A안/B안 중 선택 (또는 제3안). 미확정
2. **비교 방식** — 같은 모델로 A/B 두 번 실행 = 68 호출 + 재시도. 상한 설정 필요
3. **A6·A7 판정 기준** — 과잉 복사를 어떻게 셀 것인지 사전 정의
4. **D5 처리** — 모호 케이스를 지표에서 제외할지 별도 보고할지

## 10. 하지 않은 것

- 모델 호출 없음 · 프롬프트 후보 작성 없음 · v1.3.2 없음
- canonical core 수정 없음 · v1.3.1 수정 없음
- historical 113-item 사용 없음 (few-shot도, 평가 세트도 아님)

---

## 4. `experiments/stage1_v13/phase5b_dev/cases.jsonl` — 전문 (34줄)

한 줄 = 한 root case. `expected_*`는 **사전 등록된 기계적·provenance 속성**이지 정답지가 아니다.

```jsonl
{"case_id":"A1","criterion_type":"exclusion","root_criterion_text":"Clinically significant pericardial effusion or clinically significant ascites documented within 28 days prior to randomization.","trial_has_cohorts":null,"rule_family":["X2","H1-B"],"boundary":"shared TEMPORAL qualifier placed after the second conjunct — the S04 shape with new content","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"A2","criterion_type":"exclusion","root_criterion_text":"Within 6 months before enrollment, myocardial infarction or cerebrovascular accident.","trial_has_cohorts":null,"rule_family":["X2","H1-B"],"boundary":"shared TEMPORAL qualifier placed BEFORE the coordination — syntactic cue favours both branches","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"A3","criterion_type":"exclusion","root_criterion_text":"Peripheral sensory neuropathy or peripheral motor neuropathy, either of Grade 2 or higher.","trial_has_cohorts":null,"rule_family":["X2","H1-B"],"boundary":"shared SEVERITY qualifier with an explicit sharing marker ('either of')","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"A4","criterion_type":"inclusion","root_criterion_text":"Serum albumin and serum total protein each at least 3.0 g/dL at screening.","trial_has_cohorts":null,"rule_family":["X2","H1-B"],"boundary":"shared NUMERIC threshold distributed over two analytes by 'each'","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"A5","criterion_type":"inclusion","root_criterion_text":"Measurable hepatic lesion or measurable nodal lesion, in either case confirmed on contrast-enhanced imaging.","trial_has_cohorts":null,"rule_family":["X2","H1-B"],"boundary":"shared CONDITIONAL/method qualifier applying to both branches","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"A6","criterion_type":"exclusion","root_criterion_text":"Prior allogeneic stem cell transplant, or prior autologous stem cell transplant within 100 days before the first dose.","trial_has_cohorts":null,"rule_family":["X2"],"boundary":"BRANCH-SPECIFIC temporal qualifier — must NOT be copied to the first branch","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis_negative_control"}
{"case_id":"A7","criterion_type":"exclusion","root_criterion_text":"Requiring dialysis, uncontrolled hypertension, or symptomatic heart failure.","trial_has_cohorts":null,"rule_family":["X2","H1-B"],"boundary":"NO shared qualifier at all — nothing should be copied between children","expected_structural":"composite_split","expected_provenance":"H1-B primary","expected_recursion":false,"role":"x2_hypothesis_negative_control"}
{"case_id":"A8","criterion_type":"inclusion","root_criterion_text":"Documented disease progression on, or documented intolerance to, first-line platinum therapy.","trial_has_cohorts":null,"rule_family":["X2","X1"],"boundary":"grammatically incomplete children that remain semantically complete; shared object after the coordination","expected_structural":"composite_split","expected_provenance":"H1-B primary; X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"B1","criterion_type":"exclusion","root_criterion_text":"Active hepatitis B infection or chronic hepatitis B infection.","trial_has_cohorts":null,"rule_family":["H1-A"],"boundary":"same screening target differing only in status/history — merge, do not split","expected_structural":"none","expected_provenance":"H1-A primary","expected_recursion":false,"role":"control"}
{"case_id":"B2","criterion_type":"inclusion","root_criterion_text":"Life expectancy of at least 12 weeks and adequate venous access for study drug administration.","trial_has_cohorts":null,"rule_family":["H1-B"],"boundary":"two plainly independent requirements — clean H1-B split","expected_structural":"composite_split","expected_provenance":"H1-B primary","expected_recursion":false,"role":"control"}
{"case_id":"B3","criterion_type":"inclusion","root_criterion_text":"Locally advanced urothelial carcinoma with documented FGFR3 fusion.","trial_has_cohorts":null,"rule_family":["H2-B","H1-B"],"boundary":"diagnosis + independently required biomarker — H2-B is the on-point canonical rule","expected_structural":"composite_split","expected_provenance":"H2-B or H1-B primary; H2-A should NOT be primary","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"B4","criterion_type":"inclusion","root_criterion_text":"Diffuse large B-cell lymphoma and at least one prior anthracycline-containing regimen.","trial_has_cohorts":null,"rule_family":["H1-B","H2-A"],"boundary":"diagnosis + treatment history — different semantic categories, but H1-B sets the boundary","expected_structural":"composite_split","expected_provenance":"H1-B primary; H2-A supporting at most","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"B5","criterion_type":"inclusion","root_criterion_text":"Total bilirubin no greater than 1.5 times the upper limit of normal and no ongoing treatment with UGT1A1 inhibitors.","trial_has_cohorts":null,"rule_family":["H1-B","H2-A"],"boundary":"lab value + medication restriction — the S12 pattern in a new domain","expected_structural":"composite_split","expected_provenance":"H1-B primary; H2-A supporting at most","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"B6","criterion_type":"inclusion","root_criterion_text":"Pathologically documented triple-negative breast cancer.","trial_has_cohorts":null,"rule_family":["H2-B"],"boundary":"confirmation belongs to the diagnosis proposition — must not split confirmation out","expected_structural":"none","expected_provenance":"H2-B or H0 primary","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"B7","criterion_type":"exclusion","root_criterion_text":"Ongoing infection requiring intravenous antimicrobials, including bacteremia, osteomyelitis, or endocarditis.","trial_has_cohorts":null,"rule_family":["H3"],"boundary":"open/non-exhaustive list — keep the broad parent, do not split named examples","expected_structural":"none","expected_provenance":"H3 primary","expected_recursion":false,"role":"control"}
{"case_id":"B8","criterion_type":"inclusion","root_criterion_text":"Adequate coagulation function, defined as international normalized ratio no greater than 1.5 and activated partial thromboplastin time no greater than 1.5 times the upper limit of normal.","trial_has_cohorts":null,"rule_family":["H3","H4"],"boundary":"closed list under a true umbrella — macro gate. PAIR MEMBER 1 with B9","expected_structural":"macro_aggregate","expected_provenance":"H3 primary preferred (umbrella/coverage decided it)","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"B9","criterion_type":"inclusion","root_criterion_text":"The participant must meet all of the following pulmonary parameters: forced expiratory volume in one second at least 50 percent predicted, and resting oxygen saturation at least 92 percent on room air.","trial_has_cohorts":null,"rule_family":["H3","H4"],"boundary":"structurally analogous to B8 in a different domain — tests primary-rule STABILITY across equivalent cases. PAIR MEMBER 2","expected_structural":"macro_aggregate","expected_provenance":"same primary as B8 (stability check)","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"B10","criterion_type":"exclusion","root_criterion_text":"Concurrent use of a strong P-glycoprotein inhibitor or a strong OATP1B1 inhibitor.","trial_has_cohorts":null,"rule_family":["H1-A","H1-B"],"boundary":"same transporter domain but pharmacologically distinct exposure checks — H1-A merge must FAIL, continue to H1-B","expected_structural":"composite_split","expected_provenance":"H1-B primary","expected_recursion":false,"role":"primary_rule_hypothesis"}
{"case_id":"C1","criterion_type":"inclusion","root_criterion_text":"Histologically confirmed gastric adenocarcinoma with HER2 overexpression, and adequate cardiac function defined as left ventricular ejection fraction at least 50 percent.","trial_has_cohorts":null,"rule_family":["H6","H1-B","H3"],"boundary":"composite whose second child is itself an umbrella — one recursive child, depth 2","expected_structural":"composite_split","expected_provenance":"H1-B primary at root","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"C2","criterion_type":"exclusion","root_criterion_text":"Active central nervous system involvement or leptomeningeal disease, and any Grade 3 or higher immune-related adverse event or any unresolved Grade 2 pneumonitis.","trial_has_cohorts":null,"rule_family":["H6","H1-B","H5"],"boundary":"TWO recursion targets and SIBLING recursive branches at the same level","expected_structural":"composite_split","expected_provenance":"H1-B primary at root","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"C3","criterion_type":"exclusion","root_criterion_text":"Prior solid organ transplant and ongoing immunosuppressive therapy are exclusionary, unless the participant has been off all immunosuppression for at least 6 months.","trial_has_cohorts":null,"rule_family":["H6","H4","X3"],"boundary":"nested_exception -> main -> composite; main must recurse and then split","expected_structural":"nested_exception","expected_provenance":"H4 primary at root","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"C4","criterion_type":"inclusion","root_criterion_text":"Adequate organ reserve, defined as estimated glomerular filtration rate at least 45 mL/min per 1.73 square metres, and hepatic function with aspartate aminotransferase and alanine aminotransferase each no greater than 3 times the upper limit of normal.","trial_has_cohorts":null,"rule_family":["H6","H3","X2"],"boundary":"macro_aggregate whose hepatic child is itself composite with a shared numeric qualifier — recursive child under a macro","expected_structural":"macro_aggregate","expected_provenance":"H3 primary at root","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"C5","criterion_type":"inclusion","root_criterion_text":"Confirmed relapsed disease and either measurable extramedullary disease or documented bone marrow involvement of at least 10 percent.","trial_has_cohorts":null,"rule_family":["H6","H5"],"boundary":"mixed logic A AND (B1 OR B2) — must stay hierarchical, not flattened","expected_structural":"composite_split","expected_provenance":"H1-B primary at root; child_logic AND at root, OR at child","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"C6","criterion_type":"exclusion","root_criterion_text":"Uncontrolled intercurrent illness, including either ongoing symptomatic congestive heart failure or unstable angina, and any psychiatric condition that would limit compliance, are exclusionary unless resolved before the first dose.","trial_has_cohorts":null,"rule_family":["H6","H4","H5"],"boundary":"deepest case — exception over a composite whose first child is itself an OR pair; targets depth 3","expected_structural":"nested_exception","expected_provenance":"H4 primary at root","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"C7","criterion_type":"inclusion","root_criterion_text":"Body weight at least 40 kg and body mass index at least 18 kg per square metre.","trial_has_cohorts":null,"rule_family":["H6"],"boundary":"split whose children are already leaves — needs_recursion must be FALSE despite a split","expected_structural":"composite_split","expected_provenance":"H1-B primary","expected_recursion":false,"role":"recursion_coverage_negative_control"}
{"case_id":"D1","criterion_type":"inclusion","root_criterion_text":"Absolute lymphocyte count at least 0.5 x 10^9/L without growth factor support in the preceding 14 days.","trial_has_cohorts":null,"rule_family":["H4","H1-B"],"boundary":"'without X' is a negative REQUIREMENT, not an exception — must not become nested_exception","expected_structural":"composite_split or none","expected_provenance":"H1-B primary; NOT H4","expected_recursion":false,"role":"exception_distinction"}
{"case_id":"D2","criterion_type":"exclusion","root_criterion_text":"Live attenuated vaccine within 30 days before the first dose, unless administered as part of standard institutional practice for seasonal influenza.","trial_has_cohorts":null,"rule_family":["H4","X3"],"boundary":"'unless X' is a genuine waiver of the main rule","expected_structural":"nested_exception","expected_provenance":"H4 primary; X3 supporting","expected_recursion":false,"role":"control"}
{"case_id":"D3","criterion_type":"exclusion","root_criterion_text":"Systemic antibiotics are not allowed during screening; topical antibiotic use is permitted if limited to a single body region.","trial_has_cohorts":null,"rule_family":["H4"],"boundary":"'permitted if' conditional allowance encodes a waiver","expected_structural":"nested_exception","expected_provenance":"H4 primary","expected_recursion":false,"role":"exception_distinction"}
{"case_id":"D4","criterion_type":"exclusion","root_criterion_text":"Any prior malignancy, other than non-melanoma skin cancer treated with curative intent.","trial_has_cohorts":null,"rule_family":["H4","X3"],"boundary":"'other than X' carve-out; exception span must start at the trigger's first word","expected_structural":"nested_exception","expected_provenance":"H4 primary; X3 supporting","expected_recursion":false,"role":"exception_distinction"}
{"case_id":"D5","criterion_type":"inclusion","root_criterion_text":"All screening assessments must be completed within 28 days before the first dose, except where a longer window is specified in the Study Manual.","trial_has_cohorts":null,"rule_family":["H4","X5"],"boundary":"exception-shaped wording that DELEGATES to an external document rather than waiving eligibility — should not become a substantive nested_exception carve-out","expected_structural":"none or nested_exception (ambiguous by design)","expected_provenance":"X5 delegation note expected","expected_recursion":false,"role":"exception_distinction"}
{"case_id":"E1","criterion_type":"exclusion","root_criterion_text":"Interstitial lung disease or radiation pneumonitis, in either case requiring systemic corticosteroids, diagnosed at any time before screening.","trial_has_cohorts":null,"rule_family":["X1","X2"],"boundary":"TWO shared qualifiers, one of them non-contiguous with the first target — multi-segment spans expected","expected_structural":"composite_split","expected_provenance":"H1-B primary; X1/X2 supporting","expected_recursion":false,"role":"x2_hypothesis"}
{"case_id":"E2","criterion_type":"inclusion","root_criterion_text":"Eligible participants must have documented EGFR exon 19 deletion or L858R substitution, and must have received prior osimertinib.","trial_has_cohorts":null,"rule_family":["X1","X7","H6"],"boundary":"recursive pass must not import the prior-osimertinib sibling text into the biomarker child's spans","expected_structural":"composite_split","expected_provenance":"H1-B primary","expected_recursion":true,"role":"recursion_coverage"}
{"case_id":"F1","criterion_type":"inclusion","root_criterion_text":"In Part 2 only, participants must have documented progression on prior immunotherapy.","trial_has_cohorts":["Part 1","Part 2"],"rule_family":["X4","H0"],"boundary":"cohort scope recorded verbatim at top level for a non-split criterion","expected_structural":"none","expected_provenance":"H0 primary; X4 supporting","expected_recursion":false,"role":"control"}
{"case_id":"F2","criterion_type":"inclusion","root_criterion_text":"Participants in Cohort A must have measurable disease, and participants in Cohort B must have evaluable disease.","trial_has_cohorts":["Cohort A","Cohort B"],"rule_family":["X4","H1-B"],"boundary":"cohort-specific eligibility CONTENT differs — split, with scope on the relevant children and top-level scope null","expected_structural":"composite_split","expected_provenance":"H1-B primary; X4 supporting","expected_recursion":false,"role":"x2_hypothesis"}
```
