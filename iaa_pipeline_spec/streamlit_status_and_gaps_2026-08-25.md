# Streamlit 판정 앱 — 구현 현황 및 정리 필요 항목 (2026-08-25)

> **rev 2.1** — 2차 검토 반영: 갭 1 양방향 검증, 갭 4 `span_override` 지위 재정의, **GPT 비교 분모 39/46 확정**, D-1-lite 조인 지침, 마감 구간 추가. 변경 내역은 §10.
>
> **rev 2** — 외부 검토 반영 + 지적 항목 코드 실측 검증. 검증 결과 **갭 4가 필수로 승격**, **갭 1의 범위 정정**, **8 trial 정체 확정**, **신규 리스크 2건 발견**.
>
> **이 문서의 목적**: 저장소 접근 없이도 논의할 수 있도록, 현재 코드에 **실제로 구현된 것**과 **문서 기준으로 어긋난 것**을 정리한 브리핑. 모든 주장은 코드를 직접 열어 실측했으며, 근거 파일·줄번호를 병기했다. 검증 로그는 §부록 C.
>
> **맥락**: AMIA 2027 초록(9/3 마감) 크리티컬 패스로 판정(adjudication) 61건을 8/27~29에 수행한다. 판정 준거는 **spec v1.2.2 + v1.2.3 패치 + guideline v1.2.1**로 동결됐고, 재귀 분할은 **옵션 B(최상위 라벨만 + `needs_recursion` 보류 플래그)**로 결정됐다.

---

## 0. 한눈에

| 구분 | 상태 |
|---|---|
| 판정 앱 핵심 기능 (GOLD 액터, 2단 통과, 판정 기록 필드, gap ticket, span 검증) | ✅ **전부 구현·검증 완료** |
| 판정 시작 전 반드시 고쳐야 할 것 | ❌ **4건** (§4) |
| 초록 크리티컬 패스 신규 리스크 | ⚠️ **2건** (§5) |
| 하지 말아야 할 것 | 🚫 재귀 계층 UI (§6) |
| 문서 정리 필요 | 📄 **5건** (§7) |
| 테스트 | 판정 36/36 통과 · IAA 35/37 (실패 2건 원인 규명 완료, §8) |

---

## 1. 문서 지형 — 어느 것이 유효한가

같은 주제의 문서가 여러 버전 공존한다. **논의 시 아래 "유효" 열을 기준으로 삼을 것.**

### 1-1. 온톨로지 스펙

| 파일 | 날짜 | 유효 | 비고 |
|---|---|---|---|
| `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md` | 05-08 | ✅ 본문 | 823줄 |
| `pipeline/schema/ontology_spec_v1_2_3_patch.md` | 08-11 | ✅ **패치 (본문 미반영)** | 176줄. 변경 7건. **본문에 머지되지 않았으므로 둘을 함께 읽어야 함** |
| `pipeline/schema/ontology_full_specification_v1.2.1.md` | 05-05 | ⛔ 구버전 | |
| `pipeline/schema/ontology_v1.2.1.json` | 05-05 | ⛔ dead reference | `config.py`가 실제 source of truth |

**v1.2.3 패치 7건 요약** (판정에 직접 영향):
1. `Criterion.child_logic` — default 생략 규칙 폐지 → **composite/macro 모두 항상 명시**
2. `IS_PART_OF` 사용 규칙 — #1과 동일 취지 문장 정리
3. `INCLUDES_EXCEPTION` — `EXCLUDES_*` 한정 → `REQUIRES_*`/`EXCLUDES_*` 무관으로 확장
4. `parent_role.nested_exception_parent` 정의 명확화
5. `REQUIRES_STATUS` From→To 확장 (Criterion → Observation / Stage)
6. `sub_criteria.text_span` — **string → array of strings** (연속 세그먼트, substring 검증 전제)
7. `cohort_scope` 빈 값 — "빈 array 또는 생략" → **생략으로 통일**

### 1-2. 어노테이션 가이드라인

| 파일 | 날짜 | 유효 | 비고 |
|---|---|---|---|
| `pipeline/schema/annotation_guideline_v1_2_1.md` | 08-25 17:33 | ✅ **판정 준거 동결본** | 변경 11건. §3에 "category 혼재 → split" 편입 |
| `pipeline/schema/annotation_guideline_v1_2.md` | 08-25 16:30 | 📄 **정리 대상** (v1.2.1이 대체) | |
| `pipeline/schema/stage1_iaa_review_and_guideline_v1_1.md` | 08-25 16:46 | ✅ 검토 기록 | Round 2 IAA 차이 영역 8개 + 상세 예시. 가이드라인 본문 아님 |
| `pipeline/schema/annotation_guideline_v0_2_stage1 (1).md` | 05-11 | ⛔ 구버전 (v0.2) | 1369줄. 혼동 위험 |

### 1-3. 판정(adjudication) 문서

| 파일 | 날짜 | 유효 | 비고 |
|---|---|---|---|
| `iaa_pipeline_spec/adjudication_guide_v2_notion.md` | 08-25 17:33 | ✅ **작업자용 최신** | 61건 스코프, 준거 동결, `needs_recursion` |
| `iaa_pipeline_spec/adjudication_guide_notion.md` | 08-25 16:47 | 📄 **정리 대상** (v2가 대체) | 113건 스코프 기준 |
| `iaa_pipeline_spec/adjudication_handover.md` | 07-30 | ✅ **기술 설계 근거** | 944줄. §3 작업목록 A~D, §10 구현 기록 |
| `iaa_pipeline_spec/audit_streamlit_v1.md` | 05-27 | ✅ **블라인딩 아키텍처 근거** | 누출 A1~A7. UI 수정 전 필독 |
| `streamlit_apps/handover_streamlit_hierarchical_labeling.md` | 08-25 16:47 | ⏸ **보류 (Paper 1 트랙)** | 재귀 계층 UI 요구사항. 이번에 구현 안 함 |

