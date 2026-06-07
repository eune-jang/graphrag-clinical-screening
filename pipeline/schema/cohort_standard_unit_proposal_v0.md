# Cohort 표준 단위 정의 (제안 초안 v0)

> ## ⏸️ 상태: **DEFERRED (2026-06-07 결정)** — 현 시점 미채택.
> **결정**: 지금은 cohort_scope를 **정규화하지 않고 표면형(surface form) 그대로** 사용한다.
> **이유**: 정규화를 요구하는 소비자가 현재 0개로 확인됨 —
>   - neo4j ingest는 cohort_scope를 Criterion 노드의 **납작한 문자열 property**로만 저장(Cohort 노드/관계 없음, `07_neo4j_ingest.py:150`),
>   - screening/retrieval/agent 레이어(`src/graphrag_screening/*`)는 **전부 0줄 stub**(미구현),
>   - IAA는 표면형 문자열 exact-set 비교로 충분,
>   - v1.2.2 스펙도 cohort_scope 값이 registry 키여야 한다고 규정하지 않음.
>   - annotation 화면에선 프로토콜 표면형 그대로가 가장 덜 헷갈림(crosswalk·어휘 불일치 함정 회피).
> **재검토 트리거**: cohort-aware 자동 필터링을 하는 screening/retrieval 소비자가 실제로 생길 때.
>   그때는 annotation을 건드리지 말고 **다운스트림 query-시점 resolution 레이어**로 1회 구현.
>
> 아래 내용은 그 재검토 시점을 위한 분석 보존용이며, 현재 파이프라인에는 적용하지 않음.
> ---
> 근거: 30개 trial annotation 출력 전수 조사 (`pipeline/output/*_annotation.json`).
> (당초) 해결하려던 문제: v1.2.2는 `cohort_scope`/`cohorts`만 정의하고 **"cohort가 어떤 단위인가"를 규정하지 않음** → 실데이터에서 arm/dose/Part/disease/phase 5단위가 난립하고 registry↔scope 정합성이 깨짐(5/15 trial).

---

## 1. 실데이터가 말하는 것 (요약)

`Trial.cohorts` registry는 전부 ClinicalTrials.gov **arms/interventions**에서 유래. 실제 단위 분포:

| 단위 | trial 수 | 성격 |
|---|---|---|
| treatment arm / regimen | ~13 | 약물 조합, drug vs placebo |
| dose level (mg/kg) | 2 | arm의 하위 분할 |
| Part / phase (escalation·expansion) | 3 | 프로토콜 구조 |
| disease / tumor type (basket) | 2 | 환자 모집단 축 |
| MIXED (한 문자열에 압축) | 3 | KEYNOTE-001 등 |

핵심 관찰:
- **모집단이 실제로 배정되는 원자 단위 = "프로토콜 arm/cohort" (registry 1개 항목).**
- 그러나 criterion이 gating하는 단위는 종종 더 **거친 축**(예: "Part F", "NSCLC 환자")이며, 이는 원자 cohort들의 **합집합**이다.
- KEYNOTE-001은 한 registry 문자열에 `disease × dose × part` 3축을 압축(`"NSCLC: Pembrolizumab 2 mg/kg Q3W (Part F)"`)해 정규화가 불가능했다.

---

## 2. 표준 단위 정의

### 2.1 원자 단위(Atomic Cohort)

> **Cohort = 환자가 배정되는 프로토콜 상의 atomic enrollment group.** 1개 = `Trial.cohorts` registry의 1개 항목 ≈ CT.gov arm/intervention.

- `cohort_scope`가 가리키는 값은 **반드시 이 registry의 canonical `cohort_id` 중 하나**여야 한다 (referential integrity).
- 자유 텍스트("Part F", "F") 금지 — registry에 정의되지 않은 값은 무효.

### 2.2 Canonical cohort_id 정규화 규칙

registry의 원본 문자열(`label`)은 보존하되, 매칭/비교용 `cohort_id`를 별도로 둔다:

1. NFKC 정규화 → 소문자 → 공백/슬래시 `_` → 영숫자·`_`·`-` 외 제거
2. 안정적(immutable)·trial 내 유일
3. 예: `"SG 10 mg/kg"` → `sg_10_mg_kg`, `"Part B: AZD8186 monotherapy"` → `part_b`

### 2.3 구조화 축(Structured Axes) — MIXED 문자열 분해

압축 문자열을 풀기 위해 각 cohort에 **선택적 축 메타데이터**를 부여한다. 이게 거친 gating의 결정적 해법:

| 축 | 의미 | 예 (KEYNOTE-001) |
|---|---|---|
| `part` | 프로토콜 Part/단계 라벨 | `"A"`, `"F"`, `"F-1"` |
| `disease` | 종양/모집단 유형 (basket) | `"NSCLC"`, `"MEL"`, `"solid"` |
| `regimen` | 약물 조합 | `"pembrolizumab"` |
| `dose` | 용량/스케줄 | `"2mg/kg Q3W"` |

원자 cohort는 이 축들의 **구체적 조합 하나**. 거친 gating은 축 값으로 표현하고 **원자 id 집합으로 전개(expand)**한다.

### 2.4 cohort_scope 의미론 + 전개 규칙

