# Stage 1 v1.3 development runtime

> **최종 갱신**: 2026-09-08 (PHASE 4)
> **구현 위치**: `pipeline/stage1_v13/`
> **규범**: [`../guidelines/stage1/canonical_core_v1_3_0.md`](../guidelines/stage1/canonical_core_v1_3_0.md) (v1.3.0, FROZEN)
> **프롬프트**: `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` (v1.3.1, **비규범**)
>
> ⚠️ **개발용 실행 경로다.** 프로덕션 준수 선언이 아니고, 최종 프롬프트 동결도 아니다.

---

## 1. 왜 병렬 경로인가

기존 프로덕션 경로(`pipeline/orchestrator.py` + `prompt_1_splitting.txt`)를 바로 v1.3으로 뜯어고치면
두 가지가 동시에 깨진다: 30-trial 산출물을 만든 기존 파이프라인의 동작이 바뀌고, v1.3 프롬프트를
실제로 돌려볼 수단은 아직 없다. 그래서 **버전이 붙은 개발 실행 경로를 따로** 만들었다.

```
LAYER 2    canonical core v1.3.0                    규범
LAYER 3    stage1_prompt_v1_3_1.txt                 비규범 개발 프롬프트
LAYER 3.5  pipeline/stage1_v13/                     개발 실행 경로  ← 이 문서
LAYER 4    pipeline/orchestrator.py + prompt_1      레거시 프로덕션, 여전히 v1.3 비준수
```

**PHASE 4는 LAYER 4를 고치지 않았다.** 새 층을 추가했을 뿐이다.
`docs/CURRENT_STATUS.md`의 "런타임은 아직 v1.3을 따르지 않는다"는 진술은 그대로 유효하다.

---

## 2. 아키텍처

| 모듈 | 역할 |
|---|---|
| `contracts.py` | v1.3 출력 계약, 규칙 ID 집합, tier 파생, 필드 분류, **historical 기록 읽기 어댑터** |
| `context.py` | 실행 컨텍스트(X1 입력 모델), PARENT_CONTEXT 구성, **nested_exception main 파생** |
| `validators.py` | 강한 검증. span 충실성, 구조, cohort scope, provenance |
| `runner.py` | 한 패스 실행 + 재귀 + 개발 CLI |

재사용한 것: `pipeline.llm_client`의 `_call_provider`(프로바이더 라우팅), `_parse_json_response`,
`_substitute_template`. 프로바이더 분기를 복제하지 않기 위해서다.
**재사용하지 않은 것**: `call_llm()` — 프로덕션 `filename_map`과 `examples.json` 주입에 묶여 있다.

`iaa_pipeline`은 import하지 않는다. 캐시는 `get`/`put`을 가진 객체로 **덕 타이핑**해 받고,
CLI에서 `--cache-dir`를 줄 때만 `iaa_pipeline.cache.LLMCache`를 지연 import한다.
`pipeline/` → `iaa_pipeline/` 방향 의존을 만들지 않기 위해서다.

---

## 3. 입출력 계약

### 입력 (canonical X1)

| 필드 | 의미 |
|---|---|
| `ROOT_CRITERION_TEXT` | 원문 criterion 전체. **읽기 전용 문맥** |
| `TARGET_SEGMENTS` | 이번 패스가 어노테이션하는 정확한 원문 세그먼트들. **출력 span의 유일한 출처** |
| `CRITERION_TYPE` | inclusion / exclusion |
| `TRIAL_HAS_COHORTS` | 코호트 라벨 목록 |
| `PARENT_CONTEXT` | 재귀 패스에서만. 해석 보조 |
| `NEIGHBORING_CRITERIA` | 읽기 전용 해석 문맥 |

루트에서 `TARGET_SEGMENTS = [ROOT_CRITERION_TEXT]`, `PARENT_CONTEXT = null`.

`Stage1Context`는 생성 시점에 **모든 target segment가 root의 축자 부분문자열인지** 검사한다.
호출자가 이미 합성한 텍스트를 넘기면 이후 모든 span 검사가 그 오염을 물려받으므로 경계에서 막는다.