---

## 2. 코드 인벤토리 — 판정 앱 실행에 관여하는 파일

### 실행 진입점
| 파일 | 줄수 | 역할 |
|---|--:|---|
| `iaa_pipeline/streamlit_app.py` | 1610 | **로컬 앱 본체.** 어노테이션 + 판정 UI 전부 |
| `streamlit_apps/stage1_app.py` | 605 | 호스팅용(Community Cloud). 위 파일의 blind 폼 재사용 |

실행: `streamlit run iaa_pipeline/streamlit_app.py` → 사이드바 Role: Adjudicator, Round: 2, Blind: ON

### 앱이 직접 import 하는 로직
| 파일 | 줄수 | 역할 |
|---|--:|---|
| `iaa_pipeline/adjudication.py` | 394 | 판정 순수 로직. `TIERS`, `RULE_STATUSES`, `span_violations`, `validate_adjudication`, `build_gold_record`, `build_gap_ticket`, `load_queue` |
| `iaa_pipeline/stage_schemas.py` | 288 | `SPLITTING_DECISIONS`/`CHILD_LOGIC` enum + `validate_stage1_record` |
| `iaa_pipeline/metrics.py` | 614 | Cohen's κ + `compute_sd_axes` (SD 2축 분해) |
| `pipeline/config.py` | 163 | 스키마 enum 원천 + **LLM 모델 프리셋** (§5-2 관련) |

### 앱 입력을 만드는 스크립트
| 파일 | 줄수 | 역할 |
|---|--:|---|
| `scripts/build_adjudication_queue.py` | 466 | 층화 판정 큐 → `adjudication_queue.{csv,json}` |
| `scripts/tier0_check.py` | 171 | 스펙 위반 위생 점검 |
| `scripts/compute_iaa.py` | 288 | κ 계산 (`--round` 지원) |

### 테스트
`tests/test_adjudication.py` (36건) · `tests/test_iaa_metrics.py` (37건)

---

## 3. 구현 현황 — `adjudication_handover.md` §3 대조

**§6 "1일차 (코드)" 범위는 전량 구현돼 있고, 코드로 실측 확인했다.**

| 항목 | 문서 요구 | 실제 코드 | 상태 |
|---|---|---|---|
| **A-1** 지표 2단 분해 | `SD_binary_κ`/`SD_type_κ`/obs·exp/direction_bias | `metrics.py:206 compute_sd_axes`, `compute_iaa.py:112-113` SDbin·SDtyp 컬럼 | ✅ |
| **A-2** Tier 0 위생 점검 | 위반 CSV (gating 아님) | `scripts/tier0_check.py` (round2 실측 3건) | ✅ |
| **A-3** 판정 큐 | 층화 S1>S2>S3>S4, 배타 배정 | `build_adjudication_queue.py`, `--s2-filter` default `strong` → 113건 | ✅ |
| **A-4** NCT03800134 원문 복구 | input.json | `iaa_workspace/NCT03800134/stage1/input.json` | ✅ (단 §5-1 참조) |
| **B-1** GOLD 액터 | round 폴더에 GOLD 기록 | `streamlit_app.py:87 GOLD_ACTOR = "GOLD"` | ✅ |
| **B-2** blind 토글 | 숨김이 아니라 **미로드** | `build_adjudication_seed`가 `peer_records`를 인자로 안 받음. blind 시 peer 탭 자체가 없음 | ✅ |
| **B-3** span 검증 | 비부분문자열 저장 거부 + override | `adjudication.py:125 span_violations`, `:232` override 없으면 차단 | ✅ |
| **C-1** peer notes 원문 표시 | 있는 경우에만 | `_render_peer_panel` (blind OFF 전용) | ✅ |
| **C-2** 판정 기록 필드 | tier·rationale_short 필수, 분해 시 child_rationale 필수 | `validate_adjudication` (`:210-227`), UI `:659-722` | ✅ |
| **C-2-🔴** tier=3 → gap ticket | GOLD에 null 라벨 금지 | `streamlit_app.py:1005 is_gap`, `build_gap_ticket` | ✅ |
| **D-2** GOLD 포함 3쌍 산출 | 코드 수정 0 | `compute_iaa.py --round` 동작 확인 | ✅ |
| **D-1/D-3/D-4/D-5** | 판정 **후** 코드 작업 | `scripts/`에 없음 | ⏸ 단 **D-1-lite·GPT비교는 초록 크리티컬 패스** (§9) |

### v2 가이드 §2-4 입력 항목 ↔ 코드 매핑 (전부 존재)

| v2 가이드 (일상용어) | 코드 필드 | 검증 |
|---|---|---|
| 정답 라벨 ★ | `splitting_decision` | enum 검사 |
| 근거 등급 ★ | `tier` (0/1/2/3) | 필수 |
| 이유 한 줄 ★ | `rationale_short` | 필수 (미입력 시 저장 거부) |
| 조각별 이유 ★ | `sub_criteria[].rationale` | 분해 시 필수 |
| 규칙 번호 | `rule_id` | 자동 추천 **의도적으로 없음** |
| 규칙 상태 | `rule_status` (existing/new/conflict/gap) | enum 검사 |
| PI 확인 | `escalate_pi` | bool |
| — | `span_override` | 비부분문자열 span 저장 시 사유 필수 |

