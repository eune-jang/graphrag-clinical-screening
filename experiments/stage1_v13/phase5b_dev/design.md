# Phase 5B 개발 세트 — 설계

> **작성일**: 2026-09-08 · **교정일**: 2026-09-09 · **미실행.** 모델을 호출하지 않았다.
> 가설: [`../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md`](../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md)
> 채점·예산: [`SCORING_PLAN.md`](SCORING_PLAN.md)

## 1. 무엇을 위한 세트인가

Phase 5A에서 두 관측이 나왔다 — 공유 qualifier 누락 1건(S04), `primary_rule_id`가 확인 규칙으로
채워진 사례 3건(S03·S12·S13). **각각 1건과 3건이다. 규칙군 차원의 실패인지 알 수 없다.**

목적은 **문장 하나를 고칠 수 있는지가 아니라, 규칙군 차원의 실패가 존재하는지 판정하는 것**이다.
따라서 설계 원칙은 유병률 추정이 아니라 **규칙군 커버리지**다. 35건으로 비율을 말하지 않는다.

## 2. 실험 구조 — 가설을 격리한다

두 명확화를 한 후보에 함께 넣으면 결과가 좋아져도 **무엇 때문인지 알 수 없다.**
초안의 실제 결함이었고, 아래로 교정했다.

```
P0 = 변경 없는 v1.3.1

5B-0   P0 × 전체 35건            ← 공유 baseline, 한 번만 측정
         ↓
5B-1   P-X2 × X2 서브셋 (14)     P0의 해당 서브셋과 비교
5B-2   P-PR × provenance 서브셋 (12)
         ↓
     ██ 사람 검토 ██             자동으로 combined를 만들지 않는다
         ↓
5B-3   P-COMBINED × 전체 35건    승인 후에만
```

**P0 전체 1회 측정이 핵심이다.** 가설별로 P0를 다시 돌리면 같은 baseline을 세 번 재고,
재귀군(C1–C6, E2)은 5B-1·5B-2 서브셋에 없으므로 **baseline 없는 케이스가 생긴다.**

후보 명명은 `candidate_<가설>_from_v1_3_1.txt` — **검증 전 후보에 릴리스 버전을 붙이지 않는다.**

## 3. 구성 — 35 케이스

| metric_group | 건수 | 케이스 |
|---|--:|---|
| `x2_positive` | **6** | A1 A2 A3 A4 A5 E1 |
| `x2_negative_control` | **2** | A6 A7 |
| `x2_safety_control` | **1** | A8 |
| `provenance_target` | **7** | B3 B4 B5 B6 B8 B9 B10 |
| `recursion_coverage` | **7** | C1 C2 C3 C4 C5 C6 E2 |
| `recursion_negative_control` | 1 | C7 |
| `exception_distinction` | 4 | D1 D3 D4 D6 |
| `structural_control` | **5** | B1 B2 B7 D2 F1 |
| `cohort_scope_coverage` | 1 | F2 |
| `qualitative_probe` | 1 | D5 |

분모는 `metric_group`으로 기계적으로 정해진다 — 출력을 본 뒤 바꿀 수 없다.

## 4. A군 — X2 공유 qualifier

S04를 고쳐 쓰지 않고 **qualifier 유형 × 구문 위치**를 교차시켰다.

| case | 유형 | 구문 위치 | 공유 표지 | 그룹 |
|---|---|---|---|---|
| A1 | 시간 | 두 번째 conjunct 뒤 (S04 형태) | **없음** | positive |
| A2 | 시간 | coordination **앞** | 없음 | positive |
| A3 | 중증도 | 뒤 | `either of` | positive |
| A4 | 수치 | 분배 | `each` | positive |
| A5 | 조건/방법 | 뒤 | `in either case` | positive |
| E1 | 방법 + 시간 (2개) | 하나는 비연속 | `in either case` | positive |
| **A6** | 시간 | **한 분기 안에만** | — | **negative** |
| **A7** | 없음 | — | — | **negative** |
| **A8** | **entity** (qualifier 아님) | 뒤 | — | **safety** |

**A1·A2에 표지를 일부러 뺐다** — S04(실패)와 S05·S12(성공)의 차이가 표지였을 수 있다.

