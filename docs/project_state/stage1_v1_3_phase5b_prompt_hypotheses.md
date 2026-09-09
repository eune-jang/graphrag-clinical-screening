# Stage 1 v1.3 — Phase 5B 프롬프트 가설

> **작성일**: 2026-09-08 · **문구 확정**: 2026-09-09 (pre-execution correction) · **성격**: 사전 등록된 **가설**이다.
> **P0(v1.3.1)를 수정하지 않았다. canonical core를 수정하지 않았다. v1.3.2를 만들지 않았다.**
> 후보는 P0를 건드리지 않고 `candidates/`에 별도 파일로 만들었다.
> 근거: [`../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md`](../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md)

두 가설 모두 **비규범(non-normative) 프롬프트 명확화 후보**다. canonical 의미를 바꾸지 않는다.

**2026-09-09 교정에서 문구가 확정되었고 두 후보 프롬프트가 생성되었다.** 아래 각 가설의
**확정 문구** 절을 보라. 대안 표현은 선택 근거를 남기기 위해 그대로 둔다.

```
P0    pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt            (변경 없음)
P-X2  pipeline/prompts/development/stage1/candidates/candidate_x2_from_v1_3_1.txt
P-PR  pipeline/prompts/development/stage1/candidates/candidate_pr_from_v1_3_1.txt
P-COMBINED                                                                    미생성
```

**명명 규칙**: 검증 전 후보에 `v1_3_2a` 같은 릴리스 버전을 붙이지 않는다.
`candidate_<가설>_from_<기반 버전>` 형식의 provenance 이름을 쓰고, **다음 v1.3.x 버전 번호는
사람 검토를 통과한 후보에만** 부여한다.

**두 가설은 실험적으로 격리한다** — 한 후보에 둘 다 넣으면 개선의 원인을 귀속할 수 없다.
5B-0(P0 전체 baseline) → 5B-1(P-X2) / 5B-2(P-PR) → 사람 검토 → 5B-3(combined).
설계: [`../../experiments/stage1_v13/phase5b_dev/SCORING_PLAN.md`](../../experiments/stage1_v13/phase5b_dev/SCORING_PLAN.md)

---

## H-X2-1 — 공유 qualifier 복사 누락

### 관측 (S04, 1건)

```
"Women who are pregnant or breastfeeding at the time of screening."

[a] ["Women who are pregnant"]                          ← qualifier 없음
[b] ["breastfeeding at the time of screening"]
notes: "The phrase 'at the time of screening' applies to both coordinated conditions by shared context."
```

모델이 **두 조건 모두에 적용된다고 스스로 서술**하고도 자식 a에 넣지 않았다.
런타임 손실이 아니고(런타임은 `text_span` 내용을 만들지도 바꾸지도 않는다),
능력 문제도 아니다(같은 실행의 S05·S12에서 동일 유형을 정확히 복사했다).

### 프롬프트 원문

```
X2. SHARED EXPRESSIONS / QUALIFIER SCOPE

- Do not duplicate a shared clinical entity solely to make children grammatical.
- Repeat a shared dependent qualifier in every child it semantically modifies.
- A child may be grammatically incomplete if ROOT/PARENT context supplies shared meaning.
```

canonical 원문도 같은 구조다(`Copy a shared dependent qualifier … into every child it
semantically modifies.` / `A child may be grammatically incomplete if root/parent context is
available downstream.`).

### 가설

> **두 번째 불릿(복사 의무)과 세 번째 불릿(문법적 불완전 허용)이 나란히 놓여 있어,
> 세 번째가 두 번째의 예외로 읽힐 수 있다.**
> 세 번째 불릿은 *문법적* 불완전성 허용이지 *의미적으로 수식하는 qualifier의 생략 허가*가 아니다.
> 두 절의 관계를 명시하면 누락이 줄어들 것이다.

### ✅ 확정 문구 — 후보 A 방향 (관계 명시), 축약본

