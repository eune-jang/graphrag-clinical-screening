# Handover — Stage 1 Splitting Adjudication (Gold Set 구축) · **검증 반영판 v2.3**

> **인계 대상**: Claude Code
> **작성 목적**: Stage 1(splitting) IAA 2라운드 종료 후, gold set 구축(adjudication)을 위한 코드 작업 및 UI 수정 인계
> **작성일 기준 상태**: IAA 1·2라운드 완료, 3라운드 미실시, 프롬프트 수정 보류
> **v2 성격**: 초안(v1)을 실제 코드·데이터와 대조해 사실관계를 교정한 버전. 전략·설계는 v1 유지, 코드/데이터 현황 전제만 수정. 교정 내역은 §0.1, 검증 근거는 §9.
> **v2.1**: v2 검토 라운드에서 발견된 파급 5건 반영(스키마↔자동발견 충돌, D-4 필드 유지, Tier 0 문구, A-2 강등, S4 순차표집). 변경은 §0.2, 근거는 §9-8~§9-10.
> **v2.2**: v2.1 검토에서 발견된 6건 반영 — ①v2.1이 새로 만든 두 결함(D-2 `--subdir`은 액터 1명이라 pairs=0 / tier=3 `null`이 κ 5번째 클래스로 오염), ②기존 설계 결함(S2 키워드가 umbrella/나열 위험을 놓침), child_rationale·S4 트리거·문서 정합. 변경은 §0.3, 근거는 §9-11~§9-12.
> **v2.3**: 착수 전 최종 검증(코드 **실행** 대조) 반영 6건 — 🟠E-G/D-G κ가 판정 표본(불일치 과대표집) 위에서 계산되어 E-D κ와 비교 불가(D-1/D-2 해석 가드), 🟡B-3 완료기준↔override 모순 + D-4 span 검증 충돌, 🟡streamlit_app.py의 round 비인지(B-1 구현 범위 명시), 🟡S2/S3 층 중복 규칙, ⚪gap ticket에 `tier`·`blind_label` 추가, ⚪D-4 템플릿 `notes` 누락·cohort_scope 위치 가변. v2.2의 🔴1/🔴2/§9-6 수치는 실행으로 전부 재확인됐고, **A-1은 이미 구현 완료**로 확인됨. 변경은 §0.4, 근거는 §9-13~§9-16.

---

## 0. 이 문서를 읽는 순서

1. **§0.1~§0.4 교정 요약 — 먼저 읽을 것.** 이전 버전을 본 사람은 무엇이 바뀌었는지 여기서 확인 (특히 §0.2 ①②·§0.3 🔴·§0.4 🟠1은 구현 전 필수)
2. §1 배경 — **반드시 읽을 것.** 왜 이 작업을 하는지 이해하지 않으면 잘못된 자동화를 만들게 됨 (특히 §1.4)
3. §2 용어 정의
4. §3 작업 목록 — 실제 구현 대상
5. §4 사람이 할 일 / §5 금지사항
6. §6 실행 순서
7. §7 부록 — 데이터 위치, 스키마
8. §9 검증 로그 — v2 교정의 코드 근거

---

## 0.1 v1 → v2 교정 요약

실제 코드베이스(2026-07-30 기준)와 대조한 결과, **전략적 판단은 모두 유효**하나 코드·데이터 현황에 대한 전제 6건이 실제와 달랐다. 근거는 §9.

| # | v1 서술 | 실제 | 영향 | 반영 위치 |
|---|---|---|---|---|
| 1 | EHJ/DYK notes가 "논거 원자료", 표시만 하면 재수집 불필요 | `rationale` 필드는 record·child **0건**. `notes`는 688 중 **47건(~7%)** | **D-3 재료는 harvest 불가 → 판정 중 C-2로 생성**해야 함. C-2 중요도 상승 | §3 C-1, C-2, D-3, §7.4 |
| 2 | §7.2 최우선 4건 모두 "현재 불일치" | 4건 중 **2건(NCT03728556 E6, NCT02474355 E8)은 2차에서 둘 다 none으로 해소** | 해당 2건은 S1(불일치)→**S2(일치+위험군)** 재분류. 문서 "둘 다 틀림" 가설의 오히려 강한 사례 | §7.2 |
| 3 | D-2 "compute_iaa.py를 액터 쌍 파라미터화" (신규 작업) | **이미 파라미터화됨.** 내용 기반 자동 발견 + 전체 페어 자동 계산 | GOLD를 committed 어노테이터로 저장 시 E-G/D-G/E-D **자동 산출**. (v2.1은 `--subdir` 일반화가 필요하다 했으나 v2.2에서 그것도 불가로 판명 → 안 A로 대체, §0.3-🔴1) | §3 D-2, B-1 |
| 4 | 재사용 대상 = `workspace.py` | `iaa_pipeline/workspace.py` **없음**(참고본만 `docs/audit_reference/`). 실제 앱은 `iaa_pipeline/streamlit_app.py` | 재사용 방향은 맞음, 파일명 교정 | §3 B-*, C-*, §7.1 |
| 5 | trial 원문 = `iaa_workspace/{trial}/input.json` | 실제 `iaa_workspace/{trial}/**stage1/**input.json` | 경로 교정 | §7.1 |
| 6 | A-2가 08_review_queries 3.2/3.3/2.2/2.3 이식 | **3.2/3.3만 이식 가능.** 2.2/2.3은 semantic_category(=Stage 2 데이터) 기반, Stage 1 envelope엔 없음 | A-2 스코프 축소 | §3 A-2 |

**변하지 않은 것(검증 통과)**: §1.2/§1.3의 모든 지표 수치, S1=49(21+15+13), matched 172, 방향편향(9→3 / 20→24), 유형 7→7, examples.json 예시 출처, streamlit_app.py의 blind/phase gating 실재, NCT03800134 input.json 결측, Stage 1 envelope에 semantic_category 없음. → **§1의 진단과 전략은 그대로 신뢰 가능.**

---

## 0.2 v2 → v2.1 교정 요약 (검토 라운드 반영)

v2를 다시 코드로 검증하는 과정에서, v2 교정의 **파급이 덜 반영된 지점 5건**을 발견해 반영했다. ①②는 구현 전 반드시 고쳐야 하는 정합성 버그였다. 근거는 §9-8~§9-10.

| # | 문제 | 조치 | 시급도 | 반영 |
|---|---|---|---|---|
| ① | §7.4 스키마가 `gold_label` 안에 `splitting_decision`을 중첩 → `metrics.py:201`이 record **최상위**의 `splitting_decision`을 읽으므로 **GOLD 축 SD κ가 전부 None**이 됨. v2의 "자동 발견" 주장과 자기모순 | gold를 **record 최상위**로 올리고 `blind_label`·`adjudication`만 부가 키로 | **구현 전 필수** | §7.4 |
| ② | v2 §5/§7.4가 `sub_criteria[].rationale`을 전면 금지 → 그러나 `prompt_1_splitting.txt:53-59`는 child `rationale`·`cohort_scope`를 **요구**하고 기존 examples도 전부 포함. D-4에 적용 시 프롬프트 계약 위반 | 방향 분리: **읽기**(사람 envelope)는 rationale 없음 전제 / **쓰기**(gold→few-shot)는 rationale·cohort_scope 필수. C-2에 child별 rationale 선택 입력 추가 | **구현 전 필수** | §5, §7.4, C-2, D-4 |
| ③ | §7.3 Tier 0 문구가 "권위 계층"과 "자동 검사 가능성"을 혼동 → "단일 semantic_category = Stage 2 소관"으로 오해되어 **가장 강한 판정 논거**가 강등될 위험 | Tier 0 = spec 구조 제약(권위). 자동 검출 여부와 무관. 단일 category도 Tier 0이되 사람이 직접 확인 | 판정 시작 전 | §7.3 |
| ④ | A-2가 3.2/3.3만 남으면 실측 위반 **5건뿐**(§9-9) → gating 아님. 한편 S4는 both-wrong base rate를 모른 채 20~30% 고정 표집 | A-2를 "위생 점검"으로 강등(선행조건 해제). S4를 **순차 표집**(추정 비율에 따라 확대)으로 전환 | 판정 시작 전 | A-2, A-3, §6, §7.5 |
| ⑤ | notes 7%는 D-3 소스 문제일 뿐 아니라, **성향 진단("EHJ=query-unit / DYK=표면접속사")이 편향된 7% 표본에서 나왔을** 가능성 — 사람은 애매할 때만 메모함 | C-2 필수화 근거에 "이번 판정이 성향 진단의 첫 충분 표본"이라는 함의 한 줄 추가 | 선택 | C-2 |

> ③④의 절차적 세부(예: S4 순차표집 임계값)는 판정 설계자(연구자)가 확정할 사항이다. 아래 본문에는 검토안 값을 잠정 기입했다.

---

## 0.3 v2.1 → v2.2 교정 요약 (검토 라운드 반영)

v2.1을 다시 검증하니, **v2.1이 새로 만든 결함 2건(🔴)**과 기존 설계 결함 1건 등 6건이 나왔다. 🔴 2건은 GOLD 축 지표를 조용히 오염시키므로 구현 전 필수. 근거는 §9-11~§9-12.

| # | 문제 | 조치 | 시급도 | 반영 |
|---|---|---|---|---|
| 🔴1 | **D-2 완료 기준이 실행 불가.** `--subdir adjudication`은 GOLD 1명만 발견 → `combinations([GOLD],2)=0쌍`. "3쌍 출력"은 불가능(`compute_iaa.py:182,191,198`) | **GOLD를 `round2/`에 저장(안 A)** → 같은 discovery에서 {EHJ,DYK,GOLD} 발견 → E-D/E-G/D-G 3쌍. `--subdir` 작업·경로 변경 삭제 | **구현 전 필수** | D-2, B-1, §6, §7.1/§7.4 |
| 🔴2 | **tier=3 `splitting_decision:null`이 IAA에서 제외 안 됨.** `cohens_kappa`가 None을 `"__NONE__"` 센티넬 **별도 클래스로 계수**(`metrics.py:81-83`) → GOLD 축 κ 오염. ①의 최상위화가 오히려 이 위험을 만듦 | **tier=3은 GOLD envelope에 넣지 않고 `gap_tickets.json`으로 분리.** gold set = "확정된 정답"만 | **구현 전 필수** | C-2, D-3, §7.4, §8 |
| 🟠3 | **S2 키워드가 잘못된 위험을 겨냥.** 진단/biomarker(Tier 1)만 잡고, 실증된 both-wrong 메커니즘인 umbrella/나열(Tier 2, §7.2 E8은 키워드로 안 잡힘·하드코딩으로만 포함)을 놓침 | S2에 **umbrella/나열 패턴 필터 추가**(불일치분석 §5 근거). 하드코딩은 안전망으로만 | **판정 전 필수** | A-3 |
| 🟡4 | child_rationale "few-shot 후보일 때 권장"은 **실행 불가** — 채택은 D-4 이후 결정이라 판정 시 알 수 없음 | `splitting_decision != none`이면 **child_rationale 필수**(부담 작음) | 구현 전 | C-2, D-4 |
| 🟡5 | S4 임계값 5%/15%가 **n=25에서 판정 불가**(2/25 → 95%CI ≈1~26%, 세 구간 다 걸침) | **절대 건수 트리거**(0/1/2+건)로 전환. 비율·CI는 최종 표본에서 보고 | 판정 전 | A-3, §7.5 |
| ⚪6 | 문서 내부 불일치: §1.5 흐름도가 Tier 0을 파이프라인 2단계로 표기(A-2 강등과 불일치), §8 헤더가 신규 미해결 누락 | §1.5 흐름 수정, §8에 🔴1/🔴2 미해결 반영 | 선택 | §1.5, §8 |

> 🟠3의 키워드 목록은 CRC 관점 검토, 🟡5의 트리거 건수는 판정 설계 결정 — 본문엔 검토안을 잠정 기입.

---

## 0.4 v2.2 → v2.3 교정 요약 (착수 전 최종 검증 반영)

v2.2 전체를 **코드 실행**으로 재검증했다(이전 라운드는 코드 열람 대조까지만). 결과: 🔴1/🔴2/§7.4 스키마/§9-6 수치는 전부 실행으로 재확인됐고(§9-13), **A-1은 이미 워킹트리에 구현 완료** — `compute_sd_axes` 등 회귀 목표치(9/20/7 → 3/24/7, obs 0.791 → 0.802)를 정확히 재현한다. 남은 결함 6건을 반영한다. 근거는 §9-13~§9-16.

