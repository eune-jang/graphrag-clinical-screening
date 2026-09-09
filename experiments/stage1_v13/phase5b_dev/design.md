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