`candidate_x2_from_v1_3_1.txt`에 X2 세 번째 불릿 **바로 뒤** 한 항목으로 삽입됐다.
P0 대비 **이 삽입 외 변경 없음**(diff 검증 완료).

```
- The grammatical-incompleteness allowance does not override the shared-qualifier rule
  above. If a dependent qualifier semantically modifies multiple children, include its
  exact source span in every affected child.
```

canonical에 없는 의무를 새로 만들지 않는다 — 기존 두 문장의 **관계만** 분명히 한다.

### (기록) 초안 후보 A — 더 긴 형태

```
- A child may be grammatically incomplete if ROOT/PARENT context supplies shared meaning.
  This does NOT permit omitting a shared dependent qualifier that X2 requires: if a
  temporal/numeric/conditional/severity qualifier semantically modifies more than one
  child, its exact source span must appear in every child it modifies.
```

### (기록) 초안 후보 B — 자기 점검으로 이동

X2 본문은 그대로 두고 SILENT PRE-OUTPUT CHECK에 한 줄 추가:

```
18. If I concluded that a qualifier applies to more than one child, I copied its exact
    source span into every one of them.
```

B의 장점: 규칙 본문을 건드리지 않아 규범 해석 변경 위험이 더 낮다.
B의 단점: 점검 목록이 이미 17항목이라 희석될 수 있다.

**A 방향을 택한 이유**: canonical X2 자체가 이미 명확하고(복사 의무 + 별도의 문법 허용),
문제는 **두 문장의 관계가 프롬프트에 없다는 것**이다. 관계를 본문에서 직접 잇는 편이
점검 목록 한 줄보다 원인에 가깝다.

### 기대되는 관측 효과

- 공유 qualifier 누락 **감소**
- **동시에** 무효 span 복사(원문에 없는 텍스트를 만들어 붙이는 것)가 **증가하지 않을 것**
- 분기 전용 qualifier를 잘못 복사하는 사례가 늘지 않을 것 (아래 대조군이 이를 잡는다)

두 번째·세 번째가 핵심이다. "복사하라"를 강화하면 **과잉 복사**로 넘어갈 수 있으므로,
개발 세트에 **복사하면 안 되는 케이스**를 반드시 포함한다.

### 과적합 방지

S04를 여러 번 고쳐 쓰지 않는다. 서로 다른 qualifier 유형(시간/중증도/수치/조건),
서로 다른 구문 위치(coordination 앞 / 두 번째 conjunct 뒤), 그리고 **분기 전용 qualifier**를
독립적으로 작성한 케이스로 검증한다. 확인하려는 것은 문장 하나의 수정 가능성이 아니라
**규칙군(rule family) 차원의 실패 여부**다.

---

## H-PR-1 — `primary_rule_id`가 확인 규칙으로 채워짐

### 관측 (S03·S12·S13, 3건 / S06 vs S07, 1건)

| case | primary | 실제로 경계를 세운 규칙 | tier |
|---|---|---|--:|
| S03 | **H2-A** | H1-B → canonical H2-B가 진단 vs 바이오마커를 직접 규정 | **0** |
| S12 | **H2-A** | H1-B (모델이 supporting에 직접 기재) | **0** |
| S13 | **H2-A** | H1-B (모델이 supporting에 직접 기재) | **0** |
| S06 | H3 | H3 (macro gate) | 2 |
| S07 | **H1-B** | H3 (closed list + umbrella) — S06과 구조 동일한데 선택이 갈림 | 2 |

세 건 모두 **같은 방향의 역전**이다: 결정적 규칙이 `supporting_rule_ids`로 내려가고
확인 규칙이 primary로 올라갔다. tier는 primary에서 파생되므로 **tier 0 주장 3건**이 발생했다.

canonical은 H2-A를 이렇게 규정한다:

> H2-A **validates** the H1 proposition boundary; it should not turn Stage 1 into concept extraction.

그리고 tier 규칙은:

> Evidence tier should be derived from the **primary decisive canonical rule**.