프롬프트의 6개 placeholder를 **전부** 채운다. 레거시 프로덕션 경로는 prompt_1의 3개 중 2개만 넘겨
`{{neighboring_criteria}}`가 치환되지 않은 채 전송되는데(deferred legacy defect), 이 런타임은 그 결함을
반복하지 않는다.

### 출력

```json
{
  "splitting_decision": "none | composite_split | macro_aggregate | nested_exception",
  "child_logic": "AND | OR | null",
  "cohort_scope": ["..."] | null,
  "sub_criteria": [{"child_id": "a", "text_span": ["..."], "cohort_scope": null, "rationale": "..."}],
  "needs_recursion": true | false,
  "recursion_targets": ["a"] | ["main"] | [],
  "recursion_note": "...",
  "primary_rule_id": "H1-B",
  "supporting_rule_ids": ["X2"],
  "notes": "..."
}
```

### 필드 분류 — ontology 오염 방지

| 그룹 | 필드 |
|---|---|
| **pipeline-control** | `needs_recursion`, `recursion_targets`, `recursion_note` |
| **provenance** | `primary_rule_id`, `supporting_rule_ids` |
| **execution context** | `ROOT_CRITERION_TEXT`, `TARGET_SEGMENTS`, `PARENT_CONTEXT`, `NEIGHBORING_CRITERIA` |
| **ontology 표현** | `splitting_decision`, `child_logic`, `cohort_scope`, `sub_criteria[].{child_id,text_span,cohort_scope}` |

앞의 세 그룹은 **ontology property가 아니다.** 이 단계에서 온톨로지 명세에 아무것도 추가하지 않았다.

---

## 4. 재귀 메커니즘

한 LLM 호출 = 정확히 한 계층 (canonical H6).

```
root ── pass ── validate ── needs_recursion?
                              ├─ false → 정지
                              ├─ composite_split / macro_aggregate
                              │    recursion_targets의 각 child_id에 대해:
                              │      TARGET_SEGMENTS = 그 자식의 text_span (그것뿐)
                              │      PARENT_CONTEXT = 부모 결정 + 형제 span
                              │      → 다시 pass
                              └─ nested_exception, targets == ["main"]
                                   TARGET_SEGMENTS = 현재 세그먼트 − exception span
                                   → 다시 pass
```

- **exception span은 절대 재귀하지 않는다.** 그렇게 되는 코드 경로가 없다.
- 자식은 자기 span만 `TARGET_SEGMENTS`로 받으므로 형제나 루트 전용 텍스트에 닿을 수 없다.
- 혼합 논리(`A AND (B1 OR B2)`)는 계층으로 유지된다. 각 레벨이 자기 `child_logic`을 갖는다.
- `max_depth`(기본 5)에 도달하면 예외를 던지지 않고 멈추며, **노드의 런타임 메타데이터**에 기록한다.
  개발 실행이 거기까지 만든 계층은 그대로 반환된다 (§4-B).

### 4-B. 구현 정책 3가지

이 세 가지는 **구현 정책**이다. canonical v1.3.0의 규범 의미가 아니며, 규범을 새로 정의하지 않는다.

#### (1) punctuation-only 잔여 조각

exception subtraction 이후:

- **의미 있는 텍스트에 붙어 있는 punctuation은 그대로 보존한다.**
  `"Adequate hepatic function (AST, ALT), unless Gilbert syndrome."` → `["Adequate hepatic function (AST, ALT),"]`
  (내부 괄호·쉼표, 후행 쉼표 모두 유지)
- **제거로 독립적인 punctuation-only 조각이 생긴 경우에만** 버린다.
  `"Stage III NSCLC, unless resectable."` → `["Stage III NSCLC,"]` — 홀로 남은 `"."` 은 버린다.
- 의미 있는 문자나 punctuation을 **normalize·재작성하지 않는다.** 하는 일은 양끝 공백 트림뿐이며,
  결과는 여전히 원문의 축자 부분문자열이다.
- 따라서 TARGET_SEGMENTS의 **source text provenance가 유지된다.**

판정 기준은 "영숫자를 하나라도 포함하는가"이다. `", or"` 는 `or` 때문에 보존된다.