- criterion의 `cohort_scope` = 그 criterion이 적용되는 **원자 cohort_id의 (flat) 집합**.
- 거친 의도("Part F에 적용")는 작성 시 `part="F"`로 두되, **저장 형태는 `{part==F}에 해당하는 모든 cohort_id의 합집합}`으로 전개**한다.
- 이렇게 하면 `cohort_scope`는 항상 flat한 canonical id 집합 → **IAA exact-set 비교와 neo4j 노드 연결이 둘 다 성립**.
- 비어있음/생략 = 모든 cohort에 적용(기존 v1.2.2 §159–162 규칙 유지).

---

## 3. 워크드 예시 (실 trial)

### 3.1 KEYNOTE-001 (NCT01295827) — MIXED 분해

registry(발췌)를 축으로 분해:

| cohort_id | part | disease | dose |
|---|---|---|---|
| `solid_pembro_1mpk_q2w_part_a` | A | solid | 1mg/kg Q2W |
| `mel_pembro_2mpk_q3w_part_bd` | B,D | MEL | 2mg/kg Q3W |
| `nsclc_pembro_2mpk_q3w_part_f` | F | NSCLC | 2mg/kg Q3W |
| `nsclc_pembro_10mpk_q3w_part_cf` | C,F | NSCLC | 10mg/kg Q3W |
| … (15개) | | | |

**I1의 child별 cohort_scope (전개 후)** — 기존엔 전부 `null`이라 유실됐던 정보:

| child | text 근거 | gate | 전개된 cohort_scope |
|---|---|---|---|
| I1a | "In Part A" | part∈{A} | `{part_a 계열 cohort_id들}` |
| I1b | "In Parts B and D" | part∈{B,D} | `{part_b*, part_d*}` |
| I1c | "In Parts C and F" | part∈{C,F} | `{part_c*, part_f*}` |
| I1d | "In Part F1" | part∈{F-1} | `{part_f1*}` |

→ 한 criterion의 child들이 서로 다른 cohort에 속하는 케이스가 **정확히 표현됨**.
→ 기존 I3 `["B","C","D","F"]`(짧은 코드)와 I4(긴 문자열)의 불일치도, 둘 다 `part` 축으로 전개하면 동일 어휘로 정합.

### 3.2 NCT01884285 (AZD8186) — 이미 Part 단위, 오류 교정

원자 cohort = `part_a, part_b, part_c1, part_c2, part_d1, part_d2`.
- 기존 I9c "Part C (all patients)"가 부모와 같은 `[A,B,D1]`로 **잘못** 부여됨 → 표준 적용 시 `part="C"` → `{part_c1, part_c2}`로 교정.

### 3.3 NCT01631552 (dose-level) — 원자=dose arm

`sg_8_mg_kg, sg_10_mg_kg, sg_12_mg_kg, sg_18_mg_kg`. 이미 원자적·정합. 추가 축 불필요(dose가 곧 arm).

### 3.4 NCT00730639 (disease basket) — 원자=disease cohort

`melanoma, rcc, mcrpc, nsclc, crc`. `disease` 축이 곧 원자 단위. mCRPC criterion → `cohort_scope=["mcrpc"]`.

### 3.5 NCT03425643 (drug vs placebo) — 단순 arm

`nac_pembro, nac_placebo`. 표준 그대로 적용, 변경 없음.

---

## 4. v1.2.2 온톨로지와의 정합

기존 스키마를 **깨지 않고 제약·확장만** 추가:

- `Trial.cohorts: array of {id, description}` → `{cohort_id, label, group_type, part?, disease?, regimen?, dose?}`로 **필드 추가**(기존 id/description 호환).
- `Criterion.cohort_scope: array of strings` → **값은 `cohort_id`로 제한**(자유 텍스트 금지). 타입 불변.
- child(sub-criterion)는 이미 별개 Criterion 노드이므로 per-child cohort_scope는 v1.2.2가 이미 허용(별도 변경 불필요).

---

## 5. 후속 작업 (이 정의가 확정되면)

1. annotation_guideline §4.1.5 / §6.2.6: "cohort = 원자 enrollment group, scope는 cohort_id 집합, 거친 gate는 축으로 전개" 규칙으로 개정.
2. cohort registry 빌더: CT.gov arms → canonical id + 축 분해(특히 KEYNOTE-001류 압축 문자열).
3. production prompt_1: cohort_scope를 자유 생성하지 말고 **제공된 registry에서 선택**하도록 변경 + 거친 gate 전개.
4. mismatch 5개 trial(NCT01295827, 02857270, 03219268, 02279433, 03780517) scope 값 교정.
5. (선택) per-child cohort_scope 채택 여부 — 이 표준 위에서 별도 결정.

---

## 6. 미해결 결정 사항 (검토 필요)

- **A. 원자 단위를 dose-level까지 내릴지, arm/regimen에서 멈출지.** KEYNOTE-001은 같은 part·disease 안에 dose arm이 여럿(2 vs 10 mg/kg). criterion이 dose를 구분하는 경우가 거의 없다면 dose는 축 메타로만 두고 원자 단위를 (part×disease)로 잡는 게 실용적일 수 있음.
- **B. cohort_scope 저장 형태:** 전개된 원자 id 집합(현 제안) vs 축 표현(`{part:"F"}`) 보존. 전자는 IAA/graph에 유리, 후자는 작성 의도 보존·재전개 가능. 하이브리드(둘 다 저장) 가능.
- **C. 거친 gate 전개 시점:** 어노테이션 입력 시 vs 다운스트림 transform 시.
