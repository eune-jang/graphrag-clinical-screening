# Stage 1 Annotation Guideline v1.2.1 (판정 동결본)

> v1.0 → v1.1: 8개 trial IAA 검토에서 도출된 8개 차이 영역을 반영해 수정. 기존 구조·톤 유지, 보강 내용 반영.
> v1.1 → v1.2: 온톨로지 스펙(v1.2.2) 정합성 검토, LLM 파이프라인 검증 가능성 검토, adjudication 중 발견된 혼합 로직 표현 한계를 반영해 수정.
> v1.2 → v1.2.1: **판정(adjudication) 착수 전 동결본** (2026-08-25). 기존에 실제로 적용해 온 "종류가 다른 항목 혼재 → split" 규칙이 검토 기록에만 있고 본문에 없던 것을 §3으로 편입 (신규 규칙 아님, 문서화 누락 보정). **판정이 끝날 때까지 이 문서는 수정하지 않으며**, 판정 중 발견되는 개정 필요 사항은 판정 기록(rule_status=conflict/gap)으로 남겨 v1.3 재료로 넘긴다.
>
> ※ IAA Round 2 검토 결과(종합 평가 / 상세 예시 / 보강 방향)는 별도 문서 `stage1_iaa_review_and_guideline_v1_1.md` 참조. 본 문서는 라벨링 시 참조하는 가이드라인 본문만 포함.

---

## v1.1 → v1.2 변경 요약

| # | 변경 항목 | v1.1 | v1.2 | 사유 |
| --- | --- | --- | --- | --- |
| 1 | **재귀 분할 도입** | 단층 분할 (1회 판정) | split으로 생성된 각 조각을 다시 ①~③으로 판정, 모든 조각이 none이 될 때까지 반복 | 혼합 로직 A AND (B1 OR B2)를 단층으로 표현 불가. parent당 child_logic 1개 제약상 판정 하나가 그래프에서 유실됨 |
| 2 | child_logic 명시 범위 | composite_split만 항상 명시 | composite_split·macro_aggregate 모두 항상 명시 | macro에도 OR 구조 존재. 스펙 v1.2.3과 정렬 |
| 3 | Text_span 원칙 구조 | 규칙 5개 + 재량 표현("가급적", "복제해도 됨") + 비연속 허용 예외 | 대원칙(연속 substring) + 세그먼트 배열 형식 + 보조규칙 6개. 재량 표현 전면 제거 | 사람·LLM 공통 결정성 확보. substring 자동 검증 및 UI 하이라이트 가능 |
| 4 | 공통 표현 복제 규칙 | 거리 기준 (바로 앞이면 복제 가능 / 멀면 금지) | 기능 기준 (개체 → 복제 금지 / 제약 → 적용 child 모두에 세그먼트 추가) | 거리 기준은 판단 재량 발생. "이 표현 하나만으로 CRC가 조회할 수 있는가" 테스트로 이원화 |
| 5 | header 판정 기준 보강 | umbrella 명사구 유무 | + 리트머스 테스트: header 후보에 하위 항목이 커버하지 않는 pass/fail 내용이 남으면 header가 아니라 별도 child | 판정 내용이 header에 숨으면 그래프에서 평가되지 않고 유실됨 |
| 6 | 외부 문서 위임 규칙 신설 | — | umbrella가 있어도 하위 항목이 외부 문서(IB 등)에만 위임 → none + notes 기록 | 본문에 독립 판정 단위 없음. ECG 케이스(NCT02474355 E8)와 동일 논리 |
| 7 | 진단·병기 재결합 서술 | Concept:Stage property(value/status/resectability) 인용 | Stage 노드 재결합 가능성만 명시, property 구성은 spec v1.3 위임 | 현행 스펙 Concept:Stage에 status·resectability property 없음 |
| 8 | nested_exception 용어·구조 | "child text_span" | "예외 조각(exception span)" + Neo4j에서 child Criterion 노드 미생성 명시 | annotation JSON의 조각과 그래프의 child 노드 개념 혼동 방지 |
| 9 | 스팬 경계 규칙 신설 | — | 리스트 마커·선행/후행 구두점 처리 규칙 | 경계 토큰이 사람·LLM 공통 스팬 불일치 최대 원인 |
| 10 | cohort_scope 빈 값 표기 | null / 빈 array / 생략 혼재 | 생략으로 통일 | 파이프라인 JSON 검증 일관성 |
| 11 | 🔁 v1.2.1: category 혼재 → split 명문화 | 검토 기록(§7 참고)에만 존재 | §3 본문 규칙으로 편입 + §4와 적용 범위 구분 명시 | 운영 문서에 규칙이 없으면 라벨링·판정 준거가 갈라짐. 기존 관행의 문서화이며 신규 규칙 아님 |

