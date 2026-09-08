# Stage 1 v1.3 — implementation gap inventory

> **작성일**: 2026-09-08 (PHASE 3)
> **성격**: **재고 조사 전용.** 이 문서를 만들면서 코드를 한 줄도 바꾸지 않았다.
> **비교 기준선**: `docs/guidelines/stage1/canonical_core_v1_3_0.md` (현행 규범) **vs** 현재 저장소 구현
> — v1.2.3 패치 대비가 아니다.
> **반입 기록**: [`../decisions/0001-stage1-v1-3-method-import.md`](../decisions/0001-stage1-v1-3-method-import.md)

---

## 0. 읽는 법

`status` 값:

| 값 | 의미 |
|---|---|
| `conformant` | 현재 구현이 v1.3.0 요구를 이미 만족 |
| `partial` | 일부만 만족. 확장 필요, 충돌은 없음 |
| `missing` | 구현이 존재하지 않음 |
| `incompatible` | 현재 구현이 v1.3.0과 **어긋난 동작**을 함. 고치면 기존 출력이 바뀜 |
| `historical-only` | v1.2.2 판정 트랙에만 존재. 현행 규범 구현이 아니라 **재현용 앵커** |

`normative vs implementation-only`:
- **normative** — 고치면 Stage 1 라벨/구조 의미가 바뀐다. 연구 측 판단 필요.
- **implementation-only** — 배선·전달·검증 문제. 의미를 바꾸지 않는다.

### 조사 대상

`pipeline/prompts/prompt_1_splitting.txt` · `pipeline/prompts/examples.json` · `pipeline/orchestrator.py` ·
`pipeline/validators.py` · `pipeline/config.py` · `pipeline/llm_client.py` ·
`iaa_pipeline/stage_schemas.py` · `iaa_pipeline/adjudication.py` · `iaa_pipeline/stage_runner.py` ·
`iaa_pipeline/cache.py` · `iaa_pipeline/aligners.py` · `scripts/` · `tests/`

---

## 1. 요약

| status | 건수 |
|---|--:|
| conformant | 5 |
| partial | 8 |
| missing | 12 |
| **incompatible** | **6** |
| historical-only | 4 |

### Phase 4 최우선 5건 (전부 `incompatible`)

| # | 항목 | 왜 최우선인가 |
|---|---|---|
| 1 | **`validators.py`의 `nested_exception ≥2 sub_criteria`** | v1.3과 어긋날 뿐 아니라 **historical 113 gold의 nested_exception 10건 중 9건을 거부**한다. 현재 코드가 자기 저장소의 gold와도 불일치 |
| 2 | **`text_span` 문자열 소비 (`orchestrator.py:155`)** | v1.3 X1은 배열. 배열을 넘기면 Prompt 2–4가 리스트를 텍스트로 받아 조용히 오작동 |
| 3 | **`prompt_1`의 inclusion=AND / exclusion=OR 기본값** | v1.3 H5는 criterion type·표면 연결어에서 추론 금지. 라벨 의미가 직접 바뀜 |
| 4 | **`prompt_1`이 인접 criterion 텍스트를 자식 span 출처로 지시** | v1.3 X7 정면 위반. criterion-local 원칙 붕괴 |
| 5 | **`prompt_1`의 "as defined in Table" → `macro_aggregate`** | v1.3 X5는 위임된 임계값을 `none` + delegation note로 처리. 같은 입력에 다른 라벨 |

---

## 2. H 계층 gap

### H0 — role / scope gate

| | |
|---|---|
| canonical 요구 | 분할 전에 각 구절의 역할(구조적 내용 vs qualifier/method/scope/definition/permissive)을 먼저 판정. 문맥 복원 후 독립 요건으로 남는지 테스트 |
| 현재 구현 | **없음.** `prompt_1_splitting.txt`는 곧바로 4개 라벨 정의로 들어간다. 역할 게이트 개념이 없다 |
| status | **missing** |
| affected | `pipeline/prompts/prompt_1_splitting.txt`, `pipeline/prompts/examples.json` |
| Phase 4 작업 | 프롬프트 재작성 |
| 구분 | **normative** |
| 하위호환 | 신규 출력의 분할 수가 줄어들 수 있음 (concept-counting 억제) |
| 113 재현성 | 영향 없음 — 113건은 사람이 v1.2.2 가이드라인으로 판정 |

### H1-A — same screening-target test

