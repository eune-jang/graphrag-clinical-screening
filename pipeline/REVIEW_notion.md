# LLM Annotation 검수 워크플로우

> 💡 LLM이 자동으로 만든 30개 임상시험(trial) 어노테이션을 사람이 한 번 더 점검하는 절차. 이 문서를 처음 보는 검수자도 따라할 수 있도록 작성됨.

> 🗝️ **용어 안내**
>
> - **Trial (임상시험)**: NCT 번호로 식별되는 임상시험 1건. 한 trial에 수십 개의 선정/제외 기준이 들어있음.
> - **Criterion (기준)**: 임상시험의 선정/제외 기준 1개 (예: "ECOG 0-1", "BCC/SCC 제외").
> - **Cypher / Neo4j**: 그래프 데이터베이스 검색 언어 / 도구. SQL 비슷한데 노드-관계 구조에 최적화.
> - **Validator (자동 검사)**: 컴퓨터가 사전에 돌린 형식 검사. 명백한 결함은 미리 빨간 표시(`_passed=false`).
> - **Issue (문제 유형)**: 자동 검사가 잡은 결함 종류 (예: `value_props_missing` = 필수 숫자 누락).
> - **R/C 코드**: validator 검출 규칙의 short name. **R**1-R4 = relation 검사 (예: R4 `value_props_missing`), **C**1-C3 = criterion 검사 (예: C2 `nested_exception_no_carveout`). 5개 항목 표 + Step 3a 결과 표에 등장.
> - **5개 검수 항목**: 검수자가 점검할 5가지 영역. 모든 결함은 이 5개 중 하나로 분류됨 (아래 표 참조).

---

## 📋 검수 5개 항목 (canonical)

> 💡 검수는 5개 항목으로 구조화되며, 각 항목은 두 layer로 검토합니다.
>
> - **(a) 자동 layer** — `06_validate_annotation.py`의 R/C 규칙이 `_issues` 코드로 surface
> - **(b) 판단 layer** — 사람이 Cypher / JSON에서 직접 확인
>
> Step 3a (fail 있는 trial) / Step 3b (clean trial 전수 검토) 모두 아래 표를 공통 체크리스트로 사용.

| # | 항목 | 커버 영역 | 자동 검출 (issue code) | 판단 포인트 (사람이 봐야 할 것) | 수정 도구 / Cypher |
|---|---|---|---|---|---|
| **①** | **Criterion 분해 구조** | IS_PART_OF span + parent_role + child_logic + duplicate | C1 `orphan_parent_role`, C2 `nested_exception_no_carveout`, C3 `duplicate_entry`, R2 부분 (자녀 span ⊄ 부모) | 자녀 span이 부모를 적절한 단위로 쪼개나 / parent_role 결정이 spec에 맞나 (composite_split vs macro_aggregate vs nested_exception_parent) / child_logic 명시 필요 여부 | `_archive_dedup_nested_exception.py` (C3) / 수동 (C1/C2) / `review_queries.cypher` ① |
| **②** | **Criterion 메타 분류** | semantic_category + type + cohort_scope | (단계 02 enum validator) | enum은 맞지만 의도 부합? (예: "BMI <25"가 demographic vs observation) / multi-cohort trial에서 cohort_scope 적절히 제한됐나 | 수동 수정 / `review_queries.cypher` ② |
| **③** | **Cross-layer relation 식별** | relation_type + target_subtype + 누락 검사 | R1 `subtype_mismatch`, R2 `span_not_in_text` | relation_type 선택이 가장 적합한가 (예: NCT03219268_E16c처럼 `EXCLUDES_STATUS→Biomarker`인지 `REQUIRES_BIOMARKER`+status=negative인지) / 누락된 relation 없는가 (validator 사각지대 — "있는 게 잘못됐는지"만 봄) | `04_correct_relation_type.py` (R1) / 수동 (R2/누락) / `review_queries.cypher` ③ |
| **④** | **Relation 속성 완전성** | HAS_VALUE/HAS_TEMPORAL 필수 키 + alternative_constraint + exception_qualifier + biomarker_details | R3 `temporal_props_missing`, R4 `value_props_missing` | property 값이 의미적으로 맞나 (anchor_type 분류 / unit 일관 / alternative_constraint 누락 / biomarker_details 완전성) | `03_recover_has_value.py` (regex), `05_reextract_constraints.py` (LLM) / `review_queries.cypher` ④ |
| **⑤** | **Concept 정규화** | preferred_name 일관성 + hub 식별 + cross-trial 중복 | (없음 — 전수 사람 검토) | 같은 개념이 trial마다 다른 preferred_name로 등록 안 됐나 ("ECOG performance status" vs "Eastern Cooperative Oncology Group...") / Layer 3 dedup 후보 hub 식별 | 수동 수정 / `review_queries.cypher` ⑤ (hub analysis) |