**A6·A7·A8이 설계의 핵심이다.** "복사하라"를 강화하면 과잉 복사로 넘어간다.
positive에서 복사가 늘고 **음성 대조군에서 늘지 않아야** 가설이 지지된다.

**A8은 positive가 아니다.** canonical X2 첫 불릿이
`Do not duplicate a shared clinical entity solely to make a child grammatical` 이고,
`first-line platinum therapy`는 **entity이지 dependent qualifier가 아니다.**
문법을 맞추려 복제하면 **실패**이며, child가 문법적으로 불완전하게 남는 것이 정답이다.

**F2는 X2 지표에서 제외**한다 — 핵심이 X4 코호트별 내용 차이이지 공유 qualifier가 아니다.

## 5. B군 — primary_rule_id

같은 semantic 조합을 반복하지 않았다. 허용 primary 집합을 케이스마다 **사전 등록**했다.

| case | 조합 | 사전 등록 |
|---|---|---|
| B3 | 진단 + 바이오마커 | `{H2-B, H1-B}` · H2-A primary = FAIL |
| B4 | 진단 + 치료력 | `{H1-B}` · H2-A primary = FAIL |
| B5 | 검사값 + 약물 제한 | `{H1-B}` · H2-A primary = FAIL |
| B6 | 확인 귀속 | `{H2-B, H0}` · H1-A / H2-A primary = FAIL |
| **B8 / B9** | umbrella + closed list ×2 | `{H3, H4}` · **서로 일치해야 함** |
| B10 | 같은 도메인·다른 기전 | `{H1-B}` |

**B6 사전등록 축소 (2026-09-09 승인)**: `pathologically documented`는 독립 screening target의
대안이 아니므로 H1-A를 primary로 인정하는 것은 너무 넓다. canonical H0가 다른 요건을 지원하기만 하는
확인 방법을 독립 자식으로 만들지 말라고 하고, H2-B가 확인의 진단 귀속을 더 구체적으로 규정한다.
둘 중 하나를 배제할 근거는 현행 동결 canonical만으로는 약하므로 **H2-B를 preferred로 고정하지 않고**
`{H2-B, H0}` 두 값을 모두 허용한다.

**B8/B9 쌍이 안정성 자체를 측정한다.** 도메인만 다르고 구조가 같다 —
같은 primary면 안정, 갈리면 S06 vs S07 관측이 재현된 것이다.

## 6. C군 — 재귀

**깊이는 runner 규약을 따른다: root = depth 0.**

| case | 겨냥 경로 | max depth | 최심 pass |
|---|---|--:|--:|
| C1 | AND 루트 → 치료력 대안군이 OR로 재귀 (창 12 vs 6개월로 H1-A 병합 차단) | 1 | 2 |
| C2 | **복수 recursion_targets + 형제 재귀 분기** | 1 | 2 |
| C3 | nested_exception → main → composite | 1 | 2 |
| C4 | macro_aggregate 아래 재귀 자식 | 1 | 2 |
| C5 | 혼합 논리 A AND (B1 OR B2) | 1 | 2 |
| **C6** | **nested_exception → main(AND) → BTK/BCL-2 자식(OR)** | **2** | **3** |
| E2 | 분기 내부 allowance → 그 자식이 nested_exception으로 재귀 | 1 | 2 |
| C7 | 분할했으나 자식이 leaf → `needs_recursion=false` | 0 | 1 |

**C6이 최심이고 예상 max depth는 2다.** 최심 경로 pass가 3회지만 depth 3에서 실제 패스는 없다 —
`depth 3`이라 부르지 않는다. 초안에서 이 표기를 틀렸고 교정했다.

**C1 교정**: 초안의 `adequate cardiac function defined as LVEF ≥50%`는 로컬 임계값이 하나뿐이라
canonical H4의 macro_aggregate 요건(`Two or more`)을 만족하지 못해 재분해 근거가 없었다.
ECOG + 치료력 대안군 구조로 다시 썼다.

**C6 교정**: 초안은 `including`을 썼는데 canonical H3가 이를 **open-list 신호**로 명시한다.
그러면 모델이 재귀하지 않았을 때 H6 실패인지 H3 성공인지 구분할 수 없다. list 신호를 제거했다.