**`rule_status` 4값이 이미 있으므로, "당시 규칙으로도 틀림 / 이후 정련으로 뒤집힘"을 분리 보고하는 데는 코드 수정이 필요 없다.**

### 화면에 이미 표시되는 것
- `stratum` + `s1_kind` 배지 (`streamlit_app.py:950-952`) → `S1 (resolved)` 형태
- `⚠️ §7.2 예외조항 충돌` / `🚩 Tier 0 위반` / `S2 위험 신호` / `✅` / `🎫`
- "미판정 항목만 보기" 필터
- GOLD 포함 쌍 선택 시 **비교 불가 경고**

---

## 4. 판정 시작 전 반드시 고쳐야 할 것 (4건)

### ❌ 갭 1 — `child_logic`이 macro_aggregate에서 입력 불가

**근거 문서**: guideline v1.2.1 변경 #2 / spec v1.2.3 패치 변경 1 — "composite_split·macro_aggregate **모두** child_logic 항상 명시, 기본값 생략 규칙 폐지"

**현재 코드** (`iaa_pipeline/streamlit_app.py:436-449`) — 판정 폼도 이 함수를 공유한다:

```python
with col2:
    if decision == "composite_split":
        cl_value = seed.get("child_logic") or "(unset)"
        child_logic_choice = st.selectbox("child_logic", CHILD_LOGIC_OPTIONS, ...)
        child_logic_val = None if child_logic_choice == "(unset)" else child_logic_choice
    else:
        child_logic_val = None                                    # ← macro면 값을 버림
        st.markdown("_child_logic only applies to composite_split_")
```

**영향**: 판정자가 `macro_aggregate`를 고르는 순간 입력란이 사라진다. 61건 중 "쪼갤까 말까" 유형이 다수(감사 25건의 핵심 패턴)라 첫 세션에서 바로 걸린다.

#### 🔬 검증 결과 — 수정 범위는 **두 층**이지 세 층이 아니다

외부 검토가 "UI·판정검증·스키마검증 세 층이 같은 규칙을 봐야 한다"고 지적했으나, 실측 결과 한쪽은 **위험이 실재하지 않는다.**

| 층 | 실측 | 조치 |
|---|---|---|
| **UI** `streamlit_app.py:436` | macro에서 입력란 미생성 | ✅ **수정** — `("composite_split", "macro_aggregate")`로 확장 |
| **판정 검증** `adjudication.py validate_adjudication` | `child_logic`을 **전혀 검사하지 않음.** `build_gold_record:269-270`이 저장만 함 | ✅ **수정** — split 계열이면 필수로 강제 |
| **스키마 검증** `stage_schemas.py validate_stage1_record` | "composite 전용" 단언 **없음** (아래 참조). macro+OR gold가 거부되지 않음 | ⛔ **손대지 말 것** (아래 사유) |

```python
# stage_schemas.py:247-251 — child_logic 관련 코드는 이게 전부. enum 체크뿐.
child_logic = record.get("child_logic")
if child_logic is not None and child_logic not in CHILD_LOGIC:
    errors.append(f"invalid child_logic: {child_logic!r} ...")
```

**`validate_stage1_record`를 건드리면 안 되는 이유**: 이 함수는 **판정 경로에서 호출되지 않는다.** 호출처는 어노테이션 폼(`streamlit_app.py:802`), 호스팅 앱(`stage1_app.py:477`), LLM 출력 검증(`stage_runner.py:203`) 세 곳뿐이다. 즉 **EHJ/DYK의 라운드 1·2 라벨과 LLM 출력을 검증하는 층**이다. 여기에 v1.2.1 규칙을 넣으면 라벨링 당시 규칙으로 만들어진 기존 작업이 무효로 뜬다 — `tier0_check.py`에 적용한 원칙과 동일하다.

**같은 이유로 `tier0_check.py:74`도 손대지 말 것**:
```python
# scripts/tier0_check.py:53, 72-74
"composite_split인데 child_logic이 null/공백 (결합 규칙 미명시)",
if ...: out.append(("T0_COMPOSITE_NULL_CHILD_LOGIC", f"child_logic={cl!r}"))
```
라벨링 **당시 규칙**으로 점검하는 위생 검사다. macro까지 확장하면 "라벨링 이후 생긴 규칙" 위반이 대량으로 뜨는데, 그건 Tier 0 위반이 아니라 판정 시 `rule_status=new`로 분류할 사안이다.

#### 구현 지침 — 검증은 **양방향**으로

`validate_adjudication`에 두 방향을 모두 넣는다. require만 넣으면 반대편이 열린다.

| 방향 | 규칙 (v1.2.1) |
|---|---|
| **require** | `composite_split` / `macro_aggregate` → `child_logic` 필수 |
| **forbid** | `nested_exception` / `none` → `child_logic`이 있으면 거부 |

UI의 `else` 분기가 `None`으로 만들긴 하지만, 검증층이 forbid를 명시해야 외부에서 들어온 오염값이 gold에 못 들어간다. 이 함수는 **gold만 검증**하므로 레거시 라벨과 충돌하지 않는다.

테스트 2건: macro에 child_logic 미입력 시 거부 / nested_exception에 값이 있으면 거부.

**규모**: ~15줄 + 테스트 (당초 ~4줄에서 상향).

---

### ❌ 갭 2 — `needs_recursion` 플래그가 존재하지 않음