---

## splitting_decision 선택

### 1) composite_split *vs.* macro_aggregate *vs.* nested_exception 정의

**composite_split**:

- 독립 복수 판정(CRC가 나눠서 생각)이 필요하고, **Umbrella header 없이** 항목들이 결합되어 있을 때 적용.
- child_logic은 원문 표현 대신 *실제 의미*로 판정 (→ child_logic 섹션 참고).

**macro_aggregate**:

- 독립 복수 판정이 필요하고, **Umbrella header 아래** 항목들이 나열되어 있을 때 적용.
    - 예: "adequate organ function" header 아래 lab values, "uncontrolled illness" header 아래 comorbidity 나열.

**nested_exception:**

- inclusion/exclusion criteria 구분없이 구조적 패턴으로 판단
- 본문에서 떨어져 나오는 조건부 예외 구조(트리거)가 있으면 nested_exception
    - **예외 트리거 표현**: `except`, `excluding`, `unless`, `other than`, `with the exception of`, `~ are eligible`, `~ is/are allowed`, `~ is not excluded`, `not required if ~`
- 🔁 **v1.2**: 예외 조각(exception span)은 annotation JSON에 기록하되, Neo4j에서는 별도 child Criterion 노드를 생성하지 않고 단일 Criterion 노드에 INCLUDES_EXCEPTION relation으로 표현됨. composite/macro의 child와 구분하기 위해 "예외 조각"으로 부름. (따라서 예외 조각은 항목별로 더 쪼개지 않으며, child_logic도 부여하지 않음)

---

### 2) splitting_decision 판단 순서

복합 문장은 다음 **순서**로 판단한다 (순서 고정).

```
① 최상위 결합(OR/AND)로 갈린 이질 파트 분리
② 각 파트 내부에서 nested_exception(예외) 분리
③ 각 파트 내부에서 split 여부(none/split) 및 split 타입(macro/composite) 판정
④ 🔁 v1.2: split으로 생성된 각 조각을 ①~③으로 다시 판정 (재귀).
   모든 조각이 none이 될 때까지 반복하며, none인 조각이 leaf(최종 판정 단위)가 된다.
```

- 문장 전체의 큰 덩어리를 먼저 나눈 뒤, 각 덩어리 안에서 포함항목/예외항목을 고려
    - 예: "severe or uncontrolled systemic diseases, *including* HTN, bleeding, infection, **or** significantly impaired bone marrow reserve or organ function, *including* hepatic and renal impairment"
    → 최상위 OR로 [전신질환 파트] / [골수·장기기능 파트] 2개로 분리 → composite_split
    → 각 내부의 "including ~"은 큰 파트 안의 포함항목이므로 나누지 않음
- 한 개의 기준에 nested_exception과 composite_split이 혼재하면 큰 파트를 우선적으로 고려.
    - 즉, A or B에서, B 전체가 예외 조건일 경우는 nested_exception. 그러나 B의 일부가 예외 조건일 때는 composite_split
        - 예: "Active autoimmune disease or a documented history of autoimmune disease or syndrome that requires systemic steroids or immunosuppressive agents, except vitiligo or resolved childhood asthma/atopy."
            → B 전체가 A 항목의 예외 조건이므로 nested_exception
        - 예: "NCI CTCAE Grade 3 or higher toxicities due to any prior therapy (e.g., radiotherapy) (excluding alopecia)"
        → B 전체가 A 항목의 예외 조건이므로 nested_exception
        - 예: "Medical condition that requires chronic systemic steroid therapy, or on any other form of immunosuppressive medication, **excepting use of inhaled steroids**"
            → B의 일부가 B의 예외 조건이므로 composite_split

