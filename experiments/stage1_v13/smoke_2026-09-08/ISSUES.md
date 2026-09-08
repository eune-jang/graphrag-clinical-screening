# PHASE 5A — 후보 이슈 목록

> 분류만 한다. **이 단계에서 B/D는 고치지 않는다.** A는 사소하고 명백히 구현 전용일 때만 고친다.
>
> | 분류 | 의미 |
> |---|---|
> | **A** | runtime / software 문제 |
> | **B** | 프롬프트 문구·형식 문제 |
> | **C** | 모델 능력 문제 가능성 |
> | **D** | 규범(normative method) 문제 가능성 |

실행 결과 요약: 14 케이스 / 15 호출 / hard failure 0 / 재시도 0 / validator 실패 0 /
span 위반 0 / 불완전 계층 0. 상세는 [`summary.md`](summary.md).

---

## I-01 — 공유 qualifier가 한쪽 자식에만 복사됨 (S04)

**분류: B (우선) / C (가능)**

```
"Women who are pregnant or breastfeeding at the time of screening."
[a] ["Women who are pregnant"]
[b] ["breastfeeding at the time of screening"]
notes: "The phrase 'at the time of screening' applies to both coordinated conditions by shared context."
```

canonical X2: *"Copy a shared dependent qualifier (temporal/numeric/conditional/severity) into every
child it semantically modifies."*

모델이 공유 적용을 **스스로 서술**하면서도 자식 a에 복사하지 않았다.
같은 실행의 S05·S12에서는 정확히 복사했으므로 능력 부재라기보다 **적용 조건이 흔들린다.**

B로 보는 근거: 프롬프트 X2가 "복사한다"와 "부모 문맥이 공유 의미를 제공하면 문법적으로 불완전해도 된다"를
나란히 두어, 모델이 후자를 근거로 복사를 생략할 여지가 있다.

관측 표본 1건. **수정하지 않음.**

---

## I-02 — 대등한 형제 간 span 형태 비대칭 (S05)

**분류: B (경미) — 규칙 위반 아님**

```
[a] ["Grade 3 peripheral neuropathy", "each persisting for more than 6 weeks after the last dose"]
[b] ["Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose."]
```

둘 다 X1을 만족한다. 자식 b는 원문에서 연속이라 한 세그먼트가 오히려 정확하다.
다만 의미적으로 대등한 두 자식의 span 구조가 달라, downstream 소비자가 형태 일관성을 가정하면 안 된다.

프롬프트 문제라기보다 **원문 어순의 자연스러운 귀결**일 수 있다. 관찰로만 기록. **수정하지 않음.**

---

## I-03 — `primary_rule_id`가 H2-A로 쏠려 Tier 0 비율이 높음

**분류: D (검토 필요) / B (가능)**

| | 이번 스모크 | historical 113-item gold |
|---|--:|--:|
| tier 0 | 3 / 14 (21%) | 10 / 113 (≈9%) |

H2-A는 canonical provenance 기본값에서 **Tier 0**(스펙 구조만으로 결정)으로 매핑된다.
해당 3건(S03·S12·S13)은 모두 서로 다른 semantic_category를 요구하는 사례라 H2-A 선택이 방어 가능하지만,
결정적 규칙이 H1-B(독립 주장 테스트)인데 H2-A를 골랐을 여지도 있다.

Tier 0은 "논의 불가"에 가까운 권위 주장이므로 **과대주장 여부를 사람이 판단해야 한다.**
표본 14건이라 분포 차이를 통계로 해석하면 안 된다.

D인 이유: 이것이 규범 문제라면 canonical의 tier 매핑 또는 "primary decisive rule" 정의를 손봐야 하고,
그것은 v1.4 사안이다. **수정하지 않음.**

---

## I-04 — 재귀 경로의 실전 노출이 얕음

**분류: A (테스트 설계) — 소프트웨어 결함 아님**

재귀는 14건 중 **1건(S10)** 에서만 발생했고 최대 depth는 1이었다.
S13은 재귀할 수도 있었으나 H1-A 병합으로 한 단위를 유지했다(방어 가능, 불일치 아님).

결과적으로 다음 경로가 실제 모델로는 아직 검증되지 않았다:

- depth ≥ 2 다단 재귀
- `composite_split` 자식 재귀 (관측된 재귀는 `nested_exception → ["main"]` 하나뿐)
- 여러 `recursion_targets` 동시 처리
- `max_depth` 절단, `empty_main`

**단위 테스트(mock)에서는 모두 통과**하지만 실제 모델 응답으로는 미노출이다.
Phase 5B 케이스 설계 시 다단 구조를 의도적으로 포함할 필요가 있다.

---

## I-05 — 설치된 openai SDK가 reasoning 파라미터를 명시 지원하지 않음

**분류: A — 이번 단계에서 우회했고, 소스는 건드리지 않음**

설치본은 `openai==1.6.1`이고 `chat.completions.create`에 `reasoning_effort` /
`max_completion_tokens` 명시 파라미터가 없다(최신은 3.8.0).

우회: `extra_body={"reasoning_effort": "medium", "max_completion_tokens": 8000}`.
사전 1-call 프로브로 동작을 확인한 뒤 사용했고, 15회 호출 전부 정상이었다.

이 우회는 **실험 harness 안에만** 있다. `pipeline/llm_client.py`(레거시 프로덕션 공유 코드)도,
`pipeline/stage1_v13/`도 수정하지 않았다 — 러너의 `llm=` 주입점을 썼다.

향후 v1.3 경로를 상시 실행하려면 결정이 필요하다:

1. SDK 업그레이드 (공유 의존성 → 레거시 프로덕션 경로에도 영향)
2. `extra_body` 우회를 런타임에 내재화
3. 현행 유지 (실험 harness가 호출을 소유)

`openai`는 `requirements.txt`·`pyproject.toml` 어디에도 선언되어 있지 않다 — 이것도 별도 정리 대상.
**사람 판단 필요.**

---

## I-06 — 프롬프트 토큰 비용

**분류: A (운영) — 결함 아님**

호출당 prompt 토큰 약 **6,900** (프롬프트 33KB). 이번 실행 합계 107,247 토큰 / 15 호출.

재귀가 깊어지면 호출 수에 선형으로 붙는다. 모델 계열 비교 단계에서
`케이스 수 × 평균 패스 수 × 6.9k × 모델 수` 로 예산을 잡아야 한다.

---

## 수정하지 않은 것

- `docs/guidelines/stage1/canonical_core_v1_3_0.md` — 무변경
- `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` — 무변경
- v1.3.2 미생성
- `pipeline/stage1_v13/` 런타임 소스 무변경
- 레거시 프로덕션 경로 무변경