**근거 문서**: `adjudication_guide_v2_notion.md` §3-3
> "A이고, 그리고 (B1 또는 B2)" 같은 문장은 v1.2.1대로면 여러 계층으로 나눠야 하지만, **이번에는 최상위 라벨 + 직계 조각까지만** 정하고 `needs_recursion` 플래그를 켜둠.
> - 플래그 켠 항목은 초록의 오답 집계에서 **제외** (라벨 차이가 아니라 표기 방식 차이라서)
> - 마감 후 플래그 목록만 모아 계층 완성 작업을 한 번 더 함

**현재 코드**: `needs_recursion` 문자열이 저장소 전체에 **없다.** 옵션 B 결정 이후 생긴 요구라 미구현.

**필요한 것**:
1. 판정 폼에 체크박스 + 한 줄 메모 (`recursion_note`)
2. `adjudication.py:251 build_gold_record`에 두 필드 저장
3. 항목 목록에 🔁 배지

**왜 판정 *전*이어야 하나**: 이 플래그가 초록의 both-wrong 집계 **제외 목록을 자동 생성**하는 장치다. 없이 판정하면 나중에 61건을 다시 훑어 재구성해야 하고, 그 시점엔 판정 당시의 판단 근거가 남아 있지 않다. **집계 스크립트(§9)의 필수 입력이기도 하다.**

**설계 참고**: 혼합 로직 항목(예: KEYNOTE-671 I3)은 단층 프레임에서 `macro_aggregate`, 재귀 프레임에서 최상위 `composite_split(AND)`가 될 수 있다. 어노테이터는 단층 프레임에서 라벨했으므로 이 불일치는 **오류가 아니라 프레임 차이**다. 61건 중 1~3건 예상.

**규모**: ~15줄 + 테스트.

---

### ❌ 갭 3 — 큐 순서가 61건 계획과 불일치 (앱 아님, 스크립트)

**근거 문서**: `adjudication_guide_v2_notion.md` §4-1 — 해소 15 → 무작위 감사 25 → 지속 21

**현재 코드**: `build_adjudication_queue.py:341 sort_queue`가 층 우선(S1 > S2 > S3 > S4) 순으로 `priority`를 부여한다. S1 내부는 persist/resolved/new를 구분하지 않는다.

**좋은 소식**: 필요한 태깅이 **이미 있다.**
```python
# build_adjudication_queue.py:269-278, 296
s1_kind = ""
if ...:  s1_kind = "persist"    # 두 라운드 모두 불일치 → 21건
elif ...: s1_kind = "resolved"  # 1차에만 불일치      → 15건
elif ...: s1_kind = "new"       # 2차에 새로 생김     → 13건 (이번엔 제외)
```
`_FIELDS`(`:356`)에 CSV 컬럼으로 포함돼 있고, 앱은 이미 화면에 표시한다.

**앱은 수정 불필요**: `adjudication.py:104-110 load_queue`가 `priority` 순으로 정렬하므로 큐만 바꾸면 앱이 따라온다.

#### 🔬 검증 결과 — S4 표본 재추첨 위험

외부 검토의 "S4 무작위 25건이 바뀌면 안 된다"는 지적은 타당하다. 실측:

```python
# build_adjudication_queue.py:372-375
--s4-size  default=25
--seed     default=20260730    # "S4 sampling seed — FIXED and reported"
```
**seed는 이미 고정**이므로 동일 플래그 재실행 시 표본은 재현된다. 그러나 **진짜 위험은 `--s2-filter`다** — S4 프레임이 "round-2 일치 − S2 − S3"이라, S2 필터가 바뀌면 프레임이 바뀌고 표본도 바뀐다.

**권장 방식**: 큐를 **재생성하지 말고 기존 CSV의 `priority` 컬럼만 재부여**한다. 층·표본·flags를 전부 보존하므로 재추첨 위험이 원천적으로 0이 된다. (재생성한다면 반드시 `--s2-filter strong --seed 20260730 --s4-size 25` 고정 + 기존 S4 목록과 diff)

**부수 확인**: §7.2 배지 4건 중 해소된 2건(NCT02474355 E8, NCT03728556 E6)은 `s1_kind=resolved`에 속하므로 abstract61 순서에서 자연히 ①블록 초반에 온다. 별도 처리 불필요.

**규모**: ~20줄.

---

### ❌ 갭 4 — `text_span` 세그먼트 배열 입력 **(권장 → 필수로 승격)**

**근거 문서**: v2 가이드 §3-2 2번 — "떨어진 표현은 이어붙이지 말고 세그먼트로 — `["locally advanced", "Stage III"]`" / spec v1.2.3 패치 변경 6

**현재 코드** (`streamlit_app.py:497, 510`): 단일 문자열이다.
```python
span = st.text_area("text_span", value=default_span, key=f"{key_prefix}_sub_{i}_span", height=68)
...
entry = {"child_id": child_id, "text_span": span.strip()}   # ← 문자열
```

#### 🔬 필수로 승격한 사유 (rev 1에서는 "권장"이었음)

당초 근거는 "D-4가 `span_override` 항목을 few-shot에서 자동 제외한다"였는데, 더 무거운 근거 두 개가 있다.

**① 동결 준거와 산출물 형식의 모순.** 판정 준거를 v1.2.3 패치 포함으로 동결했고, 패치 변경 6이 배열 형식을 명시한다. 문자열+override로 gold를 만들면 **"v1.2.3 기준으로 판정했다"는 Methods 서술과 reference standard 자체의 형식이 어긋난다.** 초록 숫자를 막지는 않지만 정답셋의 정합성 문제다.