| | |
|---|---|
| canonical 요구 | screening target = 술어가 아니라 임상 객체/상태. 3개 merge 조건 전부 충족 시에만 기본 병합 |
| 현재 구현 | **없음.** 병합 개념 자체가 프롬프트에 없다 |
| status | **missing** · **normative** |
| affected | `prompt_1_splitting.txt`, `examples.json` |
| 113 재현성 | 영향 없음 |

### H1-B — independent assertion test

| | |
|---|---|
| canonical 요구 | 공유 문맥 복원 후 각 후보가 개별 충족/위반 가능한 요건으로 남는가. 진리값 대비는 보조 증거 |
| 현재 구현 | **없음.** `composite_split` 정의가 "Multiple independent meanings combined in one criterion, often with different semantic categories or relation types" 한 줄뿐 |
| status | **missing** · **normative** |

### H2-A — semantic-category leaf validity

| | |
|---|---|
| canonical 요구 | leaf가 서로 다른 Stage-2 `semantic_category`를 요구하는 **독립 주장**을 복수 포함하면 안 됨. qualifier/purpose/method/scope에는 적용 금지 |
| 현재 구현 | `prompt_1`이 "often with different semantic categories or relation types"를 **분할 단서**로만 언급. leaf 유효성 게이트가 아님. `validators.py`·`stage_schemas.py`에 검사 없음 |
| status | **partial** · **normative** |
| Phase 4 | 프롬프트 규칙화 + (선택) Stage 1↔2 교차 검증 |
| tier | canonical 기본값 **Tier 0** |

### H2-B — oncology / domain refinement + confirmation rule

| | |
|---|---|
| canonical 요구 | 진단·병기·절제가능성·바이오마커는 **현재 criterion이 각각을 coordinate 요건으로 독립 주장할 때만** 분리. axis가 다른 술어의 대상/모집단이면 scope. **확인(histologic/cytologic/pathologic/documented)은 원칙적으로 진단 명제에 귀속** — v1.3 명시적 규범 변경 |
| 현재 구현 | **없음.** 종양학 축 규칙도, 확인 규칙도 프롬프트에 없다 |
| status | **missing** · **normative** |
| 하위호환 | ⚠️ v1.3이 v1.2.2 canonical 예시를 **의도적으로 supersede**함. v1.2.2로 판정된 항목과 v1.3 출력이 이 지점에서 달라질 수 있다 — 정상이며, 그래서 113 세트를 v1.3으로 재라벨하지 않는다 |
| tier | canonical 기본값 **Tier 1** |

### H3 — list / coverage check

| | |
|---|---|
| canonical 요구 | open(비망라) vs closed(운영상 망라) 목록 구분. open이면 named item을 쪼개지 말고 넓은 부모 의미를 한 단위로 유지. 항목별 임계값은 **강한 단서이지 폐쇄 증명이 아님**. 잉여 residual-umbrella 자식 생성 금지 |
| 현재 구현 | **없음.** open/closed 개념 자체가 없다 |
| status | **missing** · **normative** |
| 하위호환 | 신규 출력에서 분할 수 감소 방향 |

### H4 — structure type / exception behavior

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| 4개 라벨 enum | `config.SPLITTING_DECISIONS = {composite_split, macro_aggregate, nested_exception, none}` | **conformant** |
| `none` → `sub_criteria` 비어 있음 | `validators.py:66-69`, `stage_schemas.py:250-253` 모두 검사 | **conformant** |
| composite/macro ≥2 children | `validators.py:52-54`, `stage_schemas.py:242-247` | **conformant** |
| **`nested_exception` sub_criteria 규약** | `validators.py:59-61`이 **≥2 (main+exception)** 를 요구 | **incompatible** |
| macro gate (진짜 umbrella + 잉여 pass/fail 없음) | 프롬프트는 "sub-bullet 구조 또는 'as defined in Table' 참조"로 정의 | **incompatible** (X5 참조) |
| branch-specific exception (상위 분할 후 재귀) | 없음 | **missing** |
| 조건부 허용문 `allowed/permitted if Y` | 없음 | **missing** |

