# 연구 진행 현황 정리 — AMIA 2027 Amplify (Informatics Summit, CRI 트랙) 제출 준비용

> **작성일**: 2026-08-21 (최종 갱신: **2026-09-03** — §2.6 adjudication 결과 반영)
> **목적**: 지금까지의 작업을 제출용 프레이밍/초안 작성의 재료로 정리. 수치는 전부 저장소 내 문서·결과 파일에서 검증된 값만 기재.
> **제출 대상**: AMIA 2027 Amplify Informatics Conference (2027-04-12~15, Atlanta), Informatics Summit — Clinical Research Informatics 트랙
> **마감**: **2026-09-03 (목) 23:59 EDT** — 예외 없음

---

## 1. 프로젝트 한 줄 요약

임상시험 적격성 기준(eligibility criteria)을 4-layer 의료 온톨로지(Neo4j LPG)로 구조화하는 GraphRAG 스크리닝 시스템의 **Phase 1**: LLM 5단계 어노테이션 파이프라인 구축 + blind 이중 어노테이터 IAA 평가 프레임워크 + adjudication 기반 gold set 구축(진행 중). 도메인은 NSCLC.

---

## 2. 완료된 작업 (영역별)

### 2.1 프로덕션 어노테이션 파이프라인 (`pipeline/`)

- **입력**: ClinicalTrials.gov / AACT 원문 criteria → **NSCLC 30 trial** 배치 실행 완료
- **5단계 LLM 흐름** (`orchestrator.py`):
  1. Prompt 1 — splitting 판단 + cohort_scope
  2. Prompt 2 — semantic_category + relation_type + target_subtype
  3. Prompt 3 — preferred_name 정규화
  4. Stage I/J — regex 추출(`regex_extractor.py`) + Prompt 4 LLM fallback → HAS_VALUE / HAS_TEMPORAL
  5. Prompt 5 — alternative_constraint / exception_qualifier (frontier 모델)
- **스키마**: 자체 설계 온톨로지 명세 **v1.2.2** (`pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md`), enum 정의는 `pipeline/config.py`가 단일 소스. v1.2.3 패치 문서 초안 존재
- **후처리·품질 체계**: 멱등 cleanup 3종(03–05) → 검증 스크립트(06, 6개 검출 패턴, 현재 30 trial / 40 issues) → Neo4j 적재(07) → **Cypher 리뷰 쿼리 21종**(08) + 리뷰어 워크플로우(`REVIEW.md`, `review_session.py` → xlsx)
- **재현성 장치**: temperature 0.0 고정, 모델 preset 체계(A–D), provider 자동 감지(OpenAI/Anthropic), sha256 키 LLM 디스크 캐시
- **검수→규칙 승격 원칙**: 동일 패턴이 ≥3 trial에서 발견될 때만 `validators.py` 규칙(R1–R4/C1–C3)으로 승격

### 2.2 IAA 평가 프레임워크 (`iaa_pipeline/` + `streamlit_apps/`)

- **범위**: Stage 1(splitting)이 end-to-end로 완성. Stage 2–5는 스키마·정렬 로직까지 구현, runner는 stub
- **구성요소**:
  - 정렬(`aligners.py`): Stage 1은 criterion_id, Stage 2는 fuzzy span(SequenceMatcher ≥ 0.85)
  - 지표(`metrics.py`): 자체 구현 Cohen's κ(외부 의존성 없음), set agreement, per-field F1, span F1
  - **Blinding을 함수 시그니처 수준에서 강제** — blind 렌더 함수가 `llm_record` 파라미터 자체를 받지 않음. UI 정보 누출 자체 감사(`audit_streamlit_v1.md`: critical 3건 전부 시그니처 수준 봉쇄)
  - 어노테이션 UI 2종: 로컬(파일시스템 기반) + Streamlit Community Cloud 호스팅(무상태·세션 한정·다운로드 워크플로우)
  - 테스트: `test_iaa_metrics.py` 44건 + `test_adjudication.py` 50건 (LLM/런타임 불필요)
- **표본 설계**: 층화 추출 — 상세 경로는 §2.3

### 2.3 표본 선정 경로 (source-of-truth 확정, 2026-08-24 검증)