| # | 문제 | 조치 | 시급도 | 반영 |
|---|---|---|---|---|
| 🟠1 | **E-G/D-G κ가 편향 표본 위에서 계산됨.** GOLD envelope는 판정된 ~85건(그중 S1 불일치 49건)만 담으므로 GOLD 축 alignment의 모집단은 불일치 과대표집 층화 표본 → κ가 구조적으로 낮고, 전수 172건 기준 E-D κ와 **같은 표에 나란히 찍히지만 비교 불가**. trial별 matched 3~10건이라 κ 다수 `—`/불안정 | D-1/D-2에 **해석 가드** 명시: GOLD 축 지표는 층별 진단용, 정확도 보고는 D-1이 층별 분모 명시로 수행, E-D κ와 병렬 비교·논문 인용 금지 | **판정 전 필수** | D-1, D-2 |
| 🟡2 | **B-3 내부 모순 + D-4 충돌.** B-3 완료기준("부분문자열 아니면 저장 안 됨")과 주의("경고 + override 허용")가 모순이고, override로 저장된 비연속 span은 **D-4의 부분문자열 검증에서 반드시 실패** | B-3 완료기준을 "override 없는 한 거부"로 정정, D-4에 `span_override != null` 항목 few-shot 후보 자동 제외 규칙 추가 | 구현 전 | B-3, D-4 |
| 🟡3 | **streamlit_app.py에 round 개념이 없음.** 저장(`annotator_envelope_path`)·발견(`list_committed_annotator_envelopes`) 모두 stage_dir 평면 경로(§9-14) → B-1의 round2/ 저장과 C-1의 round2/ 읽기는 **round 경로 지원 신규 구현이 전제**. D-2 "코드 수정 0"의 비용이 B-1로 이전된 것 | B-1 스코프에 round 경로 지원 명시 | 구현 전 | B-1, D-2 |
| 🟡4 | **S2/S3 층 중복 배정 규칙 미정의.** SD 일치 + child#/span 불일치이면서 위험군 필터에도 걸리는 항목의 소속 불명 → 층별 건수와 S4 표집 프레임 불명확 | 배정 우선순위 **S1 > S2 > S3 > S4**(항목은 한 층에만), S4 프레임 = 일치 138 − S2 − S3 | 큐 생성 전 | A-3 |
| ⚪5 | gap ticket 스키마에 `tier`·`blind_label` 없음 → tier=3("본질적으로 어려운") 항목의 판정자 blind 의견이 유실되고 D-3 blind≠gold 분석에서 gap 항목 누락 | gap ticket 스키마에 두 필드 추가 | 구현 전 | §7.4, D-3 |
| ⚪6 | D-4 템플릿에 `notes` 누락(실측: 기존 예시 5개 **전부** output에 notes 존재) + cohort_scope 위치 가변(KEYNOTE-001 I1_F는 child에만, none 예시는 sub_criteria 부재) → "동일 스키마" 검증이 기존 예시 자체에서 실패 | 템플릿에 `notes` 추가, 스키마 검증이 위치 가변을 허용하도록 명시 | 구현 전 | D-4 |

---

## 1. 배경

### 1.1 프로젝트 컨텍스트

임상시험 적격성 기준(eligibility criteria)을 4-layer LPG 온톨로지(Neo4j)로 구조화하는 GraphRAG 파이프라인. 5단계 LLM 어노테이션 파이프라인 중 **Stage 1 = splitting**, 즉 하나의 criterion 텍스트를 몇 개의 독립 판정 단위로 분해할지 결정하는 단계.

Stage 1 어노테이션 스키마 — **실제 committed envelope 기준**(v1 초안 스키마에서 `rationale`·`notes`는 선택/희소, §9-1 참조):

```json
{
  "criterion_id": "NCT..._E6",
  "splitting_decision": "composite_split | macro_aggregate | nested_exception | none",
  "sub_criteria": [{"child_id": "a", "text_span": "..."}],
  "child_logic": "AND | OR | null",
  "confidence": "high | medium | low",
  "notes": "...(선택; 실측 ~7% 항목에만 존재)"
}
```

> ⚠️ v1 초안이 제시한 `sub_criteria[].rationale`, `cohort_scope`는 실제 데이터에서 각각 0건 / 4건뿐이다. 프롬프트 출력 스키마(`prompt_1_splitting.txt`)에는 이 필드들이 정의돼 있으나 **어노테이터 committed 산출물에는 거의 채워지지 않았다.** 판정 도구를 이 필드에 의존하게 설계하지 말 것.

Stage 1이 틀리면 Stage 2~5 전체가 오염된다. child 하나에 서로 다른 semantic_category가 섞여 있으면 Stage 2가 단일 category를 정할 수 없고, 그 결과 relation type과 Concept subtype 매핑이 전부 어긋난다. 즉 **Stage 1은 파이프라인 정확도의 상한을 결정하는 단계**다.

### 1.2 지금까지 한 것

NSCLC 임상시험 8건에 대해 어노테이터 2명(EHJ, DYK)이 blind 어노테이션 → IAA 측정 → 가이드라인 개정(v1.0 → v1.1) → 2라운드 재측정.

| 지표 | 1차 | 2차 | Δ |
|---|--:|--:|--:|
| SD κ (splitting_decision, 주요 지표) | 0.608 | 0.650 | +0.042 |
| CL κ (child_logic) | 0.763 | 0.867 | +0.104 |
| child#.exact (분해 개수 일치) | 0.430 | 0.593 | +0.163 |
| span F1 (분해 경계 일치) | 0.556 | 0.677 | +0.121 |

*(모두 `results/iaa/iaa_stage1_report.md` 및 독립 재계산으로 검증됨 — §9-6.)*

### 1.3 2라운드가 실패한 이유

숫자만 보면 개선됐지만, 실제로는 **개선이 필요한 축에서 개선되지 않았다.**

| 축 | 상태 |
|---|---|
| 분해 **방식** (몇 조각으로, 어디서 자를지) | 크게 개선 — 기계적으로 검증 가능한 규칙이 대응 |
| 분해 **여부** (쪼갤지 말지) | **정체** — SD 불일치 건수 36 → 34 |
| 분해 **유형** (macro/composite/nested) | **변화 없음** — 7 → 7 |

불일치의 약 80%가 `무언가 ↔ none`, 즉 "한 명은 쪼갰고 한 명은 통짜로 뒀다"는 유형이다. 이 판단의 유일한 근거는 query-unit("CRC가 따로 조회하는가")인데, 이건 **규칙이 아니라 판단 원칙**이라 문서로 전달되지 않았다.

추가로 κ 개선폭 자체가 과대 보고다. 관측 일치는 **136/172(0.791) → 138/172(0.802)로 +1.1%p(2건)**뿐이고(§9-6에서 실측 확인), κ 상승분 대부분은 EHJ가 보수적으로 이동해 두 사람의 marginal 분포가 벌어진 artifact다. 방향성 편향도 해소되지 않고 오히려 심화됐다(**EHJ만 분해 9→3 / DYK만 분해 20→24** — 실측 일치).

**결정적 증거**: 가이드라인 v1.1에 정답이 명시된 예시와 거의 동일한 문장이 2차에서도 불일치로 남았다. (아래 두 건은 **2차에도 불일치 유지**임을 §9-3에서 재확인.)

| 가이드라인에 정답이 있는 예시 | 2차 지속 불일치 항목 |
|---|---|
| "Uncontrolled illness such as CHF, HTN, angina" → **macro_aggregate** | NCT05756153 E6 "uncontrolled systemic diseases, such as hypertension or diabetes" → EHJ **none** / DYK macro |
| "Adequate organ function: ANC≥1500, Plt≥100k, Cr≤1.5" → **macro_aggregate** | NCT02474355 I6 "Adequate bone marrow reserve and organ function as demonstrated by CBC…" → EHJ **none** / DYK macro |

→ 문제는 **규칙 부재가 아니라 규칙 미적용**. 원인은 (a) 가이드라인 §4 참고의 "단일 카테고리 한 번 조회 → none" 예외 조항이 경계 조건 없이 열려 있어 general none-license로 작동, (b) query-unit이 조작적 정의가 아니라 개인 경험 의존, (c) **adjudicated gold 없이 문서만 배포**해서 내재화된 임계값이 교정되지 않음.

### 1.4 ⚠️ 그래서 이번 작업의 성격 — 오해하기 쉬운 지점

**adjudication은 두 라벨러가 논의해서 합의하는 작업이 아니다.** 판정자(연구자)가 외부 권위에 근거해 정답을 확정하는 작업이다.

이 구분이 중요한 이유:

- 논의로 합의하면 κ는 올라가지만 **두 사람이 합의한 답이 틀릴 수 있다.** 실제로 1차 IAA 검토에서 진단·병기 granularity에 대해 "EHJ의 under-split도, DYK의 5분할 over-split도 둘 다 틀렸고 정답은 3-way(NCCN 근거)"라고 판정된 사례가 있다. **더구나 §7.2에서 보듯, 2라운드에 두 사람이 새로 "합의"한 답(둘 다 none)이 가이드라인 정답(macro)과 어긋나는 실제 사례가 나왔다** — 합의가 정답을 보장하지 않는다는 직접 증거다.
- 프롬프트 수정에 필요한 것은 **일치도가 아니라 gold set**이다. 일치도가 0.9로 올라가도 프롬프트 few-shot 예시는 gold에서 나와야 한다.
- 따라서 **다수결·2:1 자동 판정을 구현하면 안 된다** (→ §5 금지사항).

또한: **가이드라인 개정(v1.2)은 이 작업의 산출물이지 입력이 아니다.** 규칙을 먼저 정해서 강요하면 v1.1 실패를 반복한다. 판정 논거를 사후 집계해서 규칙을 귀납해야 한다. Claude Code는 규칙을 제안하지 말고, **논거 빈도 집계 도구만 제공**할 것 (작업 D-3).

> **v2 중요 보강**: v1은 D-3의 논거 재료가 기존 EHJ/DYK notes에 있다고 가정했으나, 실측상 notes는 7% 항목에만 존재하고 `rationale`은 전무하다(§9-1). 따라서 **v1.2 귀납의 논거는 판정 과정에서 C-2로 새로 생성되는 `rationale_short`가 사실상 유일한 소스**다. C-2를 "있으면 좋은 메타데이터"가 아니라 **필수 산출물**로 취급할 것.

### 1.5 최종 목표 흐름

```
[현재] IAA 1·2라운드 완료, 정체
   ↓
① 지표 2단 분해            ← 코드 (오늘 가능, 어노테이터 시간 0)
② 판정 큐 생성             ← 코드 (A-2 선행 불필요)
   └ Tier 0 위생 점검(~5건) ← 코드, ②와 병렬·부가 (gating 아님; §0.3-④)
③ Streamlit GOLD 라벨러 추가 ← 코드
   ↓
⑤ 판정 작업 (~85건)        ← 사람 (8~11시간, 3~4세션)
   ↓
⑥ gold set 확정
   ↓
⑦ 라벨러별 정확도·편향 집계 ← 코드   → 캘리브레이션 피드백
⑧ 논거 빈도 집계           ← 코드   → 가이드라인 v1.2 (사람이 작성)
⑨ gold → few-shot 변환      ← 코드   → 프롬프트 v2 (사람이 검토)
⑩ held-out trial 샘플링     ← 코드   → 3라운드 (새 trial 4~6건)
```

**3라운드를 기존 8 trial로 반복하지 않는다.** 판정 과정에서 두 라벨러가 해당 8건에 노출되어 학습효과와 원칙 내재화가 구분 불가해지므로, 논문용 최종 IAA는 held-out trial에서 측정한다.

---

## 2. 용어 정의

| 용어 | 정의 |
|---|---|
| **adjudication** | 불일치·위험 항목에 대해 판정자가 정답 라벨을 확정하는 작업 |
| **gold set** | 판정 결과로 확정된 정답 어노테이션. 프롬프트 few-shot 및 파이프라인 평가의 기준 |
| **blind 라벨** | 판정자가 EHJ/DYK 라벨을 보지 않은 상태에서 독립적으로 매긴 라벨. 제3의 독립 의견이며 **투표권이 아니다** |
| **Tier** | 판정 근거의 권위 계층 (§7.3) |
| **gap ticket** | 어느 Tier로도 판정되지 않은 항목. 억지로 정답 처리하지 않고 명시적으로 남긴다 |
| **rule_status** | 판정 시 인용한 가이드라인 규칙의 상태: `existing` / `new` / `conflict` / `gap` |
| **envelope** | 기존 어노테이션 저장 단위. `{actor}_{trial}_stage1_committed.json` |