### 프롬프트 원문

```
PROVENANCE

Output one primary decisive rule ID.

Suggested default evidence tier mapping:
- H2-A -> Tier 0
...
For primary_rule_id:
- choose ONE decisive rule
- put secondary rules in supporting_rule_ids
```

"decisive"의 뜻이 정의되어 있지 않다. **"결정을 정당화하는 규칙"과 "결정을 만든 규칙"을
구분하는 문장이 없다.**

### 가설

> **`primary_rule_id`는 Stage 1 구조 결정을 가장 직접적으로 성립시킨 규칙이어야 한다.
> 다른 규칙이 이미 세운 경계를 검증·확인하기만 하는 규칙은 원칙적으로 `supporting_rule_ids`다.**
>
> 구체적으로: H1이 이미 명제 경계를 세운 뒤 H2-A가 leaf 적정성을 확인했을 뿐이라면
> H2-A는 primary가 되지 않는다.
>
> `macro_aggregate`의 경우: 구조를 결정한 것이 H3의 open/closed 판정 또는 umbrella 테스트라면,
> 단지 복수의 독립 자식을 식별했다는 이유로 H1-B를 고르지 말고 **H3를 결정적 규칙으로 본다.**

### ✅ 확정 문구 — 일반 원칙만 (H2-A·H3 미지목)

`candidate_pr_from_v1_3_1.txt`의 OUTPUT CONSTRAINTS 안 기존 `For primary_rule_id:` 블록에
**두 항목만 추가**됐다. P0 대비 **이 삽입 외 변경 없음**(diff 검증 완료).

```
For primary_rule_id:
- choose ONE decisive rule
- put secondary rules in supporting_rule_ids
- "decisive" means the rule whose substantive test most directly determines the
  structural decision at the current level
- a rule that only validates or confirms a structural boundary established by
  another rule belongs in supporting_rule_ids
```

**H2-A와 H3를 이름으로 지목하지 않는다.** 일반 원칙을 먼저 시험하고, 그것으로 해소되지 않을 때에만
규칙명 지정이 필요한지 판단한다. 지목하면 Phase 5A 관측 3건에 맞출 위험이 있다.

> ⚠️ 일반 문구로 H2-A 역전이 해소되지 않으면 **같은 실험 안에서 H2-A 지목 문구를 점진적으로
> 덧붙이지 않는다.** 그것은 실험이 아니라 튜닝이다. 규범/사람 검토로 넘긴다.

### (기록) 초안 후보 A — 규칙명 지목형

```
For primary_rule_id:
- choose the ONE rule that most directly ESTABLISHED the structural decision
- a rule that only validates or confirms a boundary another rule already established
  belongs in supporting_rule_ids
- in particular, do not select H2-A as primary merely because it validates semantic
  leaf adequacy after an H1 boundary was already established
- for macro_aggregate, if H3's coverage/umbrella test determined the structure,
  H3 is the decisive rule
```

### (기록) 초안 후보 B — 최소 개입

두 줄만 추가:

```
- "decisive" = the rule that established the decision, not a rule that confirms it
- if another rule already fixed the boundary, that rule is primary
```

B의 장점: H2-A·H3를 이름으로 지목하지 않아 특정 사례 과적합 위험이 낮다.
B의 단점: 모델이 일반 원칙을 이번 사례에 적용할지 불확실하다.

### 기대되는 관측 효과

- 부적절한 H2-A primary 선택 **감소**
- 구조적으로 동등한 `macro_aggregate` 케이스에서 H3 primary 선택이 **더 안정적**
- **구조 결정 자체(splitting_decision / child_logic)는 변하지 않을 것**

세 번째가 안전 조건이다. provenance 지침을 손댔는데 라벨이 바뀐다면
그것은 프롬프트 명확화가 아니라 **의미 변경**이므로 즉시 중단하고 규범 검토로 넘긴다.

### 과적합 방지