**convenience sample이 아니라 명시적 stratified purposive sampling.** 3개 소스에 기록돼 있음: `results/nsclc_protocol_candidates_selected.xlsx`, `iaa_pipeline_spec/iaa_8trials_selection.md`, `pipeline/HANDOFF.md` §12-10b.

**3단계 깔때기**

| 단계 | n | 방법 | 소스 |
|---|--:|---|---|
| ① AACT sampling frame | **8,520** | NSCLC 전체. Phase/Status/Enrollment/Modality/Biomarker/Line/Histology/Stage/Sponsor 속성 + eligibility 원문 별도 파일 | `nsclc_sampling_frame.xlsx`, `..._eligibility.xlsx` |
| ② 후보 추출 | **47** | **NCCN v5.2026 치료 경로 분기 구조**에 기반한 15개 selection cell (Primary 8 = Stage × Line, 각 target 2–4 / Secondary 7 = driver·modality coverage, 각 1) | `nsclc_protocol_candidates.xlsx` |
| ③ 최종 선정 | **30** | 검수자가 51행(47 + 검토 중 추가 4)을 판정. 21건 제외, 사유 전건 기록 | `nsclc_protocol_candidates_selected.xlsx` |
| ④ IAA 하위표본 | **8 (+1)** | 30건 중 층화 재추출 + 이후 1건 추가 | `iaa_8trials_selection.md`, commit `e0da99c` |

③의 제외 사유 분포 (전건 free-text `reviewer_comment` 동반): 분류 부적합 8 · 풍부도 부족 5 · NSCLC 비특이적 4 · cross-cell 패턴 중복 2 · 셀 내 패턴 중복 2. 검토 중 추가된 4건 = PACIFIC(NCT02125461), NCT00326378, NCT01168973, eNRGy(NCT02912949).

**④ IAA 하위표본의 층화 축** (`iaa_8trials_selection.md`)

- Stage: Early 1 · LocAdv 2 · Advanced 1 · Metastatic 4
- Line: 1L 4 · 2L+ 2 · Maint/Consol 1 · 미지정 1
- Biomarker: PD-L1 4 · EGFR 1 · ALK 1 · KRAS 1 · NRG1 1
- Modality: Chemo+IO 4 · TKI 1 · Surgery 1 · Bispecific 1 · ChemoRT/Surgery 1
- Phase: PHASE1 1 · PHASE1/2 1 · PHASE2 1 · PHASE3 5 / Enrollment 47–3,017 (median 547) / basket 1건
- 추가로 **stage별 stress-test 매핑**을 명시 (Stage 1 = macro_aggregate·cohort_scope·basket, Stage 3 = variant_type 4종, Stage 4 = patient_event anchor 등)

**선정 문서의 8개 ≠ 실제 분석된 8개** (2026-08-24 해소 — 근거 확정 후 `iaa_8trials_selection.md`에도 반영 완료)

| | 구성 |
|---|---|
| 선정 문서의 8개 | KEYNOTE-671, PACIFIC, GEMSTONE-301, ALEX, KEYNOTE-001, ASTRIS, GFH925, eNRGy |
| **실제 분석 8개 (172쌍)** | PACIFIC, GEMSTONE-301, ALEX, KEYNOTE-001, ASTRIS, GFH925, eNRGy, **AEGEAN(NCT03800134)** |

- **KEYNOTE-671(NCT03425643)은 분석에서 빠짐.** committed envelope 32개(=8 trial × 2인 × 2라운드)를 전수 확인한 결과 KEYNOTE-671 것은 **0건**. 선정 문서는 이 trial을 "**Pilot — EHJ/DYK already reviewed**", HANDOFF는 "(pilot, macro_aggregate)"로 기재 → 두 어노테이터가 이미 본 파일럿 trial
- **AEGEAN이 그 자리를 대체.** 2026-06-04 commit `e0da99c`, 커밋 메시지 "perioperative durvalumab+chemo, **parallel-structure cross-validation vs KEYNOTE-671**". AEGEAN은 8,520건 sampling frame에는 있었으나 47건 후보 추출에서는 뽑히지 않았던 trial이며, criteria는 AACT `eligibilities.txt` + `design_groups.txt`에서 직접 추출
- **대체의 구조적 평행성은 frame 속성으로 검증됨** — 둘 다 PHASE3 · Early/Perioperative · PD-L1 · Surgery 포함 · INDUSTRY 스폰서. enrollment만 797 → 825로 바뀌어 하위표본의 **range(47–3,017)·median(547)·phase·biomarker·modality 분포가 모두 불변**. 즉 층화가 실제로 보존됨(주장이 아니라 확인된 사실)