**🔁 재귀(④) 운영 규칙**

- 한 번의 판정은 **한 계층**만 다룬다. 화면(또는 프롬프트)에서 하위 계층까지 한꺼번에 입력하지 않음.
- split으로 생긴 조각은 **예외 없이 전부** 다시 판정 대상이 된다. "더 나눠질 것 같은 조각만" 골라 재판정하지 않음(재량 방지). 대부분의 조각은 none으로 즉시 종료됨.
- nested_exception의 경우 **main 조각만** 재판정 대상. 예외 조각은 child가 아니므로 재판정하지 않음.
- 재귀 판정 시 판단 근거는 항상 **루트 criterion 원문 전체**를 보고 정함 (조각만 떼어놓고 판단하지 않음).

---

### 3) split 여부 — 나눌 것인가 말 것인가 (split vs none)

- **query-unit** 기준: CRC가 항목마다 따로 판단하는가(다른 검사·다른 기록·다른 조회 단위)
    - 단일 판정(한 번 판단) → none

        ```
        "IBD (eg, Crohn's, UC)"  → IBD 진단 유무 = 진단 목록에서 한 번 판단 → none
        ```

    - 독립 복수 판정(항목마다 따로 조회) → split

        ```
        "Adequate organ function: ANC ≥1500, Plt ≥100k, Cr ≤1.5"  → ANC 충족? / Plt 충족? / Cr 충족? = 항목마다 따로 판단 → split
        ```

        ```
        "recovered from major surgery or significant traumatic injury at least 28 days"
        → 수술 회복 기록 / 외상 회복 기록 = 별도 판단 → split
        ```

- 🔁 **v1.2.1 — 종류가 다른 항목이 섞여 있으면 무조건 split**: 한 기준 안에 성격이 명백히 다른 항목(진단 / 약물 / 검사 / 수술·처치 등 = semantic_category가 다른 항목)이 함께 있으면, query-unit을 따질 필요 없이 split.
    - 이유 ① (스펙 강제): Criterion 노드는 semantic_category를 **하나만** 가짐. 섞인 채로 두면 Stage 2에서 category를 정할 수 없음.
    - 이유 ② (CRC 업무): comorbidity(동반질환)와 conmed(병용약물)는 같은 페이지에 적혀 있어도 CRC는 나눠서 생각함.

        ```
        "recovered from major surgery or significant traumatic injury at least 28 days"
        → (a) major surgery = 수술·치료 이력 (treatment_history)
          (b) traumatic injury = 질환·상태 (condition)
        → 종류가 다르므로 split (같은 category 안에서만 query-unit으로 재판정)
        ```

    - ※ 적용 범위: 이 규칙은 **나눌지 말지(§3)**에만 쓴다. 어떤 타입으로 나눌지(§4, macro vs composite)를 정할 때는 category를 보지 않는다.

- 🔁 **v1.2 — 외부 문서 위임 → none**: umbrella 표현이 있어도 하위 항목이 프로토콜 텍스트(본문 또는 인접 criterion)에 열거되지 않고 외부 문서(IB, Table, appendix)에만 위임된 경우, 독립 판정 단위가 텍스트에 없으므로 단일 판정 → none. notes에 "thresholds delegated to {외부 문서}" 기록.

    ```
    "Adequate bone marrow reserve and organ function as demonstrated by complete blood count,
     biochemistry in blood and urine at baseline (please refer to IB for guidance)"
    → 항목별 임계값이 본문에 없고 IB에 위임 / CBC·biochemistry는 판정 항목이 아니라 평가 수단
    → 단일 판정 → none / notes: "thresholds delegated to IB"
    ```

    - 단, 인접 criterion에 실제 lab 수치("ANC ≥ 1500" 등)가 이어서 나열되면 해당 문장은 macro_aggregate parent로 처리 (수치 항목들이 child).

---

### 4) split 타입 결정 (macro_aggregate vs composite_split)