**② 미루면 "재작업"이 아니라 "복원 불가".** 마이그레이션 규칙("1개짜리 배열로 감싸기")은 단일 세그먼트에만 작동한다. override로 이어붙인 span(`"locally advanced Stage III"`)은 **어디서 끊어야 할지 정보가 데이터에 없어** 자동 변환이 불가능하다. `span_override` 사유 텍스트에도 경계 정보는 남지 않는다. `adjudication_handover.md` §10-3 실측(어노테이터 span의 10~25%가 비부분문자열)대로면 61건 중 **6~15건이 수동 재분할 대상**이 된다.

**③ 부작용(기존 근거).** 붙여 쓰면 `span_violations`에 걸려 매번 `span_override`를 써야 하고, D-4(few-shot 변환)가 그 항목을 자동 제외한다(`adjudication_handover.md` §0.3-🟡2).

**`||` 구분자 폴백은 권장하지 않는다.** 시간이 정 없으면 `locally advanced||Stage III` 표기로 나중 마이그레이션을 기계적 split으로 만들 수 있으나, 동결된 reference standard에 비표준 구분자를 넣으면 **v1.2.3 준수도 아니고 평문도 아닌 상태**가 되고 모든 다운스트림 소비자가 그 규약을 알아야 한다. 40줄이면 제대로 넣는 편이 낫다.

#### 구현 지침 — `span_override`의 지위 재정의

세그먼트 배열이 들어오면 **override의 정당한 사용처가 사실상 0**이 된다. v1.2.1의 모든 케이스가 substring으로 해결되기 때문이다:

| v1.2.1 규칙 | 세그먼트 배열에서의 처리 |
|---|---|
| Text_span (1) 개체 공통 표현 | 복제 금지 → 상위 AND 계층 (override 불필요) |
| Text_span (2) 떨어진 조각 | 세그먼트로 분리 (override 불필요) |
| Text_span (3) 제약 표현 | 해당 child마다 세그먼트 추가 (각각 substring) |
| Text_span (5) 예외 조각 | 트리거부터의 연속 구간 (substring) |

따라서 **기본 경로 = 세그먼트별 substring 하드 거부**로 단순화한다. 다만 `span_override` 필드는 **명시적 탈출구로 유지**한다 — 가이드라인 때문이 아니라 **입력 경로 때문**이다: 판정자가 `st.markdown`으로 렌더된 원문에서 드래그 복사할 때 렌더링이 문자를 바꿀 수 있다(비단절 공백, `µ`/`μ`, 특수 하이픈, 연속 공백 축약). 탈출구가 없으면 61건 작업이 그 지점에서 멈춘다.

- override 사용 시 **큰 경고** + 레코드에 자동 플래그
- 경고 문구는 "세그먼트를 잘못 잘랐다는 신호"로 표현 (예외가 아니라 오류 경로임을 명시)
- D-4가 자동 제외하고, 사후 감사도 가능해진다

배열과 override가 어정쩡하게 공존하지 않고 override가 "예외적 오류 경로"로 지위가 명확해진다.

**규모**: ~40줄. `text_area` 하나를 "세그먼트 N개 입력 + 추가/삭제" + 저장 시 배열로 바꾸는 것. **계층 구조는 건드리지 않는다** — §6(재귀 UI)과 규모가 전혀 다르다.

---

## 5. 신규 발견 — 초록 크리티컬 패스 리스크 (2건)

외부 검토·본 문서 rev 1 모두 놓쳤던 항목. **GPT 비교 문단(초록 조건부)에 직접 영향한다.**

### ⚠️ 5-1. AEGEAN(NCT03800134)에 보관된 LLM 예측이 없다

IAA 8 trial × `llm_output.json` 존재 여부 실측:

```
NCT01295827   iaa_workspace:✓   bundle:✓
NCT02075840   iaa_workspace:✓   bundle:✓
NCT02125461   iaa_workspace:✓   bundle:✓
NCT02474355   iaa_workspace:✓   bundle:✓
NCT02912949   iaa_workspace:✓   bundle:✓
NCT03728556   iaa_workspace:✓   bundle:✓
NCT03800134   iaa_workspace:✗   bundle:✗      ← 8개 중 유일
NCT05756153   iaa_workspace:✓   bundle:✓
```

AEGEAN이 나중에 추가되면서(commit `e0da99c`) `input.json`만 복구되고(handover A-4) `llm_output.json`은 만들어지지 않았다.

**영향**: GPT 비교 스크립트가 **8 trial 중 7개만 커버**한다. 지속 21건·감사 25건에 AEGEAN 항목이 포함되므로 초록의 `[X%] vs [Y%]`가 부분 표본이 된다.

**선택지**: (a) AEGEAN에 대해 prompt_1을 재실행해 예측 생성 — 단 **현행 프롬프트는 pre-calibration이 아니므로** "보관된 예측"과 조건이 달라진다 / (b) 비교 대상을 7 trial로 명시하고 분모를 밝힌다. **(b) 확정** — 초록 주장이 "인간이 애매해한 항목은 LLM도 어렵다"이므로 7 trial로도 성립하고, (a)는 프레임을 오염시킨다.

#### 🔬 분모 확정 (2026-08-25 실측, `results/adjudication/adjudication_queue.csv` 113건)

| 블록 | 건수 | AEGEAN | GPT 비교 분모 |
|---|--:|--:|--:|
| ① 해소 (S1-resolved) | 15 | 3 (E10·E11·I5) | — (LLM 비교 대상 아님) |
| ② 감사 (S4) | 25 | 4 (E4·E12·I1·I3) | **21** |
| ③ 지속 (S1-persist) | 21 | 3 (E2·E9·I9) | **18** |
| **GPT 비교 합계** | **46** | **7** | **39** |