**✅ 제외 근거 확정 (2026-08-24, 연구자 확인)**
KEYNOTE-671은 **어노테이션 워크플로우 파일럿·캘리브레이션에 사용된 trial이므로 의도적으로 측정 대상에서 제외**했다. 두 어노테이터가 이미 해당 trial에 노출된 상태라 blind 조건이 성립하지 않기 때문이다. 비게 된 Perioperative 셀은 구조적으로 평행한 AEGEAN(perioperative durvalumab+chemo)으로 대체하여 층화를 보존했다. → 이 결정은 이후 3라운드 설계 원칙("기존 trial 재측정 금지, held-out trial 사용")과 동일한 사전 노출 통제 논리이며, **일관된 방법론으로 서술 가능**하다.

**참고**: `results/review_log_*.xlsx` 6건(2026-05-11)은 라운드1 어노테이션(6월 11일)보다 앞서며, 그중 ALEX·PACIFIC은 IAA 8건에 포함된다. 다만 내용은 relation/HAS_VALUE 등 **Stage 2/4 검수**이지 Stage 1 splitting이 아니므로 직접 오염은 아님. 리뷰어 지적 가능성이 있으니 인지만 해둘 것.

**Methods 문장 — 초록용 (영문, 확정판)**

> From an AACT-derived sampling frame of 8,520 NSCLC trials, we applied stratified purposive sampling across six axes (disease stage, line of therapy, biomarker, modality, histology, and phase) organized by the treatment-pathway branch points of NCCN NSCLC v5.2026, yielding 47 candidates from which 30 protocols were selected; additional selection stopped at theoretical saturation, when no new eligibility-criteria patterns emerged. Eight trials were drawn for dual-annotator evaluation. The trial used to pilot and calibrate the annotation workflow was excluded from measurement to avoid prior-exposure bias and was replaced by a perioperative trial from the same stratification cell, matched on phase, stage, biomarker, modality, and enrollment (825 vs. 797 participants), leaving the subsample's stratification distribution unchanged. The analytic sample comprised 8 trials and 172 aligned criterion pairs.

한 문장으로 더 줄여야 할 경우:

> Eight NSCLC trials (172 aligned criterion pairs) were drawn by stratified purposive sampling over six axes structured by NCCN v5.2026 treatment pathways; the workflow-calibration pilot trial was excluded from measurement to avoid prior-exposure bias and replaced by a structurally parallel trial from the same stratum.

**국문 원본** (selected.xlsx Summary 시트에 이미 작성돼 있던 문장 + 확정된 파일럿 제외 절 추가):
> 6개 층화 기준(Stage, Line of Therapy, Biomarker, Modality, Histology, Phase)에 대해 NCCN v5.2026의 치료 경로 분기 구조에 기반한 stratified purposive sampling을 수행하였다. Stage × Line of Therapy를 primary axis로 하여 각 셀에서 최소 2개 시험을 선정하고, Biomarker × Modality 다양성 및 Histology/Phase coverage를 보충하여 총 30개 시험을 선정하였다. 추가 시험의 선정은 새로운 eligibility criteria 패턴이 더 이상 관찰되지 않을 때(theoretical saturation) 중단하였다. 이 중 8개 시험을 이중 어노테이션 평가 대상으로 추출하였으며, 어노테이션 워크플로우의 파일럿·캘리브레이션에 사용된 시험은 사전 노출 편향을 피하기 위해 측정에서 제외하고 동일 층의 구조적으로 평행한 perioperative 시험으로 대체하였다.

### 2.4 IAA 실험 — 2라운드 완료

설계: NSCLC **8 trial(분석 대상, §2.3)**, 어노테이터 2명(EHJ, DYK), from-scratch blind → IAA 측정 → 가이드라인 개정(v1.0→v1.1) → 재측정. 정렬된 criterion 쌍 **172건(POOLED)**.

