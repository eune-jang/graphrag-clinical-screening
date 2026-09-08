# PHASE 5A — Stage 1 v1.3 real-LLM smoke test

> **실행일**: 2026-09-08 · **성격**: **개발 아티팩트**. 정확도 평가가 아니다.
> **모델**: `gpt-5.6-terra`, reasoning effort **medium**
> **프롬프트**: `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt`
> sha256 `dfce30245473b8f69627d5030cb772be3ef84f8e23957b09d170e6ac288590f9`
> **런타임**: `pipeline/stage1_v13/` — **소스 변경 없음** (`llm=` 주입점 사용)

목적: v1.3 개발 런타임이 실제 모델을 호출해 프롬프트를 렌더하고, 응답을 파싱·검증하고,
재귀를 수행하고, 실행 provenance를 보존하는지 확인. **프롬프트 튜닝·정확도 평가·모델 비교가 아니다.**

---

## 1. 집계

| 항목 | 값 |
|---|--:|
| root 케이스 | 14 |
| **총 API 호출** | **15** (사전 프로브 1회 별도 = 누계 16/50) |
| 재귀 호출 | 1 |
| 재시도 호출 | **0** |
| hard failure | **0** |
| 완결된 계층 | **14 / 14** |
| 불완전(execution-incomplete) | **0** |
| `max_depth` 절단 | **0** |
| `empty_main` | **0** |
| 관측 최대 depth | **1** |
| depth 분포 | depth 0: 13 · depth 1: 1 |
| latency | min 1.6s / med 3.3s / max 6.7s |
| 토큰 | prompt 103,517 · completion 3,730 · **합계 107,247** |

### 형식 / 검증

| 지표 | 값 |
|---|---|
| 첫 시도 JSON 파싱 성공 | **15 / 15 (100%)** |
| 첫 시도 validator 통과 | **15 / 15 (100%)** |
| 최종 통과 | 15 / 15 |
| validator 실패 카테고리 | **없음** |
| API 오류 | 0 |

### span / provenance

| 지표 | 값 |
|---|---|
| TARGET_SEGMENTS 밖 span 시도 | **0** |
| sibling-only span 시도 | **0** |
| ROOT-outside-target span 시도 | **0** |
| 합성/정규화 span 시도 | **0** |
| `primary_rule_id` 누락/무효 | **0** |
| `supporting_rule_ids` 무효 | **0** |

harness 검증과 별개로, 저장된 계층 전체를 **독립 재검증**했다 — TARGET_SEGMENTS 밖 span **0건**.

---

## 2. 케이스별 리뷰

`expected_*`는 통합 점검용 **기계적 속성**이지 정답지가 아니다.

| id | 기대 family | 관측 결정 | logic | depth | 완결 | 재시도 | primary_rule | 관측 사항 |
|---|---|---|---|--:|---|--:|---|---|
| S01 | none | none | — | 0 | ✅ | 0 | H1-A | `0 or 1`을 값 범위로 처리 |
| S02 | none | none | — | 0 | ✅ | 0 | X5 | 포괄 적정성 → 분할 안 함 |
| S03 | composite_split | composite_split | AND | 0 | ✅ | 0 | H2-A | **confirmation이 진단에 귀속** ✅ |
| S04 | composite_split | composite_split | OR | 0 | ✅ | 0 | H1-B | ⚠️ 공유 qualifier 미복사 (§3-1) |
| S05 | composite_split | composite_split | OR | 0 | ✅ | 0 | H1-B | **multi-segment span** ✅ / 비대칭 (§3-2) |
| S06 | macro_aggregate | macro_aggregate | AND | 0 | ✅ | 0 | H3 | umbrella + 3 children |
| S07 | macro_aggregate | macro_aggregate | AND | 0 | ✅ | 0 | H1-B | closed list |
| S08 | none | none | — | 0 | ✅ | 0 | H3 | **open list 분할 안 함** ✅ |
| S09 | nested_exception | nested_exception | — | 0 | ✅ | 0 | H4 | exception span **1개** ✅ |
| S10 | nested_exception | nested_exception | — | **1** | ✅ | 0 | H4 | **main 재귀 성공** ✅ |
| S11 | nested_exception | nested_exception | — | 0 | ✅ | 0 | H4 | conditional allowance → waiver ✅ |
| S12 | **not** nested_exception | composite_split | AND | 0 | ✅ | 0 | H2-A | **negative requirement ≠ exception** ✅ |
| S13 | composite_split | composite_split | AND | 0 | ✅ | 0 | H2-A | 재귀 안 함 (§3-3) |
| S14 | none | none | — | 0 | ✅ | 0 | H0 | `cohort_scope=["Cohort B"]` ✅ |

**기계적 속성 일치: 14 / 14.**

### 핵심 통합 검증 — S10

nested_exception 전체 경로가 end-to-end로 동작했다.