#### (2) 동일한 exception 문자열이 여러 번 나올 때

**occurrence 단위로 왼쪽부터 결정론적으로 소비한다. 같은 문자열을 하나로 합치지 않는다.**

| 모델 출력 | 동작 |
|---|---|
| `["except Y"]` 1회 | 첫 번째 미소비 occurrence만 제거 → 두 번째는 main에 남는다 |
| `["except Y", "except Y"]` 2회 | 첫 번째 → 첫 occurrence, 두 번째 → 두 번째 occurrence |

두 개의 exception span 객체가 각각 같은 문자열을 담아도 동일하다.
즉 source에 동일 exception 구가 두 번 있고 둘 다 exception이면 **모델 출력에도 두 번 나타나야 한다.**

#### (3) `max_depth` 는 개발용 안전장치다

`max_depth`(기본 5)는 **normative Stage 1 semantics가 아니다.** 잘못된 응답이 재귀를 무한히
요구하는 상황을 막는 개발 런타임 가드다. canonical 재귀는 레벨이 `none`이 되면 끝난다.

한도에 도달했는데 `needs_recursion`이 여전히 true이면, 그 결과가 **정상 완료된 계층으로 오해되면 안 된다.**
그래서 러너는 **모델 출력을 건드리지 않고** 노드에 런타임 메타데이터를 남긴다.

```python
node.incomplete_reason   # None | "max_depth" | "empty_main"
node.is_incomplete       # 이 레벨이 요구한 재귀가 실행되지 않았다
node.is_complete         # 하위 트리 전체가 완결되었는가
node.incomplete_nodes()  # 잘린 노드 목록 (빈 리스트 == 완결)
```

`recursion_note`는 **모델의 필드**다. 완료 여부를 그 문자열로 추론하지 않는다.
`to_dict()`와 CLI 경고에도 `incomplete_reason`이 노출된다.

새 ontology property를 만들지 않았고, 프롬프트 출력 스키마도, historical record 계약도 바꾸지 않았다.
`incomplete_reason`은 `Stage1V13Node`에만 있는 런타임/내부 계층 메타데이터다.

### nested_exception main 파생 — 안전 임계

프롬프트는 main span을 출력하지 **않는다**. 파이프라인이 현재 `TARGET_SEGMENTS`에서 exception span을
빼서 유도한다. 여기서 버그가 나면 provenance가 조용히 오염되므로 규칙을 좁게 잡았다.

- **빼기만 한다.** 바꿔 쓰기·정규화·재작성 없음.
- 제거로 분리된 조각을 **다시 합치지 않는다** → 재귀 패스가 여러 세그먼트를 받을 수 있다.
- exception span 하나는 **occurrence 하나**를 소비한다. 왼쪽부터, 이미 제거된 구간은 건너뛴다.
  모델이 한 번 지목한 표현이 같은 문장 뒤쪽의 무관한 동일 표현까지 지우지 않는다.
- 조각은 공백을 트림하고(여전히 축자 부분문자열), 영숫자가 없는 조각은 버린다.
  `"A except B."` → `["A"]`이지 `["A", "."]`가 아니다.
- 남는 내용이 없으면 `None`을 반환하고 재귀하지 않는다. 오류가 아니라 정상 종료다.

---

## 5. 검증 — 전부 hard failure

검증에 실패한 출력으로는 실행이 진행되지 않는다. 재시도(`MAX_RETRIES`)는 하지만
**통과시키려고 규칙을 완화하지 않는다.**

### X1 — span 충실성

모든 세그먼트는 **현재 `TARGET_SEGMENTS` 중 하나의 축자 연속 부분문자열**이어야 한다.
오류 메시지는 잘못된 출처를 세 가지로 구분한다 — 프롬프트 개발자가 원인을 바로 알 수 있어야 하기 때문이다.

| 상황 | 메시지 |
|---|---|
| 원문에 없음 | 합성/정규화된 span |
| ROOT에는 있으나 TARGET 밖 | 재귀 패스가 형제 내용을 다시 가져옴 |
| sibling_spans에서 옴 | PARENT_CONTEXT는 해석용이며 복사 대상이 아님 |