| 지표 | 1차 | 2차 | Δ |
|---|--:|--:|--:|
| **SD κ** (splitting_decision, 주요 지표) | 0.608 | 0.650 | +0.042 |
| CL κ (child_logic) | 0.763 | 0.867 | +0.104 |
| child#.exact (분해 개수 일치) | 0.430 | 0.593 | +0.163 |
| span F1 (분해 경계 일치) | 0.556 | 0.677 | +0.121 |
| cohort.exact | 0.983 | (report 참조) | |

출처: `results/iaa/iaa_stage1_report.md`, 독립 재계산으로 검증(`adjudication_handover.md` §9-6).

### 2.5 핵심 발견 — 2라운드의 "표면적 성공, 실질적 정체" (프레이밍의 중심 후보)

숫자상 κ는 올랐지만, 축별로 분해하면:

| 축 | 결과 |
|---|---|
| 분해 **방식** (몇 조각, 어디서 자를지) | 크게 개선 (+0.12~0.16) — 기계적으로 검증 가능한 규칙이 대응 |
| 분해 **여부** (쪼갤지 말지) | **정체** — SD 불일치 36 → 34건 |
| 분해 **유형** (macro/composite/nested) | **변화 없음** — 7 → 7건 |

세부 진단:
- 불일치의 **약 80%가 `무언가 ↔ none`** 유형 ("한 명은 쪼갰고 한 명은 통짜로 뒀다"). 판단 근거인 query-unit 개념("CRC가 따로 조회하는 단위인가")은 규칙이 아닌 판단 원칙이라 문서만으로 전달 실패
- **κ 상승은 대부분 artifact**: 관측 일치는 136/172(0.791) → 138/172(0.802), **+1.1%p(2건)뿐**. κ 상승분의 대부분은 한 어노테이터가 보수적으로 이동해 marginal 분포가 벌어진 효과
- **방향성 편향은 오히려 심화**: EHJ만 분해 9→3 / DYK만 분해 20→24
- **결정적 증거**: 가이드라인 v1.1에 정답이 명시된 예시와 거의 동일한 문장이 2차에서도 불일치 유지 → 문제는 규칙 부재가 아니라 **규칙 미적용**. 심지어 2라운드에서 두 사람이 새로 "합의"한 답이 가이드라인 정답과 어긋난 사례 존재 → **합의 기반 adjudication이 정답을 보장하지 않는다는 직접 증거**

→ 결론: 가이드라인 개정만으로는 split-or-not 판단이 교정되지 않음. **외부 권위(Tier 체계) 기반 adjudication으로 gold set을 구축**하는 방향으로 전환.

### 2.6 Adjudication / gold set 구축 (**S1 층 판정 완료 — 2026-09-03**)

- 설계 문서: `iaa_pipeline_spec/adjudication_handover.md` (v2.3 — 4회 코드 실행 검증 반영)
- 핵심 설계 원칙:
  - adjudication은 **합의가 아니라 판정** — 판정자가 외부 권위(Tier 0=spec 구조 제약 > Tier 1=NCCN 등 임상 근거 > ...)로 정답 확정. 다수결/2:1 자동 판정 금지
  - 판정자 blind 라벨은 제3의 독립 의견이며 투표권 아님
  - 가이드라인 v1.2는 이 작업의 **산출물**(판정 논거의 사후 귀납)이지 입력이 아님
  - 판정 불가 항목은 억지 정답 대신 **gap ticket**으로 명시적 분리 (κ 오염 방지)