- **Umbrella header 유무**로 결정. (semantic_category가 같은지 다른지는 **타입 결정에서는** 고려하지 않음 — 나눌지 말지 단계에서는 §3의 혼재 규칙이 먼저 적용됨)
    - header 존재 → macro_aggregate

        ```
        "Uncontrolled illness such as CHF, uncontrolled HTN, unstable angina"  → CHF? / HTN? / angina? = 독립 복수 판정 → split
        → "Uncontrolled illness"라는 Umbrella header 존재 → macro_aggregate
        ```

        ```
        "Adequate organ function: ANC ≥1500, Plt ≥100k, Cr ≤1.5"  → 독립 복수 판정 → split  → Umbrella header 있음 → macro_aggregate
        ```

    - header 없음 → composite_split

        ```
        "≥18세, 치료력 없음, NSCLC 진단"  → 독립 복수 판정 → split  → Umbrella header 없음 → composite_split
        ```

        ```
        "Known HIV, active Hepatitis B without receiving antiviral treatment, or Hepatitis C; patients treated for Hepatitis C and have undetectable viral loads are eligible"
        → 독립 복수 판정 → split
        → 예외 조건이 (c) 항목의 일부이며, Umbrella header 없음 → composite_split
        ```

- 참고)
    - header란 하위 항목을 포괄하는 상위 명사구로, 그 자체가 독립 조회 단위가 아닌 경우(예: "uncontrolled illness", "adequate organ function")
    - 하위 항목이 단일 카테고리로 한 번에 조회되면 header가 아니라 single judgment → none.

        ```
        "Any prior treatment of antibody/drug that targets at T-cell coregulatory proteins (immune checkpoints, including PD-1, PD-L1, CTLA4, TIM3 and LAG3, etc.)."
        → immune checkpoints 자체가 T-cell coregulatory proteins를 수식하므로 상위 명사구 아니며, 단일 약물 카테고리로 한 번 조회되고, 뒤에 딸려오는 항목들이 단순 예시 → none
        ```

- 🔁 **v1.2 — header 리트머스 테스트**: header 후보 문구에 **하위 항목들이 커버하지 않는 pass/fail 판정 내용이 남아 있으면, 그 부분은 header가 아니라 별도 child**로 분리한다. header에 숨은 판정은 그래프에서 노드가 되지 못해 매칭 시 평가되지 않고 유실되기 때문.
    - "adequate organ function" → 하위 lab 수치가 의미를 전부 채움, 남는 판정 없음 → header ○
    - "If female, may participate if not pregnant or breastfeeding, and at least one of the following conditions apply:" → "not pregnant or breastfeeding"은 CRC가 임신검사·수유 기록으로 직접 조회하는 판정이며 하위 1)·2)에 포함되지 않음 → 해당 부분은 별도 child, header는 "at least one of the following conditions apply"만 (→ 7) 예시 참고)

---

### 5) split 후 child 구성 규칙

- split(composite_split / macro_aggregate)을 선택한 경우, **3)에서 식별한 독립 판정 단위 수만큼 child를 생성**.
- 하나의 child text_span에 둘 이상의 독립 판정 항목을 함께 넣지 않음. (한 칸에 여러 항목이 들어가면 분리가 실현되지 않아 none과 동일)

    ```
    "tuberculosis, hepatitis B and C, or human immunodeficiency virus"  → a: tuberculosis / b: hepatitis B / c: hepatitis C / d: human immunodeficiency virus (4 child)  → "TB, HBV, HCV, HIV" 전체를 한 child에 넣지 않음
    ```

- macro_aggregate의 Umbrella header는 부모의 구조적 wrapper이며, child는 항목별로 분리.
- 🔁 **v1.2**: 각 child는 저장 후 다시 판정 대상이 된다 (→ 2)-④ 재귀). 이때 child가 또 split이면 그 하위 조각이 생기고, none이면 leaf로 확정된다.

---

### 6) 진단·병기 criterion (3-way 고정)

- 진단(diagnosis) / 병기(stage) / 절제가능성(resectability) 은 각각 독립 query 단위이므로 별도 child로 분할 (3-way). trial 무관하게 granularity 고정.
    - 근거: NCCN상 resectability는 TNM staging과 독립 축. 동일 Stage III여도 resectable/unresectable이 갈림 → 진단(병리) / 병기(영상·staging) / 절제(수술적합성·MDT) = 3개 독립 query.