**sibling 텍스트가 현재 `TARGET_SEGMENTS`에도 들어 있으면 허용된다** — 금지 대상은
"TARGET 밖의 sibling 텍스트"다.

### 구조 (H4/H5/H6)

- `none` → `child_logic=null`, `sub_criteria=[]`, `needs_recursion=false`, `recursion_targets=[]`
- `composite_split`/`macro_aggregate` → `child_logic` **필수**(AND/OR), 자식 ≥2, `child_id` 고유,
  `recursion_targets ⊆ child_ids`, `"main"` 사용 금지
- `nested_exception` → `child_logic=null`, exception span **≥1**,
  `recursion_targets`는 `[]` 또는 `["main"]`만
- `needs_recursion`과 `recursion_targets`의 양방향 일관성

> **레거시 `nested_exception >= 2 sub_criteria` 규칙은 여기서 쓰지 않는다.**
> canonical H4는 exception span 1개도 유효하다고 규정하고, 동결된 113-item gold의
> `nested_exception` 10건 중 **9건이 정확히 그 형태**다. 그 레거시 규칙은 v1.3과도 gold와도 어긋난다.
> `pipeline/validators.py`의 해당 규칙은 이 단계에서 **건드리지 않았다** — 레거시 경로가 계속 쓴다.

### X4 — cohort scope

- `none` / `nested_exception` → top-level scope 허용
- `composite_split` / `macro_aggregate` → top-level은 **반드시 null**, scope는 자식에
- 라벨은 `TRIAL_HAS_COHORTS`에 있는 것만 (축자 복사)

### provenance

- `primary_rule_id` 정확히 하나, canonical 규칙 ID여야 함
- `supporting_rule_ids` 전부 유효, primary와 중복 불가
- tier는 `derive_tier()`로 **결정론적 파생** (H2-A→0, H2-B→1, 나머지→2).
  자유 텍스트에서 추론하지 않으며, 출력 필수 필드도 아니다. **historical gold tier는 재계산하지 않는다.**

---

## 6. historical 호환 경계

경계는 정확히 한 곳에 있다.

```
읽기   historical v1.2.2 기록  →  관대   contracts.read_legacy_stage1_record()
쓰기   v1.3 출력              →  엄격   validators.validate_v13_output()
```

- historical 기록에 v1.3 필드가 없는 것은 **정상**이다. 오류가 아니다.
  `recursion_targets`가 없는 v1.2.2 기록은 canonical이 명시한 대로 그 자체로 옳다.
- `text_span`이 문자열인 R1/R2 envelope도 읽힌다(`normalize_text_span`).
- **historical 기록을 v1.3 스키마로 다시 쓰지 않는다.** 어댑터는 인자를 변형하지 않는다.
- `iaa_pipeline/stage_schemas.py`를 확장하지 않았다. 동결 증거가 의존하는 계약이기 때문이다.
  v1.3 프롬프트가 동결된 뒤에 화해시킨다.
- `iaa_pipeline/adjudication.py`도 import하지 않는다. historical 판정 동작은
  **tag `stage1-adjudication-complete-2026-09-08`** 에 고정되어 있고, 이 패키지는 그 앵커를 건드리지 않는다.

테스트가 동결된 113-item export 전건(113/113)을 어댑터로 읽어 검증한다.

---

## 7. 캐시

`LLMCache` 키는 `sha256(프롬프트 내용 + payload + 모델)`이다. `cache_payload()`는 답을 바꿀 수 있는
모든 입력을 담는다 — 재귀 패스에서 두 자식은 같은 root 텍스트를 공유하고 `TARGET_SEGMENTS`와
`PARENT_CONTEXT`로만 갈리므로 둘 다 포함한다.

`node_id`와 `depth`는 **일부러 제외**했다. 같은 입력에 다른 경로로 도달한 것은 같은 호출이다.

프롬프트 내용이 키에 들어가므로 v1.3 프롬프트는 기존 캐시와 자동으로 분리된다. 캐시 동작 자체는 바꾸지 않았다.

---

## 8. 개발 스모크 테스트 실행법