동일한 semantic 조합만 반복하지 않는다. 진단+바이오마커 / 진단+치료력 / 검사값+약물 제한 /
확인(confirmation) 귀속 / open list / closed macro list를 각각 독립 작성해,
**규칙군 차원의 선택 실패인지 특정 조합의 문제인지** 가른다.

### tier 정책은 건드리지 않는다

이 가설은 `H2-A → Tier 0` 매핑 자체를 바꾸자는 것이 **아니다.**
매핑은 canonical 소관이다. 여기서 다루는 것은 **어떤 규칙이 primary가 되는가**뿐이며,
tier 변화는 그 결과로 따라오는 것이다.

---

## 규범 escalation 경계

Phase 5B 관측을 **"프롬프트 명확화"에서 "canonical 방법론 문제"로 올려야 하는 기준**.
이 단계에서 규범 질문을 **해결하지 않는다.** 기준만 정의한다.

### PROMPT 수준 (v1.3.x 비규범 패치로 처리 가능)

- 모델이 올바른 규칙을 알고 있는데 **필드 배정·형식이 불안정**하다
- 프롬프트의 primary vs supporting 지침이 **명시되어 있지 않다**(현재 "decisive" 미정의)
- 공유 qualifier를 **이해하면서도** 모든 자식에 복사하지 않는다
- 같은 규칙을 어떤 케이스에서는 지키고 어떤 케이스에서는 놓친다 → **출력 규율(discipline)** 문제
- 판정 라벨(`splitting_decision` / `child_logic`)은 옳은데 provenance만 흔들린다

**판별 질문**: 모델이 이미 옳게 판단한 것을 *기록하는 방식*의 문제인가?

### NORMATIVE 수준 (v1.4 사안, 사람 판단 필요)

- Canonical Core를 **두 가지로 합리적으로 읽을 수 있고** 각각 다른 구조 결정을 함의한다
- **어떤 규칙이 primary여야 하는지 canonical이 정하지 않는다**
- H2-A와 H1-B의 위계를 **기존 규범 텍스트만으로 해소할 수 없다**
- 고치면 **출력 규율이 아니라 결정 경계가 바뀐다**
- tier 파생 규칙 자체를 바꿔야 한다

**판별 질문**: 고치려면 *무엇이 옳은가*를 새로 정해야 하는가?

### 현재 두 가설의 위치

| 가설 | 현재 판단 | 근거 |
|---|---|---|
| H-X2-1 | **PROMPT 수준** | 모델이 규칙을 알고 있음을 자기 notes로 증명했다. 규범 텍스트에 모순이 없다 |
| H-PR-1 | **경계선** — 프롬프트로 시작하되 규범 검토 대기 | canonical이 "primary decisive rule"을 요구하면서 **decisive를 정의하지 않는다**. 프롬프트 명확화로 개선되면 PROMPT 수준, 개선되지 않으면 NORMATIVE로 승격 |

H-PR-1이 경계선인 것이 중요하다. Phase 5B에서 **후보 문구로도 H2-A 역전이 지속되면**,
그것은 프롬프트가 부족한 것이 아니라 **canonical에 판정 근거가 없다는 증거**다.

---

## 이 문서가 하지 않은 것

- `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` 수정 없음
- `docs/guidelines/stage1/canonical_core_v1_3_0.md` 수정 없음
- v1.3.2 생성 없음 · 문구 확정 없음 · tier 정책 재작성 없음
- 규범 질문 해결 없음 (escalation 기준만 정의)
- 모델 호출 없음

## 관련

- [`../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md`](../../experiments/stage1_v13/smoke_2026-09-08/TRACE_REVIEW.md) — 근거가 된 감사 전문
- [`../../experiments/stage1_v13/phase5b_dev/design.md`](../../experiments/stage1_v13/phase5b_dev/design.md) — 이 가설을 검증할 개발 세트 설계
- [`../methods/stage1_v1_3_runtime.md`](../methods/stage1_v1_3_runtime.md) — 런타임 계약