---

## 🔄 표준 검수 사이클

> ⚠️ **본 사이클은 두 부분으로 나뉨**
>
> - **자동 layer** (Step 1) — 스크립트 실행. 현재 30 trial은 이미 완료된 상태.
> - **사람 layer** (Step 2-5) — Neo4j Browser + 판단. 검수자가 직접 수행.
>
> 이미 validated + ingest된 상태에서 새로 검수만 시작하면 Step 1을 건너뜀.

<details>
<summary><strong>Step 1. Annotation 준비 (자동)</strong></summary>

```bash
# 새 annotation을 받았을 때만. 기존 30 trial 상태에서는 skip.
python pipeline/06_validate_annotation.py               # _validation 부착
python pipeline/07_neo4j_ingest.py                      # Neo4j 적재
```

</details>

<details>
<summary><strong>Step 2. 어떤 임상시험부터 검수할지 정하기</strong></summary>

> 🌐 **Neo4j Browser 접속 방법**
>
> - **URL**: `http://localhost:7474` (Neo4j Desktop이 켜져 있어야 함)
> - **계정**: `neo4j` / (DB 생성 시 설정한 password — 본 프로젝트는 `.env`의 `NEO4J_PASSWORD`)
> - **사용**: 로그인 후 상단 명령창에 cypher 붙여넣고 ▶ 실행 (Ctrl+Enter)
> - **연결 실패 시**: Neo4j Desktop에서 인스턴스가 ▶ Active 상태인지 확인

아래 명령(Cypher 쿼리)을 그대로 붙여넣어 실행합니다. 30개 trial 전체의 "자동 검사에서 의심 표시된 항목 수"가 한눈에 나옵니다.

```cypher
// 0.1  Total per trial, with failure counts
MATCH (t:Trial)
OPTIONAL MATCH (t)--(c:Criterion)
WITH t, count(DISTINCT c) AS n_crit,
     sum(CASE WHEN c._passed = false THEN 1 ELSE 0 END) AS crit_fail
OPTIONAL MATCH (t)--(:Criterion)-[r]->(:ConceptRef)
RETURN t.nct_id, n_crit, crit_fail,
       count(DISTINCT r) AS n_rel,
       sum(CASE WHEN r._passed = false THEN 1 ELSE 0 END) AS rel_fail
ORDER BY rel_fail DESC;
```

**결과 표 의미:**

- `n_crit` — 이 trial의 기준 개수
- `crit_fail` — 기준 단위에서 자동 검사가 의심 표시한 수
- `n_rel` — 관계(relation) 개수 (한 기준당 평균 1~3개)
- `rel_fail` — 관계 단위에서 의심 표시된 수

> 🎯 **우선 검수 대상**: `rel_fail`이 큰 trial부터.

> 🔀 **이 trial이 어느 갈래로 갈지 결정**
>
> - `rel_fail > 0` 또는 `crit_fail > 0` → **Step 3a** (자동 검사가 잡은 항목 검토)
> - `rel_fail = 0` 그리고 `crit_fail = 0` → **Step 3b** (사람이 직접 훑어보기)

</details>

<details>
<summary><strong>Step 3. 한 임상시험 자세히 보기</strong></summary>

위에서 정한 갈래(3a 또는 3b)로 진행. 두 갈래 검수 방식이 다릅니다.

---

### 🔴 Step 3a — 자동 검사가 의심 표시한 trial

검수 대상 trial을 정하고 (예: `NCT03219268` — 위에서 rel_fail=7 이었던 trial):

```cypher
// 0.3  All failing relations in this trial
:param nct => 'NCT03219268';

MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE r._passed = false
RETURN c.criterion_id, type(r), cr.subtype, cr.preferred_name,
       r.target_text_span AS span, r._issues AS issues
ORDER BY c.criterion_id;
```