**판정 전에 초록 문구를 확정할 수 있다**:
> "...criteria from seven trials with archived pre-calibration predictions (n=39 of 46; one trial added after the initial pipeline run lacks archived output)"

[X/15]·[Y/15](해소 블록)와 [X/25](감사 블록)는 gold vs 어노테이터 비교이므로 **AEGEAN 제외 없이 전수**를 쓴다. 분모 축소는 GPT 비교 문단에만 적용된다.

### ⚠️ 5-2. "GPT-4.1-mini"라는 근거가 봉투 안에 없다

보관된 예측 봉투 실측:
```
model:      "production-pipeline-v1.2.1"     ← 모델 id가 아니라 출처 라벨
created_at: "2026-05-27T03:47:07Z"
source:     "llm"
notes:      "Extracted from production pipeline output (pipeline/output/NCT*_annota...)"
```

`convert_production_to_iaa.py`가 프로덕션 출력을 변환하며 붙인 provenance 문자열이다. 실제 모델은 `pipeline/config.py`의 활성 프리셋에서 추론해야 한다:

```python
# pipeline/config.py:34-41 — Preset A 활성
MODELS = {
    "prompt_1": "gpt-4.1-mini",       # Splitting — pattern matching, Mini 충분
    ...
}
```

**주장 자체는 성립**하지만, 2026-05-27 실행 당시에도 Preset A였는지는 봉투가 증명하지 못한다. Methods에 모델을 명시하려면 `pipeline/HANDOFF.md`의 실행 기록으로 **한 번 교차 확인**할 것.

**초록 문구 권장**: "pre-calibration predictions generated with the initial prompt (GPT-4.1-mini, run 2026-05-27)" — 리뷰어 공격면을 줄인다.

---

## 6. 하지 말아야 할 것

### 🚫 재귀 계층 UI

`streamlit_apps/handover_streamlit_hierarchical_labeling.md`가 요구하는 것: 작업 큐 모델(한 화면 = 한 항목 = 한 계층), 경로 기반 ID(`NCT..._I3.b.a`), DFS 큐, `depth`/`parent_criterion_id`, 컨텍스트 하이라이트 패널, 진행률, 마이그레이션 스크립트.

**이번 판정에서 구현하지 않는다.** 근거:
- 초록 placeholder 전부가 **최상위 SD 라벨**로 충족된다. 재귀 깊이는 어떤 숫자에도 안 들어간다
- EHJ/DYK 라벨이 **단층**이다. gold만 계층이면 child#·span 비교가 정의상 깨진다
- 재귀는 항목당 판정 횟수를 조각 수만큼 늘린다 — 9일 경로에서 감당 불가
- 대신 `needs_recursion` 플래그로 **기록하며 미룬다** (갭 2)

이 문서는 Paper 1 트랙으로 보류. **갭 4(세그먼트 배열)와 혼동하지 말 것** — 갭 4는 계층을 만들지 않고 배열 입력만 추가하는 ~40줄 작업이다.

---

## 7. 문서 정리 필요 항목 (5건)

| # | 내용 | 제안 |
|---|---|---|
| 1 | `annotation_guideline_v1_2.md`와 `_v1_2_1.md` 공존 | v1.2.1이 동결본. v1.2 삭제 또는 `_superseded` 표기 |
| 2 | `adjudication_guide_notion.md`(113건)와 `_v2_notion.md`(61건) 공존 | v2가 최신. v1 삭제 또는 아카이브 |
| 3 | `CLAUDE.md`의 Key documentation이 v1.2.2 스펙만 언급 | v1.2.3 패치·guideline v1.2.1·v2 판정 가이드 추가 |
| 4 | 판정 준거 5개 문서가 git 미추적 | 판정 시작 전 커밋 + **태그** (아래) |
| 5 | `iaa_pipeline_spec/iaa_8trials.txt`의 이름·내용 불일치 | §8 참조. 파일명은 8, 내용은 9줄, 실제 IAA는 8. 목적 주석 추가 권장 |

### 7-4 보강 — 동결 커밋에 태그를 붙일 것

```bash
git tag adjudication-freeze-20260825
```
"판정 준거 동결"의 실효적 정의가 커밋 해시가 되고, 논문 Methods의 "guideline version frozen prior to adjudication"이 **검증 가능한 주장**이 된다.

### 문서 내부 정합성 이슈 (참고)

- `adjudication_handover.md`(07-30)는 **113건·단층 판정** 전제로 쓰였고 그대로 구현돼 있다. v2 가이드의 61건·`needs_recursion`은 그 이후 결정이므로 handover와 불일치하지만, **handover가 틀린 게 아니라 스코프가 재편된 것**이다
- handover §7.4/§C-2 스키마에 `needs_recursion`이 없다 — 갭 2를 구현하면 이 문서에도 필드 추가 필요

---

## 8. 테스트 현황 + "Eight trials" 정체 (해결)

```
python tests/test_adjudication.py    →  36/36 통과
python tests/test_iaa_metrics.py     →  35/37 통과
```

실패 2건: `test_iaa_filter_file_exists_and_parses`, `test_hosted_app_lists_only_iaa_trials` — 둘 다 `iaa_8trials.txt`가 9개인데 테스트가 8을 기대.

### 🔬 검증 결과 — 9번째는 pilot trial이다

`iaa_8trials.txt` 9줄 중 **라운드 라벨이 존재하는 것은 8개**이고, `NCT03425643`만 `round1`/`round2` 폴더가 **0개**다.