```bash
# 프롬프트 렌더만 확인 — LLM 호출 0, 비용 0
python -m pipeline.stage1_v13 \
    --text "Histologically confirmed NSCLC with EGFR mutation, except patients with prior TKI therapy." \
    --type inclusion --dry-run

# 실제 모델 호출 (명시적으로 선택해야 한다)
python -m pipeline.stage1_v13 --text "..." --type inclusion --model gpt-4.1-mini

# 입력 파일 + 결과 저장
python -m pipeline.stage1_v13 --input dev_input.json --out /tmp/stage1_v13_dev.json

# 테스트 (LLM 호출 0)
python tests/test_stage1_v13.py
```

CLI는 stderr에 `Stage 1 v1.3 DEVELOPMENT — not a production run`을 먼저 찍는다.
`--out` 경로가 `iaa_workspace/`, `evidence/`, `STAGE1_GOLD_*`, `AMIA_2027_*` 아래면 **거부**한다.
기본 출력은 stdout이다.

---

## 9. 의도적으로 구현하지 않은 것

| 항목 | 이유 |
|---|---|
| 프로덕션 경로 교체 | Layer 4는 이 단계 범위 밖. `prompt_1_splitting.txt`·`orchestrator.py`·`validators.py` 무변경 |
| `pipeline/validators.py`의 `nested_exception ≥2` 수정 | 레거시 경로가 쓰는 규칙. v1.3 경로는 자기 검증기를 쓴다 |
| `stage_schemas.py` 필드 추가 | 동결 증거가 의존하는 계약. 프롬프트 동결 후 화해 |
| `examples.json` 사용/수정 | v1.2.2-era few-shot. historical 113건을 few-shot에 넣지 않는다 |
| IAA 정렬(`aligners.py`) 확장 | 재귀 출력은 criterion당 1 record가 아니다. **프롬프트 개발에 불필요하므로 연기**. 필요해지면 경로형 키(`root.a.b`) 설계부터 |
| tier 출력 필수화 | 파생 함수만 제공. 개발 워크플로가 요구할 때 붙인다 |
| 온톨로지 직렬화 | 이 단계의 출력은 프롬프트 개발·디버깅·검증용이다 |
| 레거시 `{{neighboring_criteria}}` 미치환 결함 수정 | deferred legacy bug. 공유 인프라가 강제하지 않는 한 v1.3 작업에 섞지 않는다 |
| 실제 모델 호출·프롬프트 튜닝·모델 비교 | Phase 5 이후. 이 단계에서 유료 API를 호출하지 않았다 |

---

## 10. historical gold를 v1.3 정확도 기준으로 쓰지 말 것

canonical v1.3.0은 일부 동작을 **의도적으로 변경**한다. 따라서 113건 전부를 v1.3 정확도의 gold로
직접 쓰면 안 된다. 나중에 회귀 비교 스캐폴드를 만들 때는 최소 셋으로 나눈다.

| 구분 | 의미 |
|---|---|
| **A** | 하위호환이 유지될 것으로 기대되는 동작 |
| **B** | **의도적 규범 변경**의 영향을 받는 사례 (H2-B confirmation, H3 open list, X5 위임, X7 criterion-local) |
| **C** | 미해결/모호 |

**B를 "모델 오류"로 계산하지 않는다.** Phase 4에서는 113건 평가를 수행하지 않았다.

---

## 11. 관련 문서

- [`../guidelines/stage1/CURRENT.md`](../guidelines/stage1/CURRENT.md) — 4층 governance
- [`../guidelines/stage1/canonical_core_v1_3_0.md`](../guidelines/stage1/canonical_core_v1_3_0.md) — 규범 본문
- [`../repository/SOURCE_OF_TRUTH.md`](../repository/SOURCE_OF_TRUTH.md) — 목적별 권위
- [`../project_state/stage1_v1_3_implementation_gap.md`](../project_state/stage1_v1_3_implementation_gap.md) — 구현 격차 재고
- [`../decisions/0001-stage1-v1-3-method-import.md`](../decisions/0001-stage1-v1-3-method-import.md) — v1.3 반입 ADR