> **최우선 gap #1 상세.** v1.3 H4는 "Exception spans are not child Criterion nodes"이고
> DEV 프롬프트는 `sub_criteria contains one or more EXCEPTION spans`라고 규정한다 — 즉 **1개도 유효**하다.
> `validators.py:59-61`은 `nested_exception requires ≥2 sub_criteria (main+exception)`를 강제한다.
> 실측: **historical 113 gold의 `nested_exception` 10건 중 9건이 `sub_criteria` 1개**다.
> 이 검증기는 v1.3과도, 자기 저장소의 gold와도 어긋나 있다.
> 구분: **normative** (main span을 자식으로 두느냐는 표현 규약의 문제). 113 재현성: **영향 없음** — gold는 이 검증기를 통과한 적이 없다(판정 트랙은 `adjudication.py`를 쓴다).

### H5 — child_logic semantics

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| enum `{AND, OR}` (XOR 제거) | `config.py:94` | **conformant** |
| composite/macro 양쪽 **필수** | `iaa_pipeline/adjudication.py:271-281` 양방향 강제 | **conformant** (판정 트랙) |
| 〃 프로덕션 검증 | `validators.py:46-48` — **존재할 때만 enum 검사** | **missing** |
| 〃 저장 계약 | `stage_schemas.py:112` `child_logic: str \| None` optional, `:254-258` enum만 | **missing** |
| `none`/`nested_exception`에 금지 | `adjudication.py:278-281` 강제 / `validators.py` 미검사 | **partial** |
| **표면 and/or·criterion type에서 추론 금지** | `prompt_1`: "inclusion without explicit OR → AND (default, can omit)", "exclusion with sub-bullets or 'or' → OR (default for exclusion)", "macro_aggregate, child_logic is always AND (omit)" | **incompatible** |
| applicable-branch AND 의미 | 없음 | **missing** |
| 혼합 논리 `A AND (B1 OR B2)` 계층 표현 | 없음 (한 레벨만 출력) | **missing** |
| tier-0 위생 점검 | `scripts/tier0_check.py:72-74` — composite의 null child_logic만 | **partial** |

> **최우선 gap #3 상세.** v1.3 H5는 "Determine logic from eligibility semantics, not from surface `and/or`,
> criterion type, or punctuation"이다. 현재 프롬프트는 **criterion type(inclusion/exclusion)에서 직접 기본값을 유도**한다.
> 구분: **normative**. 113 재현성: 영향 없음 — gold의 child_logic은 사람이 부여했다.

### H6 — recursion

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| 한 패스 = 한 계층 | 프롬프트가 한 레벨만 출력하므로 사실상 성립 | **partial** |
| 자식 재평가 루프 | **없음.** `stage_runner.run_stage1_splitting()`은 criterion당 1회 호출 | **missing** |
| `nested_exception` main만 재귀 | `orchestrator.py:161-163` — "Process as single unit; exception handled in Prompt 5" | **missing** |
| `needs_recursion` | Stage1Record TypedDict에 **없음**. 프롬프트도 출력하지 않음. 판정 기록에는 113/113 존재 | **historical-only** |
| `recursion_targets` | 어디에도 없음. gold 113건에도 **0건** (canonical이 명시한 대로 v1.3 신규 필드) | **missing** |
| `recursion_note` | 코드에 없음. gold 6건에 존재 | **historical-only** |

**실측**: 113 gold 중 `needs_recursion=true` **8건** — Phase 4에서 재귀를 구현하면 이 8건이 첫 검증 대상이 된다.

---

## 3. X 계층 gap

### X1 — ROOT_CRITERION_TEXT / TARGET_SEGMENTS / text_span 배열 충실성

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| `ROOT_CRITERION_TEXT` 입력 | 없음. 프롬프트 placeholder는 `{{criterion_text}}` | **missing** |
| `TARGET_SEGMENTS` 입력 | **없음** | **missing** |
| `text_span` 배열 출력 | `prompt_1` 출력 스펙: `"text_span": "exact text from original criterion"` (문자열) | **incompatible** |
| `text_span` 배열 소비 | `orchestrator.py:155` `"text": sub["text_span"]` — 문자열 전제로 Prompt 2–4에 전달 | **incompatible** |
| 저장 계약 | `stage_schemas.py:96` `list[str] \| str` (구 문자열 수용) | **partial** |
| 판정 트랙 정규화 | `adjudication.normalize_text_span:137` 양쪽 수용 | **conformant** |
| 축자 부분문자열 검증 | `export_adjudicated_dataset.py:191-194` — 단 **criterion 전문** 기준이며 `TARGET_SEGMENTS` 기준이 아님 | **partial** |
| 세그먼트가 **현재 TARGET_SEGMENTS 내부**여야 함 | 개념 자체가 없음 | **missing** |