`pipeline/HANDOFF.md:512`에 정체가 명시돼 있다:
```
NCT03425643  KEYNOTE-671  (pilot, macro_aggregate)
```
그리고 `pipeline/prompts/examples.json:42, 99, 171`의 few-shot 예시가 전부 KEYNOTE-671(NCT03425643) 출처다.

**주의 — 흔한 오해**: "원래 8은 AEGEAN 없는 8"이 아니다. 실제 **IAA 8 = 9줄 − NCT03425643**이고 **AEGEAN(NCT03800134)은 포함**된다. 파일이 8→9로 커진 이력과 실제 실험 8개는 서로 다른 집합이다. `iaa_8trials.txt`는 IAA trial 정의가 아니라 **호스팅 앱 드롭다운 필터**이며, 이름과 내용이 둘 다 오해를 부른다.

**결론**:
- 초록의 `"Eight trials (excluding one pilot trial used for worked examples)"`는 **정확한 표현**이다
- 파일럿이 프롬프트 few-shot의 출처이므로 IAA·held-out에서 빠지는 것이 방법론적으로도 옳다 (leakage 회피)
- 테스트는 파일 목적(호스팅 드롭다운 필터)에 맞게 9를 기대하도록 수정하거나, 파일에 목적 주석을 추가

---

## 9. 작업 규모 및 일정

### 판정 전 (8/26)

| 작업 | 규모 |
|---|--:|
| 갭 1 — child_logic macro 허용 (UI + `validate_adjudication` 2층) | ~15줄 + 테스트 |
| 갭 2 — `needs_recursion` 플래그 | ~15줄 + 테스트 |
| 갭 3 — 큐 61건 재정렬 (priority만 재부여) | ~20줄 |
| 갭 4 — text_span 세그먼트 배열 | ~40줄 |
| §7 문서 정리 + git 커밋·태그 | ~30분 |
| §5-1 AEGEAN 예측 처리 방침 결정 | 판단 |
| §5-2 모델 출처 교차 확인 | ~10분 |

→ **8/26 하루로 충분. 8/27 판정 시작 유지 가능.**

### 판정 중~직후 (8/28~30) — **초록 크리티컬 패스**

당초 §3에서 "⏸ 판정 후 작업"으로 분류했으나, **초록 마감 기준으로는 8/30까지 있어야 하는 필수 항목**이다.

