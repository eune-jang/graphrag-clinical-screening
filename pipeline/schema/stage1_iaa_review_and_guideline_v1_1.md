# Stage 1 IAA 검토 결과 (Round 2) — 종합 평가 및 보강 방향

> 8개 trial Round 2 IAA에서 도출된 annotator 간 차이 영역 · 상세 예시 · 가이드라인 보강 방향.
> 이 검토를 반영한 가이드라인 본문은 `annotation_guideline_v1_2.md` 참조 (본 문서는 검토 기록만 보관).
> 출처: `stage1_annotation_guideline_v1_2_draft.md` 1~110행 — 본문 분리 후 원본 폐기 (2026-08-25).

---

- 단순 단일 조건(none), 명확한 분리(composite)은 두 명이 거의 다 일치
- 예외는 대체로 아래 패턴에 몰려있음

## 1) 두 annotator 간 확연한 차이 (= 가이드라인 보강 필요 지점)

| 차이 영역 | EHJ 경향 | DYK 경향 |
| --- | --- | --- |
| macro child 구성 | 묶을 때 항목마다 칸을 나눔 (TB/HBV/HCV/HIV → 4칸) | 묶을 때 여러 항목을 한 칸에 모아 넣는 편 (7개 trial에서 나타남) |
| nested_exception 처리 | "~면 가능/제외" 같은 예외 단서를 적극적으로 잡아 예외로 뺌 (단 NCT01295827 E5 1건은 나열로 처리) | 예외 단서를 일반 나열로 보고 항목별로 나누는 편 (3건) |
| 진단·병기 split 여부 | 진단/병기/절제를 나누는 편이나 trial마다 granularity가 흔들림 (2~4개) | 한 덩어리로 안 나누거나(none) 너무 잘게 나누는(5개) 등 편차가 큼 |
| macro/composite 기준 | "따로 조회하나?"(query-unit)로 판정하는 편 | 나열 형태가 보이거나 umbrella 단어가 있으면 macro로 보는 편 |
| child_logic 표기 | "and/or" 단어보다 의미(둘 다? 하나만?)로 판정하는 편 | 기본값(inclusion=AND)이나 표면 접속사를 따라가는 편 |
| 상위 or vs 내부 including | 큰 "or"로 갈린 두 파트를 먼저 보고 나누는 편 | including 안쪽까지 분해 |
| semantic_category에 따른 split | 수술/처치 항목을 나누되 근거를 category로 설명하는 편 | 나누지 않는(none) 편 |
| cohort_scope 분할 granularity | cohort 그룹(Part) 단위로 묶어 분할 (NCT01295827 I1 → 3칸) | 진단명·조건마다 잘게 쪼개고 cohort_scope를 항목별로 분배 (같은 문장 → 8칸) |

## 2) 상세 예시

### 1. macro child 구성

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | 묶을 때 항목마다 칸을 나눔 | **NCT03800134 E5** "TB, HBV, HCV, HIV" → a: tuberculosis / b: hepatitis B / c: hepatitis C / d: human immunodeficiency virus **(4칸)** |
| **DYK** | 여러 항목을 한 칸에 모아 넣음 (7개 trial) | **NCT03800134 E5** 동일 문장 → a: "tuberculosis hepatitis B and C, or human immunodeficiency virus" **(1칸)** · **NCT05756153 E6** → a: "hypertension or diabetes" (1칸) · **NCT03800134 E12** → a: "pneumonectomy, segmentectomies, or wedge resections" (1칸) |

---

### 2. nested_exception 처리

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | 예외 단서를 적극적으로 잡아 예외로 뺌 (단 1건 역방향) | **NCT02912949 E4** → nested_exception, a: "patients treated for Hepatitis C and have undetectable viral loads are eligible" · ※ **NCT01295827 E5** "excepting inhaled steroids"는 composite로 처리 (1건 반대 방향) |
| **DYK** | 예외 단서를 일반 나열로 보고 항목별로 나누는 편 (3건) | **NCT02912949 E4** 동일 문장 → composite_split, a: "Known HIV" / b: "active Hepatitis B..." / c: "Hepatitis C; patients treated... eligible" · **NCT03728556 E5** ("OS follow-up is allowed") → composite_split · **NCT03800134 I5** ("excluding 항암백신") → macro_aggregate |

