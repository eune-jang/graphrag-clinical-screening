# Phase 5B — 채점 계획 (실행 전 사전 등록)

> **작성일**: 2026-09-09 · **상태: 미실행.** 모델을 호출하지 않았다.
> 지표·수용 기준·예산을 **출력을 보기 전에** 고정한다. 사후 기준 변경을 막는 것이 이 문서의 목적이다.

---

## 1. 실험 구조

```
P0 = 변경 없는 v1.3.1
     pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt

5B-0   P0 × 전체 35건                    ← 공유 baseline. 한 번만 측정
         ↓
5B-1   P-X2  × X2 관련 서브셋            P0의 해당 서브셋과 비교
5B-2   P-PR  × provenance 서브셋         P0의 해당 서브셋과 비교
         ↓
     ██ 사람 검토 체크포인트 ██          자동으로 combined를 만들지 않는다
         ↓
5B-3   P-COMBINED × 전체 35건            승인 후에만. 지금 파일도 만들지 않았다
```

**P0를 한 번만 도는 이유**: 가설마다 P0를 다시 돌리면 같은 baseline을 세 번 측정하게 되고,
재귀군(C1–C6, E2)과 대조군은 5B-1·5B-2 서브셋에 없으므로 **baseline이 아예 없는 케이스가 생긴다.**
전체 1회 측정이 비용도 낮고 모든 비교에 기준선을 준다.

## 2. 프롬프트 후보 명명 규칙

**검증되지 않은 후보에 `v1_3_2a` 같은 릴리스 버전을 붙이지 않는다.** 아직 버전이 아니다.

```
pipeline/prompts/development/stage1/
├── stage1_prompt_v1_3_1.txt                    ← P0. baseline, 불변
└── candidates/
    ├── candidate_x2_from_v1_3_1.txt            ← P-X2
    ├── candidate_pr_from_v1_3_1.txt            ← P-PR
    └── (candidate_combined_from_v1_3_1.txt)    ← 아직 만들지 않음
```

**다음 v1.3.x 버전 번호는 사람 검토를 통과한 후보에만 부여한다.**
그 전까지 파일명은 `candidate_<가설>_from_<기반 버전>` 형식의 provenance 이름을 쓴다.

## 3. X2 지표 (5B-1)

분모는 `metric_group`으로 기계적으로 정해진다. 사후에 바꾸지 않는다.

| 그룹 | 케이스 | 수 |
|---|---|--:|
| `x2_positive` | A1 A2 A3 A4 A5 E1 | **6** |
| `x2_negative_control` | A6 A7 | **2** |
| `x2_safety_control` | A8 | **1** |
| (제외) `cohort_scope_coverage` | F2 | — |

### 주 지표 — case-level 공유 qualifier 준수

케이스 단위 PASS / FAIL.

- **PASS**: qualifier가 의미적으로 수식하는 **모든** child가 그 정확한 원문 span을 포함
- **FAIL**: 영향받는 child 중 **하나라도** 누락

각 케이스의 `shared_qualifier`와 `qualifier_applies_to`는 `cases.jsonl`에 사전 등록되어 있다.

### 보조 지표 — affected-child qualifier recall

```
분자 = 요구된 정확한 qualifier span을 포함한 affected child 수
분모 = 그 qualifier가 수식한다고 사전 등록된 child 수
```

case-level이 주 지표인 이유: 자식 1/2에만 복사한 S04형 실패가 recall 0.5로 절반의 성공처럼
보이면 안 되기 때문이다.

### 안전 지표 — **주 지표에 합산하지 않는다**

| 지표 | FAIL 조건 |
|---|---|
| **A6** branch-specific over-copy | 분기 전용 qualifier(`within 100 days before the first dose`)가 그것이 수식하지 않는 child에 나타남 |
| **A7** no-shared-qualifier | 공유 dependent qualifier가 없는데 형제/공유 문맥에서 유래한 span 세그먼트가 child에 추가됨 |
| **A8** shared-entity 중복 | 공유 clinical entity(`first-line platinum therapy`)가 문법을 맞추려는 목적만으로 양쪽 child에 복제됨 |