> 📊 **실제 결과 예시** (NCT03219268 — 7 rows)
>
> | criterion_id | rel_type | issue | 매핑 항목 |
> |---|---|---|---|
> | E14a | HAS_VALUE | `value_props_missing` | ④ 속성 |
> | E14b | HAS_VALUE | `value_props_missing` | ④ 속성 |
> | E16a | INCLUDES_EXCEPTION | `span_not_in_text` | ① / ③ |
> | E16c | EXCLUDES_STATUS | `subtype_mismatch:EXCLUDES_STATUS->Biomarker` (×3) | ③ Cross-layer |
> | I2 | HAS_VALUE | `value_props_missing` | ④ 속성 |
>
> **분포**: ④ 속성 3건 / ③ Cross-layer 3건 / ① IS_PART_OF 1건

**Q0.3b** — `crit_fail > 0`이면 추가 실행. Q0.3은 relation 단위만 보여줌. 기준(criterion) 단위 결함은 따로 조회:

```cypher
// Q0.3b  Criterion-level fail — validator C1/C2/C3
//   C1 orphan_parent_role         (parent_role 설정인데 자녀 없음)
//   C2 nested_exception_no_carveout (carve-out 누락)
//   C3 duplicate_entry             (criterion_id 중복 — 현재 30 trial은 0건)
MATCH (c:Criterion {trial_id: $nct})
WHERE c._passed = false
RETURN c.criterion_id, coalesce(c.parent_role,'') AS parent_role,
       c._issues AS issues, left(c.text, 140) AS text;
```

**검수자가 결과 표의 각 행에서 할 일 (Q0.3 / Q0.3b 모두 동일):**

1. **문제 유형 확인** — `issues` 컬럼의 코드를 보고, 문서 상단 5개 항목 중 어느 영역의 결함인지 표시 (예: `value_props_missing` → ④ 속성, `nested_exception_no_carveout` → ① 분해 구조)
2. **처리 방향 결정** — 5개 항목 표의 "수정 도구" 컬럼에서 추천 처리 (자동 스크립트 또는 수동 수정) 확인
3. **맥락 확인** — 애매하면 원본 JSON 파일 (`pipeline/output/{nct}_annotation.json`)을 열어 해당 기준의 전체 텍스트와 다른 관계도 함께 봄

---

### 🟢 Step 3b — 자동 검사 통과한 trial (사람이 직접 훑어보기)

> Step 2 결과에서 `rel_fail = 0` & `crit_fail = 0`인 trial은 자동 검사 통과 상태. 그러나 자동 검사는 **"있는 것이 잘못됐는지"만 확인**하고 "있어야 할 것이 빠졌는지"는 못 봅니다. 사람이 기준 전체를 훑으며 누락이나 의미적 어색함을 찾는 단계.

**Q0.4** — 기준 전체 목록 (47개를 한 화면에 보기):

```cypher
// Q0.4  Trial overview — 모든 기준의 메타 정보
:param nct => 'NCT03425643';

MATCH (t:Trial {nct_id: $nct})--(c:Criterion)
RETURN c.criterion_id, c.type, c.semantic_category,
       coalesce(c.parent_role, '') AS parent_role,
       coalesce(c.child_logic, '') AS child_logic,
       coalesce(c.parent_criterion_id, '') AS parent_id,
       left(c.text, 80) AS text
ORDER BY c.criterion_id;
```

**Q0.5** — 기준 1개의 모든 관계 자세히 보기 (의심되는 기준에 사용):

```cypher
// Q0.5  단일 기준 deep-dive
// 예: NCT03425643_E11 ("any condition, therapy, or laboratory abnormality...")
//     — 3개 관계로 다중 entity 추출되는 모범 케이스
MATCH (c:Criterion {criterion_id: 'NCT03425643_E11'})-[r]->(cr:ConceptRef)
RETURN type(r) AS rel_type,
       cr.subtype AS subtype,
       cr.preferred_name AS target,
       r.target_text_span AS span,
       properties(r) AS props;
```

> 💡 `parent_role=composite_split` 또는 `macro_aggregate`로 표시된 기준(예: `NCT03425643_I4`)을 Q0.5로 보면 관계가 0건입니다. 이는 정상 — 부모 기준은 자녀로 분해되고, 관계는 자녀 기준(`I4a`, `I4b`)에 붙어있음. 자녀 ID로 다시 조회하세요.

**Q0.6** — Trial 전체의 관계 종류별 개수 (비정상 분포 감지용):

