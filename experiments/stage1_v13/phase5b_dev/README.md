# Phase 5B 개발 세트

> **상태: 미실행.** 모델을 호출하지 않았다. **개발 아티팩트** — 규범 증거도, gold standard도,
> held-out 평가 세트도 아니다.
> **작성 2026-09-08 · 교정 2026-09-09** (pre-execution correction)

## 파일

| 파일 | 내용 |
|---|---|
| [`cases.jsonl`](cases.jsonl) | **35**개 합성 케이스 (한 줄 = 한 root case) |
| [`manifest.json`](manifest.json) | 매니페스트 + 분모 + 프롬프트 해시 + 예산 (파일에서 생성) |
| [`design.md`](design.md) | 설계 근거, 군별 의도, 교정 내역 |
| [`SCORING_PLAN.md`](SCORING_PLAN.md) | **지표·수용 기준·호출 예산 (사전 등록)** |

가설: [`../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md`](../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md)

## 실험 구조 — 가설 격리

```
P0 = 변경 없는 v1.3.1

5B-0   P0 × 전체 35건            ← 공유 baseline, 한 번만
5B-1   P-X2 × X2 서브셋 (14)
5B-2   P-PR × provenance 서브셋 (12)
   ██ 사람 검토 ██
5B-3   P-COMBINED × 전체 35건    승인 후에만 (파일 미생성)
```

두 명확화를 한 후보에 넣으면 **개선의 원인을 귀속할 수 없다.** P0를 전체에 한 번만 돌리는 이유는
가설별 재측정을 피하고 재귀군·대조군에도 baseline을 주기 위해서다.

## 케이스 스키마

```json
{
  "case_id": "A1",
  "criterion_type": "inclusion | exclusion",
  "root_criterion_text": "...",
  "trial_has_cohorts": ["..."] 또는 null,
  "rule_family": ["X2", "H1-B"],
  "boundary": "겨냥하는 경계",
  "expected_structural": "...",
  "expected_provenance": "허용 primary 집합 포함",
  "expected_recursion": true | false | null,
  "expected_max_depth": 0 | 1 | 2 | null,
  "role": "...",
  "metric_group": "분모를 기계적으로 정하는 필드"
}
```

X2 케이스는 `shared_qualifier` / `qualifier_applies_to`(또는 `branch_specific_qualifier`,
`shared_entity`)를 추가로 갖는다. E2는 `leakage_forbidden_span`을 갖는다.
`expected_*`는 **사전 등록된 기계적·provenance 속성**이지 정답지가 아니다.

## 분모 (`metric_group`)

| 그룹 | 수 | 케이스 |
|---|--:|---|
| `x2_positive` | **6** | A1 A2 A3 A4 A5 E1 |
| `x2_negative_control` | **2** | A6 A7 |
| `x2_safety_control` | **1** | A8 |
| `provenance_target` | **7** | B3 B4 B5 B6 B8 B9 B10 |
| `recursion_coverage` | **7** | C1 C2 C3 C4 C5 C6 E2 |
| `recursion_negative_control` | 1 | C7 |
| `exception_distinction` | 4 | D1 D3 D4 D6 |
| `structural_control` | **5** | B1 B2 B7 D2 F1 |
| `cohort_scope_coverage` | 1 | F2 (X2 지표 제외) |
| `qualitative_probe` | 1 | D5 (정량 수용 제외) |

## 검증된 provenance

프로그램으로 확인했다 — v1.3.1 프롬프트 인라인 예제 **0건** · Phase 5A 케이스 **0건** ·
historical 113-item **0건** · `case_id` 중복 **0건** · 비결정 라벨 **0건**(qualitative probe 제외).

## 설계에서 가장 중요한 세 가지

**1. 음성 대조군.** A6(분기 전용 qualifier)·A7(공유 없음)은 **복사하면 안 되는** 케이스다.
positive에서 복사가 늘고 음성에서 늘지 않아야 가설이 지지된다. 한쪽만 개선되면 **편향 이동**이다.

**2. A8은 safety control이다.** `first-line platinum therapy`는 shared **entity**이지
dependent qualifier가 아니다. canonical X2 첫 불릿상 문법을 맞추려 복제하면 **실패**다.

**3. B8/B9는 쌍이다.** 도메인만 다르고 구조가 같은 macro_aggregate 두 건으로,
`primary_rule_id` 선택이 **안정적인지** 측정한다. "고칠 수 있는가"가 아니라 "규칙군 문제인가"를 묻는다.

## 재귀 — 깊이는 runner 규약 (root = 0)

**C6이 최심**: `root(0) → root.main(1) → root.main.<child>(2)`.
최심 경로 Stage-1 패스 3회, **관측 예상 max depth는 2**다. `depth 3`이라 부르지 않는다.

`max_depth` 가드와 `empty_main`은 자연스러운 criterion으로 유도하기 어려워 mock 테스트가 담당한다.

## 실행 시 지켜야 할 것

- `pipeline/stage1_v13`의 `JsonlTracer`를 **반드시 사용** — Phase 5A는 실패 시도를 남기지 못했다(I-07)
- `run_config`에 model · **requested**_reasoning_effort · max_completion_tokens ·
  SDK/Python 버전 · prompt artifact + sha256
- 호출 상한: 5B-0 **60** · 5B-1 **25** · 5B-2 **25** · 검토 전 누계 **100** · 향후 5B-3 **70**
- 비교 중 **SDK를 올리지 않는다**
- `iaa_workspace/` · `evidence/` · `STAGE1_GOLD_*/` · `results/adjudication/`에 쓰지 않는다

## 해석 한계

35건으로 **유병률을 추정하지 않는다.** 커버리지는 rule family 기준이다.
P0는 **1회 관측**이므로 통계적 우월성을 주장하지 않으며, 수용이 단일 불일치 케이스에 달려 있으면
성공 선언 대신 **paired confirmation 필요**로 표시한다.