**A8은 positive 사례가 아니다.** canonical X2 첫 불릿이
`Do not duplicate a shared clinical entity solely to make a child grammatical` 이고,
`first-line platinum therapy`는 entity이지 temporal/numeric/conditional/severity qualifier가 아니다.
child가 문법적으로 불완전하게 남는 것이 **정답**이다.

### P-X2 수용 방향

```
공유 qualifier 준수가 개선되거나 이미 완벽하면 유지   (x2_positive)
  AND  A6/A7 over-copy 신규 오류 없음
  AND  A8 entity 중복 회귀 없음
  AND  structural_control 회귀 없음
```

네 조건 **전부** 충족해야 한다. 첫 조건만 좋아지면 편향 이동이지 개선이 아니다.

## 4. Primary-rule 지표 (5B-2)

분모: `provenance_target` = **B3 B4 B5 B6 B8 B9 B10 (7건)**.
각 케이스의 허용 primary 집합은 `cases.jsonl`의 `expected_provenance`에 **사전 등록**되어 있다.
canonical이 실제로 복수 해석을 허용하는 경우에만 집합을 넓게 잡았다(예: B6 `{H2-B, H0}` —
H0는 확인 방법을 dependent content로 판정하는 직접적 gate이고 H2-B는 확인의 진단 귀속을
구체적으로 규정한다. 현행 동결 canonical만으로 둘 중 하나를 배제할 근거는 약하다).

### 보고 항목

1. **validating rule이 primary로 잘못 선택된 건수** — 사전 등록 집합 밖의 primary
2. **실제 decisive rule이 supporting으로 강등된 건수** — `supporting_rule_ids`에 더 결정적인 규칙이 있는 경우
3. **B8/B9 쌍 일치 여부** — 구조적으로 동등한 두 케이스가 같은 primary를 냈는가
4. **P0 대비 구조 결정 변화** — `splitting_decision` / `child_logic`
5. **tier 결과** — primary에서 결정론적으로 파생된 값

**tier를 직접 최적화하지 않는다.** tier는 `primary_rule_id`의 결과이지 목표가 아니다.

### P-PR 수용 방향

```
provenance 적절성 개선
  AND  구조 결정 회귀 없음        ← 이것이 안전 조건
  AND  structural_control 회귀 없음
```

> ⚠️ **일반 문구로 H2-A 역전이 해소되지 않으면, 같은 실험 안에서 H2-A 지목 문구를 점진적으로
> 덧붙이지 않는다.** 그것은 실험이 아니라 튜닝이다. 규범/사람 검토로 넘긴다.

## 5. 대조군 정책

`structural_control` = **B1 B2 B7 D2 F1 (5건)** — clean H1-A none · clean H1-B split ·
H3 open list · clear nested_exception · cohort scope.

> **명확화가 안정 대조군의 올바른 구조 결정을 바꾸면 그 후보는 기각 / 사람 검토 대상이다.**
> **대상 규칙군의 개선이 대조군 회귀를 상쇄하지 못한다.**

## 6. 정량 수용에서 제외

| 케이스 | 처리 |
|---|---|
| **D5** | `qualitative_normative_probe`. X2 수용 · PR 수용 · 후보 승패 · 구조 성공 분모 **전부에서 제외**. H4/X5 위임 경계 관찰용으로 **별도 보고** |
| **F2** | X2 지표에서 제외 (`cohort_scope_coverage`). 구조 대조로는 사용 가능 |

## 7. 재귀 커버리지 (5B-0 / 5B-3에서 관측)

`recursion_coverage` = C1 C2 C3 C4 C5 C6 E2 (7건), `recursion_negative_control` = C7 (1건).

**깊이 표기는 runner 규약을 따른다: root = depth 0.**

| case | 겨냥 경로 | 예상 max depth | 최심 경로 pass 수 |
|---|---|--:|--:|
| C1 | AND 루트 → 치료력 대안군이 OR로 재귀 | 1 | 2 |
| C2 | **복수 recursion_targets + 형제 재귀 분기** | 1 | 2 |
| C3 | nested_exception → main → composite | 1 | 2 |
| C4 | macro_aggregate 아래 재귀 자식 | 1 | 2 |
| C5 | 혼합 논리 A AND (B1 OR B2) | 1 | 2 |
| **C6** | **nested_exception → main(AND) → BTK/BCL-2 자식(OR)** | **2** | **3** |
| E2 | 분기 내부 allowance → 그 자식이 nested_exception으로 재귀 | 1 | 2 |
| C7 | 분할했으나 자식이 leaf → `needs_recursion=false` | 0 | 1 |