- 구현 완료: 층화 판정 큐 생성(`build_adjudication_queue.py`, **113건**: S1 불일치 49 = 21+15+13, S2/S3 위험군, S4 순차 표집), Tier 0 위생 점검(`tier0_check.py`), 지표 2단 분해(`compute_sd_axes`), Streamlit Adjudicator 역할/Round 2 지원, 테스트 50건
- **판정 완료: 74건** — S1 전체 49건(persist 21 + resolved 15 + new 13) + S4 25건. gap ticket 0건, 8 trial. 남은 S2 35 / S3 4는 초록 범위 밖(future work)
- freeze: `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/` (sha256 포함 MANIFEST) — 기록 `docs/amia2027_gold_freeze_2026-09-03.md`
- 초록 숫자는 **live workspace가 아니라 frozen export에서** 재계산: `scripts/amia_stage1_numbers.py` → `docs/amia_stage1_numbers.md`
- 후속 계획: gold set → 라벨러별 정확도·편향 집계 → 논거 빈도 집계 → 가이드라인 v1.2 → gold 기반 few-shot 프롬프트 v2 → **held-out trial 4–6건으로 3라운드** (기존 9 trial 재측정은 학습효과 오염으로 금지)

#### 2.6-1 판정 결과 — 초록에 쓸 숫자 (74건 기준)

| outcome | n |
|---|--:|
| 두 사람 일치 → gold 확정 | 37 |
| 갈림 → gold가 EHJ 편 | 17 |
| 갈림 → gold가 DYK 편 | 14 |
| **두 사람 만장일치 → gold가 둘 다 뒤집음** | **3** |
| 갈림 → gold가 **제3의 답** | **3** |

**2:1 다수결로는 나올 수 없는 케이스가 6건**(만장일치 뒤집기 3 + 제3의 답 3). §2.5의 "합의가 정답을 보장하지 않는다"를 gold set 위에서 정량화한 값으로, 권위 기반 adjudication 논지의 핵심 근거.

Gold 축 일치도(판정 대상 74건):

| 축 | n | agreed | observed | κ |
|---|--:|--:|--:|--:|
| EHJ vs GOLD | 74 | 54 | 0.730 | 0.524 |
| DYK vs GOLD | 74 | 51 | 0.689 | 0.494 |
| EHJ vs DYK (같은 표본) | 74 | 40 | 0.540 | 0.286 |

> ⚠️ 판정 큐는 불일치를 의도적으로 과대표집한 층화 표본이므로 **74건과 round-2 전체 172건은 비교 불가**. 74건 κ를 corpus 일치도의 두 번째 추정치로 쓰지 말 것. 또한 gold 축 κ는 chance-corrected agreement이지 **accuracy가 아님** — 정답률에 해당하는 값은 `agreed` 열(73.0% / 68.9%). 상세 가드는 `docs/amia_stage1_numbers.md` §2·§3.

`rule_status`: existing 64 · new 9 · conflict 1(`NCT05756153_E6`) · `escalate_pi=true` 3건. 판정은 **전건 단일 blind pass**이므로 blind→revealed 수정 표본(D-3)은 0건 — 초록에서는 "single blind pass"로 명시.

### 2.7 부수 산출물

- LLM(Prompt 1)을 제3 어노테이터로 취급하는 비교 축 지원 (`compute_iaa.py --include-llm`)
- 라운드 간 비교 도구 (`compare_rounds.py`, 2-axis SD Δ 테이블)
- 프로덕션 출력 → IAA envelope 무비용 변환기 (`convert_production_to_iaa.py`, LLM 호출 0)
- NSCLC 표본 추출 프레임 (`results/nsclc_sampling_frame*.xlsx` — 30 trial 선정 과정)

---

## 3. 미완 작업 (제출 시 한계/향후 연구로 처리할 것)

| 항목 | 상태 | 제출 프레이밍 |
|---|---|---|
| Adjudication 판정 | ✅ **74건 완료** (2026-09-03) | 초록 본문 결과로 사용. S2 35 / S3 4는 미판정 → 한계 절 |
| 가이드라인 v1.2 + 프롬프트 v2 | gold set 이후 | Future work |
| Held-out 3라운드 (최종 IAA) | 미실시 | Future work — "최종 검증 미완"은 리뷰어 지적 가능 지점 |
| Stage 2–5 IAA | runner stub | 명시적 scope 한정: "Stage 1은 파이프라인 정확도의 상한을 결정" 논리로 정당화 |
| 하류 GraphRAG 에이전트 | scaffold만 | 배경/동기로만 언급 |

---

## 4. AMIA CRI 트랙 프레이밍 후보

### 4.1 왜 CRI 트랙에 맞는가