---

### 3. 진단·병기 split 여부

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | 나누는 편이나 trial마다 granularity가 다름 (2~4개) | **NCT03728556 I3** → 3칸: a "histologically confirmed" / b "locally advanced/unresectable" / c "stage III NSCLC" · **NCT03800134 I2** → 4칸 · **NCT02474355 I3** → 2칸 (진단·병기 묶음 / T790M) ← granularity 흔들림 |
| **DYK** | 안 나누거나(none) 모두 잘게 나눔(5개) | **NCT03728556 I3** 동일 문장 → none · **NCT02125461 I2** → none · 반면 **NCT02474355 I3** → 5칸: 병기 / EGFRm / NSCLC / 절제 / T790M ※ notes에 "한 기록지라 묶음"이라 작성했으나 split |

> 참고: 정답 granularity는 3-way (진단 / 병기 / 절제, biomarker는 별도 칸 → NSCLC NCCN 가이드라인 기준). EHJ의 묶음도 under-split, DYK의 5분할도 over-split이라 **양쪽 다 맞춰야 함.**

---

### 4. macro / composite 기준

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | "CRC 업무 시 따로 조회하나?"(query-unit)로 판정 | **NCT03728556 E6** "immune checkpoints, including PD-1, PD-L1, CTLA4..." → none, notes: "단일 약물카테고리로 한 번 조회, etc.로 열려 분할 이익 없음" · **NCT02474355 E8** (ECG) → none, notes: "resting ECG 하나로 판정" |
| **DYK** | 나열 형태나 umbrella 단어가 있으면 macro로 보는 편 | **NCT03728556 E6** 동일 문장 → macro_aggregate, a: "PD-1, PD-L1, CTLA4, TIM3 and LAG3, etc." (1칸) · **NCT02474355 E8** → macro_aggregate ("LBBB, 3도/2도 block" 1칸) · **NCT03728556 E10** "Crohn's or UC" → macro_aggregate |

---

### 5. child_logic 표기

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | "and/or" 단어보다 의미(둘 다? 하나만?)로 판정 | **NCT02912949 I1** "measurable OR (일부는) evaluable" → **OR** (하나만 충족하면 됨) · **NCT02075840 E8** (시점 분리) → **OR** |
| **DYK** | 기본값(inclusion=AND)이나 표면 접속사를 따라가는 편 | **NCT02912949 I1** 동일 문장 → **AND** (inclusion default) · **NCT02075840 E8** 동일 문장 → **AND** · **NCT02912949 I16** → **OR** (locally-adv/metastatic 표면 분리) |

> 참고: 구조(칸 나누기)는 두 라벨러가 거의 동일하게 봄. **AND/OR 표기만** 갈림.

---

### 6. 상위 or vs 내부 including

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | 큰 "or"로 갈린 두 파트를 먼저 보고 나눔 | **NCT02474355 E3** → composite_split (2칸) · a: "severe/uncontrolled systemic diseases, including HTN, bleeding, infection..." · b: "significantly impaired bone marrow reserve or organ function, including hepatic and renal impairment..." |
| **DYK** | including 안쪽까지 한 덩어리로 평탄화하는 편 | **NCT02474355 E3** 동일 문장 → macro_aggregate (1칸) · a: "uncontrolled hypertension, active bleeding diatheses, active infection... or significantly impaired bone marrow reserve or organ function..." (최상위 or 무시, 전체 통합) |

---

### 7. semantic_category에 따른 split

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | 수술/처치 항목을 나누되 근거를 category로 설명 | **NCT02075840 I6** "major surgery or traumatic injury" → composite_split, notes: "(a) major surgery → treatment_history (b) traumatic injury → condition" · **NCT02125461 E2** → notes: "GI는 K00–K63, liver는 K70–K77, 별도 카테고리" |
| **DYK** | 나누지 않는(none) 편 | **NCT02075840 I6** 동일 문장 → none · **NCT02125461 E2** → composite (근거 설명 없음) |