```cypher
// Q0.6  Trial 전체 relation type 분포
MATCH (:Criterion {trial_id: $nct})-[r]->(:ConceptRef)
RETURN type(r) AS rel_type, count(*) AS n
ORDER BY n DESC;
```

> 💡 **의심 발견 휴리스틱 5종** — Q0.4의 47줄 결과를 훑으면서 아래 5가지 패턴에 부합하면 멈추고 Q0.5로 자세히 봅니다.
>
> 1. **여러 자녀로 나뉜 부모** (`parent_role=composite_split` 또는 `macro_aggregate`): 자녀 분해가 부모의 의미를 합리적으로 쪼개는지. 자녀 텍스트가 부모 텍스트의 부분이어야 자연스러움.
> 2. **관계가 1개인데 텍스트에 "and"/"or"가 있음** (n_rel=1): "X and Y"로 두 entity가 있어야 하는데 1개로 합쳐졌을 가능성 — 누락 의심.
> 3. **관계가 3개 이상인 기준** (n_rel ≥ 3): 다중 entity 추출이 잘 됐는지 — 각 관계가 텍스트의 어느 부분을 대표하는지 확인.
> 4. **HAS_VALUE 또는 HAS_TEMPORAL의 value가 0**: 텍스트에 명시적으로 "0"이 안 보이면 의심. "기간이 미정"이거나 "범위의 하한"만 추출된 placeholder일 가능성.
> 5. **Q0.6 결과에서 INCLUDES_EXCEPTION이 0건**: spec에선 carve-out 패턴이 있어야 할 수도 있음. 텍스트에서 "except", "unless" 같은 단어가 있는 기준을 따로 검색.

> ℹ️ 위 휴리스틱 외 일반 판단 항목 list는 문서 상단 **검수 5개 항목 (canonical)** 표의 "판단 포인트" 컬럼을 참조. 각 기준마다 ①~⑤ 5가지 영역을 점검.

기존에 자동화로 못 잡는 의미적 결함의 예시는 아래 **"사람만 잡을 수 있는" 항목** 섹션 참조.

</details>

<details>
<summary><strong>Step 4. 자동 검사 사각지대 추가 점검 (필수)</strong></summary>

Step 3a/3b로는 못 잡는 영역 — 자동 검사가 그냥 통과시키지만 사람이 직접 봐야 하는 케이스. 가장 대표적인 게 **예외(INCLUDES_EXCEPTION)에 type 분류가 빠진 경우**.

**Q4.6** — 예외 관계의 type/qualifier 확인:

```cypher
// Q4.6  INCLUDES_EXCEPTION의 exception_type 채움 상태
MATCH (c:Criterion {trial_id: $nct})-[r:INCLUDES_EXCEPTION]->(cr:ConceptRef)
RETURN c.criterion_id, cr.preferred_name AS target,
       r.exception_type AS exc_type,
       r.exception_qualifier AS exc_qual;
```

결과에서 **`exc_type`이 비어있는(`None`/`null`) 행**을 찾습니다. 이건 자동 검사가 잡지 못하는 사각지대로, 사람이 텍스트를 보고 적절한 type (`condition_carveout` / `procedure_carveout` / `drug_carveout` / `status_carveout`)을 채워야 합니다.

> 💡 NCT03219268 사례: 9개 예외 중 3개가 `exc_type=None`. 자동 도구로는 발견 불가.

</details>

<details>
<summary><strong>Step 5. 결과 기록</strong></summary>

발견 사항을 trial별 **xlsx finding log**로 기록.

### 📝 xlsx 표준 양식 (8 columns)

| 컬럼 | 값 | 출처 |
|---|---|---|
| `criterion_id` | NCT_xxx_yyy | Cypher 결과 |
| `step` | 3a / 3b / 4 | 검수자 분류 |
| `source_query` | Q0.3 / Q0.5 / Q0.6 / Q4.5 / Q4.6 / Q5.1 / manual | 어느 쿼리에서 발견 |
| `항목` | ① ② ③ ④ ⑤ | 상단 5개 항목 표 매핑 |
| `description` | Cypher가 surface한 사실 (text 발췌 포함) | 객관 |
| `reviewer_comment` | [발견] + [근거] + [의문점] | 주관 판단 |
| `suggested_action` | **삭제 / 수정 / 추가 / 보류 / 재추출 / 검토 / 정규화** | 표준 동사 7종 중 1개 |
| `date` | YYYY-MM-DD | 검수일 |

### ✅ 한 trial 검수 완료 체크리스트

