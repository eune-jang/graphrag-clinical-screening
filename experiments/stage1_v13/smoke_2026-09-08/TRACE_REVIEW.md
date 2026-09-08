# PHASE 5A — trace review (read-only semantic audit)

> **작성일**: 2026-09-08 · **성격**: 사람 검토용 read-only 감사.
> **코드·프롬프트·canonical core 수정 없음. API 추가 호출 없음. Phase 5B 미착수.**
>
> 근거는 전부 `traces/passes.jsonl`, `outputs/*.json`, `cases.jsonl` **원본 파일**이다.
> `summary.md`의 서술을 근거로 삼지 않았고, 숫자는 원본에서 다시 계산했다.

## 0. 성능 주장 없음

이 스모크 세트는 **14건의 합성 통합/개발 케이스**다. accuracy·sensitivity·specificity·모델 우열·
tier 분포 유병률 같은 연구 성능 주장을 하지 않는다.

기계적 속성 14/14 일치가 뜻하는 것은 **"선택된 스모크 메커닉이 의도대로 동작했다"** 뿐이다.

---

## 1. 검토 범위

| 항목 | 값 |
|---|--:|
| root 케이스 | 14 (전수, 샘플링 없음) |
| 재귀 패스 | 1 (`S10/root.main`) |
| **검토한 총 패스** | **15** |
| 유료 호출 트레이스 | 15 |
| 사전 프로브 (harness 외부) | 1 |

### ⚠️ 트레이스 로깅 결손 — 이 감사에서 처음 확인

Phase 5A 지시 §6은 패스별로 20개 항목 로깅을 요구했다. 제가 만든 harness가
`traces/passes.jsonl`에 남긴 것은 **11개**뿐이다.

| 기록됨 | 누락 |
|---|---|
| case_id · model · reasoning_effort · prompt_artifact · prompt_sha256 · criterion_type · trial_has_cohorts · raw_response · latency_s · usage · api_error | **hierarchy_path · depth · ROOT_CRITERION_TEXT · TARGET_SEGMENTS · PARENT_CONTEXT · parsed JSON · validation result · validation errors · retry count · cache hit/miss** |

누락분 대부분은 `outputs/*.json`(node_id·depth·target_segments·parent_context·파싱된 출력·
incomplete_reason)과 `cases.jsonl`에서 **복원 가능**했고, validation 결과는 저장된 계층에 대해
validator를 **오프라인 재실행**해 확인했다(API 호출 0). 따라서 이번 감사는 완전하게 수행됐다.

그러나 **재시도가 발생한 실패 패스는 트레이스에 남지 않는다** — 이번 실행은 재시도 0이라 손실이
없었지만, 재시도가 생기는 실행에서는 실패한 응답이 유실된다. 이것이 실질적 결손이며 **I-07**로 등록한다.

---

## 2. 원본 파일에서 재계산한 수치 (§8)

| 지표 | 원본 재계산 | 비고 |
|---|--:|---|
| root 케이스 | 14 | `cases.jsonl` 14줄 = `outputs/` 14파일 |
| 유료 호출 (harness) | 15 | `traces/passes.jsonl` 15레코드 |
| 사전 프로브 | 1 | harness 외부, 별도 스크립트 |
| **누계 유료 호출** | **16 / 50** | 상한 미달 |
| 성공 패스(계층 노드) | 15 | root 14 + 재귀 1 |
| 재귀 호출 | 1 | 노드 15 − root 14 |
| **재시도 호출** | **0** | 호출 15 − 성공 패스 15 |
| JSON 첫 시도 파싱 | **15 / 15** | 저장된 `raw_response` 전건 재파싱 |
| **validator 첫 시도 통과** | **15 / 15** | 재시도 0이므로 저장된 모든 패스가 첫 시도 |
| validator 최종 통과 | 15 / 15 | |
| validator 오프라인 재검증 | 15 패스 / **오류 0건** | API 호출 없이 재실행 |
| validator 실패 카테고리 | 없음 | |
| incomplete 노드 | **0** | `max_depth` 0, `empty_main` 0 |
| 토큰 | prompt 103,517 / completion 3,730 / **합계 107,247** | usage 누락 호출 0 |
| API 오류 | 0 | |

**이전 보고와의 차이 1건** — depth 분포 표기:

| 기준 | 값 |
|---|---|
| 케이스별 최대 depth (`summary.json`, 이전 보고) | depth 0: **13** · depth 1: 1 |
| **패스(노드) 단위** | depth 0: **14** · depth 1: 1 |

둘 다 옳고 서로 다른 것을 센다. 불일치가 아니라 **표기 기준 차이**이므로 기존 파일을 수정하지 않고
여기에만 기록한다. 이전 보고가 "depth 분포"라고만 쓴 것은 모호했다.

이 밖에 `summary.json`의 수치와 원본 재계산 사이에 **불일치는 없었다.**

---

## 3. 케이스별 검토

각 블록의 Input/Model result/Recursive result는 원본 파일에서 **기계적으로 생성**했다(전사 오류 방지).
Mechanical validity 이하가 사람 판단이다.

---

## S01


### Input