```
root   nested_exception, exception span = ["unless completed more than 12 months before enrollment"]
       needs_recursion=true, recursion_targets=["main"]
  ↓    러너가 main 파생 (빼기만, 재작성 없음)
root.main  TARGET_SEGMENTS = ["Prior thoracic irradiation and prior systemic chemotherapy are exclusionary,"]
       → composite_split AND
         [a] "Prior thoracic irradiation"
         [b] "prior systemic chemotherapy"
```

파생된 main이 **후행 콤마를 보존**했다 — Phase 4에서 확정한 punctuation 정책이 실제 실행에서 확인됐다.
exception span은 재귀하지 않았다.

---

## 3. 수동 리뷰 플래그 — validator는 통과했으나 검토가 필요한 것

> **validator 통과 ≠ 의미적 정확성.** 아래는 관찰이며, 이 단계에서 프롬프트를 고치지 않는다.

### 3-1. S04 — 공유 qualifier가 한쪽 자식에만 들어갔다 ⚠️

```
[a] ["Women who are pregnant"]
[b] ["breastfeeding at the time of screening"]
notes: "The phrase 'at the time of screening' applies to both coordinated conditions by shared context."
```

모델이 **스스로 두 자식 모두에 적용된다고 서술**하면서도 자식 a에는 복사하지 않았다.
canonical X2는 *"Copy a shared dependent qualifier … into every child it semantically modifies"* 라고 규정한다.
반면 S05·S12에서는 정확히 복사했다 — **같은 규칙에 대한 처리가 케이스마다 갈린다.**

### 3-2. S05 — 형제 간 span 형태 비대칭

```
[a] ["Grade 3 peripheral neuropathy", "each persisting for more than 6 weeks after the last dose"]
[b] ["Grade 3 ototoxicity, each persisting for more than 6 weeks after the last dose."]
```

둘 다 X1을 만족한다(자식 b는 원문에서 연속이므로 한 세그먼트가 맞다). 다만 의미적으로 대등한 두 자식이
서로 다른 span 형태를 갖는다. 규칙 위반은 아니고, downstream 소비자가 알아야 할 특성이다.

### 3-3. S13 — 재귀하지 않음 (규칙 위반은 아님)

`"relapsed or refractory multiple myeloma"`를 한 단위로 유지했다.
H1-A의 same-screening-target 병합으로 방어 가능하다 — 하나의 운영상 질병 상태이며 분기별 제약이 없다.
기대값을 `null`로 열어 두었으므로 불일치가 아니다. 다만 **재귀 표본이 1건뿐**이라 재귀 경로의 실전 노출이 얕다.

### 3-4. `primary_rule_id` → tier 분포

| rule | 건수 | 파생 tier |
|---|--:|--:|
| H2-A | 3 | **0** |
| H1-B | 3 | 2 |
| H4 | 3 | 2 |
| H3 | 2 | 2 |
| H1-A / X5 / H0 | 각 1 | 2 |

Tier 0이 **3/14 (21%)** 이다. historical 113-item gold의 tier 0은 10/113 (≈9%)였다.
세 건 모두 서로 다른 semantic_category를 요구하는 사례라 H2-A 선택 자체는 방어 가능하지만,
**Tier 0은 "스펙 구조만으로 결정"을 뜻하므로 권위 과대주장 여부를 사람이 볼 필요가 있다.**
표본이 14건이라 분포 차이를 통계로 해석하면 안 된다.

### 3-5. 비용 특성

호출당 prompt 토큰이 약 **6,900**이다(프롬프트 33KB). 재귀가 늘면 호출 수에 선형으로 붙는다.
이후 단계의 예산 계획에 반영이 필요하다.

---

## 4. 이 단계에서 하지 않은 것

- 프롬프트·canonical core 수정 없음 (둘 다 외부 원본과 바이트 동일 유지)
- v1.3.2 생성 없음, 최종 프롬프트 동결 없음
- historical 113-item 채점 없음 — v1.3은 일부 경계를 의도적으로 바꿨고, 이 세트는 방법 개발에서
  held-out도 아니다
- 모델 계열 비교 없음 (`gpt-5.6-luna` / `gpt-5.6-sol` 미사용)
- 런타임 소스 수정 없음

## 5. 관련

- 후보 이슈 분류: [`ISSUES.md`](ISSUES.md)
- 케이스 매니페스트: [`manifest.json`](manifest.json) · 원본: [`cases.jsonl`](cases.jsonl)
- 실행 설정: [`run_config.json`](run_config.json) · 집계: [`summary.json`](summary.json)
- 패스별 전체 트레이스: `traces/passes.jsonl` · 계층 출력: `outputs/`
- 런타임 문서: [`../../../docs/methods/stage1_v1_3_runtime.md`](../../../docs/methods/stage1_v1_3_runtime.md)