- [ ] Step 2 Q0.1 → trial 위치 확인 (rel_fail 분포)
- [ ] Step 3a (fail 있으면): Q0.3 모든 행 처리 + xlsx 기록
- [ ] Step 3b (clean): Q0.4 + 휴리스틱 5종 적용 + Q0.5 deep-dive
- [ ] Step 4: Q4.6 INCLUDES_EXCEPTION qualifier 검토 (validator 사각지대)
- [ ] 모든 finding이 xlsx에 기록 (criterion_id, action, comment 포함)

**마지막 trial 검수 후 1회만**:

- [ ] Q5.1 Hub query → cross-trial preferred_name 정규화 후보 식별

> 🎚️ **자동화 후보 승격 기준**: 같은 패턴이 ≥3 trial에서 발견되면 `06_validate_annotation.py`의 새 detection rule 후보. xlsx의 `description` 컬럼을 grep하여 빈도 확인.

</details>

---

## 🚶 Worked Example — NCT03219268 시나리오 (10 findings, ~20분)

> 처음 검수하는 사람이 그대로 따라할 수 있는 narrative.

<details>
<summary><strong>Phase 1 — Step 2 트리아지</strong></summary>

```cypher
// Q0.1 실행
```

결과 보고 판단: **"NCT03219268이 rel_fail=7로 최우선 검수 대상"** → Step 3a 진입.

</details>

<details>
<summary><strong>Phase 2 — Step 3a 진입 (Q0.3 → 7 rows)</strong></summary>

```cypher
:param nct => 'NCT03219268';
// Q0.3 실행 → 7 rows
```

각 행에 대해:

### 행 1: `E14a` HAS_VALUE missing operator/value

- issue 코드 → 매핑 **④**
- Q0.5로 E14a deep-dive 실행:

  ```cypher
  MATCH (c:Criterion {criterion_id: 'NCT03219268_E14a'})-[r]->(cr:ConceptRef)
  RETURN type(r), cr.preferred_name, properties(r)
  ```

- **발견**: HAS_TEMPORAL(within 7 days, anchor=initiation) + EXCLUDES_CONDITION(viral infection)이 이미 의미를 담음. HAS_VALUE는 "Requires parenteral treatment"에 부착됐지만 텍스트에 numeric 없음.
- **판단**: HAS_VALUE 부적절 부착.
- **xlsx 1행 추가**:

  ```
  E14a | 3a | Q0.3 | ④ | HAS_VALUE missing op/value | 텍스트에 numeric 없음 | 삭제
  ```

### 행 2: `E14b`

E14a와 동일 패턴 (bacterial 버전) → 동일 처리, xlsx 1행 추가.

### 행 3: `E16a` INCLUDES_EXCEPTION span_not_in_text

- 매핑 **①**
- Q0.5로 E16a deep-dive → 정상 INCLUDES_EXCEPTION(Hepatocellular carcinoma)이 별도로 있음. 이 행은 span이 텍스트 범위 벗어남(hallucination).
- xlsx 1행: action=**삭제**

### 행 4-6: `E16c × 3` EXCLUDES_STATUS → Biomarker (Pattern D)

- 매핑 **③**
- 모두 hepatitis viral marker (HBsAg, HBV core, HCV RNA)
- 판단: REQUIRES_BIOMARKER + status=negative로 의미 변환 (EXCLUDES_BIOMARKER가 schema에 없음)
- xlsx 3행: action=**수정**

### 행 7: `I2` HAS_VALUE missing

- 매핑 **④**
- 텍스트: "ECOG performance status of 0 or 1" — range
- 판단: operator=≤, value=1 입력 또는 alternative_constraint
- xlsx 1행: action=**수동**

</details>

<details>
<summary><strong>Phase 3 — Step 4 항목별 detail 쿼리</strong></summary>

Q4.6 (INCLUDES_EXCEPTION qualifier) 실행:

```cypher
MATCH (c:Criterion {trial_id:'NCT03219268'})-[r:INCLUDES_EXCEPTION]->(cr:ConceptRef)
RETURN c.criterion_id, cr.preferred_name, r.exception_type, r.exception_qualifier;
```

**발견**: 9건 중 3건이 `exception_type=None` — **validator/시뮬레이터 사각지대**.

xlsx 3행 추가 (I1c, E3, E16a) — action=**수동** (exception_type 입력).

</details>

