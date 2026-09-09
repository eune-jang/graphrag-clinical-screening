# PHASE 5A trace review — 요약

> 전문: [`TRACE_REVIEW.md`](TRACE_REVIEW.md) (1,399줄). 이 문서는 그 요약이며 **새로운 주장을 담지 않는다.**
> 감사일 2026-09-08 · read-only · 코드/프롬프트/canonical core 수정 없음 · API 추가 호출 없음

**성능 주장 없음.** 14건 합성 통합 케이스다. accuracy·모델 우열·tier 유병률을 말하지 않는다.
기계적 속성 14/14 일치가 뜻하는 것은 "선택된 스모크 메커닉이 의도대로 동작했다" 뿐이다.

---

## 한 문단 결론

**런타임은 문제없다.** 15 패스 전건이 첫 시도에 파싱·검증을 통과했고 span 위반 0, 재시도 0,
불완전 계층 0이었다. 실질 발견은 두 가지다 — 모델이 **공유 qualifier를 한 자식에만 복사한 사례 1건**(S04),
그리고 **결정적 규칙이 아닌 확인 규칙(H2-A)을 primary로 골라 Tier 0을 주장한 사례 3건**(S03·S12·S13).
후자는 3건에서 같은 방향으로 반복돼 **메커니즘이 확인됐다**(비율이 아니다).
모델 능력 문제를 시사하는 관측은 **0건**이다.

---

## 검증된 수치 (원본 파일 재계산)

| 지표 | 값 |
|---|--:|
| 검토 패스 | **15** (root 14 + 재귀 1), 전수 |
| 유료 호출 + 프로브 | 15 + 1 = **16 / 50** |
| **재시도** | **0** |
| JSON 첫 시도 파싱 | **15 / 15** |
| **validator 첫 시도 통과** | **15 / 15** |
| validator 오프라인 재검증 | 15 패스 / **오류 0** |
| span 위반 | **0** |
| incomplete 노드 | **0** (`max_depth` 0, `empty_main` 0) |
| 토큰 | 103,517 + 3,730 = **107,247** |

**표기 차이 1건** (불일치 아님, 기존 파일 미수정): depth 분포가 `summary.json`은 케이스별 최대 depth
(0:13, 1:1), 패스 단위로는 (0:14, 1:1).

관측 분포 — decision: `none` 4 / `composite_split` 6 / `macro_aggregate` 2 / `nested_exception` 3.
tier: 2가 12건, **0이 3건**.

---

## 판정 집계

| | 결과 |
|---|---|
| Mechanical validity | **PASS 14 / 14** |
| Semantic review | **PASS 13 · QUESTIONABLE 1 · LIKELY ERROR 0** |
| Rule provenance | **적절 11 · 의심 4** (그중 tier 영향 3) |
| 케이스별 분류 | E 9 · D 3 · B 2 |

---

## 핵심 발견 3가지

### 1. S04 — 공유 qualifier 미복사 → **clear prompt/model adherence failure**

```
"Women who are pregnant or breastfeeding at the time of screening."
[a] ["Women who are pregnant"]                          ← qualifier 없음
[b] ["breastfeeding at the time of screening"]
notes: "…applies to both coordinated conditions by shared context."   ← 자기 출력과 모순
```

- **런타임 손실 아님** — 런타임은 `text_span` 내용을 생성·변형하지 않는다
- **복사 가능했음** — TARGET_SEGMENT 안의 축자 부분문자열
- **능력 문제 아님** — 같은 실행의 S05·S12에서 동일 유형을 정확히 복사
- **의미 손실 있음** — "스크리닝 시점 임신" ≠ "임신력"

프롬프트 측 원인 후보: X2의 *"grammatically incomplete … if ROOT/PARENT context supplies shared
meaning"* 절이 생략 허가로 읽힐 여지. **표본 1건, 일반화하지 않음.**

### 2. S05 — 형제 span 비대칭 → **이슈 아님 (E)**

두 자식 **모두** 공유 qualifier 보존, span provenance 전건 만족, 의미 손실 없음.
형태 차이는 원문 어순의 귀결이며(자식 b는 qualifier와 연속) X1이 명시 허용한다.
**대칭성은 요구되지 않는다.**

### 3. H2-A primary → **Tier 0 inflation 가능성 (normative 검토 필요)**

| case | H2-A가 split을 강제했나? | 실제 경계 규칙 | 선호 primary | tier |
|---|---|---|---|---|
| S03 | ❌ | H1-B → canonical H2-B가 진단 vs 바이오마커를 직접 규정 | **H2-B** | 0 → 1 |
| S12 | ❌ | H1-B | **H1-B** | 0 → 2 |
| S13 | ❌ | H1-B | **H1-B** | 0 → 2 |