- 병기 세부등급(Stage IIIB vs IIIC 등) 자체는 Stage 카테고리에 해당되는 세부표현이므로 각각을 분리하지 않고 하나의 덩어리로 취급.
- **biomarker(EGFR, ALK, KRAS, NRG1, T790M 등)는 진단과 semantic_category가 다르므로(biomarker ≠ condition) 반드시 별도 child로 분리**

**예시**

**(A) 진단 + 병기 + 절제 (3-way)**

```
"NSCLC (locally advanced, unresectable, Stage III)"
→ (a) NSCLC                        (진단)
  (b) locally advanced Stage III   (병기)
  (c) unresectable                 (절제가능성)
→ 3-way
```

※ "locally advanced"와 "Stage III"는 같은 병기 판정의 두 표현 → 같은 병기 단위. 원문 어순상 떨어져 있으므로 **세그먼트 배열**로 기입: `["locally advanced", "Stage III"]` (→ Text_span (2))

**(B) 진단 + 병기 + 절제 + biomarker (4-way 이상)**

```
"Histologically or cytologically confirmed advanced KRAS G12C-mutated NSCLC"
→ (a) Histologically or cytologically confirmed    (진단확인)
  (b) advanced                                     (병기)
  (c) KRAS G12C-mutated                            (biomarker)
  (d) NSCLC                                        (진단)
→ 4-way
```

- 후속 단계(Stage 2~5)와의 관계
    - 위 분할은 Stage 1-prompt #1 (splitting) granularity 규칙.
    - **spec상 진단·병기·biomarker는 각각 다른 Concept subtype + 다른 relation으로 연결됨**:
        - 진단(NSCLC) → Concept:Condition / REQUIRES_CONDITION (icd10, snomed)
        - 병기(Stage III) → Concept:Stage
        - biomarker(EGFRm) → Concept:Biomarker / REQUIRES_BIOMARKER (gene_symbol, variant, variant_type, variant_notation)
    - 한 child에 "EGFRm NSCLC"를 묶으면 Stage 2가 단일 semantic_category·단일 relation을 못 정함(biomarker인가 condition인가). 끊어두면 각 child가 자기 Concept·relation·property로 깨끗이 매핑됨. (Stage 3의 biomarker variant_notation auto-fill, preferred_name 정규화도 child별 분리 전제)
    - 근거: spec v1.2.2가 Concept:Stage TNM descriptor를 "한 노드에 여러 의미 압축"이라는 이유로 제거(Layer Separation 원칙). biomarker·진단을 한 child에 묶는 것도 같은 위반 방향.
    - 단, stage · resectability는 Stage 2에서 재결합될 수 있음
        - stage(병기) · resectability(절제가능성)는 둘 다 Concept:Stage로 향할 수 있어, Stage 2에서 동일 Concept:Stage 노드로 합쳐져 표현될 수 있음. 🔁 **v1.2**: Criterion → Concept:Stage 연결 relation과 resectability 표현 방식은 spec v1.3에서 정의 예정이므로 특정 property 구성을 전제하지 않음.
    - 반면 biomarker · 진단은 아예 다른 Concept subtype이라 재결합되지 않음 → 끊기의 필요성은 biomarker·진단 쪽이 더 강함.
    - Stage 1에서는 모두 끊되, 재결합 여부는 Concept subtype이 같은지로 갈린다는 점만 이해하면 됨 ("어차피 합쳐지니 안 끊어도 된다"고 판단하지 않음).

---

### 7) child_logic 표기

- 🔁 **v1.2**: composite_split·macro_aggregate **모두** child_logic을 **항상 명시**. (기본값 생략 규칙 폐지 — 생략 시 omit/default 의도 구분 불가. macro_aggregate도 "at least one of the following" 같은 OR 구조가 가능하므로 AND 고정으로 두지 않음)
- nested_exception·none에는 child_logic을 부여하지 않음.
- 선정/제외기준 모두 **표면 표현형("and"/"or") 대신, 실제 의미**로 판정
    - 모든 child를 충족해야 함 → **AND**
    - child 중 하나만 충족하면 됨 → **OR**

    ```
    "measurable lesion OR (일부 cohort는) evaluable disease"
      → 하나만 충족하면 되므로 OR (inclusion이지만 default AND를 따르지 않음)
    ```