**C6이 최심이며 관측 예상 max depth는 2다** — 최심 경로에서 Stage-1 패스가 3회지만
depth 3에서 실제 패스가 일어나지는 않는다. `depth 3`이라 부르지 않는다.

`max_depth` 가드와 `empty_main`은 자연스러운 criterion으로 유도하기 어려워 **mock 테스트가 계속 담당**한다.

### E2 누출 시험 (X1 / X7)

antiplatelet 자식의 재귀 패스에서 **모든 출력 span이 그 자식의 TARGET_SEGMENTS 안에** 있어야 하고,
형제 문맥의 `therapeutic anticoagulation`을 **가져오면 안 된다**. `cases.jsonl`의
`leakage_forbidden_span`에 등록되어 있다.

## 8. 호출 예산

**지금 한 통도 쓰지 않는다.** 아래는 상한(ceiling)이지 목표가 아니다.

| 단계 | 케이스 | 예상 root pass | 예상 재귀 pass | 재시도 여유 | **hard cap** |
|---|--:|--:|--:|--:|--:|
| **5B-0** P0 × 전체 | 35 | 35 | ~9 | ~16 | **60** |
| **5B-1** P-X2 × 서브셋 | 14 | 14 | ~1 | ~10 | **25** |
| **5B-2** P-PR × 서브셋 | 12 | 12 | 0 | ~13 | **25** |
| **사람 검토 전 누계** | | | | | **100** |
| (향후) **5B-3** P-COMBINED × 전체 | 35 | 35 | ~9 | ~26 | **70** |

재귀 pass 추정: C1–C5·E2 각 +1, C6 +2 = 8, C2의 형제 분기로 +1 = **약 9**.

**서브셋 구성** (§21 — 무관한 케이스에 후보 호출을 쓰지 않는다):

```
5B-1 (14) = x2_positive 6 (A1–A5, E1)
          + x2_negative_control 2 (A6, A7)
          + x2_safety_control 1 (A8)
          + structural_control 5 (B1, B2, B7, D2, F1)

5B-2 (12) = provenance_target 7 (B3, B4, B5, B6, B8, B9, B10)
          + structural_control 5 (B1, B2, B7, D2, F1)
```

## 8-B. 단일 관측의 한계 — 통계 주장 금지

이것은 **프롬프트 개발**이지 확률적 성능 연구가 아니다. 따라서 P0 1회 관측을 개발 baseline으로 쓰되:

- **통계적 우월성 주장을 하지 않는다**
- 의미상 중요한 차이는 **전부 trace review를 거친다**
- **후보 수용이 단 한 건의 불일치 케이스에 달려 있으면**, 성공을 선언하지 말고
  **paired confirmation 필요**로 표시한다

이번 교정 단계에서 확인 호출을 자동으로 수행하지 않는다.

## 9. 환경 고정

P0 / P-X2 / P-PR 비교 동안 아래를 **바꾸지 않는다**. SDK 변경은 프롬프트라는 독립변수에
다른 변수를 섞는다.

```
Python 3.11.5 · openai==1.6.1 · 같은 extra_body 경로
requested_reasoning_effort = medium · 같은 max_completion_tokens
같은 runtime · 같은 validator · 같은 trace 형식
```

기록: [`../environment/README.md`](../environment/README.md) · [`../environment/requirements-phase5.txt`](../environment/requirements-phase5.txt)

**모든 실행은 `pipeline/stage1_v13`의 `JsonlTracer`를 쓴다** — Phase 5A는 실패한 시도를 남기지
못했다(I-07). `run_config`에 model · `requested_reasoning_effort` · max_completion_tokens ·
SDK/Python 버전 · prompt artifact + sha256을 넣는다.

## 10. 이 단계에서 하지 않은 것

- 유료 API 호출 0회 · P0 미실행 · 후보 미실행
- `candidate_combined_from_v1_3_1.txt` **미생성**
- canonical core · v1.3.1 프롬프트 무변경
- v1.3.2 버전 부여 없음 · open-weight 미착수 · historical 113 채점 없음