<details>
<summary><strong>Phase 4 — 완료 체크</strong></summary>

✅ 위 체크리스트 모두 ✓.

**최종**: xlsx 10 findings (④×6 / ③×3 / ①×1).

### 4 reference trial 검수 후 cross-trial wrap

Q5.1 Hub query 1번 실행 → "Non-small cell lung cancer" 16 trial 등장 같은 패턴 확인 → 정규화 후보 별도 sheet에 기록.

</details>

---

## 🔧 Validator issue code → 5개 항목 매핑 (참고용)

> 문서 상단 표에 통합된 내용이지만, **`_validation.issues` 필드에서 본 코드를 빠르게 찾고 싶을 때** 쓰는 reverse-lookup.

| Code | 위치 | 매핑된 검수 항목 |
|---|---|---|
| `orphan_parent_role:X` | Criterion | ① Criterion 분해 구조 |
| `nested_exception_no_carveout` | Criterion | ① Criterion 분해 구조 |
| `duplicate_entry` | Criterion | ① Criterion 분해 구조 |
| `subtype_mismatch:X->Y` | Relation | ③ Cross-layer relation 식별 |
| `span_not_in_text` | Relation | ① (IS_PART_OF 자녀일 때) / ③ (일반 cross-layer) |
| `temporal_props_missing:k1,k2,...` | Relation | ④ Relation 속성 완전성 |
| `value_props_missing:k1,k2,...` | Relation | ④ Relation 속성 완전성 |

---

## 🗂️ 검수 데이터의 두 가지 진입점

| 도구 | 강점 | 약점 |
|---|---|---|
| **Neo4j Browser** + `.cypher` | 그래프 traversal, hub 분석, cross-trial 집계 | Property 직접 수정 불가 |
| **원본 JSON 파일** (`pipeline/output/NCT*_annotation.json`) | Property 직접 수정/주석, git diff로 변경 추적 | 집계/조인 어려움 |

> 🔁 검수자는 양쪽을 함께 씁니다 — Neo4j에서 surface된 의심 케이스를 JSON에서 수정.

---

## 🧠 "사람만 잡을 수 있는" 항목 (자동화 불가)

> 자동 검출이 어려운 검수 관점

- **Span의 의미적 적절성**: "non-infectious pneumonitis"를 span으로 잡았는데 spec상 더 좁은 표현이 정답일 수 있음
- **preferred_name 정규화**: "ECOG performance status"와 "Eastern Cooperative Oncology Group performance status"가 같은 개념인지
- **drug class vs specific drug**: "platinum-containing regimen" → drug class? 특정 drug?
- **Implicit context**: "in past 5 years"의 5년 기준이 randomization인지 informed consent인지 (anchor 추론)
- **Negation scope**: "no significant history of..." — what's the scope of "no"?

> 📝 이런 케이스는 검수자 메모로 남기고, 패턴이 반복되면 spec/guideline에 반영.

---

## ➕ 새 trial 추가 시 동일 사이클 재현

```bash
# 1. 새 trial annotation 생성
python pipeline/02_llm_annotation.py --trial NCT_NEW

# 2. cleanup (필요시 — 새 annotation은 03/05만 주로 유용. 04는 Prompt 2 분류 오류 발생 시)
python pipeline/03_recover_has_value.py --trial NCT_NEW      # regex post-hoc
python pipeline/04_correct_relation_type.py --trial NCT_NEW  # subtype↔relation 정정
python pipeline/05_reextract_constraints.py --trial NCT_NEW  # LLM Prompt 4 (비용 발생)

# 3. validate + ingest
python pipeline/06_validate_annotation.py --trial NCT_NEW
python pipeline/07_neo4j_ingest.py --trial NCT_NEW --reset

# 4. 검수 — review_queries.cypher 사용 with :param nct => 'NCT_NEW'
```

---

## 🔗 관련 문서

- [`PIPELINE.md`](PIPELINE.md) — 스크립트 인벤토리 + 데이터 흐름
- [`review_queries.cypher`](review_queries.cypher) — Neo4j Browser용 쿼리 모음
- [`schema/ontology_full_specification_unified_v1_2_2_ko.md`](schema/ontology_full_specification_unified_v1_2_2_ko.md) — 4-layer ontology 전체 스펙
- [`schema/annotation_guideline_v0_2_stage1 (1).md`](<schema/annotation_guideline_v0_2_stage1 (1).md>) — annotation guideline (현재 stage 1)