- 🔁 **v1.2 — 혼합 로직은 계층으로 분할**: A AND (B1 OR B2) 형태는 한 parent에 담지 않는다. 계층을 나누고 **각 parent가 자기 child_logic을 하나씩** 가진다.

    ```
    "If female, may participate if not pregnant or breastfeeding, and at least one of the
     following conditions apply: 1) not a woman of childbearing potential (WOCBP); or
     2) a WOCBP who agrees to follow contraceptive guidance during the treatment period ...
     and agrees not to donate eggs ... during this period."   (KEYNOTE-671 I3)

    → 1차 판정: composite_split, child_logic = AND
         a: ["If female", "not pregnant or breastfeeding"]              (독립 판정)
         b: ["If female", "at least one of the following conditions apply"]
    → 2차 판정(b 재귀): macro_aggregate, child_logic = OR
         b-a: ["not a woman of childbearing potential (WOCBP)"]
         b-b: ["a WOCBP who agrees to follow contraceptive guidance during the treatment
                period ... and agrees not to donate eggs ... during this period"]
    → 3차 판정: a, b-a, b-b 모두 none → leaf 3개 확정

    ※ 문장 전체에 OR 하나만 부여하면 임신·수유 판정이 OR 안으로 들어가
       "임신 중이어도 동의만 하면 통과"로 잘못 해석됨. 최상위 AND가 이를 방지.
    ※ b-b 내부의 "agrees to ... and agrees not to ..."는 단일 동의 판정(query-unit 1개) → none
    ```

---

## Text_span 작성 원칙

**대원칙**: 모든 text_span은 원문의 **연속된 부분 문자열**이어야 함. 오타·대소문자·구두점까지 원문 글자 그대로 잘라내며, 원문에서 검색(Ctrl+F)해서 나오지 않는 문자열은 무효. 판단 기준과 검증 방법이 동일함 — annotator는 검색으로, validator는 substring 검사로 같은 것을 확인.

**형식**: text_span은 **항상 세그먼트 배열**로 기록 (대부분 세그먼트 1개). 각 세그먼트는 개별적으로 대원칙(연속 substring)을 충족해야 하며, 기준은 항상 **루트 criterion 원문**.

```
"text_span": ["previously untreated"]              ← 일반 케이스 (세그먼트 1개)
"text_span": ["locally advanced", "Stage III"]     ← 떨어진 조각 (세그먼트 2개)
```

### (1) 개체성 공통 표현(질환명·약물명 등)은 child에 복제하지 않음

- 여러 child가 공유하는 개체 표현은 각 child 조각에 끌어다 붙이지 않고 parent 원문에 남겨둠.
- 복제하면 원문에 없는 문자열 조합이 생겨 검증 불가. "무엇에 대한 것인지"는 후속 단계가 parent 원문을 함께 받아 채움 (→ (4) 전제 참고).
    - 예 (KEYNOTE-671 I1): "previously untreated and pathologically confirmed resectable Stage II, IIIA, or IIIB (N2) NSCLC" (NSCLC가 맨 끝에 한 번)
        - 조각 a = `["previously untreated"]` (NSCLC 안 붙임), 끝 조각에만 "...NSCLC" 남김. `["previously untreated NSCLC"]`처럼 붙이면 ✗.
- 공통 요구사항이 여러 갈래에 걸리는 경우에도 복제하지 않고, **상위 계층의 child_logic(AND)로 표현**한다 (→ 7) KEYNOTE-671 I3 예시). "공통이니까 각 갈래에 넣는다"는 v1.1 방식은 폐지.

### (2) 같은 판정 단위의 떨어진 조각은 이어붙이지 말고 세그먼트로 나눔

- 원문 어순상 떨어져 있는 표현들이 하나의 판정 단위에 속하면(예: 병기 관련 표현), 임의로 이어붙여 한 문자열로 만들지 않고 배열에 세그먼트로 나눠 담음.
    - 예: "locally advanced ... Stage III" → `["locally advanced", "Stage III"]` (`"locally advanced Stage III"`로 합쳐 쓰면 원문에 없는 문자열 → ✗)