---

## 3. 작업 목록

각 작업에 **왜 필요한가 / 무엇을 만드는가 / 완료 기준 / 주의**를 명시했다. "왜"를 건너뛰고 구현하지 말 것 — 이 작업들은 대부분 목적이 명확하지 않으면 잘못 만들어진다.

### A. 판정 전 코드 작업

---

#### A-1. 지표 2단 분해 (`iaa_pipeline/metrics.py`, `scripts/compute_iaa.py`)

**왜 필요한가**

현재 SD κ는 4-class(`composite_split`/`macro_aggregate`/`nested_exception`/`none`) 단일 지표다(`compute_stage1_iaa`, `metrics.py:188`). 그런데 이 라벨에는 **성격이 다른 두 개의 결정**이 압축돼 있다.

1. 쪼갤 것인가 말 것인가 (split vs none) — 정체된 축
2. 쪼갠다면 어떤 유형인가 (composite/macro/nested) — 개선된 축

두 결정을 한 지표로 측정하면 후자의 개선이 전자의 정체에 상쇄되어 헤드라인 숫자가 거의 움직이지 않는다. 분해해서 보면 **어느 결정이 문제인지 특정되고, 판정 우선순위가 정해진다.**

**무엇을 만드는가**

기존 지표를 유지한 채 아래를 추가:

| 신규 지표 | 계산 |
|---|---|
| `SD_binary_κ` | 라벨을 `split`(composite/macro/nested 통합) vs `none` 2-class로 축약한 Cohen's κ |
| `SD_type_κ` | **양쪽 모두 split**인 쌍만 필터링 후 3-class(composite/macro/nested) Cohen's κ |
| `observed_agreement` | SD 관측 일치율 (κ와 함께 항상 병기 — §1.3의 과대보고 방지) |
| `expected_agreement` | κ 계산의 기대 일치. marginal 분포 변화 추적용 |
| `direction_bias` | (EHJ만 split, DYK만 split, 유형만 다름) 튜플 |

trial별 + POOLED 모두 산출. 기존 리포트 표에 컬럼 추가 형태로 출력.

**완료 기준**

- 1·2라운드 양쪽에 대해 위 지표가 계산되고, 1차→2차 Δ 표가 생성된다
- `SD_type_κ`가 `—`(분산 0)로 나오는 trial이 있으면 관측 일치율을 대신 표기한다
- ASTRIS(NCT02474355)의 fair 수준 κ(0.266→0.252)가 binary 축 문제인지 type 축 문제인지 판별된다

**주의**

- `SD_binary_κ`에서 `nested_exception`을 `split`으로 묶는 근거: nested_exception도 sub_criteria를 생성하며(child 1개), "통짜로 두지 않았다"는 점에서 none과 대비된다. 이 판단을 코드 주석에 남길 것
- κ가 정의 불가한 경우(분산 0) 예외 처리를 반드시 구현. 기존 코드에 이미 `—` 처리 로직이 있으므로 재사용
- 참고: `direction_bias`·`observed_agreement`는 이미 별도 스크립트로 실측된 값이 있다(§9-6). 재계산 결과가 그 값(9/20/7, 3/24/7)과 일치하는지 회귀 테스트로 활용할 것

---

#### A-2. Tier 0 기계 검증 — **위생 점검(gating 아님)** (`validators.py` / `08_review_queries.py` 재사용)

> ⚠️ **v2.1 재평가(④)**: A-2의 원래 목적은 "판정 건수 줄이기(gating)"였으나, 이식 가능한 3.2/3.3만 남기니 **실측 위반이 5건뿐**(composite_split 202건 중 3.2 2건 + 3.3 3건; §9-9)이다. CL κ가 계산됐다는 것 자체가 child_logic이 대체로 채워져 있다는 뜻이다. 따라서 A-2는 **gating 작업이 아니라 5분짜리 데이터 위생 점검**으로 격하한다 — A-3의 선행 조건이 아니며, 병렬로 돌려도 된다.

**왜 필요한가 (격하된 목적)**

전수 판정 대상 중 spec v1.2.2를 구조적으로 위반한 소수(약 5건)를 미리 표시해, 판정자가 "이 라벨은 spec상 이미 틀림"을 알고 들어가게 한다. 건수가 적으므로 큐 축소 효과는 없고, "spec 위반 자동 오답"과 "판단이 갈리는 건"을 라벨로 구분해 D-3 오염만 막는다.

**무엇을 만드는가 (v2 스코프 축소)**

Stage 1 envelope에 **실제로 존재하는 필드만으로 검사 가능한 규칙**을 JSON 직접 검사로 포팅:

| 이식 대상 | 근거 쿼리 | Stage 1 적용 |
|---|---|---|
| composite_split인데 sub_criteria < 2 | `08_review_queries.py` **3.2** | ✅ 가능 (splitting_decision + sub_criteria로 판정) |
| composite_split인데 child_logic null | `08_review_queries.py` **3.3** | ✅ 가능 |
| ~~비정형 category×relation 조합~~ | ~~2.2~~ | ❌ **불가** — semantic_category는 Stage 2 데이터, Stage 1 envelope에 없음(§9-4) |
| ~~category null~~ | ~~2.3~~ | ❌ **불가** — 동일 사유 |

- 대상: `iaa_workspace/{trial}/stage1/round2/{EHJ,DYK}_*_committed.json`
- 출력: `tier0_violations.csv` — trial, criterion_id, actor, violation_code, detail

**완료 기준**

- 두 라벨러의 2차 envelope 전체가 검사되고 위반 목록이 나온다
- 각 위반이 spec v1.2.2의 어느 조항 위반인지 `violation_code`로 식별된다
- A-3의 판정 큐에 위반 라벨(`tier0_flag`)로 **부가**된다 — 선행 차단이 아니라 표시용. A-3는 A-2 완료를 기다리지 않아도 된다

**주의**

- **자동으로 gold를 확정하지 말 것.** Tier 0 검증은 "이 라벨은 틀렸다"까지만 판정한다. **정답이 무엇인지**는 여전히 사람이 정한다
- semantic_category 혼재 검사는 Stage 1 envelope에 category 정보가 **없음이 확인됐다**(§9-4). 이 검사는 구현하지 말고, 필요하면 Stage 2 gold 구축 시로 미룰 것. 없는 필드를 추론해 검사하지 말 것

---

#### A-3. 판정 큐 생성

**왜 필요한가**

판정 대상은 불일치 49건만이 아니다. **양쪽이 일치했지만 둘 다 틀린 경우가 실재한다**(§7.2에서 실제 2건 확인). 일치했다는 이유로 감사에서 제외하면 **gold set에 오답이 그대로 남는다.** 동시에 172건 전수 판정은 시간이 과하므로 **위험도 기반 층화**가 필요하다.

**무엇을 만드는가**

`adjudication_queue.csv` (또는 JSON):

| 층 | 대상 | 건수(예상) | 선정 방식 |
|---|---|--:|---|
| S1 | SD 불일치 (지속21 + 해소15 + 신규13) | 49 | 전수 |
| S2 | 양측 일치 + **위험군** | ~15 | 아래 regex 매칭 + §7.2의 "해소되었으나 가이드라인과 어긋나는" 2건 포함 |
| S3 | SD 일치 + child#/span만 불일치 | ~20 | S1 미포함분 전수 |
| S4 | 나머지 일치 항목 | ~25 → 가변 | **순차 표집**(아래 ④) — 무작위 표본을 먼저 판정한 뒤 both-wrong 비율에 따라 확대 |