> 참고: split 여부는 두 단계로 판정. ① 한 기준에 서로 다른 semantic_category(진단/약/검사/처치 등 명백히 다른 종류)가 혼재하면 split — 한 Criterion은 단일 category만 가지므로 강제. ② 같은 category 안에서는 query-unit("따로 조회하는가")으로 판정.

---

### 8. cohort_scope 분할 granularity

|  | 경향 | 예시 |
| --- | --- | --- |
| **EHJ** | cohort **그룹(Part) 단위**로 묶어 분할 | **NCT01295827 I1** (multi-cohort) → 3칸 · a: Part A 솔리드종양 조건 (Solid Tumors cohort 6종) · b: Parts B·D 흑색종 조건 (MEL cohort 3종) · c: Parts C·F NSCLC 조건 (NSCLC cohort 3종) → 각 child에 해당 Part 그룹 전체를 cohort_scope로 부여 |
| **DYK** | 진단명·조건마다 잘게 쪼개고 cohort_scope를 항목별로 분배 | **NCT01295827 I1** 동일 문장 → 8칸 (a~h) MEL / carcinoma / metastatic / locally advanced ... 를 각각 분리, 같은 Part 안의 조건들까지 별도 child로 나눔 · ※ notes: "cohort를 나누는 경우 해당 문장 조건은 세부적으로 나눌 수 없음 / cohort A면 A가 들어가는 모든 cohort 포함" |

> 참고: cohort_scope는 **텍스트가 적용 cohort를 제한할 때만** 기록하며, composite_split에서는 각 child에 개별 부여. 같은 cohort에 함께 적용되는 조건들을 cohort가 다르다는 이유로 추가 분할하지 않음 — 분할 입도는 query-unit으로, cohort_scope는 그 위에 부여하는 속성.

## 3) 보강 방향

| 차이 영역 | 보강 방향 |
| --- | --- |
| macro child 구성 | split을 선택했으면 항목 하나당 child 하나로 나눔. 한 칸에 여러 항목이 들어가면 분리가 실현되지 않으므로 각 항목을 개별 child로 |
| nested_exception 처리 | 1) "except / unless / excluding / ~면 eligible / ~는 allowed" 단서가 있으면 nested_exception을 먼저 적용. 나열 분해보다 예외 분리가 우선. 2) 해당 단서들을 text_span 범위 안에 포함 (e.g., "except ~~") |
| 진단·병기 split 여부 | 조직학적 진단 / 병기 / 절제가능성을 각각 독립 query 단위로 split (3-way). biomarker가 있으면 별도 child 추가. 입도를 trial 무관하게 고정 |
| macro/composite 기준 | 1) "항목마다 따로 조회하는가"(query-unit)를 기준으로 none/split 항목 구분. 2) umbrella 단어 유무로 macro/composite를 분리 |
| child_logic 표기 | 기본값 생략 규칙 폐지, AND/OR 항상 명시. 표면 접속사가 아니라 의미(둘 다 충족 필요 → AND / 하나만 → OR)로 판정 |
| 상위 or vs 내부 including | 최상위가 or로 갈린 이질 파트인지 먼저 확인 → 그다음 각 파트 내부의 umbrella(macro)/나열(exception) 판정 (판정 순서 고정) |
| ~~semantic_category에 따른 split~~ | ~~split 판정 근거를 semantic_category가 아니라 query-unit으로. category 판단은 Stage 2 소관이므로 Stage 1 분할 근거로 사용하지 않음.~~ → crc 임상 워크플로우 상, condition(comorbidity)와 medication(conmed)가 설령 같은 페이지에 적혀있다고 하더라도 crc는 이를 나눠서 생각함. semantic_category가 다를 경우 query-unit이 달라질 확률 높으므로 클로드 제안 reject |
| cohort_scope 분할 granularity | 분할 granularity는 query-unit으로 정하고, cohort_scope는 그 위에 부여하는 속성. 같은 cohort에 함께 적용되는 조건들을 cohort가 다르다는 이유로 추가 분할하지 않음. cohort 그룹 단위로 묶고 각 child에 개별 cohort_scope 부여 |