### (3) 시점·수치·조건 제약 표현은 적용되는 모든 child에 세그먼트로 추가

- "during the treatment period" 같은 시점 표현이나 "if blocks are not available" 같은 조건 표현은 개체가 아니라 **제약**임. 제약은 그 자체로 조회 단위가 될 수 없으므로 자기가 수식하는 child를 따라감 (다음 단계에서 시간·조건 구조화의 입력이 됨).
- 제약이 여러 child에 걸리면 해당 child 모두의 배열에 동일 세그먼트를 추가함. (각 세그먼트는 연속 substring이므로 대원칙 위반 아님)

    ```
    "No chemotherapy, radiotherapy, or major surgery within 28 days prior to randomization"
    → a: ["chemotherapy", "within 28 days prior to randomization"]
      b: ["radiotherapy", "within 28 days prior to randomization"]
      c: ["major surgery", "within 28 days prior to randomization"]
    ```

- 제약이 일부 child에만 걸리는지 전체에 걸리는지는 표면 위치가 아니라 임상적 의미로 판정 (child_logic 판정과 같은 성격).
- 하위 계층에서는 상위 조각이 이미 제약을 담고 있으면 다시 붙이지 않음 (상속).
- **판별 테스트**: "이 표현 하나만 놓고 CRC가 조회할 수 있는가?" — 조회 불가(제약) → 해당 child마다 세그먼트 추가 / 조회 가능(개체) → 복제 금지, (1) 적용.

### (4) 조각이 그 자체로 완결돼 보이지 않아도 괜찮음

- "previously untreated"나 "pathologically confirmed"만 떼면 무엇에 대한 것인지 사라지지만 괜찮음. "무엇에 대한"인지는 다음 단계에서 disease concept node와 연결하며 채워짐. stage 1의 목적은 정확히 잘라내는 것까지이며 조각을 완성시키는 게 아님.
    - 예 (KEYNOTE-671 I1): 조각 b = `["pathologically confirmed"]` (무엇을 confirm했는지 안 보여도 OK)
- **전제**: 후속 단계(Stage 2~5)가 child 조각과 함께 parent 원문을 입력으로 받아야 함 (파이프라인 prompt에 PARENT_TEXT 필드 포함). 미완결 조각 허용은 이 전제 위에서만 성립.

### (5) nested_exception의 예외 조각(exception span)은 트리거 표현부터

- 예외 조각의 세그먼트는 예외 트리거 표현의 첫 단어부터 해당 절이 끝나는 지점까지 잘라냄.
    - 예: "...syndrome, except vitiligo or resolved childhood asthma/atopy" → `["except vitiligo or resolved childhood asthma/atopy"]` ("except" 포함, 선행 쉼표 제외)
- 예외 조각은 항목별로 더 쪼개지 않음 (child가 아니므로 5) child 구성 규칙 미적용).

### (6) 스팬 경계 규칙

- 시작: 리스트 마커("1)", "a.", "-")와 선행 구두점·공백은 제외하고 첫 단어부터.
- 끝: 마지막 단어까지 포함하고 후행 쉼표·세미콜론·마침표는 제외.
- 구두점·괄호가 스팬 중간에 있으면 원문 그대로 포함.

---

## Cohort_scope 선택

### 1) 정의

- Multi-cohort trial에서 특정 cohort에만 적용되는 기준을 식별하여, downstream agent가 target disease(예: NSCLC)에 해당하는 기준만 선택적으로 쿼리
- 기준 텍스트 자체가 적용 범위를 특정 cohort/part/arm으로 제한하는 경우에만 기록.
- 두 가지 시나리오:

**(1) Basket/multi-cohort trial**

- 서로 다른 tumor type / disease population이 별도 cohort로 분리되며, 해당 선정제외 기준 전체 혹은 일부가 특정 cohort에만 적용되는 경우
    - 예: "In Parts C and F, histological or cytological diagnosis of NSCLC" → `cohort_scope: ["C", "F"]`
    - 예: "evaluable disease ... in Group H" → `cohort_scope: ["H"]`

**(2) 단일 질환 trial 내 arm/part별 조건 분화**