> 🟡 **v2.3(🟡4) — 층 배정 우선순위.** 한 항목이 여러 층 조건에 동시에 걸릴 수 있다(예: SD 일치 + child#/span 불일치이면서 umbrella 필터에도 매칭 → S2·S3 양쪽 해당). 배정은 **S1 > S2 > S3 > S4** 순으로 **한 층에만** 한다. 따라서 S4의 표집 프레임은 "SD 일치 138건 − S2 − S3"로 정의된다. 이 규칙이 없으면 층별 건수 집계와 S4 무작위 표본의 모집단이 불명확해진다.

S2 위험군 판정 키워드 (criterion 원문에 매칭):

```
진단·병기: histologic, cytologic, pathologically confirmed, stage (I|II|III|IV),
           locally advanced, metastatic, resectable, unresectable, NSCLC, adenocarcinoma
biomarker: EGFR, ALK, KRAS, ROS1, NRG1, T790M, PD-L1, MET, RET, BRAF, mutation, mutated
```

> 🟠 **v2.2 필수 보강(🟠3) — umbrella/나열 패턴 필터 추가.** 위 진단·biomarker 키워드는 **Tier 1(NCCN 3-way) 위험만** 겨냥한다. 그러나 §7.2에서 실증된 both-wrong 2건 중 **NCT02474355 E8("rhythm, conduction… resting ECG")은 진단도 biomarker도 아니라 키워드로 안 잡히고 하드코딩으로만 포함**됐다. 실제 both-wrong 메커니즘은 불일치분석 §5가 특정한 **"한 문장에 조건이 콤마/`or`/`including`으로 나열된 배제기준"(umbrella vs none)** 이다 = Tier 2 위험. 이걸 규칙으로 잡으려면 아래 필터를 S2에 추가:
>
> ```
> umbrella 신호: including, such as, e.g., other than, evidence of,
>               uncontrolled, adequate, abnormalities, any factors, risk factors
> 나열 신호:    콤마 3개 이상 | "or" 2회 이상 | 세미콜론 포함
> ```
>
> 이 필터를 넣으면 E8·NCT02474355 I6·NCT01295827 E6·NCT02474355 E9 등이 **규칙으로** 잡힌다. §7.2 하드코딩 4건은 안전망으로만 남긴다. **키워드 목록은 CRC 관점에서 한 번 검토 후 확정**(§4).

큐에는 각 항목의 **A-1 결과 기반 우선순위**를 부여한다. binary 축 불일치(split-vs-none) 유형을 상위로, 유형만 다른 건을 하위로.

**④ S4 순차 표집 — 고정 20~30% 대신.** §7.2에서 "양측 일치 + 가이드라인 불일치(both-wrong)"가 의심 4건 중 2건 실제 확인됐으나, 이는 **의심한 것만 본 결과라 base rate를 모른다.** round2 일치 항목 138건 중 S4가 20~30%(~25건)만 보면, 만약 both-wrong 비율이 10%라면 숨은 오답 ~14건 중 3~4건만 잡힌다. 따라서:

```
S4 1차: 무작위 25건 판정(seed 고정) → both-wrong '건수'로 분기
   ├ 0건    → S4 종료(현행 유지)
   ├ 1건    → 25건 추가 후 재평가
   └ 2건+   → 50건 추가 후 재평가
```

> 🟡 **v2.2 정정(🟡5) — 비율 임계값 대신 절대 건수 트리거.** v2.1의 `p̂ < 5% / 5~15% / >15%`는 n=25에서 판정 불가다: 2/25면 p̂=8%지만 95% CI ≈ **1~26%**로 세 구간을 모두 걸쳐 어느 분기도 못 고른다. 표본 비율을 추론처럼 쓰지 말고 **관측 건수로 직접 트리거**하는 게 정직하다. 논문에는 "point estimate 기반 순차 확대(정밀도 제약 명시)"로 기술하고, **최종 표본에서 CI와 함께 비율을 보고**한다. ※ 트리거 건수(0/1/2+)는 검토안이며 판정 설계자가 확정한다.

부수 효과로 **"adjudicated gold 기준 양측-일치 오답률"**이라는 논문 보고용 지표가 나온다(IAA만 보고하는 연구에서 드문 숫자 → 방법론 강점).

큐 필드: `priority, stratum, trial, criterion_id, criterion_text, E_label, E_child_n, E_notes, D_label, D_child_n, D_notes, tier0_flag`

> ⚠️ **v2**: `E_notes`/`D_notes`는 ~7% 항목에만 값이 있다(§9-1). 대부분 공란이 정상이므로, 큐 생성 시 notes 결측을 오류로 처리하지 말 것.

**완료 기준**

- 약 80~90건의 정렬된 큐가 생성된다
- **예외 조항 충돌 항목이 priority 최상위에 온다** (§7.2 — v2에서 실제 불일치 유지 2건 + 해소되었으나 오답의심 2건으로 재구성). 하드코딩해도 무방
- 각 항목에서 EHJ/DYK의 원본 `notes`가 **있으면** 그대로 가져와진다 (재수집하지 않기 위함)

**주의**

- S4 무작위 표본은 **seed를 고정**하고 기록할 것. 논문에 표본 추출 방식을 기술해야 함
- 큐 파일에 gold 컬럼을 미리 넣지 말 것. 판정 결과는 Streamlit envelope에 저장되며 큐는 worklist 역할만 한다 (이중 저장 시 동기화 문제)

---

#### A-4. NCT03800134 원문 복구

**왜 필요한가**

`iaa_workspace/NCT03800134/stage1/`에 `input.json`이 없어(§9-5) 불일치 분석 문서에서 원문 발췌가 `—`로 비어 있다. 해당 trial의 불일치 항목이 다수이며(1차 기준 E2/E9/I9/E10/E11/I5 등), **원문 없이는 판정이 불가능하다.** 또한 이 trial은 1차 span F1이 0.210으로 8건 중 최저였다.

**무엇을 만드는가**

`01_criteria_extraction.py`로 NCT03800134을 ClinicalTrials.gov API v2에서 재추출해 `iaa_workspace/NCT03800134/stage1/input.json` 생성. 기존 8 trial과 동일한 포맷·criterion_id 부여 규칙 적용.

**완료 기준**

- criterion_id가 기존 envelope(EHJ/DYK가 라벨링한 것)과 **정확히 정렬**된다. 이게 깨지면 IAA 재계산과 판정이 모두 어긋난다
- `\n` + bullet 구조가 보존된다 (AACT의 flat `~*` 포맷 사용 금지 — macro_aggregate 구조가 파괴됨)

**주의**

- API v2에서 가져온 criterion 개수가 envelope의 matched 22건과 다르면 **정렬 규칙을 먼저 확인**할 것. 프로토콜 개정 가능성도 있다. 개수가 다르면 임의 매칭하지 말고 보고할 것
- 네트워크 접근이 막혀 있으면 그 사실을 보고하고 대안(사람이 수동 저장)을 제시할 것

---

### B. Streamlit 앱 수정 — **대상 파일: `iaa_pipeline/streamlit_app.py`** (v1의 `workspace.py`는 오기; §9-2)

> `iaa_pipeline/workspace.py`는 존재하지 않는다. envelope I/O(`save_envelope`, `list_committed_annotator_envelopes`), phase 접근제어(`Phase`, `resolve_tabs`), blind 렌더(`render_criterion_form_blind`), span 입력(`text_area`)은 모두 **`iaa_pipeline/streamlit_app.py`** 안에 있다. 호스트용 별도 앱은 `streamlit_apps/stage1_app.py`. 재사용 대상은 전자다.

---

#### B-1. GOLD 액터 추가

**왜 필요한가 — 그리고 새 앱을 만들지 않는 이유**

adjudication은 결국 **같은 어노테이션 작업을 판정자가 한 번 더 하는 것**이다. 판정 라벨의 스키마가 라벨러와 동일하다(splitting_decision + child_logic + text_span). 새 앱을 만들면 `streamlit_app.py`의 envelope I/O, span 입력, phase 접근제어를 전부 재구현하게 된다.

특히 **span 입력 때문에** CSV/스프레드시트 방식은 불가하다. `text_span`은 원문의 정확한 연속 부분문자열이어야 하는데, 손으로 타이핑하면 공백·하이픈·대소문자가 미세하게 달라진다. 그러면 span F1 계산(토큰 Jaccard)과 few-shot 예시 생성(D-4)이 모두 깨진다.

**무엇을 만드는가**

- 액터 `GOLD`를 기존 액터 체계에 추가. 저장 경로: **`iaa_workspace/{trial}/stage1/round2/GOLD_{trial}_stage1_committed.json`** (🔴1·D-2 안 A — GOLD를 round2/에 두어야 `compute_iaa.py`가 EHJ·DYK와 **같은 discovery**에서 발견해 E-G/D-G를 계산한다. `adjudication/` 별도 폴더에 두면 액터 1명이라 0쌍)
- envelope는 기존과 동일하게 `source: "annotator"`, `annotator: "GOLD"`, `committed: true`로 저장 — 그래야 `compute_iaa.py`가 **자동으로 액터로 인식**한다(§9-3, D-2 참조)
- **tier=3(판정 불가) 항목은 GOLD envelope에 넣지 않는다** — `gap_tickets.json`으로 분리(🔴2·§7.4). GOLD envelope에는 splitting_decision이 확정된 record만 들어간다
- 판정 전용 필드는 §7.4의 `adjudication` 블록으로 분리

**완료 기준**

- GOLD 라벨이 기존 envelope 포맷으로 저장되고, `compute_iaa.py`가 GOLD를 액터로 자동 발견해 EHJ-vs-GOLD / DYK-vs-GOLD를 계산한다(아래 D-2의 소규모 수정 후)
- 판정 큐 순서대로 항목을 넘기며 작업할 수 있다 (priority 정렬 반영)

**주의**

- 🟡 **round 경로 지원은 신규 구현이다(🟡3).** 현행 `streamlit_app.py`에는 round 개념이 전혀 없다 — 저장은 `annotator_envelope_path` = `stage_dir/annotator_{id}.json` 평면, 발견도 `list_committed_annotator_envelopes(stage_dir)` 평면 glob(§9-14). round1/round2 폴더는 수동 정리물이고 코드에서 인지하는 것은 `compute_iaa.py --round`뿐이다. B-1은 (a) GOLD 저장을 `stage1/round2/`로, (b) C-1이 표시할 EHJ/DYK envelope 읽기를 round2/에서 하도록 경로 처리를 추가해야 한다. 파일명은 discovery가 내용 기반이라 자유지만 §7.1 관례(`GOLD_{trial}_stage1_committed.json`)를 따를 것
- 기존 round1/round2 envelope를 수정하거나 덮어쓰지 않을 것. **read-only로 취급**
- `streamlit_app.py`에 이전에 식별된 bias 취약점(참고: `iaa_pipeline_spec/audit_streamlit_v1.md`)이 있다. GOLD 액터 추가 시 그 경로를 다시 열지 않도록 확인할 것

---

#### B-2. blind 토글

**왜 필요한가**

판정 절차는 2단 통과다.

1. **1차 통과** — EHJ/DYK 라벨을 **가린 상태**에서 판정자가 독립 라벨링
2. **2차 통과** — 두 라벨과 notes를 공개하고 최종 gold 확정

1차 통과가 필요한 이유: 두 라벨을 먼저 보면 판정자도 "A냐 B냐"의 이지선다에 갇힌다. 그런데 **둘 다 틀린 경우가 실재**하며(§7.2), 그걸 발견하려면 제3의 독립 라벨이 먼저 있어야 한다. 라벨러에게 적용했던 앵커링 방지 논리와 동일하다.

**무엇을 만드는가**

- `blind: true/false` 토글. `true`일 때 EHJ/DYK의 라벨·child 개수·notes·span을 모두 숨김
- 1차 통과 라벨은 `blind_label` 필드에 **별도 보존** (2차에서 gold를 바꿔도 blind_label은 남아야 함)

**완료 기준**

- blind 상태에서 저장한 라벨이 `blind_label`로 고정되고, 공개 후 수정한 최종 라벨이 `gold_label`로 따로 저장된다
- blind → 공개 전환이 항목 단위로 가능하다

**주의**

- `streamlit_app.py`의 기존 phase 접근제어(`Phase`, `resolve_tabs` — phase_2_review는 commit 후에만 IAA 노출)를 재사용할 것. 목적(앵커링 방지)이 동일하므로 새 메커니즘을 만들 필요 없음
- **blind_label과 gold_label이 다른 경우가 중요한 데이터다.** 판정자가 공개 정보를 보고 판단을 바꾼 케이스이므로, D-3 논거 집계에서 별도 표시할 것

---

#### B-3. span 검증 (저장 시)

**왜 필요한가**

gold의 `text_span`이 원문과 한 글자라도 다르면 span F1 계산, few-shot 예시 생성(원문과 불일치하는 span을 프롬프트에 넣으면 LLM이 존재하지 않는 텍스트를 생성하도록 학습됨), Neo4j ingest 원문 대조가 전부 깨진다. text_span 원칙 자체가 "원문 그대로 잘라낸 연속 구간"이므로 이건 규칙이 아니라 **불변식(invariant)**이다.

**무엇을 만드는가**

저장 시 검증: (1) `text_span`이 criterion 원문의 부분문자열인가(정확 매칭), (2) 연속 구간인가, (3) 위반 시 **저장 거부** + 원문에서 가장 가까운 후보 구간 제시.

**완료 기준**

- 부분문자열이 아닌 span은 **override 없는 한** 저장되지 않는다. override 저장은 아래 주의의 의도적 예외에 한하며 `span_override` 사유 기록이 필수다 (🟡2 — v2.2까지는 이 완료기준과 주의의 override 허용이 서로 모순이었다)
- 정규화(공백 정리, 소문자화)를 **자동 적용하지 않는다** — 원문 그대로가 원칙

**주의**

- 가이드라인에 **의도적 예외**가 있다: composite 분할 시 공통 전제를 각 갈래에 복제하는 경우, 병기 표현("locally advanced" + "Stage III"가 떨어져 있어도 붙여 기입). 이 경우 연속 구간 원칙이 깨진다. **저장 거부가 아니라 경고 + override 가능**하게 구현하고, override 사유를 기록 필드(`span_override`)에 남길 것
- 참고: 현행 `streamlit_app.py`의 span 입력은 자유 `text_area`(`streamlit_app.py:345`)라 이 검증이 **아직 없다.** 신규 구현이다

---

### C. 판정 중 (코드가 보조하는 부분)

---

#### C-1. 두 라벨러 notes 표시 (**있는 경우에만**)

**왜 필요한가**

EHJ/DYK가 committed JSON에 남긴 `notes`가 논거 단서다. 예(실측): EHJ `"진단명 예시 -> macro로 split 하지 않음"`, DYK `"실패와 내성 같은 의미이기에 non-split"`. 새로 회의를 열어 논거를 재수집하면 시간이 들고 사후 합리화가 섞인다.

> ⚠️ **v2 정정**: notes는 **688 record 중 47건(~7%)에만** 존재한다(§9-1). 따라서 "notes 표시로 논거 재수집을 대체한다"는 v1 전제는 성립하지 않는다. C-1은 **있는 notes를 보조로 띄우는 것**까지이고, 대다수 항목의 논거는 판정자가 C-2에서 직접 생성해야 한다. C-1을 D-3의 데이터 소스로 기대하지 말 것 — D-3 소스는 C-2다.

**무엇을 만드는가**

2차 통과 화면(blind=false)에서 EHJ/DYK의 `notes`가 **존재하면** 원문 그대로 표시(요약·재작성 금지). 없으면 "(no note)" 표기. `sub_criteria[].rationale`은 데이터에 없으므로 참조하지 말 것.

**완료 기준** — notes가 있는 항목에서 두 사람의 메모를 원문 그대로 읽을 수 있고, 없는 항목은 명시적으로 비어 있음을 표시한다.

---

#### C-2. 판정 기록 필드 — **이 작업의 핵심 산출물**

**왜 필요한가**

gold 라벨만 저장하면 D-3(논거 빈도 집계)이 불가능하고, 그러면 **가이드라인 v1.2를 귀납할 재료가 없다.** §1.4에서 본 대로 v1.2는 판정 논거에서 도출되어야 한다. **그리고 기존 notes가 7%뿐이라(§9-1), 판정 시점의 `rationale_short`가 v1.2 귀납의 사실상 유일한 논거 소스다.** 즉 C-2는 선택적 메타데이터가 아니라 프로젝트 산출물 자체다.

> **⑤ 추가 함의(왜 이게 v2가 말한 것보다 더 중요한가)**: 지금까지의 성향 진단 — "EHJ는 query-unit으로 판정 / DYK는 표면 접속사를 따른다" — 은 **notes가 있는 7% 표본에서 도출**됐고, 그 표본은 편향돼 있을 수 있다(사람은 확신할 때가 아니라 애매하거나 남다른 판단을 할 때 메모를 남긴다). 즉 v1.1이 빗나간 이유가 규칙 진술 문제만이 아니라 **성향 진단 자체가 얇은 근거 위에 있었을** 가능성이 있다. 이번 판정에서 ~85건 전수 논거(`rationale_short`)를 확보하면 성향 진단이 **처음으로 충분한 표본**을 갖는다. 그래서 C-2 필수화는 "귀찮은 필드"가 아니라 진단의 재정초 작업이다.

**무엇을 만드는가**

판정 화면에 아래 입력 필드 (스키마는 §7.4):

| 필드 | 타입 | 설명 |
|---|---|---|
| `tier` | 0/1/2/3 | 판정 근거 계층 (§7.3) |
| `rationale_short` | 한 줄 텍스트 | 왜 그렇게 정했는가 (criterion 단위) |
| `child_rationale` | child별 한 줄 (선택) | 분해한 경우 각 child를 왜 이렇게 잘랐는가. **few-shot 채택 후보(D-4)에서 필요** — ②·§9-8. 판정하며 쓰는 편이 사후 작성보다 정확하므로 이때 받는다 |
| `rule_id` | 문자열 or null | 인용한 가이드라인 v1.1 규칙 번호. **기존 규칙으로 설명 안 되면 반드시 공란** |
| `rule_status` | enum | `existing` / `new` / `conflict` / `gap` |
| `escalate_pi` | bool | 임상 판단이 필요해 PI 확인 대기 |

`rule_status = conflict`는 **기존 규칙이 오히려 오답을 유도한 경우**다. 이 값이 붙은 건이 예외 조항 폐쇄(§7.2)의 직접 재료이므로 별도 필드로 분리했다. `child_rationale`은 §7.4의 gold `sub_criteria[].rationale`에 저장된다.

**완료 기준**

- `tier`와 `rationale_short`는 **필수 입력** (미입력 시 저장 거부) — 논거 소스가 이것뿐이므로 강제
- 🟡 **`splitting_decision != none`이면 `child_rationale`도 필수**(🟡4). v2.1의 "few-shot 후보일 때 권장"은 실행 불가였다 — 채택은 D-4 이후 결정이라 판정 시점엔 어떤 항목이 few-shot이 될지 알 수 없다. gold ~85건 중 분해 라벨은 절반 이하이고 child당 한 줄이라 부담이 작으므로, 조건부 권장 대신 **무조건 필수**가 실행 가능하다. child_rationale은 §7.4 gold `sub_criteria[].rationale`에 저장
- 🔴 **`tier=3`(판정 불가)이면 이 record를 GOLD envelope가 아니라 `gap_tickets.json`에 쓴다**(🔴2·§7.4). GOLD에 `splitting_decision:null`을 저장하지 말 것 — κ 오염

**주의**

- `rule_id` 자동 추천 기능을 만들지 말 것. 판정자가 기존 규칙에 억지로 끼워 맞추게 되어 `new`/`gap` 발견을 놓친다

---

### D. 판정 후 코드 작업

---

#### D-1. 라벨러별 정확도 + 편향 정량화

**왜 필요한가**

1. **캘리브레이션 피드백** — v1.1 실패 원인 (c)가 "문서만 배포, 개별 오답 피드백 없음"이었다. 각 라벨러에게 "당신은 gold 대비 어느 방향으로 몇 건 틀렸다"를 제시해야 내재화된 임계값이 교정된다. EHJ는 under-split, DYK는 over-split 방향이므로 **피드백 내용이 서로 달라야 한다.**
2. **논문 보고** — 3라운드를 held-out으로 하더라도, 기존 8건에 대해 "adjudicated gold 기준 annotator accuracy"를 IAA와 함께 보고하면 학습효과 의심을 정확도 지표로 상쇄할 수 있다.

**무엇을 만드는가**

| 산출 | 내용 |
|---|---|
| accuracy | gold 대비 EHJ / DYK 각각의 SD 정확도 (trial별 + POOLED) |
| 방향 분해 | over-split / under-split / type-only 오답 건수 |
| 유형별 오답 | `none`을 골라야 할 때 split한 건수 vs 그 반대 |
| blind_label 일치 | 판정자 blind_label vs EHJ/DYK — 3자 분포 |
| **둘 다 오답** | EHJ=DYK≠gold인 건수 ← **§1.4의 핵심 가설 검증** |

**완료 기준**

- 라벨러별 개인 피드백 리포트가 각각 생성된다 (자기 오답만 담고 상대 라벨은 포함하지 않음)
- "EHJ=DYK≠gold" 건수가 명시적으로 보고된다 (§7.2의 해소 2건이 여기 잡히는지 확인)

**주의**

- 개인 리포트에 **상대 라벨러의 오답을 넣지 말 것.** 상호 비교는 "누가 더 맞았나" 프레임을 만들어 방어적 반응을 유발한다
- 🟠 **accuracy의 분모는 판정 표본(~85건)이지 전수 172건이 아니다(🟠1).** 이 표본은 S1(불일치 49건)이 과대표집된 층화 표본이므로, 전체 accuracy 하나로 뭉뚱그리면 실제보다 크게 낮아 보인다. **반드시 층(stratum)별 분모를 병기**해서 보고할 것(예: "S1 49건 중 EHJ 정답 n건"). 논문에는 "adjudicated subset 기준, 층화 구성 명시"로 기술하고, 전수 기준 추정이 필요하면 S4의 both-wrong 비율 추정으로 별도 외삽한다(자동 계산하지 말고 사람이 판단)

---

#### D-2. IAA 재계산 (GOLD 포함) — **코드 수정 0 (안 A)**

**현황**

`scripts/compute_iaa.py`는 이미 **액터 무관 자동 페어링**이다(§9-3):
- envelope를 내용으로 발견(`source=="annotator" & committed==true`, `compute_iaa.py:64`), 액터 라벨은 `annotator` 필드에서 취함
- `itertools.combinations(all_annotators, 2)`로 **모든 액터 쌍 자동 계산**(`compute_iaa.py:198`)
- 핵심 함수 `compute_stage1_iaa(envelope_a, envelope_b)`는 이미 순수 pairwise(`metrics.py:188`)

> 🔴 **v2.2 정정(🔴1)**: v2.1은 GOLD를 `adjudication/` 서브폴더에 두고 `--subdir`로 읽게 하려 했으나, 이는 **작동하지 않는다.** `discover_sources`는 **단일 디렉터리**만 스캔하고(`compute_iaa.py:182`), 액터 집합은 그 디렉터리에서 나온다(`191`). `adjudication/`엔 GOLD 하나뿐이므로 `all_annotators={GOLD}` → `combinations([GOLD],2)=0쌍` → "Need at least 2 sources"로 종료(`202-205`). E-G/D-G가 나오려면 **EHJ·DYK·GOLD가 같은 discovery 디렉터리**에 있어야 한다.

**해결 — 안 A: GOLD를 `round2/`에 저장 (권장, 코드 0)**

GOLD는 round2 라벨에 대한 판정이므로 `iaa_workspace/{trial}/stage1/round2/GOLD_{trial}_stage1_committed.json`로 저장한다. 그러면 `--round 2` discovery가 {EHJ, DYK, GOLD} 3명을 함께 발견 → E-D / E-G / D-G 3쌍이 **코드 수정 없이** 나온다.

- 트레이드오프: "round2" 폴더에 라운드가 아닌 산출물(GOLD)이 섞인다. 의미상 감수 가능(같은 라운드 라벨을 판정한 것). 단 이후 `--round 2` 실행은 항상 GOLD 3쌍을 포함하게 되므로, EHJ-DYK만 보려면 결과에서 해당 쌍만 참조
- 대안 안 B(분리 보존이 중요하면): `--extra-dir` 인자를 추가해 두 디렉터리 discovery를 병합. 소규모 코드. 기본은 A
- 🟡 **"코드 수정 0"은 `compute_iaa.py` 기준이다(🟡3).** GOLD를 round2/에 **저장하는** 쪽은 앱에 round 경로 지원이 없어 B-1에서 신규 구현한다(§9-14)

**잔여 작업** — A-1의 2단 분해 지표가 GOLD 축에서도 계산되는지 확인(코드 아님, 실행 확인)

**완료 기준** — `python scripts/compute_iaa.py --stage 1 --round 2` 실행 시 GOLD 포함 3쌍(E-D, E-G, D-G) 매트릭스가 출력된다

> 🟠 **v2.3 해석 가드(🟠1) — E-G/D-G κ는 E-D κ와 비교 불가능한 숫자다.** GOLD envelope에는 판정 표본(~85건, 그중 S1 불일치 49건)만 들어가고, pair 루프는 한쪽에 없는 record를 matched에서 제외하므로(alignment = criterion_id 교집합; §9-13) GOLD 축의 모집단은 **불일치가 과대표집된 층화 표본**이다. 결과적으로 E-G/D-G κ는 구조적으로 낮게 나오며, 같은 매트릭스에 전수 172건 기준 E-D κ와 나란히 찍혀도 **병렬 비교·논문 인용 금지**. trial별 matched가 3~10건 수준이라 κ가 `—`이거나 극도로 불안정한 것도 정상이다. GOLD 축 지표의 용도는 D-1의 층별 진단(어느 층에서 누가 어느 방향으로 틀렸나)뿐이고, 정확도 보고는 D-1이 층별 분모를 명시해 수행한다.

---

#### D-3. 논거 빈도 집계 → 규칙 승격 후보 추출

**왜 필요한가**

**이것이 가이드라인 v1.2의 유일한 정당한 입력이다.** 규칙을 선험적으로 만들면 v1.1 실패를 반복한다. 동시에 **rule bloat을 막아야 한다** — v1.1 실패 원인 중 하나가 규칙 충돌(§4 macro 규칙 vs §4 참고 none 예외)이다. spec v1.2.2가 `strictness`를 frequency 근거로 제거한 것과 같은 원칙을 적용한다.

> **v2**: 입력 데이터는 **C-2의 `rationale_short` + `rule_status` + `tier`** (판정 중 생성분)이다. 기존 EHJ/DYK notes(7%)는 보조 참고일 뿐 주 소스가 아니다.

**무엇을 만드는가**

| 산출 | 용도 |
|---|---|
| tier별 분포 | Tier 2(CRC 조회 단위) 비중이 높으면 query-unit 카탈로그 가설 지지 |
| `rationale_short` 클러스터링 | 유사 논거 그룹화. **≥3건 = 규칙 승격 후보 / 1~2건 = 사례집 only** |
| `rule_status=conflict` 목록 | 폐쇄해야 할 기존 규칙 특정 |
| `rule_status=gap` 목록 | gap ticket → v1.3 로드맵 |
| `blind_label ≠ gold_label` 목록 | 판정자도 공개 정보 없이는 틀린 = 본질적으로 어려운 항목. **gap ticket(tier=3)의 `blind_label`도 포함해 집계**(⚪5) — gap 항목이야말로 이 분석의 핵심 표본 |

**완료 기준**

- 3건 이상 반복된 논거 클러스터가 목록으로 나온다
- 각 클러스터에 해당 criterion 목록이 링크된다

**주의**

- **규칙 문장을 생성하지 말 것.** 후보 클러스터와 근거 항목만 제시한다 (§4)
- 클러스터링은 임베딩보다 **키워드/수동 검토 지원** 쪽이 안전하다. 논거가 ~85건뿐이라 자동 클러스터링 오분류 비용이 이득보다 크다

---

#### D-4. gold → few-shot 예시 변환

**왜 필요한가**

프롬프트 수정(`pipeline/prompts/prompt_1_splitting.txt` + `pipeline/prompts/examples.json`)의 재료가 gold set이다. 현재 `examples.json`의 `prompt_1_splitting` 예시 5개는 **SEQUOIA·KEYNOTE-671·KEYNOTE-001 기반**(실측 §9-7)으로, 2라운드에서 실제로 문제가 된 패턴(나열형 배제기준, umbrella 판정)이 커버되지 않았다. 특히 넣어야 할 것은 판정에서 `conflict`가 붙은 케이스 — 기존 규칙이 오답을 유도한 문장으로, LLM에게도 같은 함정일 가능성이 높다.

**무엇을 만드는가**

gold envelope → `examples.json` 포맷 자동 변환. **출력 스키마는 `prompt_1_splitting.txt`(53-59행)를 기준**으로 하며 child `rationale`·`cohort_scope`를 포함해야 한다(②):

```json
{
  "label": "...",
  "source": "{acronym} {criterion_id} ({nct_id})",
  "input": {"criterion_text": "...", "trial_has_cohorts": null},
  "output": {
    "splitting_decision": "...",
    "child_logic": "...",
    "cohort_scope": null,
    "sub_criteria": [
      {"child_id": "a", "text_span": "...", "cohort_scope": null, "rationale": "..."}
    ],
    "confidence": "high",
    "notes": "짧은 splitting 근거 (판정 메타 아님 — 아래 주의)"
  }
}
```

> ⚪ **v2.3(⚪6) — 기존 예시의 실측 스키마.** 기존 `examples.json`의 prompt_1 예시 5개는 **전부 output에 `notes` 키가 있다**(v2.2까지의 위 템플릿에는 누락돼 있었다). 또 필드 위치가 가변이다 — KEYNOTE-001 I1_F는 `cohort_scope`가 top-level 없이 child에만 있고, none-decision 예시(KEYNOTE-671 I4)는 `sub_criteria` 자체가 없다. 따라서 아래 "동일 스키마" 검증을 **키 완전 일치**로 구현하면 기존 예시 자체가 실패한다 — 이 변형을 허용하도록 구현할 것.

**완료 기준**

- 변환된 예시의 `text_span`이 `criterion_text`의 부분문자열임이 검증된다. 🟡 **`span_override != null`인 gold 항목은 이 검증을 통과할 수 없으므로 few-shot 후보에서 자동 제외**하고, 제외 목록을 별도 출력한다(🟡2 — 채택하려면 사람이 span을 수동 재구성)
- 변환된 예시의 output 키가 기존 `examples.json`의 prompt_1 예시와 **동일 스키마**(child `rationale`·`cohort_scope`·output `notes` 포함, 단 ⚪6의 위치 가변 허용)임이 검증된다 — 누락 시 LLM이 해당 필드를 안 내보내도록 학습됨
- `rule_status=conflict` 항목과 tier별로 후보를 필터링할 수 있다

**주의**

- **`examples.json`을 직접 덮어쓰지 말 것.** 후보 파일을 별도 생성하고, 채택은 사람이 결정한다 (§4)
- child `rationale`은 gold envelope의 sub_criteria에서 가져온다. C-2에서 **분해 라벨이면 child_rationale이 필수 입력**이므로(🟡4) 분해 gold에는 항상 존재한다 — 사후 작성 fallback이 불필요해졌다
- 판정 메타(`tier`·`rule_id`·`rule_status` 등 `adjudication` 블록)를 예시 `output`에 넣지 말 것 — 프롬프트에 노출되면 안 되는 내부 정보다. `output.notes`에는 짧은 splitting 근거만(판정 메타 아님)

---

#### D-5. held-out trial 샘플링

**왜 필요한가**

3라운드를 기존 8 trial로 반복하면 **학습효과와 원칙 내재화가 구분 불가**해진다. 판정 과정에서 두 사람이 gold에 노출되면 오염이 확정된다. 리뷰어가 반드시 지적할 지점이다. 논문 서술도 이 구조가 강하다: Round 1·2 = guideline development phase, Round 3 = validation phase(held-out 최종 IAA).

**무엇을 만드는가**

AACT에서 새 NSCLC trial 4~6건을 기존과 **동일한 층화 목적추출** 기준으로 샘플링(perioperative / consolidation / metastatic 1L / metastatic 2L+ / basket). 기존 8건과 중복 배제. 층화 기준은 `iaa_pipeline_spec/iaa_8trials_selection.md` 참조.

**완료 기준**

- 층화 기준과 추출 조건이 재현 가능하게 기록된다 (논문 Methods용)
- criterion 추출은 ClinicalTrials.gov API v2로 (AACT flat 포맷 금지 — A-4 주의와 동일)

---

## 4. 사람이 해야 하는 부분 (Claude Code가 하지 말 것)

| # | 작업 | 이유 |
|---|---|---|
| 1 | **~85건 blind 라벨링 + gold 확정** | 판정 그 자체. 임상 워크플로우 판단 필요 |
| 2 | **tier 지정 + rationale 작성** | 판정 근거는 판정자만 안다 (D-3의 유일 소스) |
| 3 | **gap ticket 작성** | tier=3 항목의 처리 방향 결정 |
| 4 | **규칙 승격 결정 + v1.2 문장 작성** | D-3이 후보만 제시 |
| 5 | **PI 에스컬레이션** | `escalate_pi=true` 항목의 임상 판단 |
| 6 | **few-shot 예시 채택 결정** | D-4가 후보만 생성 |
| 7 | **캘리브레이션 피드백 전달 방식** | D-1 숫자를 어떻게 전달할지 |

---

## 5. 금지사항

| 금지 | 이유 |
|---|---|
| **2:1 다수결로 gold 자동 결정** | 판정자 blind_label은 제3 의견이지 투표권이 아니다. EHJ=DYK≠gold 케이스(§7.2에서 실증)가 이 작업이 찾으려는 대상 |
| **Tier 0 위반 건의 gold 자동 확정** | "이 라벨은 틀렸다"와 "정답은 이것이다"는 다른 판단 |
| 가이드라인 v1.2 규칙 문장 생성 | 규칙은 판정 논거에서 귀납 (§1.4) |
| `examples.json` 직접 덮어쓰기 | few-shot 구성은 프롬프트 성능에 직접 영향 |
| round1/round2 envelope 수정 | 원자료. read-only |
| text_span 자동 정규화 | 원문 그대로가 원칙 |
| **새 Streamlit 앱 생성** | 기존 `iaa_pipeline/streamlit_app.py` 재사용 (§B) |
| 기존 8 trial로 3라운드 설계 | 학습효과 교락 (§D-5) |
| 댓글/논의/다중 사용자 기능 추가 | 판정자 1명, 1회성 |
| AACT flat 포맷으로 criterion 추출 | `~*` 구분자가 bullet 구조 파괴 → macro_aggregate 판정 불가 |
| 사람 envelope **읽기** 시 `sub_criteria[].rationale`·대다수 `notes`가 있다고 가정 | 실측상 rationale 0건·notes 7% (§9-1). **단 이는 "읽기"에만 적용** — gold "쓰기"(D-4)에서는 rationale·cohort_scope를 반드시 포함(②·§9-8) |

---

## 6. 실행 순서

```
1일차 (코드) — ✅ 전부 구현 완료 (2026-07-30, §10 참조)
  A-1 지표 2단 분해 ✅  metrics.py compute_sd_axes + compute_iaa.py SDbin/SDtyp 컬럼
  A-4 NCT03800134 원문 복구 ✅  번들 데이터에서 복구 (네트워크 재추출 불필요)
  A-3 판정 큐 생성 ✅  scripts/build_adjudication_queue.py (층 배정 S1>S2>S3>S4)
  A-2 Tier 0 위생 점검 ✅  scripts/tier0_check.py (round2 실측 3건)
  B-1/B-2/B-3 앱 수정 ✅  streamlit_app.py + iaa_pipeline/adjudication.py
  C-1/C-2 판정 화면 필드 ✅  tier·rationale_short 필수, 분해 시 child_rationale 필수
  D-2 코드 수정 0 ✅  합성 GOLD로 3쌍 산출 실증 (§10-2)

2~5일차 (사람)  ← 현재 여기
  판정 작업 ~113건, 4~5세션 (S2 필터 확정으로 ~85 → 113, §10-1)
  ※ §7.2 최우선 항목부터 (큐 priority 1~4에 자동 배치됨)

이후 (코드, 반나절)
  D-1 정확도·편향 집계 (🟠1 층별 분모 필수)
  D-3 논거 빈도 집계 (소스 = C-2 rationale_short)
  D-4 few-shot 후보 생성 (span_override 항목 제외)
  D-5 held-out trial 샘플링
```

**판정 시작 방법**

```bash
# 1) 큐·Tier0 생성 (이미 생성돼 있으면 생략)
python scripts/build_adjudication_queue.py --out results/adjudication
python scripts/tier0_check.py --round 2 --out results/adjudication

# 2) 판정 UI — 사이드바에서 Role = "Adjudicator", Round = 2
streamlit run iaa_pipeline/streamlit_app.py
#    · 🔒 Blind pass ON  → 1차 통과 (peer 라벨 미로드)
#    · 🔒 Blind pass OFF → 2차 통과 (peer 공개, blind_label 보존)

# 3) 판정 중 언제든 GOLD 축 확인 (해석은 🟠1 가드 참조)
python scripts/compute_iaa.py --stage 1 --round 2
```

**A-1을 맨 앞에 두는 이유**: 어노테이터 시간이 0이고, 결과가 판정 순서를 결정한다. (v2.3 시점: 이미 구현·검증 완료 — 워킹트리 미커밋 상태이므로 커밋부터 할 것.)

---

## 7. 부록

### 7.1 데이터 위치 (**v2 실측 반영**)

| 대상 | 경로 |
|---|---|
| 어노테이션 envelope | `iaa_workspace/{trial}/stage1/round{1,2}/{EHJ,DYK}_{trial}_stage1_committed.json` |
| 판정 결과 (신규) | `iaa_workspace/{trial}/stage1/round2/GOLD_{trial}_stage1_committed.json` (🔴1 안 A — GOLD를 round2/에 두어야 compute_iaa가 페어 계산) |
| gap ticket (신규) | `iaa_workspace/{trial}/stage1/round2/gap_tickets.json` (tier=3 항목; GOLD envelope에서 분리 — 🔴2) |
| trial 원문 | `iaa_workspace/{trial}/stage1/input.json` (**NCT03800134 결측** → A-4) |
| IAA 계산 | `scripts/compute_iaa.py`, `iaa_pipeline/metrics.py` |
| 어노테이션 UI (재사용 대상) | `iaa_pipeline/streamlit_app.py` · 호스트용 `streamlit_apps/stage1_app.py` |
| ~~workspace.py~~ | **존재하지 않음**. 참고본만 `docs/audit_reference/workspace.py`, 아무 데서도 import 안 됨 |
| 검증 자산 | `pipeline/validators.py`, `pipeline/06_validate_annotation.py`, `pipeline/08_review_queries.py` |
| 프롬프트 | `pipeline/prompts/prompt_1_splitting.txt`, `pipeline/prompts/examples.json` |
| 온톨로지 spec | `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md` |
| 불일치 분석 | `results/iaa/iaa_stage1_disagreements.md`, `results/iaa/iaa_stage1_report.md` |
| UI 감사/블라인딩 근거 | `iaa_pipeline_spec/audit_streamlit_v1.md` |

대상 8 trial: NCT01295827(KEYNOTE-001) / NCT02075840(ALEX) / NCT02125461(PACIFIC) / NCT02474355(ASTRIS) / NCT02912949(eNRGy) / NCT03728556(GEMSTONE-301) / NCT03800134 / NCT05756153(GFH925)

### 7.2 최우선 판정 항목 — 예외 조항 충돌 (**v2 재구성**)

가이드라인 v1.1의 §4 macro 규칙과 §4 참고의 "단일 카테고리 한 번 조회 → none" 예외 조항이 충돌하는 지점. v1 초안은 아래 4건을 모두 "현재 불일치"로 적었으나, **round2 라벨 실측 결과 2건은 이미 해소됐다**(§9-3). 다만 해소된 2건은 **둘 다 none인데 가이드라인 정답은 macro** — §1.4 "합의해도 틀릴 수 있다" 가설의 실증 사례이므로, S1이 아니라 **S2(일치+오답의심)**로 최우선 판정한다.

| trial | criterion | 원문 요지 | round1 | round2 | v2 분류 |
|---|---|---|---|---|---|
| NCT02474355 | I6 | Adequate bone marrow reserve and organ function… CBC | none / composite | **none / macro** | **S1 불일치(유지)** — 최우선 |
| NCT05756153 | E6 | uncontrolled systemic diseases, such as hypertension or diabetes | none / macro | **none / macro** | **S1 불일치(유지)** — 최우선 |
| NCT03728556 | E6 | immune checkpoints, including PD-1, PD-L1, CTLA4… | none / macro | **none / none** | **S2 일치·오답의심** — 최우선 |
| NCT02474355 | E8 | abnormalities in rhythm, conduction… resting ECG | none / macro | **none / none** | **S2 일치·오답의심** — 최우선 |

I6·E6(NCT05756153)은 가이드라인에 **정답이 명시된 예시와 거의 동일한 문장인데도** 불일치가 유지됐다(§1.3). E6(NCT03728556)·E8은 두 사람이 none으로 수렴했으나 가이드라인 macro와 어긋난다 — 판정 결과가 예외 조항을 유지할지·조건을 붙일지·폐쇄할지를 결정한다.

### 7.3 Tier 정의

| Tier | 근거 | 성격 | 예 |
|---|---|---|---|
| **0** | spec v1.2.2 구조적 제약 | 논의 불가, spec이 정답을 강제 | composite_split 부모는 child ≥2 / child_logic non-null / **한 Criterion = 단일 semantic_category** |
| **1** | 임상 권위 (NCCN NSCLC v5.2026) | 문헌 인용으로 확정 | resectability는 TNM staging과 독립축 → 진단/병기/절제 3-way |
| **2** | CRC EMR 조회 단위 | 판정자 권한 | comorbidity와 conmed는 같은 페이지라도 CRC가 따로 조회 |
| **3** | 어느 것으로도 결정 안 됨 | **gap ticket** | v1.3 로드맵 / 프롬프트 confidence=low 처리 |

> ⚠️ **v2.1 정정(③) — Tier는 권위 축이지 자동화 축이 아니다.** Tier 0은 "spec이 구조적으로 정답을 강제하는가"이며, **A-2가 자동 검출할 수 있는지와 무관**하다. 특히 **"한 Criterion = 단일 semantic_category"는 Tier 0의 가장 강한 판정 논거**다 — Stage 1 envelope에 category 필드가 없어 A-2가 자동으로 못 잡을 뿐, 권위가 낮아지는 게 아니다. 판정자는 이 논거를 "Stage 2 소관"으로 오해하지 말고 직접 확인해서 적용해야 한다. (실제 근거 사례: NCT02075840 I6 "major surgery or traumatic injury"에서 EHJ가 split의 근거로 든 것이 정확히 이 원칙이고, "semantic_category가 다르면 query-unit이 달라질 확률이 높다"는 명시적 유지 결정이 있었다.) → 요약: **자동 검사 가능한 것(child ≥2, child_logic non-null)과 사람이 확인해야 하는 것(단일 semantic_category)이 모두 Tier 0**이며, 후자는 A-2에서 걸러지지 않으니 판정 화면에서 판정자가 점검한다.

상위 Tier에서 결정되면 하위는 적용하지 않는다. **Tier 3을 억지로 정답 처리하지 않는 것이 중요하다** — Paper 1의 limitation과 human-in-the-loop 설계 근거가 된다.

### 7.4 판정 기록 스키마 (**v2.1 — `compute_iaa.py` 자동 발견과 정합**)

> ⚠️ **v2.1 정정(①)**: v2 초안은 gold를 `gold_label` 블록 안에 중첩했으나, `compute_stage1_iaa`는 각 record의 **최상위** `splitting_decision`/`child_logic`/`sub_criteria`/`cohort_scope`를 읽는다(`metrics.py:201,208-211,320,130`). 따라서 **gold 라벨은 record 최상위에 두어야** GOLD 축 IAA가 계산된다. `blind_label`·`adjudication`은 D-3에서만 쓰는 부가 키이므로 중첩으로 둔다.

GOLD envelope는 기존 committed envelope와 **동일한 record 구조**(최상위 = gold)를 쓰고, 판정 메타를 부가 키로 얹는다:

```json
{
  "criterion_id": "NCT05756153_E6",

  // ── gold = record 최상위 (compute_iaa.py가 이 필드들을 읽음) ──
  "splitting_decision": "macro_aggregate",
  "child_logic": null,
  "cohort_scope": null,
  "sub_criteria": [
    {"child_id": "a", "text_span": "...", "cohort_scope": null, "rationale": "..."}
  ],
  "confidence": "high",

  // ── 부가 키 (IAA 계산에는 무시됨, D-3에서만 사용) ──
  "blind_label": {
    "splitting_decision": "macro_aggregate",
    "child_logic": null,
    "sub_criteria": [{"child_id": "a", "text_span": "..."}]
  },
  "adjudication": {
    "tier": 2,
    "rationale_short": "hypertension과 diabetes는 진단목록에서 각각 별도 조회",
    "rule_id": "guideline_v1.1_§4_macro",
    "rule_status": "conflict",
    "conflicting_rule": "guideline_v1.1_§4_참고_단일카테고리_none",
    "escalate_pi": false,
    "span_override": null,
    "adjudicated_at": "2026-..-..",
    "queue_stratum": "S1",
    "compared": {"EHJ": "none", "DYK": "macro_aggregate"}
  }
}
```

- 🔴 **`tier=3`(판정 불가) record는 GOLD envelope에 넣지 말 것.** `null`을 최상위에 두면 `cohens_kappa`가 이를 `"__NONE__"` 별도 클래스로 계수해 GOLD 축 κ를 오염시킨다(`metrics.py:81-83`; §9-11). 대신 **`gap_tickets.json`으로 분리**한다 — gold set은 "확정된 정답"만 담는다. gap ticket 스키마 예:
  ```json
  // gap_tickets.json — tier=3 항목만
  { "criterion_id": "NCT..._E9", "tier": 3, "reason": "NCCN·CRC 어느 근거로도 미결정",
    "blind_label": {"splitting_decision": "none"},
    "EHJ": "none", "DYK": "composite_split", "escalate_pi": true, "note": "..." }
  ```
  - ⚪ **v2.3(⚪5)**: gap ticket에도 `tier`(항상 3)와 판정자의 **`blind_label`을 기록**한다. tier=3 항목이야말로 "본질적으로 어려운 항목"이므로, blind 의견을 버리면 D-3의 `blind_label ≠ gold_label` 분석에서 가장 중요한 표본이 빠진다
- **child `rationale`·`cohort_scope`는 gold(최상위) sub_criteria에 포함한다** — `prompt_1_splitting.txt`가 요구하는 필드이고 D-4 few-shot 변환의 입력이다(②·§9-8). 단 `blind_label`의 sub_criteria에는 생략해도 무방
- 주의: 사람(EHJ/DYK) 원본 envelope에는 child `rationale`이 없다(§9-1). 이는 **읽기** 규칙이고, GOLD **쓰기**에는 적용되지 않는다 — 두 방향을 혼동하지 말 것
- envelope 최상위는 기존과 동일하게 `source:"annotator"`, `annotator:"GOLD"`, `committed:true` — `compute_iaa.py` 자동 발견 요건(§9-3)

### 7.5 판정 대상 규모

| 층 | 대상 | 건수 |
|---|---|--:|
| S1 | SD 불일치 (지속21+해소15+신규13) | 49 |
| S2 | 양측 일치 + 위험군 (§7.2 오답의심 2건 포함) | ~15 |
| S3 | SD 일치 + child#/span만 불일치 | ~20 |
| S4 | 나머지 일치 항목 (순차 표집, §A-3-④) | ~25 → 가변 |
| | **합계** | **~85 (S4 확대 시 증가 가능)** |

항목당 5~8분 → 8~11시간, 3~4세션. (S1 층 구성은 `results/iaa/iaa_stage1_disagreements.md`의 지속/해소/신규 목록과 일치 — §9-6.) S4는 both-wrong 비율에 따라 확대될 수 있어 총 건수는 하한이다.

---

## 8. 착수 전 확인 요청 (**v2.3 갱신**)

| # | 확인 항목 | 상태 |
|---|---|---|
| 1 | `iaa_workspace` 구조·envelope 스키마 | ✅ 확인·§7.1/§1.1에 반영 |
| 2 | compute_iaa 액터 하드코딩 여부 | ✅ **하드코딩 아님**, 자동 페어링(§9-3). GOLD는 안 A로 round2/에 저장(🔴1) |
| 3 | Stage 1 envelope에 semantic_category 존재? | ✅ **없음**(§9-4). A-2에서 category 검사 제외 |
| 4 | NCT03800134 재추출 시 criterion 개수 22건 일치? | ✅ **해결** — 번들 데이터(`streamlit_apps/data/`)에 원문 존재, 22건·criterion_id 4개 envelope와 완전 정렬(§10-3). 네트워크 재추출 불필요 |
| 5 | streamlit_app.py bias 취약점 수정 여부 | ✅ **GOLD 경로 재발 방지 확인** — 판정 폼도 blind/open 2함수로 분리(A1/A2/A7 대응), peer 탭은 blind 시 미생성(A3 대응), blind 시 peer 파일 **미로드**. 테스트 4건(`test_adjudication.py`) |
| 6 | GOLD를 round2/에 두면 기존 `--round 2` EHJ-DYK 리포트에 GOLD 쌍이 섞임 | ✅ **안 A 채택·실증**(§10-2) — 3쌍 출력되고 EHJ-DYK POOLED는 172/0.650 그대로 불변 |
| 7 | tier=3 `gap_tickets.json` 분리 방식·스키마 | ✅ v2.3에서 스키마 확정(🔴2·⚪5·§7.4) — `tier`·`blind_label` 포함, GOLD envelope에 null 넣지 않음 |
| 8 | round2/의 `gap_tickets.json`이 discovery에 오인 발견되는가 | ✅ **안전 확인**(§9-14) — 배열이면 `_load`가 None 반환, dict여도 `source` 필터에서 제외 |
| 9 | A-1 구현 상태 | ✅ **구현 완료·회귀 일치**(§9-13) — 미커밋 diff, 커밋 필요 |
| 10 | S1>S2>S3>S4 층 배정 우선순위(🟡4) | ✅ **구현** — `build_adjudication_queue.py`, 한 항목은 한 층에만 |
| 11 | E-G/D-G κ 해석 가드(🟠1)의 논문 기술 방식 | ⏳ **연구자 확인** — 코드 측 가드는 완료(UI 경고 + D-1 층별 분모 주의). 논문 문장은 사람 몫 |
| 12 | S2 위험군 필터 최종 범위 | ✅ **`strong` 확정**(§10-1) — 문서 스펙에서 세미콜론 단독 분기만 제거. CRC 관점 키워드 재검토는 여전히 §4 사람 몫 |

---

## 9. 검증 로그 (v2 교정의 코드 근거, 2026-07-30)

- **§9-1 notes/rationale 실측**: 32개 committed envelope · 688 record 스캔. record-level `notes` **47건**, `rationale` **0건**; child-level(sub_criteria 611개) `rationale` **0건**; `cohort_scope` 4건, `confidence` 688건. 존재하는 notes 예: `"진단명 예시 -> macro로 split 하지 않음"`(EHJ), `"실패와 내성 같은 의미이기에 non-split"`(DYK).
- **§9-2 workspace.py**: `iaa_pipeline/workspace.py` 부재. `docs/audit_reference/workspace.py`만 존재하고 `grep -rn import`에서 참조 0. 실제 UI 로직은 `iaa_pipeline/streamlit_app.py`(33KB): `Phase`(56), `resolve_tabs`(106), `render_criterion_form_blind`(205, `llm_record` 미수용), `save_envelope`(148), `list_committed_annotator_envelopes`(165), span `text_area`(345).
- **§9-3 compute_iaa 자동 페어링 + §7.2 재검증**: `discover_sources`가 `source=="annotator" & committed==true`로 발견(64), `itertools.combinations`로 전 페어 계산(198), `--round`는 int(153,179). §7.2 4건 round1/round2 라벨 직접 대조 → NCT03728556 E6·NCT02474355 E8은 round2에서 둘 다 `none`(해소), NCT02474355 I6·NCT05756153 E6은 불일치 유지.
- **§9-4 semantic_category 부재**: Stage 1 record 키 = `criterion_id/splitting_decision/sub_criteria/child_logic/confidence`. category 없음 → 08_review_queries 2.2/2.3 이식 불가, 3.2/3.3만 가능(141,155행에 실재).
- **§9-5 input.json 위치**: 실제 `iaa_workspace/{trial}/stage1/input.json`. NCT03800134만 결측.
- **§9-6 지표 재현**: 독립 스크립트로 EHJ/DYK 항목 비교 → SD 불일치 36(1차)/34(2차), 관측일치 136/172→138/172, 방향편향 (EHJ만9,DYK만20,유형7)→(3,24,7), S1=지속21+해소15+신규13=49, matched 172. `results/iaa/iaa_stage1_report.md`·`iaa_stage1_disagreements.md`와 일치.
- **§9-7 examples.json**: `prompt_1_splitting` 예시 5개 출처 = SEQUOIA I1(NCT02923921), KEYNOTE-671 I5/E5/I4(NCT03425643), KEYNOTE-001 I1_F(NCT01295827).

### v2.1 검토 라운드 근거 (2026-07-30)

- **§9-8 스키마↔자동발견 충돌(①) + D-4 필드 요구(②)**: `compute_stage1_iaa`는 매칭 record의 **최상위** 필드를 읽는다 — `a.get("splitting_decision")`(`metrics.py:201`), `child_logic`(208-211), `cohort_scope`는 record + sub 레벨(`_cohort_scope_repr`, 130-133), `text_span`은 `sub.get`(320-321). 따라서 gold를 `gold_label` 안에 중첩하면 GOLD 축 전 지표가 None → §7.4를 최상위 구조로 교정. 한편 `prompt_1_splitting.txt`는 child `rationale`("brief 1-sentence reason", 59행)·child `cohort_scope`(58)·top-level `cohort_scope`(53)를 출력 스키마로 **요구**하고, 기존 examples.json 5개 output도 전부 child `rationale`+`cohort_scope`를 포함(§9-7 항목 재확인) → D-4는 두 필드를 유지해야 함. 두 사실이 결합되어: **읽기=rationale 없음 / 쓰기=rationale 필수**의 방향 분리가 강제됨.
- **§9-9 A-2 실측 위반 건수(④)**: 32 envelope 전수 스캔. `splitting_decision=="composite_split"` **202건** 중 3.2 위반(sub_criteria<2) **2건**, 3.3 위반(child_logic ∈ {null,""}) **3건**. 총 ~5건 → A-2는 gating 효과 없음, 위생 점검으로 격하.
- **§9-10 Tier 0 논거(③) 근거 사례**: 단일 semantic_category 원칙은 Stage 1 envelope에 category 필드가 없어 자동 검출 불가하나(§9-4), 판정 논거로는 최상위다. 실사용 예 NCT02075840 I6("major surgery or traumatic injury")의 split 근거가 이 원칙(불일치 분석 및 캘리브레이션 기록). → Tier(권위)와 자동화 가능성을 분리하도록 §7.3 문구 교정.

### v2.2 검토 라운드 근거 (2026-07-30)

- **§9-11 D-2 `--subdir`이 0쌍(🔴1)**: `compute_iaa.py` main 루프는 trial마다 **하나의** `round_dir`을 `discover_sources`에 넘기고(`182`), 액터 집합을 그 결과에서만 만든다 — `all_annotators = sorted({a for (anns,_) in per_trial.values() for a in anns})`(`191`). `adjudication/`엔 GOLD 1명뿐이라 `all_annotators={GOLD}` → `itertools.combinations([GOLD],2)`(`198`) = 빈 리스트 → `if not pairs`에서 "Need at least 2 sources" 반환(`202-205`). 따라서 GOLD를 EHJ·DYK와 **같은 디렉터리(round2/)**에 둬야 3쌍이 나온다. → 안 A 채택.
- **§9-12 tier=3 null이 κ 오염(🔴2)**: `cohens_kappa`(`metrics.py:61`)는 입력 라벨의 None을 제외하지 않고 **`"__NONE__"` 센티넬로 정규화해 별도 클래스로 계수**한다(`81-83`, `_norm` 함수). `compute_stage1_iaa`는 `sd_a=[a.get("splitting_decision") for a,_ in alignment.matched]`(`201`)로 매칭된 모든 record를 그대로 넣으므로, GOLD의 `splitting_decision:null`은 자동 제외되지 않고 5번째 클래스가 되어 GOLD 축 κ를 왜곡한다. v2.1이 gold를 최상위로 올린 결과(①) null이 최상위에 노출되면서 생긴 위험. → tier=3은 `gap_tickets.json`으로 분리해 GOLD envelope에서 배제.

### v2.3 검토 라운드 근거 (2026-07-30, **코드 실행** 검증)

- **§9-13 v2.2 정합성 실행 확인 + A-1 구현 완료 + GOLD 표본 편향(🟠1)**: `python scripts/compute_iaa.py --round 1` / `--round 2`를 직접 실행 → §9-6 수치 전부 재현(R1: SD κ 0.608 / obs 0.791 / 편향 EHJ9·DYK20·유형7, R2: 0.650 / 0.802 / 3·24·7). 이 출력에 SDbin/SDtyp 컬럼이 이미 존재 — **A-1은 워킹트리에 구현 완료 상태**다(`metrics.py`의 `compute_sd_axes`·`SPLIT_DECISIONS`·`expected` 필드, `compute_iaa.py`의 SDbin κ/SDtyp κ 컬럼과 direction bias 출력, 미커밋 diff; 신규 테스트 포함 `tests/test_iaa_metrics.py` 통과). 이 diff로 인해 본 문서의 기존 인용 라인번호는 밀렸다(`metrics.py:81-83→84-85`, `201→260`, `compute_iaa.py:64→64(동일)`, `182/191/198→211/220/227` 등 — 논리는 전부 유효). 한편 pair 루프는 한쪽 envelope이 없는 trial을 skip하고(`if not env_a or not env_b: continue`), `align_stage1`은 criterion_id **교집합**만 matched로 삼는다 → GOLD 쌍의 유효 표본 = GOLD envelope 수록분(판정 ~85건, S1 49건 포함)뿐. E-D(전수 172건)와 모집단이 달라 κ 병렬 비교 불가 → 🟠1 해석 가드.
- **§9-14 streamlit_app round 비인지(🟡3) + gap_tickets discovery 안전(⚪확인)**: `streamlit_app.py` 실측 — `annotator_envelope_path` = `stage_dir / f"annotator_{safe}.json"`(평면 저장), `list_committed_annotator_envelopes(stage_dir)`는 stage_dir 평면 glob, `list_trials`는 `{trial}/stage{N}/input.json` 존재를 요구(NCT03800134는 A-4 전까지 드롭다운에 안 뜸 — §6 순서와 정합). 파일 전체에 "round" 문자열 부재 — round1/round2 폴더는 수동 정리물이고 코드 인지는 `compute_iaa.py --round`뿐. 부가 확인: round2/에 둘 `gap_tickets.json`은 discovery에 안전 — JSON 배열이면 `_load`가 dict 아님으로 None 반환(`compute_iaa.py:43-48`), dict여도 `source=="annotator" & committed` 필터에서 제외.
- **§9-15 B-3↔D-4 충돌(🟡2)**: 코드가 아니라 문서 내부 논리 결함 — B-3 주의의 override 허용(병기 표현 등 의도적 비연속 span)과 B-3 완료기준("부분문자열 아니면 저장 안 됨")·D-4 완료기준(부분문자열 검증)이 양립 불가였다. v2.3에서 B-3 완료기준을 "override 없는 한 거부"로 정정하고 D-4에 `span_override != null` 후보 자동 제외를 추가해 해소.
- **§9-16 examples.json 재실측(⚪6)**: prompt_1 예시 5개의 output 키 실측 — **5개 전부 `notes` 포함**(§7.4/D-4 템플릿에는 v2.2까지 누락). `cohort_scope`는 4개가 top-level, KEYNOTE-001 I1_F만 child-level에만 존재. KEYNOTE-671 I4(none 예시)는 `sub_criteria` 자체가 없음. → D-4 "동일 스키마" 검증은 키 완전 일치가 아니라 이 변형을 허용해야 기존 예시와 정합.

---

## 10. 구현 기록 (2026-07-30)

§6 "1일차 (코드)" 전량 구현 완료. 산출물:

| 파일 | 역할 |
|---|---|
| `scripts/tier0_check.py` | A-2 Tier 0 위생 점검 → `tier0_violations.csv` |
| `scripts/build_adjudication_queue.py` | A-3 층화 판정 큐 → `adjudication_queue.{csv,json}` |
| `iaa_pipeline/adjudication.py` | 판정 순수 로직 (span 검증·필수필드·gold/gap record·경로). streamlit 미의존 |
| `iaa_pipeline/streamlit_app.py` | B-1/B-2/B-3 + C-1/C-2. Role=Adjudicator, round 경로, blind 토글, 판정 필드 |
| `tests/test_adjudication.py` | 36 테스트 전부 통과 |
| `iaa_workspace/NCT03800134/stage1/input.json` | A-4 복구본 |

### 10-1. S2 필터를 `strong`으로 확정한 근거 (⏳12 해소)

문서 §A-3의 S2 예상치 "~15건"은 **umbrella 필터 도입 전(v2.1) 수치**였다. 실측하면 dx/bm 키워드만 쓸 때 14건으로 그 추정과 거의 일치하는데, v2.2가 🟠3에서 umbrella/나열 필터를 필수로 추가하면서 건수 추정만 갱신되지 않았다. 4개 변형을 round2 일치 123건에 적용한 실측:

| 변형 | S2 | 총 큐 | 문서 요구 6건 포착 |
|---|--:|--:|---|
| `spec` (문서 문자 그대로) | 47 | 125 | 6/6 |
| **`strong` (기본값)** | **35** | **113** | **6/6** |
| `umbrella` | 26 | 106 | 6/6 |
| `keyword` (v2.1 범위) | 14 | 95 | **2/6** ❌ |

`keyword`는 "Adequate organ function."(NCT01295827_I6, 둘 다 none)과 NCT02125461_E4(가이드라인 macro 예시문과 거의 동일한데 둘 다 macro)를 놓친다 — S2가 존재하는 이유인 both-wrong 계열이므로 탈락.

`strong`은 `spec`에서 **세미콜론 단독 분기만** 제거한 것이다. 그 분기가 추가하는 12건은 실측상 (a) 12/12 라벨 일치, (b) 12/12에서 `enum:semicolon`이 유일 신호, (c) 12/12에서 세미콜론이 정확히 1개·문자열 맨 끝, (d) 11/12이 NCT02912949 한 trial — 즉 원본 목록의 **줄 끝 구분자 서식 흔적**이다(`"Pregnant or lactating;"`, `"Performance status of ECOG 0 - 2;"`). 한편 전체 8 trial에서 문장 **내부** 세미콜론 나열은 5건뿐이고, 그 5건은 3건이 이미 S1(불일치)이고 2건이 콤마/`or`/umbrella로 이미 걸린다 → **세미콜론 분기를 정교화해도 `strong` 대비 추가 0건.** 정보 손실 없는 제거다.

→ 결과 총 큐 **113건, 판정 9.4~15.1시간**(§7.5의 ~85건/8~11시간에서 상향). `--s2-filter`로 4개 변형 전환 가능. **키워드 목록 자체의 CRC 관점 재검토는 여전히 §4 사람 몫.**

### 10-2. D-2 안 A 실증 + 🟠1 재현

합성 GOLD envelope(S1 상위 30건, 6 trial)을 `round2/`에 두고 `compute_iaa.py --stage 1 --round 2` 실행 → `Annotators: DYK, EHJ, GOLD`로 **3쌍 자동 산출, 코드 수정 0**. 기존 EHJ-DYK POOLED는 172/κ 0.650 **그대로 불변**(GOLD 추가가 기존 지표를 오염시키지 않음).

동시에 🟠1이 숫자로 재현됐다: GOLD 쌍의 matched가 **30건**(전수 172 대비)이고, EHJ-GOLD κ = **-0.123 / obs 0.200**이 나왔다. 표본이 S1(불일치)만이라 구조적으로 극단값이 되는 것이며, 같은 표에 찍히는 0.650과 **비교 불가**임을 실증한다. 이 경고는 IAA 대시보드에서 GOLD가 포함된 쌍을 선택할 때 UI에 직접 표시된다.

### 10-3. 구현 중 확인된 사실

- **A-4는 네트워크 불필요**: `streamlit_apps/data/NCT03800134/stage1/input.json`에 원문이 이미 있었고, criterion 22건·criterion_id가 round1/round2 × EHJ/DYK 4개 envelope와 **완전 정렬**(누락·잉여 0). AACT flat `~*` 마커 없음. byte-identical 복사. 비부분문자열 span 비율(EHJ 2/24, DYK 7/26)도 다른 7 trial 기준선(0~9/22)과 동일 수준이어서 올바른 소스임이 교차 확인됐다.
- **A-2 실측은 round2 기준 3건**(§9-9의 5건은 round1 2건 + round2 3건 **합산**). round2만 대상인 A-2 스코프에서는 3건 — gating 효과 없음이라는 결론은 더 강해진다.
- **B-3 span 검증은 자주 발동한다**: 어노테이터 span의 약 10~25%가 이미 비부분문자열이다(공통 전제 복제·병기 표현 등 가이드라인 예외). 따라서 `span_override`는 예외적 경로가 아니라 **일상적으로 쓰이는 경로**다. D-4가 이 항목을 few-shot에서 자동 제외하므로(🟡2), 분해 gold 상당수가 few-shot 후보에서 빠질 수 있다 — 후보 수가 부족하면 사람이 span을 수동 재구성해야 한다.
- **판정 폼도 blind/open 2함수로 분리**했다. `render_adjudication_form_blind`는 `peer_records`를 **인자로 받지 않으며**(A1/A7 대응), peer 탭은 blind 시 탭 목록에서 아예 제외되고(A3 대응), blind 시 peer 파일을 **읽지 않는다**(숨기지 않고 미로드 — session_state 캐싱 누출 방지). 회귀 테스트 4건.
- **tier=3 분기 주의**: gold 라벨 필수조건(child_rationale 등)을 tier=3에도 적용하면 gap ticket이 **도달 불가**가 된다. 구현은 tier=3일 때 rationale만 요구하도록 분기했다.