eligibility criteria 구조화, 어노테이션 가이드라인 개발, IAA 방법론, 임상시험 지식표현(온톨로지) — 전부 CRI의 전형적 주제. LLM 활용은 AI/Data Science 트랙과도 겹치지만, **기여의 중심이 "어노테이션 품질 방법론"이면 CRI가 적합**.

### 4.2 기여점(contribution) 후보 — 강한 순

1. **방법론적 발견**: 가이드라인 개정만으로는 splitting 합의가 개선되지 않으며, κ 상승이 marginal artifact일 수 있음을 축 분해(방식/여부/유형)로 실증. "합의가 정답을 보장하지 않는다"는 직접 사례 → 권위 기반 adjudication의 필요성 논증
2. **재현 가능한 IAA 프레임워크**: 함수 시그니처 수준 blinding 강제, 층화 표본 설계, 자체 κ 구현, adjudication 큐의 층화 설계(불일치 + both-wrong 위험군 + 순차 표집) — 오픈소스화 가능한 설계
3. **LLM 5단계 어노테이션 파이프라인** 자체 + 30 trial 실행 결과 (단독으로는 novelty 약함 — 1·2의 맥락 재료로 사용 권장)

### 4.3 제목 방향 예시 (초안용)

- "Why did our kappa go up but agreement didn't? Decomposing inter-annotator agreement in LLM-assisted structuring of clinical trial eligibility criteria"
- "Guideline revision is not enough: an adjudication-based gold standard workflow for eligibility criteria decomposition"
- "A blinded dual-annotator framework for evaluating LLM-assisted eligibility criteria annotation in NSCLC trials"

### 4.4 제출 유형별 판단 (2026-08-21 기준)

| 유형 | 판단 | 근거 |
|---|---|---|
| **Podium abstract** | ✅ **주 후보** | 2라운드 결과 + artifact 분석만으로 완결된 스토리. 50–75단어 요약 + 본문 |
| Paper | ⚠️ 조건부 | ~~adjudication 완료~~ + gold 기반 라벨러 정확도·논거 집계까지 있으면 "준완결" 주장 가능. **2026-09-03 기준 74건 판정·집계 완료(§2.6-1)** — 남은 조건은 논거 빈도 집계와 held-out 3라운드(부재 시 한계 절 명시) |
| Poster | ✅ fallback | 예비 결과 형식 |

### 4.5 Methods 절 소스 매핑

| 논문 절 | 소스 문서 |
|---|---|
| 스키마/온톨로지 | `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md`, `pipeline/config.py` |
| 파이프라인 구조 | `pipeline/PIPELINE.md` |
| 표본 선정 | `iaa_pipeline_spec/iaa_8trials_selection.md` + `results/nsclc_protocol_candidates_selected.xlsx`(Summary 시트에 Methods 초안 문장) + `pipeline/HANDOFF.md` §12-10b — 요약은 §2.3 |
| Blinding 설계 | `iaa_pipeline_spec/audit_streamlit_v1.md` |
| IAA 지표 정의·결과 | `results/iaa/iaa_stage1_report.md` |
| 라운드 간 분석·adjudication 설계 | `iaa_pipeline_spec/adjudication_handover.md` §1 |

---

## 5. 제출 전 확인 필요 사항

- [ ] 제출 유형별 정확한 분량 제한·템플릿 — [amia.secure-platform.com/amplify](https://amia.secure-platform.com/amplify)에서 직접 확인 (사이트 봇 차단으로 자동 조회 불가)
- [ ] 미발표 원저 요건 확인 (동일 내용 타처 미제출)
- [ ] COI(이해상충) 폼 — 마감일 동일 (2026-09-03)
- [ ] 어노테이터 2인(EHJ, DYK) 저자 포함 여부 및 순서
- [x] ~~adjudication 판정 작업 일정 확정~~ → **74건 판정 완료 (2026-09-03)**. §2.6-1에 결과 반영
- [x] ~~KEYNOTE-671 제외가 의도적 설계였는지 확인~~ → **확정: 파일럿 제외 (2026-08-24)**. §2.3 반영 완료
- [x] ~~`iaa_8trials_selection.md` 문서-데이터 정합화~~ → 파일럿 제외 + AEGEAN 대체 기록 완료 (2026-08-24)