**실측**: 113 gold의 sub_criteria **123개 전부 `text_span`이 배열**이다 → gold는 이미 X1 배열 규약을 만족한다.
어긋나 있는 것은 프로덕션 프롬프트와 orchestrator다.

> **최우선 gap #2 상세.** Phase 4에서 프롬프트를 배열로 바꾸면 `orchestrator.py:155`가 리스트를 받는다.
> `target["text"]`는 그대로 Prompt 2–4의 `criterion_text`로 흘러가므로, 실패하지 않고 **리스트를 문자열화한 텍스트로
> 조용히 어노테이션**될 수 있다. 프롬프트와 orchestrator는 **반드시 같은 변경 단위**로 다뤄야 한다.
> 구분: **implementation-only** (배열 규약 자체는 v1.2.3에서 이미 규범이었다).

### X2 — shared expressions / qualifier scope

| | |
|---|---|
| canonical 요구 | 문법 위해 공유 개체 복제 금지. 의존 qualifier는 그것이 수식하는 모든 자식에 복사. 구문 위치는 **기본 단서**일 뿐 임상 의미가 우선 |
| 현재 구현 | **없음** |
| status | **missing** · **normative** |

### X3 — exception-span boundaries

| | |
|---|---|
| canonical 요구 | 명시 trigger가 있으면 **첫 단어부터** 전체 trigger 구를 포함. 괄호형 triggerless는 내용만. 형제 exception span 복수 허용 |
| 현재 구현 | **없음.** `prompt_1`은 nested_exception 트리거 예시("except", "unless")를 나열하지만 span 경계 규칙이 없다. `prompt_5`의 `exception_qualifier`는 Stage 2 관계 속성으로 별개 |
| status | **missing** · **normative** |

### X4 — cohort scope

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| 코호트 차이만으로 분할 금지 | `prompt_1`: "Do NOT infer cohort_scope from trial metadata … Most multi-arm trials share the same criteria → null" | **conformant** |
| 텍스트가 명시할 때만 기록 | 〃 "Only use cohort_scope when the criterion TEXT ITSELF restricts applicability" | **conformant** |
| 코호트 라벨 축자 복사 | 〃 "copying the matching entries VERBATIM from TRIAL_HAS_COHORTS" | **conformant** |
| split 시 **자식**에 기록, 부모 top-level은 null | 〃 per-child 배치 지시 있음 | **conformant** |
| `nested_exception`의 scope 위치 | v1.3: `none`/`nested_exception`은 **현재 Criterion에 부착 가능**. `prompt_1`은 nested_exception을 SPLIT 그룹에 넣어 자식 배치를 지시 | **incompatible** |
| 타입 검사 | `validators.py:70-` / `stage_schemas.py:260-273` list\|null 검사 | **conformant** |
| 전 코호트 적용 시 ontology 직렬화에서 생략 | `07_neo4j_ingest.py`가 납작한 문자열 property로 저장 | **partial** |

X4는 전체적으로 **가장 잘 맞는 영역**이다. per-child cohort_scope 작업(commit `ac1cb4e`)이 v1.3 규약을 선취했다.

### X5 — broad adequacy / assessment / delegation

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| 구체적 하위요건 없는 포괄 적정성 문장 → `none` | 없음 | **missing** |
| 평가 방법을 요건에서 분리하지 않음 | 없음 | **missing** |
| **IB/Table/appendix 위임 임계값 → `none` + delegation note** | `prompt_1`이 "as defined in Table" 참조를 **`macro_aggregate`의 정의적 신호**로 사용 | **incompatible** |
| 명시적 로컬 임계값은 정상 평가 | 사실상 macro로 흡수 | **partial** |

> **최우선 gap #5 상세.** 같은 입력("Adequate organ function as defined in Table 1")에 대해
> 현재 프롬프트는 `macro_aggregate`, v1.3 X5는 `none` + delegation note를 지시한다.
> 단 프롬프트 예시는 Table 참조와 **로컬 임계값 열거**("ANC ≥1500, Plt ≥100k…")를 함께 제시하므로,
> Phase 4에서 "위임만 있는 경우"와 "로컬 임계값이 함께 있는 경우"를 분리해야 한다.
> 구분: **normative**.

### X6 — conceptual queryability / evidence source