- 동일 질환이라도 arm/part 간 서로 다른 eligibility 조건이 텍스트에 명시된 경우
    - 예: "In Part F1, participants with Stage IV NSCLC without prior systemic therapy may be eligible" → `cohort_scope: ["F1"]`
- **적용하지 않는 경우**: 단순 drug arm vs placebo arm은 동일 eligibility 공유. metadata에서 추론하지 않으므로 cohort_scope를 기록하지 않음(생략).

### 2) granularity: cohort_scope는 분할 근거가 아님

- **split 여부는 query-unit으로 정하고, cohort_scope는 그 위에 부여하는 속성**
- 같은 cohort에 함께 적용되는 조건들을 **cohort가 다르다는 이유로 추가 분할하지 않음.** cohort 그룹(Part) 단위로 묶고, 각 child에 해당되는 cohort_scope를 모두 부여

    ```
    multi-cohort 진단 기준 (Part A 솔리드종양 / Parts B·D MEL / Parts C·F NSCLC)  → cohort 그룹 단위 3 child (각 child에 해당 Part 그룹 cohort_scope 부여)  → 진단명·상태마다 더 쪼개지 않음 (같은 cohort 그룹 내 조건은 묶음)
    ```

### 3) 기록 규칙 (참고)

- Cohort identifier는 프로토콜 원문 표기를 따름 (예: `"A"`, `"F-1"`, `"H"`). 하이픈 유무 등은 해당 trial 원문 그대로.
- Array 형태로 기록 (예: `["B", "D"]`)
- `composite_split`에서는 각 child Criterion 노드에 **개별 cohort_scope**를 부여 (parent가 아닌 child 레벨)
- 🔁 **v1.2**: 모든 cohort에 적용되는 경우 cohort_scope를 기록하지 않음(생략). null·빈 array 표기는 사용하지 않음.

---

## 부록 1: 차이 영역 ↔ 가이드라인 섹션 매핑

| 차이 영역 | 반영 섹션 |
| --- | --- |
| macro child 구성 | 5) split 후 child 구성 규칙 |
| nested_exception 처리 | 1) 정의 (트리거 목록) + Text_span (5) |
| 진단·병기 split 여부 | 6) 진단·병기 입도 (3-way) |
| macro/composite 기준 | 4) split 타입 결정 (header 유무 + 리트머스 테스트) |
| child_logic 표기 | 7) child_logic 표기 |
| 상위 or vs 내부 including | 2) 판단 순서 |
| semantic_category에 따른 split | 3) split 여부 (근거 한정) |
| cohort_scope 분할 입도 | Cohort_scope 2) 분할 입도 |
| (v1.2 신설) 혼합 로직·재귀 분할 | 2) 판단 순서 ④ + 7) 혼합 로직 예시 |
| (v1.2 신설) 외부 문서 위임 | 3) split 여부 |
| (v1.2 신설) 스팬 경계·세그먼트 배열 | Text_span 대원칙·(2)·(6) |

## 부록 2: 판정 요약 (quick reference)

```
[1] 루트 원문 전체를 읽는다
[2] ① 최상위 결합으로 이질 파트 분리 → ② 예외 분리 → ③ split 여부·타입 판정
[3] split이면: 독립 판정 단위 수만큼 child 생성, child_logic 명시(AND/OR)
       각 child text_span = 루트 원문의 연속 세그먼트 배열
       개체 공통 표현은 복제 금지 / 제약 표현은 해당 child마다 추가
[4] ④ 생성된 각 child를 [2]부터 다시 판정 (nested_exception은 main 조각만)
[5] 모든 조각이 none이 되면 종료. none 조각이 leaf = 최종 판정 단위
```

**자주 헷갈리는 지점 3가지**

1. **header인가 판정인가** — header 후보에 하위 항목이 커버하지 않는 pass/fail이 남아 있으면 header가 아니라 별도 child (4)
2. **복제인가 계층인가** — 공통 요구사항은 각 갈래에 복제하지 않고 상위 AND로 표현 (Text_span (1), 7)
3. **child인가 예외 조각인가** — 예외 트리거로 떨어져 나온 부분은 child가 아님. 더 쪼개지 않고, child_logic도 재귀도 없음 (1), (5)