**E2 교정**: 초안의 EGFR exon19/L858R은 H1-A의 interchangeable members로 병합될 공산이 커서
재귀가 안 일어나면 누출 시험 자체가 불가능했다. allowance를 **두 번째 conjunct 안에** 넣어
그 분기가 nested_exception으로 재귀하도록 했다.

`max_depth` 가드와 `empty_main`은 자연스러운 criterion으로 유도하기 어려워 **mock이 계속 담당**한다.

## 7. D군 — exception 구분

| case | 표현 | 사전 등록 |
|---|---|---|
| **D1** | `without X` — 부재가 **독립 요건** | `composite_split`, AND, H1-B primary. H4 primary = FAIL |
| D2 | `unless X` | nested_exception (대조군) |
| D3 | `permitted if X` | nested_exception |
| D4 | `other than X` | nested_exception |
| **D5** | `except where … in the Study Manual` | **라벨 미등록. 정량 수용에서 제외** |
| **D6** | `without X` — 부재가 **통합 목표의 일부** | `none`. H4 primary = FAIL |

**D1 교정**: 초안의 `composite_split or none`을 `composite_split`으로 고정했다.
canonical H0가 `ANC ≥1.5 … without colony-stimulating-factor support`를 독립 명제 후보로 명시한다.

**D6 신설**: D1은 프롬프트 인라인 예제(`Platelet count ≥100 … without platelet transfusion …`)와
구조가 가까워 **규칙 테스트가 아니라 예제 회상 테스트**가 될 수 있다.
`without`이 통합 목표의 일부인 다른 구조를 독립적으로 넣었다 — 핵심 관측은 **H4 미발동**이다.

## 8. 대조군 정책

`structural_control` 5건(B1 B2 B7 D2 F1)은 Phase 5A에서 이미 옳게 나온 유형이다.

> **명확화가 안정 대조군의 올바른 결정을 바꾸면 그 후보는 기각 / 사람 검토 대상이다.**
> **대상 규칙군의 개선이 대조군 회귀를 상쇄하지 못한다.**

**B1 교정**: 초안의 `Active hepatitis B infection or chronic hepatitis B infection`은
active와 chronic 범주가 겹쳐 control로 부적합했다. 또한 대체안 후보 중
`History of X or currently active X` 형태는 프롬프트 인라인 예제
(`History of asthma or currently active asthma.`)와 동형이라 피했다.
치료 상태 변이(`Untreated or incompletely treated latent tuberculosis infection`)로 바꿨다.

## 9. 비교 설계 — 문서만, 실행하지 않음

지표·수용 기준·예산은 [`SCORING_PLAN.md`](SCORING_PLAN.md)에 사전 등록되어 있다. 요약:

- **X2 주 지표**: case-level 준수(모든 affected child가 정확한 span 포함). 보조로 child-level recall
- **안전 지표**: A6 over-copy · A7 무근거 추가 · A8 entity 중복 — **주 지표에 합산하지 않는다**
- **PR 지표**: 사전 등록 primary 집합 대비 적절성 · decisive rule 강등 · **B8/B9 일치** · 구조 회귀 · tier 결과
- **안전 조건**: 구조 결정이 바뀌면 명확화가 아니라 의미 변경 → 중단
- **호출 상한**: 5B-0 60 · 5B-1 25 · 5B-2 25 · 검토 전 누계 **100** · 향후 5B-3 70

**환경 고정**: Python 3.11.5 · openai 1.6.1 · 같은 extra_body 경로 ·
`requested_reasoning_effort=medium` · 같은 runtime/validator/trace 형식.
**비교 중 SDK를 올리지 않는다** — 독립변수에 다른 변수를 섞는다.

## 10. 실행 전 확정해야 할 것

1. 첫 유료 호출(5B-0) 승인
2. A6/A7/A8 판정 기준은 SCORING_PLAN §3에 고정됨 — 이견 여부만 확인
3. 5B-1/5B-2 서브셋 구성 확인 (SCORING_PLAN §8)

## 11. 하지 않은 것

- 모델 호출 없음 · P0 미실행 · 후보 미실행
- `candidate_combined_from_v1_3_1.txt` **미생성**
- canonical core · v1.3.1 프롬프트 무변경 · v1.3.2 버전 부여 없음
- historical 113-item 사용 없음