| | |
|---|---|
| canonical 요구 | Stage 1 단위는 개념적 적격성 결정 기준. 표준 임상 출처의 독립 문서화는 **보조 증거**이며, 기관별 EMR 필드 가용성은 구조 규칙이 아니다 |
| 현재 구현 | **없음** |
| status | **missing** · **normative** |
| 비고 | `iaa_pipeline_spec/`의 판정 문서에는 "CRC EMR 조회 단위"가 **Tier 2 근거**로 등장한다(`adjudication.py:50`). v1.3은 이를 구조 규칙에서 배제하고 보조 증거로 격하 |

### X7 — criterion-local decomposition

| 하위 항목 | 현재 구현 | status |
|---|---|---|
| 인접 criterion 텍스트를 자식 span으로 가져오지 않음 | `prompt_1` 말미: *"Use the neighboring criteria to detect macro_aggregate patterns. … **The sub_criteria should reference the following lab value criteria by their text.**"* | **incompatible** |
| 다른 곳에 같은 요건이 있다고 로컬 요건을 억제하지 않음 | 규칙 없음 | **missing** |
| cross-criterion 통합은 Stage 1 밖 | 규칙 없음 | **missing** |
| NEIGHBORING_CRITERIA는 읽기 전용 | `stage_runner.py:77-105`가 ±2 창으로 전달하되 **읽기 전용 제약 문구 없음** | **partial** |

> **최우선 gap #4 상세.** 현재 프롬프트는 X7이 금지하는 동작을 **명시적으로 지시**한다.
> canonical의 legacy 매핑표도 `§3-5 → X7 (superseded)` — "neighboring-criterion macro construction moved outside Stage 1"으로 이 변경을 규범적으로 확정한다.
> 구분: **normative**. macro_aggregate 산출 방식이 근본적으로 달라진다.

---

## 4. Provenance / pipeline mechanics gap

| 항목 | 현재 구현 | status | 구분 |
|---|---|---|---|
| `primary_rule_id` | 코드 0곳, gold 113건 중 **0건** | **missing** | implementation-only (규약은 canonical이 정의) |
| `supporting_rule_ids` | 동일 — **0건** | **missing** | implementation-only |
| tier 파생 (`primary_rule_id` → tier) | `adjudication.py:47-52` `TIER_LABELS`는 **사람이 부여한 tier**를 라벨링. 자동 파생 없음 | **historical-only** | implementation-only |
| `needs_recursion` | gold 113/113, 코드 계약 없음 | **historical-only** | implementation-only |
| `recursion_targets` | 전무 (canonical이 v1.3 신규라고 명시) | **missing** | implementation-only |
| `recursion_note` | gold 6건, 코드 계약 없음 | **historical-only** | implementation-only |
| `PARENT_CONTEXT` | 전무 | **missing** | implementation-only |
| `NEIGHBORING_CRITERIA` 읽기 전용 제약 | 전달은 되나 제약 문구 없음 (X7 참조) | **partial** | normative |

### ⚠️ 부수 발견 — 프로덕션 placeholder 미치환 (v1.3 무관, 기존 결함)

`pipeline/prompts/prompt_1_splitting.txt`는 `{{criterion_text}}` · `{{cohort_list_or_null}}` ·
`{{neighboring_criteria}}` 세 placeholder를 갖는다.
`pipeline/orchestrator.py:133-136`은 **앞의 두 개만** 전달한다.
`llm_client._substitute_template:114-127`은 variables에 없는 placeholder를 **그대로 둔다**.

→ 프로덕션 배치 실행은 `{{neighboring_criteria}}` 문자열을 **치환하지 않은 채** LLM에 보낸다.
(IAA 트랙 `stage_runner.py:171-173`은 정상 전달한다.)

status **implementation-only 결함**. Phase 3에서 고치지 않았다. Phase 4 프롬프트 재배선 시 함께 해소된다.

---

## 5. Storage and Execution Contract Inventory

**Phase 3에서 `stage_schemas.py`에 필드를 추가하지 않았고 JSON 계약도 바꾸지 않았다. 재고 조사 전용.**

