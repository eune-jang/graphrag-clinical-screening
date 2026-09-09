# Phase 5B 개발 세트

> **상태: 미실행.** 모델을 호출하지 않았다. 이 디렉터리는 **사전 등록된 실험 설계**다.
> **개발 아티팩트** — 규범 증거도, gold standard도, held-out 평가 세트도 아니다.

## 파일

| 파일 | 내용 |
|---|---|
| [`cases.jsonl`](cases.jsonl) | 34개 합성 케이스 (한 줄 = 한 root case) |
| [`manifest.json`](manifest.json) | 케이스 매니페스트 + 커버리지 집계 + 해석 한계 |
| [`design.md`](design.md) | 설계 근거, 군별 의도, 비교 설계 |

가설 본문: [`../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md`](../../../docs/project_state/stage1_v1_3_phase5b_prompt_hypotheses.md)

## 케이스 스키마

```json
{
  "case_id": "A1",
  "criterion_type": "inclusion | exclusion",
  "root_criterion_text": "...",
  "trial_has_cohorts": ["..."] 또는 null,
  "rule_family": ["X2", "H1-B"],
  "boundary": "이 케이스가 겨냥하는 경계",
  "expected_structural": "기대 구조 속성",
  "expected_provenance": "기대 provenance 속성",
  "expected_recursion": true | false,
  "role": "x2_hypothesis | primary_rule_hypothesis | recursion_coverage | "
          "exception_distinction | control | *_negative_control"
}
```

`expected_*`는 **사전 등록된 기계적·provenance 속성**이지 정답지가 아니다.
가설을 실행 **전에** 고정해 두기 위한 것이다. 두 케이스(D1, D5)는 의도적으로 열어 두었다.

## 구성

34건 = x2 8 + x2 대조 2 + primary_rule 7 + recursion 7 + recursion 대조 1 +
exception 4 + control 5

| 축 | 값 |
|---|---|
| 기대 구조 | composite_split 20 · nested_exception 5 · none 4 · macro_aggregate 3 · 모호 2 |
| 재귀 기대 | 7건 |
| criterion_type | inclusion 19 / exclusion 15 |
| cohort 지정 | 2건 |
| rule family | H1-B 15 · X2 10 · H4 9 · H6 8 · H3 5 · X1/X3/H5 각 3 · 그 외 |

## 검증된 provenance

프로그램으로 확인했다.

- v1.3.1 프롬프트의 inline 예제와 **문장 중복 0건**
- Phase 5A 스모크 케이스와 **중복 0건**
- historical 113-item 세트에서 가져온 것 **없음**
- `case_id` 중복 없음

## 설계에서 가장 중요한 두 가지

**1. 음성 대조군이 있다.** A6·A7은 **공유 qualifier를 복사하면 안 되는** 케이스다.
"복사하라"를 강화하면 과잉 복사로 넘어갈 수 있으므로, A1–A5에서 복사가 늘고
**A6·A7에서는 늘지 않아야** 가설이 지지된다. 한쪽만 개선되면 편향 이동이다.

**2. B8/B9는 쌍이다.** 도메인만 다르고 구조가 같은 `macro_aggregate` 두 건으로,
`primary_rule_id` 선택이 동등 구조에서 **안정적인지** 본다. Phase 5A의 S06 vs S07 관측의 직접 후속이다.

## 실행 시 지켜야 할 것

- `pipeline/stage1_v13/`의 `JsonlTracer`를 **반드시 사용**한다 — Phase 5A는 실패한 시도를
  기록하지 못했다(I-07). 이제 attempt 단위로 남는다
- `run_config`에 model · **requested**_reasoning_effort · max_completion_tokens ·
  SDK/Python 버전 · prompt artifact + sha256을 넣는다
  ([`../environment/README.md`](../environment/README.md) §4)
- 호출 상한을 사전에 정한다. A/B 비교는 34 × 2 = 68 root 호출 + 재귀 + 재시도
- `iaa_workspace/` · `evidence/` · `STAGE1_GOLD_*/` · `results/adjudication/`에 쓰지 않는다

## 실행 전 미확정 (사람 판단)

1. 프롬프트 후보 문구 (가설 문서 A안 / B안 / 제3안)
2. 호출 상한
3. A6·A7 과잉 복사 판정 기준
4. D5(모호 케이스) 처리 — 지표 제외 또는 별도 보고

## 해석 한계

34건으로 **유병률을 추정하지 않는다.** 커버리지는 rule family 기준이며 빈도 기준이 아니다.
확인하려는 것은 비율이 아니라 **규칙군 차원의 실패 존재 여부**다.