| 작업 | 시점 | 요건 |
|---|---|---|
| **초록 집계 스크립트 (D-1-lite)** | 8/28~29 작성, 8/30 실행 | X/15·Y/15, X/25, 기전 클러스터. **`rule_status=new`와 `needs_recursion` 건을 분리 계수**하는 로직 필수 — 없으면 판정해도 초록 숫자가 안 나옴 |
| **GPT 비교 스크립트** | 8/28~29 | 보관된 pre-calibration 예측 vs gold. 대상: 지속 18 + 감사 21 = **39** (§5-1 분모 확정) |
| A-1 확장 (PABAK / Gwet's AC1 / Bias·Prevalence Index) | 판정과 병행 | "observed +1.1%p vs κ +0.042"를 kappa paradox 문헌으로 정식화 |

#### D-1-lite 구현 지침 — 필드 추가 대신 **조인**

[X/15]·[Y/15] 계수에 `s1_kind`가 필요하지만 **gold record에 필드를 추가하지 말 것.** 큐 CSV에 이미 있고(`build_adjudication_queue.py:356 _FIELDS`), gold record에는 `queue_stratum`(`adjudication.py:293`)과 `compared`(`:295`)가 저장된다. **`criterion_id`로 조인**하면 충분하다 — 동결한 저장 스키마를 안 건드리는 것이 준거 동결 취지와도 맞는다.

### 초록 마감 구간 (8/31~9/2) — 이 문서 범위 밖

앱·코드 문서라 여기서 다루지 않지만, 전체 타임라인을 이 문서로 추적한다면 참고:
**8/31~9/1** 숫자 삽입 + 문장 확정(방향 편향 한 문장, 판정자 공개, pre-calibration 프레임 명시) · **9/2** 버퍼 + PI 검토 · **9/3** 마감

### 하지 않는 것
재귀 계층 UI, prompt_1 수정, few-shot 재생성, 기존 봉투 text_span 마이그레이션, S3, held-out 샘플링, 3라운드 → **Paper 1 트랙**

---

## 10. rev 1 → rev 2 변경 내역

| # | 변경 | 사유 |
|---|---|---|
| 1 | 갭 4 **권장 → 필수** 승격 (§5 → §4) | 동결 준거와 형식 모순 + 이어붙인 span은 **복원 불가**(경계 정보 소실) |
| 2 | 갭 1 범위 **"세 층" → "두 층"** 정정, 규모 ~4줄 → ~15줄 | `validate_stage1_record`에 "composite 전용" 단언이 **없음**을 실측 확인. 대신 `validate_adjudication`이 child_logic을 **전혀 검사하지 않음**을 발견 |
| 3 | 갭 3에 S4 재추첨 분석 추가 | seed는 이미 고정(20260730). 진짜 위험은 `--s2-filter` 프레임 변경 → "priority만 재부여" 방식 권장 |
| 4 | §8 "Eight trials" **규명 완료** | 9번째 = NCT03425643 = KEYNOTE-671 pilot, 라운드 폴더 0개. `HANDOFF.md:512` 근거 |
| 5 | **§5 신규 발견 2건 추가** | AEGEAN llm_output 부재(8중 7만 커버), 봉투에 모델 id 없음 |
| 6 | §9에 판정 중~직후 크리티컬 패스 추가 | rev 1은 판정 **전** 작업만 잡아 8/30~9/1 구간이 비어 있었음 |
| 7 | §7에 git 태그 항목 추가 | 준거 동결을 검증 가능한 주장으로 |

### rev 2 → rev 2.1 (2차 검토 반영)

| # | 변경 | 사유 |
|---|---|---|
| 8 | 갭 1에 **양방향 검증** 지침 (require + forbid) | require만 넣으면 nested/none에 오염값이 들어갈 경로가 열림 |
| 9 | 갭 4에 **`span_override` 지위 재정의** 지침 | 세그먼트 배열 후 정당한 사용처 0 → 하드 거부 기본 + 탈출구는 오류 경로로 유지 (드래그 복사 시 문자 변형 대비) |
| 10 | §5-1에 **분모 확정 표** | 큐 CSV 실측: 지속 21 중 AEGEAN 3(E2·E9·I9), S4 25 중 4 → GPT 비교 분모 **39/46**. 판정 전에 초록 문구 확정 가능 |
| 11 | §9에 **D-1-lite 조인 지침** | gold record에 `s1_kind` 필드를 추가하지 말고 큐 CSV와 `criterion_id` 조인 — 동결 스키마 보존 |
| 12 | §9에 **8/31~9/2 구간** 한 줄 | rev 2 일정이 8/30에서 끊겨 마감 구간이 어디에도 없었음 |

---

## 부록 A. 블라인딩 아키텍처 (수정 시 반드시 지킬 불변식)

`audit_streamlit_v1.md`의 누출 A1~A7 대응 구조. **UI를 고칠 때 이 형태를 깨지 말 것.**

1. **함수 시그니처 수준의 보장**: `render_criterion_form_blind`는 `llm_record`를 **인자로 받지 않는다**. `render_adjudication_form_blind`는 `peer_records`를 **인자로 받지 않는다**. 넘기려 하면 `TypeError`
2. **미로드**: blind 상태에서 peer 파일을 숨기는 게 아니라 **읽지 않는다** (session_state 캐싱 누출 방지)
3. **탭 게이팅**: blind일 때 peer 탭이 탭 목록에서 아예 제외된다
4. **단일 chokepoint**: 폼 기본값은 전부 `build_form_seed` / `build_adjudication_seed`를 통과한다
5. 회귀 테스트가 이 시그니처들을 검사한다 (`test_blind_render_signature_rejects_llm_record`)

## 부록 B. 판정 실행 방법

```bash
# 큐: 재생성보다 기존 CSV의 priority 재부여를 권장 (§4 갭 3)
# 부득이 재생성 시 반드시 플래그 고정:
python scripts/build_adjudication_queue.py --out results/adjudication \
    --s2-filter strong --seed 20260730 --s4-size 25
python scripts/tier0_check.py --round 2 --out results/adjudication

# 판정 UI
streamlit run iaa_pipeline/streamlit_app.py
#   사이드바 → Role: Adjudicator — gold set (GOLD) / Round: 2 / 🔒 Blind pass: ON

# 진행 확인
python scripts/compute_iaa.py --stage 1 --round 2
#   ⚠️ EHJ-GOLD·DYK-GOLD를 EHJ-DYK와 나란히 비교하지 말 것 (편향 표본이라 구조적으로 낮음)
```

## 부록 C. 검증 로그 (2026-08-25)

이 문서의 주장 중 **코드/데이터로 직접 확인한 것**과 근거.

| 주장 | 근거 |
|---|---|
| 판정 앱 A-1~D-2 구현 완료 | 각 함수·줄번호 직접 확인 (§3 표) |
| `validate_stage1_record`에 composite 전용 단언 없음 | `stage_schemas.py:247-251` 전문 확인 |
| `validate_adjudication`이 child_logic 미검사 | `adjudication.py` 내 `child_logic` 출현 4곳 전수 확인 (`:9` docstring, `:269-270` 저장, `:391` gap ticket) |
| `validate_stage1_record` 호출처 3곳 | grep 전수: `streamlit_app.py:802`, `stage1_app.py:477`, `stage_runner.py:203` |
| S4 seed 고정값 20260730 | `build_adjudication_queue.py:372-375` |
| `s1_kind` 태깅 존재 | `build_adjudication_queue.py:269-278, 296, 356` |
| IAA 8 trial = 9줄 − NCT03425643 | `iaa_workspace/*/stage1/round{1,2}` 디렉토리 열거 (각 8개, NCT03425643 0개) |
| NCT03425643 = KEYNOTE-671 pilot | `pipeline/HANDOFF.md:512`, `pipeline/prompts/examples.json:42,99,171` |
| AEGEAN llm_output 부재 | 8 trial × 2 경로 파일 존재 확인 |
| 봉투 model = provenance 문자열 | `iaa_workspace/*/stage1/llm_output.json` 3건 파싱 |
| Preset A 활성 (`prompt_1: gpt-4.1-mini`) | `pipeline/config.py:34-41` |
| 테스트 36/36, 35/37 | 두 스크립트 실행 |
| 층별 건수·AEGEAN 분포 (15/25/21, AEGEAN 3/4/3) | `results/adjudication/adjudication_queue.csv` 113행 파싱 (2026-07-30 생성본) |
| gold record에 `queue_stratum`·`compared` 존재 | `adjudication.py:258-259, 293-296` |

**추론(미검증)**: 2026-05-27 프로덕션 실행 당시의 활성 프리셋 — `config.py` 현재 상태로부터의 추론이며 실행 기록 교차 확인 필요 (§5-2).