| 필드 / 컨텍스트 | 현재 존재? | 성격 | ontology property? | pipeline-control? | v1.2.2 기록이 보유? | 하위호환 요구 | Phase 4 소유 모듈(예상) |
|---|---|---|---|---|---|---|---|
| `splitting_decision` | ✅ | 저장 record | ✅ (Criterion parent_role) | — | ✅ 113/113 | 유지 | `config.py`, `stage_schemas.py` |
| `child_logic` | ✅ | 저장 record | ✅ | — | ✅ (split 항목) | 유지 + **필수화** | `validators.py`, `stage_schemas.py` |
| `cohort_scope` | ✅ | 저장 record | ✅ (전 코호트면 생략) | — | ✅ | 유지 | `stage_schemas.py`, `07_neo4j_ingest.py` |
| `sub_criteria[].child_id` | ✅ | 저장 record | ✅ | — | ✅ | 유지 | `stage_schemas.py` |
| `sub_criteria[].text_span` | ✅ (`list\|str`) | 저장 record | ✅ | — | ✅ **123/123 배열** | 배열 전용화 시 구 문자열 리더 유지 | `stage_schemas.py`, `orchestrator.py` |
| `sub_criteria[].rationale` | ✅ | 저장 record | ❌ 주석 | — | ✅ | 유지 | `stage_schemas.py` |
| `needs_recursion` | ❌ 계약 없음 (gold에만) | 저장 record | ❌ | ✅ | ✅ 113/113 | **신규 필드 — 구 기록에 없어도 유효해야** | `stage_runner.py` |
| `recursion_targets` | ❌ | 저장 record | ❌ | ✅ | ❌ **0건** | 구 기록은 이 필드 부재가 정상 | `stage_runner.py` |
| `recursion_note` | ❌ 계약 없음 (gold 6건) | 저장 record | ❌ | ✅ | 부분 | 선택 필드 | `stage_runner.py` |
| `primary_rule_id` | ❌ | 저장 record | ❌ provenance | — | ❌ 0건 | 구 기록은 `rule_id` 보유 → **덮어쓰지 말고 파생 필드로** | `adjudication.py`(신규 경로) |
| `supporting_rule_ids` | ❌ | 저장 record | ❌ provenance | — | ❌ 0건 | 선택 | 〃 |
| `ROOT_CRITERION_TEXT` | ❌ | **입력/실행 컨텍스트** | ❌ | 실행 전용 | 해당 없음 | — | `stage_runner.py`, `llm_client.py` |
| `TARGET_SEGMENTS` | ❌ | **입력/실행 컨텍스트** | ❌ | 실행 전용 | 해당 없음 | — | 〃 |
| `PARENT_CONTEXT` | ❌ | **입력/실행 컨텍스트** | ❌ | 실행 전용 | 해당 없음 | — | 〃 |
| `NEIGHBORING_CRITERIA` | ✅ (IAA 트랙만) | **입력/실행 컨텍스트** | ❌ | 실행 전용 | 해당 없음 | 읽기 전용 제약 필요 | `stage_runner.py` |

### 캐시 영향

`iaa_pipeline/cache.py`의 키는 `sha256(prompt_template_content + input + model)`이다.
프롬프트를 바꾸면 **캐시가 자동으로 무효화**되므로 별도 조치가 필요 없다. status **conformant**.

### 정렬(alignment) 영향

`iaa_pipeline/aligners.py:120-129`의 Stage 1 정렬은 `criterion_id` 기준 **1:1 (never missing)** 을 전제한다.
v1.3 재귀는 한 criterion에서 **여러 레벨의 record**를 만든다 → 재귀 출력의 IAA 정렬 키가 정의되어 있지 않다.
status **partial**, Phase 4 작업 범주: 정렬 키 설계 (예: `criterion_id` + 경로).

### 테스트 커버리지

`tests/test_iaa_metrics.py`(44) · `tests/test_adjudication.py`(50) 모두 **v1.2.2 계약**을 검증한다.
v1.3 규칙·재귀·provenance 필드에 대한 테스트는 **0건**. status **missing**.
기존 94개는 historical 계약의 회귀 방지선이므로 **Phase 4에서도 통과해야 한다**.

---

## 6. Ontology vs pipeline metadata 경계

**이번 단계에서 ontology 명세에 아무것도 추가하지 않았다.** 아래 경계를 Phase 4에서 유지한다.