- **ROOT_CRITERION_TEXT**: `Eastern Cooperative Oncology Group performance status of 0 or 1 at screening.`
- **TARGET_SEGMENTS**: `["Eastern Cooperative Oncology Group performance status of 0 or 1 at screening."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H0/H1 — surface 'or' names a value range, not two propositions
- **passes**: 1 · latency 4.359s · tokens 6967

### Model result

```json
{
  "splitting_decision": "none",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H1-A",
  "supporting_rule_ids": [
    "H0"
  ],
  "notes": "Performance-status values 0 or 1 are alternative values within one integrated performance-status eligibility assessment at screening."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H1-A **적절**. 결정적 규칙은 same-screening-target 병합이다 — `0 or 1`은 하나의 통합 평가 안의 대체 값이지 두 명제가 아니다. H0 supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

표면 `or`에 낚이지 않았다. 의도한 경계를 정확히 통과.

---

## S02


### Input

- **ROOT_CRITERION_TEXT**: `Adequate cardiac reserve as judged by the treating investigator.`
- **TARGET_SEGMENTS**: `["Adequate cardiac reserve as judged by the treating investigator."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: X5 — broad adequacy statement with no concrete local subrequirements
- **passes**: 1 · latency 2.298s · tokens 6953

### Model result

```json
{
  "splitting_decision": "none",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "X5",
  "supporting_rule_ids": [
    "H0"
  ],
  "notes": "Broad adequacy statement with investigator judgment and no concrete local subrequirements."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

X5 **적절**. canonical X5의 *broad adequacy statement without concrete subrequirements → none* 이 정확히 이 사례다. X-rule을 primary로 쓰는 것은 프롬프트의 `primary_rule_id` 열거상 허용된다. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

투자자 판단 위임 + 로컬 임계값 부재를 정확히 인식.

---

## S03


### Input

- **ROOT_CRITERION_TEXT**: `Cytologically confirmed pancreatic ductal adenocarcinoma with a documented germline BRCA2 pathogenic variant.`
- **TARGET_SEGMENTS**: `["Cytologically confirmed pancreatic ductal adenocarcinoma with a documented germline BRCA2 pathogenic variant."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H2-B — diagnosis + independently required biomarker; confirmation stays with diagnosis
- **passes**: 1 · latency 3.552s · tokens 7166

### Model result

```json
{
  "splitting_decision": "composite_split",
  "child_logic": "AND",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "Cytologically confirmed pancreatic ductal adenocarcinoma"
      ],
      "cohort_scope": null,
      "rationale": "H2-A/H2-B: cytologic confirmation remains part of the diagnosis proposition; pancreatic ductal adenocarcinoma is an independently required diagnosis."
    },
    {
      "child_id": "b",
      "text_span": [
        "with a documented germline BRCA2 pathogenic variant."
      ],
      "cohort_scope": null,
      "rationale": "H2-A/H2-B: the documented germline BRCA2 pathogenic variant is an independently asserted biomarker requirement requiring a separate semantic category."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H2-A",
  "supporting_rule_ids": [
    "H2-B"
  ],
  "notes": ""
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H2-A **의심스러움**. 결정은 옳지만 결정적 규칙 선택이 문제다. canonical H2-B가 *an independently required biomarker is separate from diagnosis* 로 이 사례를 직접 다루고, 명제 경계 자체는 H1-B가 세운다. canonical은 H2-A를 *validates the H1 proposition boundary; it should not turn Stage 1 into concept extraction* 으로 규정한다 — 확인 규칙이라는 뜻이다. **선호 primary: H2-B (tier 1) 또는 H1-B (tier 2). 현재 tier 0 주장.**

### Issue classification

**D — normative-method question**

### Reviewer note

confirmation(`Cytologically confirmed`)이 진단 명제에 귀속된 것은 v1.3의 명시적 규범 변경대로다 ✅. 자식 b가 선행 `with`를 포함하나 축자·연속이므로 X1 위반이 아니다.

---

## S04


### Input

- **ROOT_CRITERION_TEXT**: `Women who are pregnant or breastfeeding at the time of screening.`
- **TARGET_SEGMENTS**: `["Women who are pregnant or breastfeeding at the time of screening."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: exclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H1-B + H5 — separate states, explicit OR
- **passes**: 1 · latency 3.055s · tokens 7130

### Model result

```json
{
  "splitting_decision": "composite_split",
  "child_logic": "OR",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "Women who are pregnant"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: pregnancy and breastfeeding are distinct screening targets that can be evaluated independently; either condition makes the exclusion criterion hold."
    },
    {
      "child_id": "b",
      "text_span": [
        "breastfeeding at the time of screening"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: breastfeeding is a distinct screening target, with the screening-time qualifier retained in this contiguous source segment."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H1-B",
  "supporting_rule_ids": [
    "H5",
    "X2"
  ],
  "notes": "The phrase 'at the time of screening' applies to both coordinated conditions by shared context."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**QUESTIONABLE**

### Rule provenance review

H1-B **적절**. H5·X2 supporting 적절. tier 2. provenance 자체에는 문제가 없다.

### Issue classification

**B — prompt wording/adherence**

### Reviewer note

§3 상세 참조. 모델 notes가 `at the time of screening`이 두 조건 모두에 적용된다고 **명시**했으나 자식 a에는 복사하지 않았다 — 자기 전제와 출력이 모순된다.

---

## S05


### Input

- **ROOT_CRITERION_TEXT**: `Grade 3 peripheral neuropathy or Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose.`
- **TARGET_SEGMENTS**: `["Grade 3 peripheral neuropathy or Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: exclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: X2 — shared dependent qualifier copied into both children; multi-segment text_span expected
- **passes**: 1 · latency 4.729s · tokens 7257

### Model result

```json
{
  "splitting_decision": "composite_split",
  "child_logic": "OR",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "Grade 3 peripheral neuropathy",
        "each persisting for more than 6 weeks after the last dose"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: peripheral neuropathy and ototoxicity are distinct screening targets. The phrase 'each persisting' explicitly applies the grade-duration requirement to both alternatives (X2)."
    },
    {
      "child_id": "b",
      "text_span": [
        "Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose."
      ],
      "cohort_scope": null,
      "rationale": "H1-B: ototoxicity is independently evaluable from peripheral neuropathy and carries the shared grade-duration requirement."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H1-B",
  "supporting_rule_ids": [
    "X2",
    "H5"
  ],
  "notes": ""
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H1-B **적절**. X2·H5 supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

§4 상세 참조. 두 자식 **모두** 공유 qualifier를 보존했고, span 형태 차이는 원문 어순의 귀결이다(자식 b는 원문에서 연속). X1이 명시적으로 허용하는 표현 차이.

---

## S06


### Input

- **ROOT_CRITERION_TEXT**: `Adequate bone marrow reserve, defined as absolute neutrophil count at least 1.0 x 10^9/L, hemoglobin at least 8.0 g/dL, and platelets at least 75 x 10^9/L.`
- **TARGET_SEGMENTS**: `["Adequate bone marrow reserve, defined as absolute neutrophil count at least 1.0 x 10^9/L, hemoglobin at least 8.0 g/dL, and platelets at least 75 x 10^9/L."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H3/H4 — true umbrella fully operationalized by children
- **passes**: 1 · latency 5.505s · tokens 7398

### Model result

```json
{
  "splitting_decision": "macro_aggregate",
  "child_logic": "AND",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "absolute neutrophil count at least 1.0 x 10^9/L"
      ],
      "cohort_scope": null,
      "rationale": "The absolute neutrophil count threshold is an independently assessed component of the explicitly defined bone marrow reserve requirement."
    },
    {
      "child_id": "b",
      "text_span": [
        "hemoglobin at least 8.0 g/dL"
      ],
      "cohort_scope": null,
      "rationale": "The hemoglobin threshold is an independently assessed component of the explicitly defined bone marrow reserve requirement."
    },
    {
      "child_id": "c",
      "text_span": [
        "platelets at least 75 x 10^9/L"
      ],
      "cohort_scope": null,
      "rationale": "The platelet threshold is an independently assessed component of the explicitly defined bone marrow reserve requirement."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H3",
  "supporting_rule_ids": [
    "H1-B",
    "H4",
    "H5"
  ],
  "notes": "The three thresholds exhaustively define the broad bone marrow reserve umbrella; no residual pass/fail meaning remains in the wrapper."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H3 **적절**. canonical의 macro gate가 H3 안에 있으므로 macro_aggregate 결정의 primary로 H3는 정합적이다. H1-B·H4·H5 supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

umbrella + 3개 임계값이 잉여 pass/fail 없이 operationalize. `child_logic=AND` 명시.

---

## S07


### Input

- **ROOT_CRITERION_TEXT**: `The participant must satisfy all of the following renal parameters: serum creatinine no greater than 1.5 mg/dL, and estimated creatinine clearance at least 50 mL/min.`
- **TARGET_SEGMENTS**: `["The participant must satisfy all of the following renal parameters: serum creatinine no greater than 1.5 mg/dL, and estimated creatinine clearance at least 50 mL/min."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H3 — closed, operationally exhaustive list under an umbrella
- **passes**: 1 · latency 2.927s · tokens 7182

### Model result

```json
{
  "splitting_decision": "macro_aggregate",
  "child_logic": "AND",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "serum creatinine no greater than 1.5 mg/dL"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: serum creatinine threshold is an independently evaluable renal eligibility requirement."
    },
    {
      "child_id": "b",
      "text_span": [
        "estimated creatinine clearance at least 50 mL/min"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: estimated creatinine clearance threshold is a distinct, independently evaluable renal eligibility requirement."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H1-B",
  "supporting_rule_ids": [
    "H4",
    "H5"
  ],
  "notes": "The stated renal-parameter umbrella is fully operationalized by the two explicit thresholds."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H1-B **경미하게 의심스러움**. 구조적으로 S06과 같은 유형(umbrella + closed list)인데 S06은 H3를, S07은 H1-B를 primary로 골랐다. canonical의 closed-list 판정과 macro gate는 H3다. **선호 primary: H3.** 두 규칙 모두 tier 2라 파급은 없다.

### Issue classification

**B — prompt wording/adherence**

### Reviewer note

결정 자체는 옳다. 동일 유형 두 건에서 primary 선택이 갈린 것이 관찰점이다.

---

## S08


### Input

- **ROOT_CRITERION_TEXT**: `Active autoimmune disease requiring systemic therapy, such as rheumatoid arthritis, psoriasis, or Sjogren syndrome.`
- **TARGET_SEGMENTS**: `["Active autoimmune disease requiring systemic therapy, such as rheumatoid arthritis, psoriasis, or Sjogren syndrome."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: exclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H3 — open/non-exhaustive list; named examples must not be split out
- **passes**: 1 · latency 2.191s · tokens 7025

### Model result

```json
{
  "splitting_decision": "none",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H3",
  "supporting_rule_ids": [
    "H0"
  ],
  "notes": "The 'such as' conditions are non-exhaustive examples within the broader active autoimmune disease requirement; systemic therapy qualifies the parent condition."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H3 **적절**. open/non-exhaustive list를 쪼개지 않는 것이 정확히 H3의 결정 내용이다. H0 supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

`such as` 목록을 named item으로 분해하지 않고 잔여 범위를 보존했다. v1.3에서 가장 중요한 행동 변화 중 하나가 실제로 관측됐다.

---

## S09


### Input

- **ROOT_CRITERION_TEXT**: `Participants with a second primary malignancy are excluded, other than adequately treated cervical carcinoma in situ.`
- **TARGET_SEGMENTS**: `["Participants with a second primary malignancy are excluded, other than adequately treated cervical carcinoma in situ."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: exclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H4/X3 — single exception span with explicit trigger at the end
- **passes**: 1 · latency 3.342s · tokens 7030

### Model result

```json
{
  "splitting_decision": "nested_exception",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "other than adequately treated cervical carcinoma in situ"
      ],
      "cohort_scope": null,
      "rationale": "H4: removing this phrase restores the broader exclusion of participants with a second primary malignancy; it carves out adequately treated cervical carcinoma in situ from that otherwise excluded category."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H4",
  "supporting_rule_ids": [
    "X3"
  ],
  "notes": "Main content is one exclusion proposition; no further structure remains."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H4 **적절**. exception test가 결정적. X3(span 경계) supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

exception span **1개**로 유효 — 레거시 프로덕션 검증기의 `≥2` 규칙이었다면 거부됐을 형태다.

---

## S10


### Input

- **ROOT_CRITERION_TEXT**: `Prior thoracic irradiation and prior systemic chemotherapy are exclusionary, unless completed more than 12 months before enrollment.`
- **TARGET_SEGMENTS**: `["Prior thoracic irradiation and prior systemic chemotherapy are exclusionary, unless completed more than 12 months before enrollment."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: exclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H4 + H6 — exception waives a composite main rule; main should recurse
- **passes**: 2 · latency 4.252s, 4.253s · tokens 14450

### Model result

```json
{
  "splitting_decision": "nested_exception",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "unless completed more than 12 months before enrollment"
      ],
      "cohort_scope": null,
      "rationale": "H4: removing this explicit 'unless' phrase restores the broader exclusion of prior thoracic irradiation and prior systemic chemotherapy. The phrase waives that exclusion when the applicable prior treatment was completed more than 12 months before enrollment."
    }
  ],
  "needs_recursion": true,
  "recursion_targets": [
    "main"
  ],
  "recursion_note": "The main content contains two distinct prior-treatment screening targets joined as coordinate exclusionary conditions and requires next-level structural evaluation; the shared exception remains attached to the propagated main material.",
  "primary_rule_id": "H4",
  "supporting_rule_ids": [
    "H1-B",
    "X3"
  ],
  "notes": ""
}
```

### Recursive result

**`root.main`** (depth 1)

- TARGET_SEGMENTS: `["Prior thoracic irradiation and prior systemic chemotherapy are exclusionary,"]`
- PARENT_CONTEXT: `{"parent_decision": "nested_exception", "parent_child_logic": null, "current_child_id": "main", "sibling_spans": {"a": ["unless completed more than 12 months before enrollment"]}}`

```json
{
  "splitting_decision": "composite_split",
  "child_logic": "AND",
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "Prior thoracic irradiation"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: prior thoracic irradiation is a distinct treatment-exposure screening target."
    },
    {
      "child_id": "b",
      "text_span": [
        "prior systemic chemotherapy"
      ],
      "cohort_scope": null,
      "rationale": "H1-B: prior systemic chemotherapy is a distinct treatment-exposure screening target."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "primary_rule_id": "H1-B",
  "supporting_rule_ids": [
    "H5",
    "X1"
  ]
}
```

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H4 **적절**. H1-B·X3 supporting 적절(main이 복합임을 예고). 재귀 패스 `root.main`의 H1-B도 적절. 두 패스 모두 tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

§7 상세 참조. exception이 composite main을 waive하는 구조를 인식하고 `recursion_targets=["main"]`을 냈다.

---

## S11


### Input

- **ROOT_CRITERION_TEXT**: `Anticoagulant therapy is prohibited; low-dose prophylactic heparin is permitted if the participant remains within therapeutic monitoring range.`
- **TARGET_SEGMENTS**: `["Anticoagulant therapy is prohibited; low-dose prophylactic heparin is permitted if the participant remains within therapeutic monitoring range."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: exclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H4 — conditional allowance ('permitted if') encodes a waiver
- **passes**: 1 · latency 3.265s · tokens 7152

### Model result

```json
{
  "splitting_decision": "nested_exception",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "low-dose prophylactic heparin is permitted if the participant remains within therapeutic monitoring range"
      ],
      "cohort_scope": null,
      "rationale": "H4 conditional allowance: prophylactic heparin is an anticoagulant therapy that the main prohibition would otherwise exclude; this phrase permits it when the monitoring condition is met."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H4",
  "supporting_rule_ids": [
    "X3"
  ],
  "notes": "The main anticoagulant-therapy prohibition is one proposition; the monitoring condition is part of the conditional allowance."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H4 **적절**. canonical H4의 *Conditional permissive language* 절이 `permitted if`를 waiver로 규정한다. X3 supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

조건부 허용을 exception으로 인식. main(`Anticoagulant therapy is prohibited;`)이 단일 명제라 재귀하지 않은 것도 옳다.

---

## S12


### Input

- **ROOT_CRITERION_TEXT**: `Serum potassium within normal limits without the use of oral or intravenous supplementation at screening.`
- **TARGET_SEGMENTS**: `["Serum potassium within normal limits without the use of oral or intravenous supplementation at screening."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H4 — negative requirement 'without X' is NOT an exception
- **passes**: 1 · latency 6.657s · tokens 7374

### Model result

```json
{
  "splitting_decision": "composite_split",
  "child_logic": "AND",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "Serum potassium within normal limits",
        "at screening"
      ],
      "cohort_scope": null,
      "rationale": "H2-A: normal serum potassium is an independently asserted laboratory-condition requirement; screening timing applies to this assessment."
    },
    {
      "child_id": "b",
      "text_span": [
        "without the use of oral or intravenous supplementation at screening"
      ],
      "cohort_scope": null,
      "rationale": "H2-A: absence of oral or intravenous supplementation is an independently asserted medication/exposure requirement, distinct from the potassium result."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H2-A",
  "supporting_rule_ids": [
    "H1-B",
    "X2"
  ],
  "notes": ""
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H2-A **의심스러움**. 모델 자신이 H1-B를 supporting에 넣었는데, 명제 경계를 세운 것이 바로 그 H1-B다 — 칼륨 수치 요건과 보충제 미사용 요건은 각각 개별 충족/위반이 가능하다. H2-A는 leaf 유효성 확인에 가깝다. **선호 primary: H1-B (tier 2). 현재 tier 0 주장.**

### Issue classification

**D — normative-method question**

### Reviewer note

negative requirement(`without ...`)를 exception으로 오분류하지 않았다 ✅. 공유 qualifier `at screening`을 **두 자식 모두에** 복사했다 — S04와 정면 대조된다.

---

## S13


### Input

- **ROOT_CRITERION_TEXT**: `Confirmed diagnosis of relapsed or refractory multiple myeloma and at least two prior lines of therapy.`
- **TARGET_SEGMENTS**: `["Confirmed diagnosis of relapsed or refractory multiple myeloma and at least two prior lines of therapy."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `None`
- **intended boundary**: H6 — composite whose diagnosis child may itself split (mixed logic)
- **passes**: 1 · latency 3.319s · tokens 7171

### Model result

```json
{
  "splitting_decision": "composite_split",
  "child_logic": "AND",
  "cohort_scope": null,
  "sub_criteria": [
    {
      "child_id": "a",
      "text_span": [
        "Confirmed diagnosis of relapsed or refractory multiple myeloma"
      ],
      "cohort_scope": null,
      "rationale": "H2-A: the confirmed relapsed/refractory multiple myeloma diagnosis is an independently asserted diagnosis requirement."
    },
    {
      "child_id": "b",
      "text_span": [
        "at least two prior lines of therapy"
      ],
      "cohort_scope": null,
      "rationale": "H2-A: prior lines of therapy is an independently asserted treatment-history requirement distinct from the diagnosis."
    }
  ],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H2-A",
  "supporting_rule_ids": [
    "H1-B",
    "H2-B"
  ],
  "notes": ""
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H2-A **의심스러움**. S12와 동일 패턴 — H1-B가 supporting으로 강등됐다. 진단과 치료력은 H1-B의 독립 주장 테스트로 갈린다. **선호 primary: H1-B (tier 2). 현재 tier 0 주장.**

### Issue classification

**D — normative-method question**

### Reviewer note

`relapsed or refractory`를 H1-A 병합으로 한 단위 유지 — 하나의 운영상 질병 상태이고 분기별 제약이 없으므로 방어 가능하다. 재귀 미발생은 불일치가 아니다(기대값을 열어 두었다).

---

## S14


### Input

- **ROOT_CRITERION_TEXT**: `In Cohort B only, participants must have received at least one prior anti-angiogenic agent.`
- **TARGET_SEGMENTS**: `["In Cohort B only, participants must have received at least one prior anti-angiogenic agent."]`
- **PARENT_CONTEXT**: `None`
- **criterion_type**: inclusion · **TRIAL_HAS_COHORTS**: `['Cohort A', 'Cohort B']`
- **intended boundary**: X4 — criterion text itself restricts applicability; cohort label copied verbatim
- **passes**: 1 · latency 1.643s · tokens 6992

### Model result

```json
{
  "splitting_decision": "none",
  "child_logic": null,
  "cohort_scope": [
    "Cohort B"
  ],
  "sub_criteria": [],
  "needs_recursion": false,
  "recursion_targets": [],
  "recursion_note": "",
  "primary_rule_id": "H0",
  "supporting_rule_ids": [
    "X4"
  ],
  "notes": "The cohort phrase is explicit applicability scope; prior anti-angiogenic exposure is one eligibility proposition."
}
```

### Recursive result

없음 (`needs_recursion=false`).

### Mechanical validity

**PASS** — JSON 첫 시도 파싱, validator 첫 시도 통과, 재시도 0, span 위반 0 (저장된 계층에 대한 오프라인 재검증 포함).

### Semantic review

**PASS**

### Rule provenance review

H0 **적절**. 코호트 구문을 구조적 내용이 아니라 적용 범위로 판정한 것이 H0 role gate의 결정 내용이다. X4 supporting 적절. tier 2.

### Issue classification

**E — no issue / allowed representation difference**

### Reviewer note

`cohort_scope=["Cohort B"]` 축자 복사, `none`이므로 top-level 배치 — X4대로다.

---
## 4. S04 상세 — 공유 qualifier (§3)

```
ROOT / TARGET_SEGMENTS : "Women who are pregnant or breastfeeding at the time of screening."
PARENT_CONTEXT         : None (루트 패스)

[a] ["Women who are pregnant"]
[b] ["breastfeeding at the time of screening"]

notes: "The phrase 'at the time of screening' applies to both coordinated conditions by shared context."
```

### 1. qualifier가 원문상 어느 coordination에 scope되는가

`at the time of screening`은 두 번째 conjunct(`breastfeeding`) **뒤에** 위치한다.
canonical X2의 기본 구문 단서로는 *"a qualifier located within one conjunct is evidence that it may
modify only that branch"* — 즉 **표면상으로는 두 번째 분기만** 수식하는 것으로 읽힌다.

다만 X2는 곧바로 *"clinical/eligibility meaning overrides the default cue"* 라고 덧붙인다.
임신·수유 배제는 스크리닝 시점 상태를 묻는 것이므로 **임상적으로는 두 분기 모두에 적용된다.**
모델의 판단(두 조건 모두)이 옳다.

### 2. canonical X2상 실제로 두 child를 수정하는 shared dependent qualifier인가

**그렇다.** 임상 의미가 구문 단서를 덮는 사례다.
X2: *"Copy a shared dependent qualifier (temporal/numeric/conditional/severity) into every child it
semantically modifies."* — `at the time of screening`은 temporal qualifier다.

### 3. 각 child의 TARGET_SEGMENTS에 qualifier가 들어갈 수 있었는가

**가능했다.** 루트 패스의 TARGET_SEGMENTS는 원문 전체 한 세그먼트이고,
`at the time of screening`은 그 안의 **축자 연속 부분문자열**이다(프로그램 확인).
자식 a가 `["Women who are pregnant", "at the time of screening"]`을 내면
X1 검증을 통과했을 것이다 — S05·S12에서 모델이 실제로 낸 형태와 동일하다.

### 4. 런타임이 qualifier를 잃었는가

**아니다.** 런타임은 `text_span` 내용을 생성하지도 변형하지도 않는다.
`validators.py`는 검사만 하고, `context.py`의 자식 컨텍스트 구성은 모델이 낸 span을 그대로 옮긴다.
main 파생(`derive_main_segments`)은 `nested_exception`에서만 동작하며 이 케이스와 무관하다.
저장된 `outputs/S04.json`의 span은 모델 원응답(`raw_response`)과 일치한다.

### 5. 모델이 쓸 수 있었는데 한 child에서 빠뜨린 것인가

**그렇다.** 그리고 **모델 자신의 notes와 모순된다** — notes는 "두 조건 모두에 적용"이라 명시하는데
출력은 한쪽에만 담았다. 능력 부재가 아니다: **같은 실행의 S05와 S12에서는 정확히 복사했다.**

| 케이스 | 공유 qualifier | 복사 여부 |
|---|---|---|
| S04 | `at the time of screening` | ❌ 자식 b에만 |
| S05 | `each persisting for more than 6 weeks after the last dose` | ✅ 양쪽 |
| S12 | `at screening` | ✅ 양쪽 |

S05·S12의 qualifier에는 공유를 알리는 표지(`each`, 그리고 원문 어순)가 있고 S04에는 없다는 차이가
관측된다. 이것이 프롬프트 문구 문제로 보는 근거다.

### 6. 빠진 child가 semantic meaning을 실제로 잃었는가

**부분적으로 잃었다.** 자식 a는 `"Women who are pregnant"` 뿐이다.
"스크리닝 시점의 임신"과 "임신력"은 운영상 다른 조건이다(과거 임신은 배제 사유가 아니다).
자식 a의 span만 보는 downstream 소비자는 그 시간 제약을 볼 수 없다.

완화 요인: 재귀 시 자식 a는 `ROOT_CRITERION_TEXT`를 읽기 전용 문맥으로 받고,
`PARENT_CONTEXT.sibling_spans`에 자식 b의 span(qualifier 포함)이 들어간다.
따라서 정보 자체는 계층에 남아 있다 — 다만 **X2가 요구하는 자리에 있지 않다.**

### 결론

> **clear prompt/model adherence failure**

모델 자신의 전제를 기준으로 하면 X2의 지시는 모호하지 않다 — 수식하는 모든 자식에 복사해야 한다.
런타임 버그가 아니고, 단순 허용 표현 차이도 아니다(자식 a가 운영 제약을 잃었다).

다만 "명백한 위반"이면서 동시에 **프롬프트에 빠져나갈 구멍이 있다**: X2의 두 번째 절
*"A child may be grammatically incomplete if ROOT/PARENT context supplies shared meaning"* 은
"공유 문맥이 있으니 복사하지 않아도 된다"로 읽힐 여지가 있다. 그 절은 문법적 불완전성 허용에 관한
것이지 의미적 수식 qualifier의 생략 허가가 아니다. **프롬프트 패치 후보 (수정하지 않음).**

관측 표본 1건. 단일 관측을 일반화하지 않는다.

---

## 5. S05 상세 — 형제 span 비대칭 (§4)

```
TARGET_SEGMENTS: ["Grade 3 peripheral neuropathy or Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose."]

[a] ["Grade 3 peripheral neuropathy", "each persisting for more than 6 weeks after the last dose"]
[b] ["Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose."]
```

지시대로 오류로 가정하지 않고 세 가지를 확인했다.

| 확인 항목 | 결과 |
|---|---|
| 두 child가 동일한 shared qualifier/context를 보존하는가 | ✅ **양쪽 모두 보존** |
| 모든 span이 TARGET_SEGMENTS 축자 provenance를 만족하는가 | ✅ 오프라인 재검증 위반 0 |
| downstream hierarchy semantics가 손실되는가 | ❌ 손실 없음 |

형태 차이의 원인은 **원문 어순**이다. 자식 b의 대상(`Grade 3 ototoxicity`)은 qualifier와 원문에서
연속이므로 **한 세그먼트가 오히려 더 정확한 표현**이다(내부 쉼표까지 원문 그대로).
자식 a의 대상은 qualifier와 떨어져 있어 두 세그먼트가 필요하다.

canonical X1은 이를 명시적으로 허용한다: *"A single child may contain multiple text_span segments"*,
*"Different text_span segments of the same child MAY come from different TARGET_SEGMENTS"*.
비연속 원문을 하나로 이어붙이는 것이 금지될 뿐, 대칭성 요구는 없다.

### 결론

> **E — allowed representation difference**

span 모양이 대칭이 아니라는 이유만으로 이슈로 분류하지 않는다. 실질 문제 없음.

단, downstream 소비자가 "대등한 형제는 같은 span 구조를 갖는다"고 가정하면 안 된다는 점은
런타임 문서에 남길 가치가 있다 — 이슈가 아니라 **특성**이다.

---

## 6. primary_rule_id / provenance 감사 (§5, §6)

전 15패스 대상. **"판정 label이 맞다"와 "provenance rule ID가 맞다"를 별개로 평가**했다.

| path | decision | primary | tier | supporting | 판정 |
|---|---|---|--:|---|---|
| S01 | none | H1-A | 2 | H0 | 적절 |
| S02 | none | X5 | 2 | H0 | 적절 |
| **S03** | composite_split | **H2-A** | **0** | H2-B | **의심** → H2-B(1) 또는 H1-B(2) |
| S04 | composite_split | H1-B | 2 | H5, X2 | 적절 |
| S05 | composite_split | H1-B | 2 | X2, H5 | 적절 |
| S06 | macro_aggregate | H3 | 2 | H1-B, H4, H5 | 적절 |
| **S07** | macro_aggregate | H1-B | 2 | H4, H5 | **경미 의심** → H3 (tier 영향 없음) |
| S08 | none | H3 | 2 | H0 | 적절 |
| S09 | nested_exception | H4 | 2 | X3 | 적절 |
| S10 | nested_exception | H4 | 2 | H1-B, X3 | 적절 |
| S10/main | composite_split | H1-B | 2 | H5, X1 | 적절 |
| S11 | nested_exception | H4 | 2 | X3 | 적절 |
| **S12** | composite_split | **H2-A** | **0** | H1-B, X2 | **의심** → H1-B(2) |
| **S13** | composite_split | **H2-A** | **0** | H1-B, H2-B | **의심** → H1-B(2) |
| S14 | none | H0 | 2 | X4 | 적절 |

**적절 11 / 의심 4 (그중 tier 영향 3).**

### 6-1. H2-A primary 감사 — Tier 0 inflation 가능성

**H2-A primary: 3건 (S03, S12, S13). 전부 tier 0.**

canonical의 두 문장이 판단 기준이다:

> H2-A **validates** the H1 proposition boundary; it should not turn Stage 1 into concept extraction.
> `primary_rule_id` = ONE primary **decisive** canonical rule.

| case | H2-A가 split을 강제했는가? | 실제 경계를 세운 규칙 | 선호 primary | tier 결과 |
|---|---|---|---|---|
| S03 | ❌ 아니다 | H1-B(독립 주장) → H2-B(진단 vs 바이오마커 축)가 canonical에서 이 사례를 직접 규정 | **H2-B** (또는 H1-B) | 0 → **1** (또는 2) |
| S12 | ❌ 아니다 | H1-B — 칼륨 수치와 보충제 미사용은 각각 개별 충족/위반 가능 | **H1-B** | 0 → **2** |
| S13 | ❌ 아니다 | H1-B — 진단과 치료력의 독립 주장 | **H1-B** | 0 → **2** |

세 건 모두 **동일한 방향의 primary/supporting 역전**이다. 결정적 규칙(H1-B 또는 H2-B)이
`supporting_rule_ids`로 강등되고, 확인 규칙인 H2-A가 primary로 올라갔다.
**세 건 중 두 건(S12, S13)은 모델이 H1-B를 supporting에 직접 적어 넣었다** — 자기 출력 안에
더 결정적인 규칙을 스스로 나열하면서 primary는 다른 것을 골랐다.

**Tier 결과**: tier 0은 canonical에서 "온톨로지/스펙의 구조적 제약만으로 결정"을 뜻하는
가장 강한 권위 주장이다. 세 건이 그 권위를 주장하지만, 실제로는 H1-B의 명제 경계 판단(tier 2)이
결정적이었다. **Tier 0 inflation 가능성이 실재한다.**

> ⚠️ 14건에서 나온 비율(3/14)을 통계적으로 일반화하지 않는다. historical 113-item gold의
> tier 0 비율(10/113)과 나란히 놓는 것도 이 표본 크기에서는 의미가 없다.
> 확인된 것은 **비율이 아니라 메커니즘**이다 — 역전이 일어나는 방식이 세 건에서 동일했다.

### 6-2. 그 밖의 rule-ID 감사

- **supporting이 primary보다 더 decisive해 보이는 경우**: S12, S13에서 발생(위 참조). 그 외 없음.
- **H5가 구조 결정 primary로 잘못 선택된 경우**: **없음.** H5는 전 패스에서 supporting으로만 등장했고
  (S04, S05, S06, S07, S10/main), 구조 결정의 primary로 쓰이지 않았다. 올바른 사용이다.
- **X-rule이 semantic structure primary로 과도하게 선택된 경우**: X5가 S02에서 primary다.
  이는 **과도하지 않다** — canonical X5가 "포괄 적정성 → none"을 직접 규정하므로 그 결정의
  결정적 규칙이 맞다. 프롬프트의 `primary_rule_id` 열거도 X1–X7을 포함한다. 그 외 X-rule primary 없음.
- **H4 사용**: 3건 전부 `nested_exception`의 primary로, exception test가 결정적인 사례다. 적절.
- **H0 사용**: S14 1건. 코호트 구문의 역할 판정이 결정적이므로 적절.

---

## 7. 재귀 트레이스 검토 — S10 (§7)

```
ROOT_CRITERION_TEXT
  "Prior thoracic irradiation and prior systemic chemotherapy are exclusionary,
   unless completed more than 12 months before enrollment."

root  TARGET_SEGMENTS = [전체 원문]   PARENT_CONTEXT = None
      → nested_exception, child_logic=null, primary=H4
        exception span [a] = "unless completed more than 12 months before enrollment"
        needs_recursion=true, recursion_targets=["main"]

  ↓ 러너가 main 파생 (모델은 main span을 내지 않는다)

root.main (depth 1)
      TARGET_SEGMENTS = ["Prior thoracic irradiation and prior systemic chemotherapy are exclusionary,"]
      PARENT_CONTEXT  = {"parent_decision":"nested_exception","parent_child_logic":null,
                         "current_child_id":"main",
                         "sibling_spans":{"a":["unless completed more than 12 months before enrollment"]}}
      → composite_split, child_logic=AND, primary=H1-B, supporting=[H5, X1]
        [a] "Prior thoracic irradiation"
        [b] "prior systemic chemotherapy"
        needs_recursion=false, recursion_targets=[]
```

| 확인 항목 | 결과 |
|---|---|
| exception subtraction | ✅ `derive_main_segments`를 **독립 재실행**해 저장값과 일치 확인 |
| punctuation 보존 | ✅ 후행 콤마 유지 (`… are exclusionary,`) — Phase 4 정책이 실제 실행에서 확인됨 |
| 다음 TARGET_SEGMENTS | ✅ 축자 부분문자열, exception 텍스트 **잔존 없음** |
| PARENT_CONTEXT | ✅ 규약대로 4필드, `current_child_id="main"`, sibling_spans에 exception span |
| root context 격리 | ✅ main의 TARGET_SEGMENTS ≠ 원문 전체. depth 1의 두 span 모두 main 세그먼트 내부 |
| 재귀 결정 | ✅ 두 개의 독립 사전치료 노출 → composite_split |
| child_logic | ✅ `AND` — 배제 기준이지만 두 사전치료가 각각 별개 요건이라 AND가 맞다 |
| exception span 재귀 여부 | ✅ **재귀하지 않음.** 자식은 `root.main` 하나뿐 |
| 최종 계층 | ✅ 2노드, incomplete 없음, 완결 |

모델의 `recursion_note`도 정확하다 — main이 두 개의 사전치료 대상을 담고 있으며 공유 exception이
전파된 main 자료에 붙어 있다고 서술했다.

**nested_exception 전체 경로가 실제 모델로 end-to-end 검증됐다.**

### 7-B. Phase 5B development coverage gap (오류 목록 아님)

실제 모델로 **아직 노출되지 않은** 메커닉. 전부 mock 단위 테스트에서는 통과한다.

| 메커닉 | 실모델 노출 | mock 테스트 |
|---|---|---|
| depth ≥ 2 다단 재귀 | ❌ 미노출 (최대 depth 1) | ✅ |
| `composite_split`/`macro_aggregate` **자식** 재귀 | ❌ 미노출 (관측된 재귀는 `["main"]` 하나뿐) | ✅ |
| 복수 `recursion_targets` 동시 처리 | ❌ 미노출 | ✅ |
| 형제 재귀 분기 | ❌ 미노출 | ✅ |
| `max_depth` 가드 발동 | ❌ 미노출 (0건) | ✅ |
| `empty_main` | ❌ 미노출 (0건) | ✅ |
| validator 실패 후 재시도 경로 | ❌ 미노출 (재시도 0) | ✅ |
| 캐시 hit 경로 | ❌ 미노출 (캐시 미사용) | ✅ |

**이것은 결함이 아니라 커버리지 공백이다.** Phase 5B 케이스 설계에서 다단 구조를 의도적으로 포함해야
실제 모델 응답으로 이 경로들이 검증된다.

---

## 8. SDK 재현성 기록 (§10) — 코드 수정 없음

| 항목 | 확인값 |
|---|---|
| 실제 openai 패키지 버전 | **1.6.1** |
| 설치 위치 | `/Users/jang-eunhye/miniconda3/lib/python3.11/site-packages/openai/` |
| Python | 3.11.5 (miniconda base 환경) |
| PyPI 최신 | 3.8.0 |
| `requirements.txt`에 pin | **없음 (0건)** |
| `pyproject.toml`에 선언 | **없음 (0건)** |
| `reasoning_effort` 전달 방식 | `extra_body={"reasoning_effort":"medium","max_completion_tokens":8000}` |
| 왜 `extra_body`인가 | SDK 1.6.1의 `chat.completions.create`에 `reasoning_effort` / `max_completion_tokens` 명시 파라미터가 **없음**(서명 확인) |
| 응답에서 설정 적용을 확인할 metadata | **없음.** `usage`가 노출하는 키는 `prompt_tokens` / `completion_tokens` / `total_tokens` 뿐이며 `reasoning_tokens` 류 필드가 없다 |
| 응답 `model` 필드 | `gpt-5.6-terra` (요청과 일치, 프로브에서 확인) |

### 재현성 관점의 함의

1. **`openai`가 어떤 의존성 파일에도 선언되어 있지 않다.** 다른 환경에서 이 실행을 재현하면
   설치되는 SDK 버전이 달라지고, 3.x에서는 `extra_body` 없이 명시 파라미터를 써야 한다.
   즉 **현재 harness 코드는 SDK 버전에 암묵적으로 결합되어 있다.**
2. **reasoning effort가 실제로 medium으로 적용됐는지 응답만으로는 증명할 수 없다.**
   요청 본문에 담았다는 것은 harness 코드와 `run_config.json`으로 확인되지만,
   응답 metadata에 확인 필드가 없다. 모델 계열 비교 단계에서는 이 설정이 조건 변수이므로
   **검증 가능한 기록 방법이 필요하다.**
3. 결정 사항 3안(SDK 업그레이드 / 우회 내재화 / 현행 유지)은 그대로 미결이다.

**Phase 5B 전 재현성 결정 사항으로만 남긴다. 추가 API 호출 없음.**

---

## 9. Issue disposition (§9)

기존 `ISSUES.md`는 **수정하지 않았다.** 아래가 이번 감사의 disposition이다.

| issue_id | case_id | observed behavior | class | severity | recommended next action |
|---|---|---|---|---|---|
| **I-01** | S04 | 모델이 notes에 공유 적용을 명시하고도 qualifier를 한 child에만 복사. 런타임 무관, 모델은 S05·S12에서 정확히 수행 | **B** | **material** | **prompt patch candidate** — X2의 "문법적 불완전 허용" 절이 생략 근거로 읽히는지 검토. Phase 5B에서 동일 유형 케이스 추가 |
| **I-02** | S05 | 대등한 형제의 span 형태 비대칭 | **E** | **none** | **no action** — X1이 명시 허용. 원문 어순의 귀결이며 양쪽 모두 qualifier 보존. 런타임 문서에 "대칭 가정 금지"만 남길 가치 |
| **I-03** | S03, S12, S13 | H2-A가 primary, 실제 결정적 규칙(H1-B/H2-B)이 supporting으로 강등 → tier 0 주장 3건 | **D** | **material** | **normative review required** + Phase 5B 관찰 확대. canonical의 "primary decisive rule" 정의 또는 H2-A 서술 명확화 필요 여부 판단 |
| **I-04** | — | 재귀 1건·depth 1만 실모델 노출 | **A** (테스트 설계) | **minor** | **add development test case** — Phase 5B에 다단·복수 target·형제 분기 케이스 포함 |
| **I-05** | — | openai SDK 1.6.1, `extra_body` 우회, 의존성 미선언, reasoning 적용 확인 metadata 없음 | **A** | **material** | **investigate in Phase 5B** — 재현성 결정 3안 중 선택 + 의존성 선언. 코드 수정은 승인 후 |
| **I-06** | — | 호출당 prompt 토큰 ≈6,900 | **A** (운영) | **minor** | **no action** — 예산 산식에 반영만 |
| **I-07** ⭐ | — | **trace 로깅이 Phase 5A §6 요구 20항목 중 9개 누락.** 특히 재시도 실패 응답이 유실됨 | **A** | **material** | **runtime fix required** — harness 로깅 보강(코드 수정, 승인 후). 이번 실행은 재시도 0이라 손실 없었음 |
| **I-08** ⭐ | S06 vs S07 | 구조적으로 동일한 두 macro_aggregate에서 primary가 H3 / H1-B로 갈림 | **B** | **minor** | **investigate in Phase 5B** — tier 영향 없음. 표본 2건이라 판단 유보 |

⭐ = 이번 trace review에서 새로 등록.

### 분류별 집계

| class | 건수 | issue |
|---|--:|---|
| **A** runtime/software | 3 | I-04, I-05, I-07 |
| **B** prompt wording/adherence | 2 | I-01, I-08 |
| **C** model variability/capability | 0 | — |
| **D** normative-method question | 1 | I-03 |
| **E** no issue / allowed | 1 | I-02 |

**C가 0건**인 것이 이번 감사의 특징이다. S04는 모델이 같은 실행 안에서 같은 규칙을 두 번 정확히
수행했으므로 능력 문제로 볼 근거가 없고, 나머지도 능력 부재를 시사하지 않는다.

---

## 10. 이 감사에서 하지 않은 것

- 코드 수정 없음 · v1.3.1 프롬프트 수정 없음 · canonical core 수정 없음
- 기존 `ISSUES.md`·`summary.md`·`summary.json` 수정 없음 (불일치는 이 문서에만 기록)
- API 추가 호출 없음 (validator는 저장된 출력에 **오프라인** 재실행)
- Phase 5B 미착수 · 프롬프트 패치 미작성 · 성능 주장 없음