canonical은 H2-A를 *"validates the H1 proposition boundary"* 로 규정 — **확인 규칙**이다.
**S12·S13은 모델이 H1-B를 supporting에 직접 적어 넣었다** — 더 결정적인 규칙을 자기 출력에 나열하면서
primary는 다른 것을 골랐다. tier 0은 "스펙 구조만으로 결정"이라는 가장 강한 권위 주장이다.

> 확인된 것은 **비율이 아니라 메커니즘**이다. 3/14를 일반화하지 않는다.

**그 밖**: H5가 구조 결정 primary로 오용된 사례 0건(전 패스 supporting으로만 등장, 올바름).
X-rule 과도 선택 0건(S02의 X5는 canonical이 직접 규정). S06/S07의 primary 불일치는 tier 영향 없음.

---

## 재귀 (S10) — end-to-end 검증됨

`derive_main_segments`를 **독립 재실행**해 저장값과 바이트 일치 확인.

| 확인 | 결과 |
|---|---|
| main 파생 재현 | ✅ 일치 |
| punctuation 보존 | ✅ 후행 콤마 유지 |
| exception 텍스트 잔존 | ✅ 없음 |
| PARENT_CONTEXT 규약 | ✅ 4필드, sibling_spans에 exception |
| root 격리 | ✅ |
| **exception span 재귀** | ✅ **자식 0개** |

---

## Phase 5B coverage gap — 결함 아님

실모델 미노출 (전부 mock 테스트에서는 통과):

`depth ≥ 2` · **split 자식 재귀**(관측된 재귀는 `["main"]` 하나뿐) · 복수 `recursion_targets` ·
형제 재귀 분기 · `max_depth` 가드 · `empty_main` · **재시도 경로** · 캐시 hit

Phase 5B 케이스 설계에서 **의도적으로 다단 구조를 넣어야** 이 경로들이 실모델로 검증된다.

---

## Issue disposition

| id | case | 내용 | class | severity | next action |
|---|---|---|---|---|---|
| **I-01** | S04 | 공유 qualifier를 한 자식에만 복사, 자기 notes와 모순 | **B** | material | prompt patch candidate |
| I-02 | S05 | 형제 span 비대칭 | **E** | none | no action |
| **I-03** | S03·S12·S13 | H2-A primary → Tier 0 주장 3건 | **D** | material | **normative review required** |
| I-04 | — | 재귀 1건·depth 1만 노출 | **A** | minor | add development test case |
| I-05 | — | openai SDK 1.6.1, `extra_body` 우회, 의존성 미선언 | **A** | material | investigate in Phase 5B |
| I-06 | — | 호출당 prompt 토큰 ≈6,900 | **A** | minor | no action |
| **I-07** ⭐ | — | **trace 로깅이 §6 요구 20항목 중 9개 누락** — 재시도 실패 응답 유실 위험 | **A** | material | **runtime fix required** |
| I-08 ⭐ | S06/S07 | 동일 유형 macro에서 primary 불일치 | **B** | minor | investigate in Phase 5B |

⭐ = 이번 감사에서 신규 등록

| class | 건수 |
|---|--:|
| A runtime/software | 3 |
| B prompt wording/adherence | 2 |
| **C model capability** | **0** |
| D normative-method | 1 |
| E no issue | 1 |

**C가 0건**인 것이 이번 감사의 특징이다.

---

## SDK 재현성 (기록만, 수정 없음)

`openai 1.6.1` (miniconda base, Python 3.11.5) · 최신 3.8.0 ·
**`requirements.txt`·`pyproject.toml` 어디에도 미선언** ·
`reasoning_effort`는 `extra_body`로 전달(1.6.1에 명시 파라미터 없음) ·
**응답에 적용 확인 metadata 없음** (`usage`는 토큰 3필드뿐).

reasoning effort가 비교 조건 변수인 단계에서는 **검증 가능한 기록 방법이 필요**하다.
결정 3안(SDK 업그레이드 / 우회 내재화 / 현행 유지) 미결.

---

## Phase 5B 설계 입력

**prompt patch candidate** (작성 금지 상태)
1. X2 — 문법적 불완전 허용 절이 공유 qualifier 생략 근거로 읽히는지
2. `primary_rule_id` 선택 지침 — 확인 규칙이 아니라 경계를 세운 규칙을 primary로

**normative review**
1. canonical의 "ONE primary decisive rule" 정의 / H2-A가 확인 규칙임을 더 강하게 규정할지.
   tier 파생이 primary에 직결되므로 tier 0 권위 주장에 직접 영향

**착수 전 처리 권고**: I-07 로깅 보강(코드 수정, 승인 필요) · I-04 다단 케이스 · I-05 SDK 결정

**READY FOR PHASE 5B DESIGN: YES** — blocker 없음.