| 항목 | 분류 | 근거 |
|---|---|---|
| `needs_recursion`, `recursion_targets`, `recursion_note` | **pipeline-control metadata** | canonical H6: *"These fields are **execution metadata**, not ontology semantics"* / *"`recursion_targets` is a new v1.3 pipeline-control field. It is not an ontology property"* |
| `primary_rule_id`, `supporting_rule_ids` | **annotation / provenance metadata** | canonical "Provenance defaults"가 H0–H6 구조 결정 계층과 **분리된 규약**이라고 명시. ontology property로 규정한 문장 없음 |
| `ROOT_CRITERION_TEXT`, `TARGET_SEGMENTS`, `PARENT_CONTEXT`, `NEIGHBORING_CRITERIA` | **execution context** | canonical X1이 LLM 입력 컨텍스트로 정의. 그래프 property가 아니다 |
| `splitting_decision`, `child_logic`, `cohort_scope`, `text_span` | **ontology 표현** | v1.2.2부터 Criterion/자식 표현의 일부 |

→ Phase 4에서 recursion·provenance 필드를 `pipeline/schema/`의 온톨로지 명세에 넣지 말 것.
저장 계약(`stage_schemas.py`)과 온톨로지 명세는 **다른 문서**다.

---

## 7. 기존 drift의 v1.3 canonical 재코딩

PHASE 1·2에서 기록한 drift는 v1.2.3 기준이었다. v1.3.0이 forward 구현 목표이므로 **canonical family로 재anchor**한다.
과거 서술은 계보 추적을 위해 함께 남긴다.

| 기존 서술 (v1.2.3 기준) | v1.3 canonical family | 이 문서 위치 |
|---|---|---|
| `text_span`이 문자열 — v1.2.3 변경 6 | **X1** | §3 X1 |
| `child_logic` 생략 허용 / macro는 항상 AND(omit) — v1.2.3 변경 1 | **H5** | §2 H5 |
| inclusion=AND / exclusion=OR 암묵 기본값 | **H5** | §2 H5 |
| `NEIGHBORING_CRITERIA`를 자식 span 출처로 지시 | **X7** | §3 X7 |
| `validators.py`의 child_logic 필수성 미반영 | **H5** | §2 H5 |
| `orchestrator.py`의 segmented text_span 미지원 | **X1** | §3 X1 |
| (신규 발견) `nested_exception ≥2 sub_criteria` | **H4** | §2 H4 |
| (신규 발견) "as defined in Table" → macro_aggregate | **X5** | §3 X5 |
| (신규 발견) 재귀 루프 부재 | **H6** | §2 H6 |
| (신규 발견) Stage 1↔2 handoff — v1.2.3이 요구한 PARENT_TEXT 정합성 | **X1 / X2** | Phase 4 downstream 재설계 시 점검 |

---

## 8. historical 113 재현성 관점 요약

| 관심사 | 판단 |
|---|---|
| v1.3 반입이 113 gold를 바꾸는가 | **아니다.** 파일을 건드리지 않았고 `SHA256SUMS` 64/64 유지 |
| gold가 v1.3 X1(배열)을 이미 만족하는가 | **그렇다.** sub_criteria 123/123 배열 |
| gold가 v1.3 신규 필드를 갖는가 | **아니다.** `recursion_targets`·`primary_rule_id`·`supporting_rule_ids` 전부 0건 — canonical이 예고한 대로 |
| 프로덕션 검증기가 gold를 통과시키는가 | **아니다.** `validators.validate_prompt1`은 `nested_exception` 10건 중 9건을 거부. 단 gold는 이 검증기를 거친 적이 없다(판정 트랙은 `adjudication.py`) |
| historical 판정 동작 재현 방법 | `iaa_pipeline/adjudication.py` **@ tag `stage1-adjudication-complete-2026-09-08`** |
| v1.3-harmonized reference set | 필요해지면 **별도 버전으로 새로 만든다.** 113 세트를 재라벨하지 않는다 |

---

## 9. Phase 4 작업 범주

| 범주 | 포함 gap | 성격 |
|---|---|---|
| **A. Stage 1 프롬프트 재작성** | H0, H1-A, H1-B, H2-A, H2-B, H3, H4(exception/조건부), H5(추론 금지·applicable branch), X2, X3, X5, X6, X7 | **normative 구현** — v1.3.1 DEV 프롬프트가 이미 이 내용을 담고 있다 |
| **B. 입력 컨텍스트 배선** | `ROOT_CRITERION_TEXT`, `TARGET_SEGMENTS`, `PARENT_CONTEXT`, `CRITERION_TYPE`, NEIGHBORING 읽기 전용 | implementation-only |
| **C. 출력 계약 확장** | `needs_recursion`, `recursion_targets`, `recursion_note`, `primary_rule_id`, `supporting_rule_ids` | implementation-only |
| **D. 재귀 실행 루프** | H6 | implementation-only (의미는 canonical이 확정) |
| **E. 검증기 정렬** | `validators.py` nested_exception 규칙, child_logic 필수화, span 축자성 대 `TARGET_SEGMENTS` | 일부 **normative** |
| **F. 소비자 수정** | `orchestrator.py:155` 배열 소비, Prompt 2–4 handoff | implementation-only — **A와 동시에 해야 함** |
| **G. IAA 정렬 확장** | `aligners.py` 재귀 출력 키 | implementation-only |
| **H. 테스트** | v1.3 규칙·재귀·provenance. 기존 94개 통과 유지 | implementation-only |
| **I. few-shot 예제** | `examples.json` (현재 `text_span` 문자열, v1.3 필드 없음) | **normative 영향** — canonical은 예시 교체를 v1.3.x 비규범 패치로 허용하되 동작 불변 조건 |

---

## 9-B. PHASE 4 진행 상황 (2026-09-08 갱신)

이 재고는 **레거시 프로덕션 경로** 기준으로 작성되었고, 그 상태는 PHASE 4에서 **바뀌지 않았다**.
PHASE 4는 병렬 개발 실행 경로 `pipeline/stage1_v13/`(LAYER 3.5)를 신설했을 뿐이다.

| Phase 4 작업 범주 (§9) | 개발 경로 상태 | 프로덕션 경로 상태 |
|---|---|---|
| **B.** 입력 컨텍스트 배선 (ROOT/TARGET/PARENT/TYPE) | ✅ `stage1_v13/context.py` | 미변경 |
| **C.** 출력 계약 확장 (recursion·provenance 필드) | ✅ `stage1_v13/contracts.py` | 미변경 |
| **D.** 재귀 실행 루프 (H6) | ✅ `stage1_v13/runner.py` + main 파생 | 미변경 |
| **E.** 검증기 정렬 (H4 nested_exception, H5 필수, X1 span, X4 scope, provenance) | ✅ `stage1_v13/validators.py` | **미변경** — `pipeline/validators.py`의 `≥2` 규칙 그대로 |
| **H.** 테스트 | ✅ `tests/test_stage1_v13.py` 80건 | 기존 94건 통과 유지 |
| **A.** 프롬프트 재작성 | ✅ 반입된 v1.3.1 DEV 프롬프트가 담당 | `prompt_1_splitting.txt` **미변경** |
| **F.** 소비자 수정 (`orchestrator.py:155` 배열 소비) | 해당 없음 (개발 경로는 Prompt 2–4로 넘기지 않음) | **미변경** |
| **G.** IAA 정렬 확장 (`aligners.py`) | ⏸️ **연기** — 프롬프트 개발에 불필요 | 미변경 |
| **I.** few-shot 예제 | ⏸️ `examples.json` **미사용·미변경** | 미변경 |

연기된 두 건:

- **G. 정렬** — 재귀 출력은 criterion당 1 record가 아니므로 `aligners.align_stage1`의 1:1 전제와
  맞지 않는다. 프롬프트 개발 단계에서는 정렬이 필요 없어 손대지 않았다. 필요해지면 경로형 키
  (`root.a.b`) 설계가 선행되어야 한다.
- **I. 예제** — v1.3.1 프롬프트가 자체 synthetic 예제를 포함한다. historical 113건을 few-shot에
  넣으면 평가 대상을 오염시키므로 추가 예제가 필요하면 별도 versioned 산출물로 만들고 사람 승인을 받는다.

상세: [`../methods/stage1_v1_3_runtime.md`](../methods/stage1_v1_3_runtime.md)

---

## 10. 이 단계(PHASE 3)에서 하지 않은 것

- 코드 수정 0건
- `stage_schemas.py` 필드 추가 없음, JSON 계약 변경 없음
- ontology 명세 변경 없음
- `prompt_1_splitting.txt` / `examples.json` 변경 없음 — **v1.2.3 중간 상태를 만들지 않는다.**
  기존 drift는 v1.3에서 한 번에 해소한다
- LLM 호출·프롬프트 평가·모델 비교 없음
- DEV 프롬프트 런타임 활성화 없음 (`development artifact imported; runtime activation deferred to Phase 4`)
