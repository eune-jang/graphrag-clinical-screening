# Handoff — 2026-05-11 / 2026-05-27 세션 인계 문서

> 다음 Claude 세션을 위해 작성. 오늘 1일 작업의 맥락, 산출물, 현재 상태, 미해결 항목을 정리.
>
> **2026-05-27 업데이트** — IAA framework 1차 구현 (aligners + metrics + Streamlit UI). 자세한 내용은 §12 참조.

---

## 0. 빠른 시작 (다음 Claude가 먼저 읽을 것)

순서대로 읽기:
1. **이 문서 (HANDOFF.md)** — 오늘 전반 요약 + 다음 작업 후보 (§12에 IAA framework 추가됨)
2. **`pipeline/PIPELINE.md`** — 스크립트 인벤토리 + 데이터 흐름 (IAA framework 섹션 포함)
3. **`pipeline/REVIEW.md`** (또는 Notion 버전) — 검수 워크플로우
4. **`pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md`** — 4-layer 온톨로지 스펙 (필요 시)
5. **`iaa_pipeline_spec/`** — IAA 평가 framework 설계 문서 (03 schemas, 04 stage runners)

빠른 환경 확인:
```bash
cd /Users/jang-eunhye/graphrag-clinical-screening
# Neo4j 인스턴스 (protocol-kg-dev) 실행 중인지 확인
python3 -c "from dotenv import load_dotenv; load_dotenv('.env'); import os; from neo4j import GraphDatabase; d=GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))); d.verify_connectivity(); print('OK')"
```

---

## 1. 프로젝트 컨텍스트 (한 줄)

GraphRAG 기반 임상시험 환자 적격성 자동 스크리닝. 4-layer medical ontology (Neo4j LPG) + small LLM. NSCLC primary 도메인.

- **사용자**: 데이터/임상 연구자. 30 NSCLC trial annotation을 수동 검수 중.
- **현재 단계**: Phase 1 = LLM annotation 정제 + 검수 워크플로우 구축.
- **다음 단계 후보**: Phase 2 SMC validation (30 trial 후) — 미시작.

---

## 2. 오늘 세션의 주요 작업 흐름

### 2-1. 검수 자동화 인프라 구축 (Neo4j 기반)
- **목적**: 기존 INCEpTION + Label Studio 경로에서 이탈. Neo4j + JSON + xlsx로 검수.
- **구축**: Neo4j Desktop 2 인스턴스 (`protocol-kg-dev`) 생성, ingest 스크립트, Cypher 쿼리집, validator refactor.

### 2-2. LLM annotation 파이프라인 결함 발견 + 수정
- **30 trial 전체에 cleanup 적용**: 599 → 40 issues (93% 감소).
- **소스 코드 fix 4건** (`orchestrator.py` 3곳 + `regex_extractor.py` 종합).

### 2-3. 파이프라인 정리 + git commit
- 파일명 통일 (sequential 01-08).
- Cleanup 한 번 끝난 스크립트는 `_archive_` prefix로 분리.
- ~343MB 회수 (INCEpTION jar, Label Studio 데이터, 디버그 로그).
- **Commit `558a64b`** (36 files, +10474 lines insertions) — 푸쉬는 안 함.

### 2-4. 검수 가이드라인 작성 + 반복 개선
- `REVIEW.md` + `REVIEW_notion.md` (Notion 포맷 버전, 두 파일 sync 유지).
- 5개 검수 항목 (canonical) 표 / Step 1-5 사이클 / 휴리스틱 5종 / Worked Example.
- 실제 reviewer 시뮬레이션 → 7개 마찰점 발견 → 그 중 3개 즉시 fix.

### 2-5. Reviewer 시뮬레이션 + xlsx 산출물
- 4개 trial 검수 시뮬레이션 (KEYNOTE-671, NCT03219268, DREAM3R, PACIFIC, NCT01631552, ALEX).
- 각 trial별 xlsx finding log 생성 (`results/review_log_*.xlsx`).

---

## 3. 현재 파이프라인 구조 (변경 후)

```
01_criteria_extraction       Stage A: AACT 추출
02_llm_annotation            Stage B: 5-stage LLM orchestrator
03_recover_has_value         Cleanup ①: regex post-hoc (no LLM)
04_correct_relation_type     Cleanup ②: subtype↔relation 자동 정정
05_reextract_constraints     Cleanup ③: Prompt 4 selective LLM
06_validate_annotation       검증 메타 (_validation, _issues) 부착
07_neo4j_ingest              Neo4j 적재
08_review_queries            Cypher 21개 일괄 실행

_archive_labelstudio_export       (구) LS export — 미사용
_archive_dedup_nested_exception   orchestrator source-fix 후 미사용
_archive_rename_observation       동일

(외)
review_queries.cypher          Neo4j Browser용 cheat sheet
REVIEW.md / REVIEW_notion.md   검수자 가이드 (sync 유지)
PIPELINE.md                    스크립트 인벤토리
```

라이브러리 모듈: `config.py`, `orchestrator.py`, `regex_extractor.py`, `transforms.py`, `validators.py`, `llm_client.py`.

---

## 4. 소스 코드 fix 누적 (orchestrator + regex)

| 파일 | 위치 | 변경 |
|---|---|---|
| `orchestrator.py:357` | nested_exception 중복 emit 방지 (조건을 composite_split/macro_aggregate로 좁힘) | 110건 duplicate_entry 해소 |
| `orchestrator.py:252-300` | regex 결과 empty 시 Prompt 4 fallback 보장 (`is_complete` semantic bug) | 68건 value_props_missing 회수 |
| `orchestrator.py:320,330` | `target_subtype="LabTest"` → `"Observation"` (v1.2.2 명칭) | 18건 subtype_mismatch 해소 |
| `regex_extractor.py` | (1) 인코딩 정규화 (`\>=`, `\x1e`, `\x7f` → ≥) (2) 자연어 연산자 ("at least", "greater than or equal to" 등) (3) test_name optional + comma value 허용 | 58/172 case 회수 (33.7%) |

---

## 5. 30 trial 현재 상태

```
Trial 노드          30
Criterion 노드   1,462 (raw 1,517 — dedup 후)
ConceptRef 노드  1,188
Edge 총합        3,989

검수 결함 (40 = 0.3% crit / 2% rel)
  temporal_props_missing            18  ← HAS_TEMPORAL이 numeric 없는 target에 부착 (Prompt 2 오부착)
  value_props_missing                8  ← 동일
  span_not_in_text                   6  ← 3건 hallucination + 3건 unicode mangling
  nested_exception_no_carveout       5  ← Prompt 5 미생성
  subtype_mismatch                   3  ← Pattern D: EXCLUDES_STATUS → Biomarker
```

기존 처음 599 결함의 trajectory:
```
Original                          599
After Path 1 (orchestrator)       384
After Option 3 (regex)            304
After Option 1 (span fuzzy)       188
After Option 2 (subtype correct)  127
After LLM 재추출                   40   ← 현재 상태
```

---

## 6. 검수 시뮬레이션에서 발견된 cross-trial 패턴 (validator 후보)

### 🚨 Performance Status range 누락 — **5 trial 확정**
```
NCT03425643_I5  ECOG "0 to 1"  →  op=≥, val=0  (상한 누락)
NCT03219268_I2  ECOG "0 or 1"  →  empty
NCT04334759_I4  ECOG "0 or 1"  →  empty
NCT02125461_I4  WHO PS "0 to 1" →  op=≥, val=0  (상한 누락)
NCT02075840_I3  ECOG PS "0-2"  →  op=≤, val=2  (하한 누락) — ALEX
```
**처리 권장**: validator R5 추가 (HAS_VALUE for ECOG/WHO PS 패턴에서 range 양쪽 확인) 또는 prompt_4 examples 보강.

### 🚨 INCLUDES_EXCEPTION `exception_type=None` — 5 trial 누적, 평균 50%
```
NCT03219268    9 IE  /  3 None (33%)
NCT04334759   17 IE  / 11 None (65%)
NCT01631552    6 IE  /  3 None (50%)
NCT02075840    4 IE  /  2 None (50%)
```
**처리 권장**: validator R6 추가 (`INCLUDES_EXCEPTION + exception_type=null`) 또는 Prompt 5 출력 정규화.

### Life expectancy numeric 추출 누락 — 2 trial 확인
```
NCT02125461_I5  "life expectancy more than 12 weeks"   →  HAS_VALUE/HAS_TEMPORAL 없음
NCT02075840_I2  "Life expectancy at least 12 weeks"    →  동일
```
**처리 권장**: 휴리스틱 추가 ("text에 numeric+unit 있는데 HAS_VALUE/HAS_TEMPORAL 없음").

---

## 7. 미해결 / 다음 작업 후보 (우선순위순)

> **2026-05-27 변경** — 기존 후보 G (Phase 2 SMC validation 준비) 앞 단계로 **IAA framework**가 추가 구현됨. §12 참조. 아래 A~H는 production pipeline 관련 후보로 그대로 유효.

### A. 검수 워크플로우 보강 (low effort, high value)
- **Step 3b 휴리스틱 우선순위 가이드** — 큰 trial(ALEX 34, DREAM3R 87)에서 의심 case 15+ 발화. 검수자 시간 배분 가이드 필요.
- **새 휴리스틱 추가** — "text에 numeric+unit 있는데 HAS_VALUE/HAS_TEMPORAL 없음" (life expectancy 패턴).

### B. validator 규칙 추가 (medium effort)
- **R5 PS range 패턴** — ECOG/WHO PS의 "0 to 1" / "0-2" / "0 or 1" range가 single value로만 추출됨.
- **R6 INCLUDES_EXCEPTION exception_type=null** — 평균 50%가 누락. 자동 검출 강력 후보.

### C. Pattern D 정리 (medium effort, 3건만)
- NCT03219268_E16c 3건 EXCLUDES_STATUS→Biomarker → REQUIRES_BIOMARKER + status=negative 변환.
- relation_type 변경 + property 추가 → 09_correct_relation_type.py에 special case 추가 또는 수동 마이그레이션.

### D. macro_aggregate 추출률 (high effort)
- 30 trial 162 criteria 중 8건만 macro_aggregate. 스펙 권장보다 낮음 (KEYNOTE-671 I4 organ function 등 missing).
- Prompt 1 examples 보강 + 재추출 사이클.

### E. 4 reference 외 26 trial 검수 실행
- 검수자가 REVIEW.md 따라가며 진행할 예정. xlsx는 trial당 1개씩 생성.

### F. Cross-trial concept normalization
- Q5.1 hub query 결과 (top 15 hubs) 기록됨.
- "ECOG performance status" vs "Eastern Cooperative Oncology Group..." 같은 변종 정리 필요.
- Layer 3 Concept 정규화 prep 작업.

### G. Phase 2 SMC validation 준비
- 30 trial 검수 완료 후 진행. 별도 데이터셋 합류 필요.

### H. 코드 ↔ ontology spec v1.2.2 정합성 패치 (2026-05-12 점검)

코드가 v1.2.2 self-correction 5개 중 3개만 반영 상태. 나머지 2개 + 부수 항목 정리 필요. 30 trial 영향 측정 완료 (아래 표).

**이미 반영된 v1.2.2 항목** (수정 불필요):
- `strictness` strip (config.py:150 LLM_OUTPUT_STRIP_FIELDS)
- `t/n/m_descriptor` strip (config.py:152-154)
- `requirement_waiver` 제거 → `EXCEPTION_TYPES` 4개 (config.py:107-110)
- `procedure_event` 제거 → `ANCHOR_TYPES` 3개 (config.py:103)
- LabTest → Observation 명칭 변경 → `CONCEPT_SUBTYPES` (config.py:86)

**v1.2.1 잔존 (수정 대상)**:

| # | 위치 | 현재 | v1.2.2 spec | 실제 emit 수 (30 trial) |
|---|---|---|---|---|
| ① | `config.py:90` | ✅ **RESOLVED 2026-05-27**: `CHILD_LOGIC = {AND, OR}`. `stage_schemas.py:104` docstring 동기화. Streamlit dropdown에서 XOR 옵션 제거됨. 30 trial XOR emit 0건 확인 → 데이터 무영향. | `{AND, OR}` (XOR 제거) | XOR **0건** |
| ② | `config.py:92-95` | ✅ **RESOLVED 2026-05-27**: `VARIANT_TYPES` 6개 (amplification/methylation/unknown 제거됨). 5건 영향 (NCT01884285 amp 1 + unknown 3, NCT03219268 amp 1) — **모두 비-IAA trials**라 즉시 영향 X. 22 follow-up corpus 작업 시 재처리. | 6개 | amplification 2 + unknown 3 (모두 비-IAA) |
| ③ | `config.py:105, 160` | ✅ **POLICY DECIDED 2026-05-27**: 현재 strip 유지 (코드 보수). 코멘트 "v1.3" → "Stage 3 IAA work begins" 로 갱신. v1.2.2 spec align은 Stage 3 IAA 작업과 함께 진행 예정. | 5 enum active (정책 보류) | ~58 variant 잠재 영향 (보류) |
| ④ | `config.py:17` | ✅ **DOCUMENTED 2026-05-27**: SCHEMA_PATH는 사용처 0 (dead reference). v1.2.1.json은 historical reference로 유지. v1.2.2 JSON 생성은 Stage 3 IAA 작업과 함께. | (deferred) | 무영향 |
| ⑤ | `validators.py:8` docstring | ✅ **RESOLVED 2026-05-27**: 모듈 docstring을 v1.2.2 self-correction 현황표로 재작성 (CHILD_LOGIC/VARIANT_TYPES/EXCEPTION_TYPES/ANCHOR_TYPES/CONCEPT_SUBTYPES aligned, variant_notation/strictness/descriptor deferred). | — | 주석 정합성 확보 |

**결과 영향 요약** (2026-05-27 갱신):
- **재처리 필요했던 5건**: 모두 비-IAA trials (NCT01884285, NCT03219268) → 22 follow-up corpus 작업 시 처리. IAA 8 trials 무영향.
- **variant_notation policy decided**: strip 유지 — Stage 3 IAA 시작 시 spec align 재검토.
- **enum/주석 정리 완료**: XOR 제거 ✓, amplification/methylation/unknown 제거 ✓, validators.py docstring 갱신 ✓, SCHEMA_PATH 코멘트 추가 ✓.

**부수 발견 — child_logic 과다 명시 가능성**:
- 30 trial에서 child_logic: AND 84건, OR 173건 (총 257건)
- spec line 157: "default와 다른 semantics일 때만 명시" — 즉 inclusion-AND, exclusion-OR은 omit 권장
- prompt_1_splitting.txt:24-32는 이 룰을 명시하지만 LLM이 default 케이스도 전부 명시 emit 중
- 검토 거리 (데이터 손실은 아님). 진짜 override 케이스(inclusion-OR, exclusion-AND)만 추리는 후처리 가능.

**처리 순서 권고** (한번에 반영 시):
1. config.py enum 2개 정리 (XOR, variant_type 3개 제거) + SCHEMA_PATH + 주석 정합화
2. 영향 받은 5건 (NCT01884285, NCT03219268) 재추출 또는 수동 정정
3. variant_notation 정책 결정 → 살리면 prompt_3 또는 prompt 추가 + 30 trial 재추출
4. child_logic 과다 명시는 별도 후처리 (08_review_queries.py 검토 쿼리 추가 또는 ingest 시 default 케이스 strip)

---

## 8. 주요 파일 위치 (다음 세션 빠른 참조)

### 코드 (active)
- `pipeline/01_criteria_extraction.py` — AACT raw → input_trials.json
- `pipeline/02_llm_annotation.py` — orchestrator wrapper
- `pipeline/03_recover_has_value.py` — regex post-hoc (no LLM)
- `pipeline/04_correct_relation_type.py` — subtype/relation 매핑 자동 정정
- `pipeline/05_reextract_constraints.py` — Prompt 4 selective LLM
- `pipeline/06_validate_annotation.py` — _validation 메타 부착 (R1-R4, C1-C3)
- `pipeline/07_neo4j_ingest.py` — Neo4j 적재
- `pipeline/08_review_queries.py` — Cypher 21개 일괄
- `pipeline/orchestrator.py` — LLM 5-stage 파이프라인 (Path 1 fix 적용됨)
- `pipeline/regex_extractor.py` — 정규화 + 자연어 패턴 (Option 3 fix 적용됨)

### 문서
- `pipeline/PIPELINE.md` — 스크립트 인벤토리
- `pipeline/REVIEW.md` — 검수 워크플로우 (canonical)
- `pipeline/REVIEW_notion.md` — Notion 포맷 (REVIEW.md와 sync)
- `pipeline/review_queries.cypher` — Cypher cheat sheet
- `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md` — v1.2.2 스펙

### 데이터 (untracked)
- `pipeline/output/NCT*_annotation.json` — 30 trial annotation (validation 메타 포함)
- `results/review_log_*.xlsx` — reviewer 시뮬레이션 산출물 (총 7개)
- `results/nsclc_protocol_candidates_selected.xlsx` — 30 trial 선정 기록

### 환경
- `.env` (project root) — Neo4j credentials (`NEO4J_PASSWORD=12345678` 테스트용)
- `pipeline/.env` — OPENAI_API_KEY
- Neo4j Desktop 2 인스턴스: `protocol-kg-dev` (port 7687, db `neo4j`, 2026.04.0 enterprise)

### 아카이브 (참조용, 실행 X)
- `pipeline/_archive_labelstudio_export.py`
- `pipeline/_archive_dedup_nested_exception.py`
- `pipeline/_archive_rename_observation.py`

### IAA framework (2026-05-27 추가, `iaa_pipeline/` — production pipeline과 별개 트랙)
- `iaa_pipeline/stage_runner.py` — Stage 1 (Splitting) runner, Stage 2-5 stub
- `iaa_pipeline/stage_schemas.py` — TypedDict + lightweight validator
- `iaa_pipeline/cache.py` — sha256 키 disk-backed LLM 캐시
- `iaa_pipeline/cli.py` — `python -m iaa_pipeline.cli stage1 ...`
- `iaa_pipeline/aligners.py` — record 정렬 (Stage 1 by criterion_id, Stage 2 fuzzy span, Stage 3-5 composite key, error_type by record_locator)
- `iaa_pipeline/metrics.py` — Cohen's κ (self-contained), set agreement, per-field F1. `compute_stage{1,2,4}_iaa()`, `compute_error_type_iaa()`. Stage 3/5 stub
- `iaa_pipeline/streamlit_app.py` — Stage 1 annotation UI + 실시간 IAA 대시보드
- `iaa_pipeline_spec/{README,03_json_schemas,04_stage_runners}.md` — 설계 문서
- `tests/test_iaa_metrics.py` — 18 smoke tests (script-mode + pytest 둘 다 지원)
- `scripts/run_iaa_ui.sh` — Streamlit launcher

---

## 9. Conventions / Gotchas

### Conventions
- **파일 prefix**: 01-08 sequential 실행 순서. `_archive_*` = 비활성 보관.
- **5개 검수 항목**: ① 분해 구조 / ② 메타 분류 / ③ Cross-layer / ④ 속성 / ⑤ 정규화. (REVIEW.md 상단 표 참조)
- **검수 issue codes**: R1-R4 (relation), C1-C3 (criterion). R/C 매핑은 REVIEW.md "Validator issue code → 5개 항목 매핑" 표.
- **xlsx 표준 양식**: 8 columns (criterion_id, step, source_query, 항목, description, reviewer_comment, suggested_action, date). action 표준 동사 7개 (삭제/수정/추가/보류/재추출/검토/정규화).
- **자동화 후보 승격 기준**: 같은 패턴이 **≥3 trial**에서 발견되면 validator R/C 규칙 후보.

### Gotchas
- **Neo4j 인스턴스 1개만 동시 실행 가능** (포트 7687 충돌). Desktop에서 다른 인스턴스 stop 후 protocol-kg-dev start.
- **REVIEW.md / REVIEW_notion.md sync**: 두 파일 같은 콘텐츠. 한쪽 수정 시 다른 쪽도 같은 변경 (Notion은 emoji + `<details>` 포맷).
- **pipeline/output/ 는 git untracked** (1.8MB, 30 files). Commit 의도적 제외 — reproducible 데이터.
- **`pipeline/.env`에 OPENAI_API_KEY**, **`./.env`에 Neo4j creds** — 두 위치 분리. 새 스크립트는 둘 다 load 필요 (예: `10_reextract_constraints.py` 참조).
- **Python 모듈명에 숫자 prefix**: `01_*.py` 같은 파일은 `python -m pipeline.01_*` import 불가 — `python pipeline/01_*.py` 직접 실행 필요.
- **review_session.py** (`pipeline/review_session.py`): 시뮬레이터. 사용자가 reviewer 시뮬레이터의 휴리스틱 false positive를 우려하여 **최종 권장 워크플로우에서 제외**. 검수자 직접 cypher → xlsx 양식.

### 사용자 선호 (대화에서 누적 학습)
- 한국어 응답 선호.
- 정직한 평가 + tradeoff 명시 좋아함 ("정직하게..." prefix 적절).
- 복잡한 제안보다 **단순한 실용 방안** 선호.
- 산출물 자동 생성보다 **사람이 직접 작업한 결과** 중심 (e.g., 시뮬레이터 vs cypher+xlsx 직접 작성).
- 큰 변경 전 항상 **사용자 확인** 받기.
- Push to remote는 **명시 요청 시만**.

---

## 10. 다음 세션을 위한 권장 첫 액션

1. **HANDOFF.md 읽기 (이 문서)** — 5분
2. **PIPELINE.md + REVIEW.md 읽기** — 10분
3. **Neo4j 연결 확인 + 현재 상태 점검**:
   ```bash
   python3 pipeline/06_validate_annotation.py 2>&1 | tail -15
   ```
   기대값: 30 trial / 40 issues / breakdown 위 §5와 일치
4. **사용자가 원하는 작업 확인** — 위 §7 후보 중 어느 것을 진행할지 물어보기.
5. **현재 git 상태 확인** — `git status` + `git log --oneline -5`. 마지막 commit `558a64b`.

---

## 11. 오늘 작업의 한 줄 요약

> **30 trial annotation 결함 599 → 40 (93% 감소)**, 검수 워크플로우 구축 (Neo4j + xlsx), 가이드라인 문서화 (REVIEW.md/REVIEW_notion.md), 8-stage 파이프라인 정리, 343MB cruft 정리, git commit (push 대기).

다음 세션은 위 §7 후보 중 사용자 우선순위 따라 진행.

---

## 12. 2026-05-27 세션 — IAA framework 1차 구현

### 12-1. 한 줄 요약
**IAA(inter-annotator agreement) 평가 인프라 구축** — aligners + metrics 모듈 + Stage 1 Streamlit annotation UI. 18 smoke tests 통과. Production pipeline은 변경 없음.

### 12-2. 배경 / 동기
- 사용자 목표: "IAA 평가 후 온톨로지 spec을 필요 시 수정". 평가 인프라 자체가 없어 실험 시작 불가능한 상태였음.
- `iaa_pipeline_spec/`은 완성도 높은 설계 문서 (Stage 1-5 전체 schema, IAA 필드 매핑, alignment 알고리즘)인 반면, `iaa_pipeline/` 코드는 Stage 1 LLM runner 1개만 있었음. **스펙과 코드의 갭이 컸음**.
- 사용자 결정: 폴더 재구조(A) / Streamlit UI(B) / metrics+aligners(C) 3안 중 **C 우선**. 이유 — 어차피 gold 없으면 UI도 의미가 제한적이고, κ 계산 자체가 빠진 게 가장 critical path였음. 이후 B(UI) → A(재구조) 순서로 합의.
- 이번 세션은 C + B 완료. A는 추후.

### 12-3. 산출물
| 영역 | 파일 | LOC | 메모 |
|---|---|---|---|
| Alignment | `iaa_pipeline/aligners.py` | ~220 | Stage 1/2/3/4/5 + error_type. Stage 2 fuzzy span (`SequenceMatcher.ratio() ≥ 0.85`) |
| Metrics | `iaa_pipeline/metrics.py` | ~280 | Cohen's κ self-contained (sklearn 무의존), set agreement, per-field F1. `compute_stage{1,2,4}_iaa()` + `compute_error_type_iaa()` |
| UI | `iaa_pipeline/streamlit_app.py` | ~360 | 4 tabs (Annotate / LLM Output / IAA / Upload). Annotator envelope 저장 + 실시간 κ 계산 |
| Tests | `tests/test_iaa_metrics.py` | ~250 | 18 smoke tests. `python tests/test_iaa_metrics.py` 또는 pytest |
| 설정 | `pyproject.toml` `[iaa]` extra | — | `streamlit>=1.30`, `typing_extensions>=4.0` |
| 실행 | `scripts/run_iaa_ui.sh` | — | Streamlit launcher (사전 설치 체크 포함) |
| Public API | `iaa_pipeline/__init__.py` v0.2.0 | — | 15개 symbol export |

### 12-4. 설계 결정 요약
- **Cohen's κ self-contained** — sklearn 의존성 회피. ~30 LOC. `None` 라벨 처리, single-class 시 `κ=None` 반환 (observed agreement은 그대로).
- **Stage 2 fuzzy alignment** — exact normalized 1차 → `SequenceMatcher.ratio() ≥ 0.85` 2차. 한 record는 한 번만 매칭. 임계값은 파라미터로 조정 가능.
- **`AlignmentResult`** — `matched / only_a / only_b` 3-way split + `presence_agreement` property. 모든 stage 재사용.
- **Stage 4 dual partition** — `relation_type`별(HAS_VALUE / HAS_TEMPORAL) + `extraction_source`별(regex / llm) 두 축으로 분리. spec §319 권고.
- **Error type multi-label** — `"R-MISSING, M-CATEGORY"` 콤마 문자열은 set 정규화 후 비교 (순서/공백 무관).
- **UI workspace 분리** — production `pipeline/output/`과 충돌 방지 위해 default `./iaa_workspace/{trial_id}/stage1/{input,llm_output,annotator_*}.json` 사용.

### 12-5. 의도적 미구현 (stub)
| Stage | 사유 |
|---|---|
| **Stage 3 LLM-assisted α/β/γ/δ** | 4-way envelope (LLM, A, B, consensus) 필요. spec §246-254. 호출 시 `NotImplementedError`로 spec 라인 참조 |
| **Stage 5 adjudication metrics** | adjudication 파일 포맷 미정의 (spec §355-365) |
| **`iaa_pipeline_spec/05_iaa_metrics.md`** | 스펙 자체가 없음. metrics.py가 사실상 spec 역할 — 추후 별도 문서로 분리 권장 |

### 12-6. 현재 상태 / 검증
- 18/18 smoke test 통과 (`python tests/test_iaa_metrics.py`)
- `from iaa_pipeline import *` 정상 동작 — 외부 의존성 추가 없음 (`difflib.SequenceMatcher`만 stdlib)
- Streamlit 미설치 환경에서 syntax 검증만 완료 — **실제 UI 동작 확인은 다음 세션 시 사용자가 `pip install -e ".[iaa]"` 후 실행 필요**
- gold data 없음 → 시범 IAA는 다음 세션

### 12-7. 다음 세션을 위한 IAA 후보 (우선순위순)

#### **I. 시범 IAA 실행** (low effort, high value)
1. `pip install -e ".[iaa]"`
2. 기존 30 trial 중 1개(예: NCT03425643) 선정
3. AACT raw text → `Stage1Input` JSON 변환 스크립트 작성 (간단)
4. Streamlit UI에서 직접 gold annotation 1회
5. `python -m iaa_pipeline.cli stage1 ...`로 LLM Stage 1 실행
6. UI **📊 IAA 탭**에서 LLM ↔ annotator κ 확인
7. κ 낮은 항목 → 온톨로지 spec 또는 prompt 수정 신호

#### **J. Stage 2 runner 구현** (medium effort)
- spec `04_stage_runners.md` §141-220 따라 `run_stage2_category_relation()` 작성
- Stage 1 runner 패턴 그대로 + `upstream_gold[1]` 검증 로직 추가
- Stage 2 IAA는 이미 `compute_stage2_iaa()` 완성됨

#### **K. AACT → Stage1Input 변환기** (low effort, prerequisite for I)
- `01_criteria_extraction.py`의 출력 (`input_trials.json`) 또는 AACT raw → `Stage1Input` 변환
- 새 스크립트 `scripts/aact_to_iaa_input.py` 또는 `iaa_pipeline/cli.py`에 서브커맨드 추가

#### **L. `iaa_pipeline_spec/05_iaa_metrics.md` 작성**
- `metrics.py`의 동작을 문서화 (Cohen's κ formula, set agreement, per-field F1)
- 논문 Method 섹션의 기반

#### **M. 폴더 재구조 (HANDOFF §7 외 추가, 옵션 A)**
- `src/graphrag_screening/` 통합, 숫자 prefix `.py` → `scripts/` 분리
- 큰 마이그레이션 (~30 파일 이동, ~15 import 수정). 사용자 선호: 코드가 stable해진 뒤 batch로

### 12-8. 사용 방법 (다음 사용자/세션 빠른 참조)

```bash
# 첫 설치 (1회)
pip install -e ".[iaa]"

# Streamlit UI 실행
bash scripts/run_iaa_ui.sh
# 또는: streamlit run iaa_pipeline/streamlit_app.py

# Stage 1 LLM 추출 (CLI)
python -m iaa_pipeline.cli stage1 <input.json> \
    --output-dir iaa_workspace/ --cache-dir cache/

# IAA 메트릭 단위 테스트
python tests/test_iaa_metrics.py    # 18 smoke tests
```

UI 첫 사용 워크플로우:
1. 사이드바에서 annotator ID 입력
2. **⬆️ Upload 탭** → Stage 1 input JSON (`{trial_id, criteria[]}`) 업로드 → workspace에 저장
3. 사이드바에서 trial 선택
4. **📝 Annotate 탭** → criterion별 `splitting_decision` 등 입력 → 💾 Save
5. (선택) `iaa_pipeline.cli stage1`로 LLM 출력 생성 → UI에 자동 표시
6. **📊 IAA 탭** → 2+ source 있으면 κ/agreement 자동 계산

### 12-9. 알려진 한계 / 주의사항
- **Streamlit 실제 실행 미검증** — UI는 syntax + signature + 31 tests로 검증되나 실제 브라우저 동작은 사용자가 확인 필요.
- **`iaa_workspace/` 경로 vs production `pipeline/output/`** — 분리됨. `scripts/convert_production_to_iaa.py`로 다리 완성 (LLM 호출 0건으로 30 trial 변환).
- **Cohen's κ undefined 처리** — annotator 모두 동일 single class면 κ=None 반환 (observed=1.0). UI에서는 "undefined" 표시.
- **Stage 2 fuzzy threshold 0.85** — 임의 default. 실제 데이터로 검증 필요.
- **A6 / A8 (audit_streamlit_v1.md)** — annotator identity는 honor system (text input). 다른 사람 ID 입력하면 그 사람 envelope 로드됨. 실제 auth는 production deployment 단계로 deferred. Streamlit session state도 ID 변경 시 자동 purge 안 됨.

### 12-9b. 2026-05-27 후반 — Blinding audit + fix
외부 review가 IAA bias 우려 제기 → self-audit 진행 (`iaa_pipeline_spec/audit_streamlit_v1.md`).

**발견**: CRITICAL 3 + MODERATE 3 + MINOR 2 = 8개 leak.
- A1: LLM 출력이 form default value로 leak (가장 심각)
- A2: 매 criterion마다 "🤖 LLM suggestion" expander
- A3: "🤖 LLM Output" 탭 Stage 1에서도 항상 보임
- A4: 사이드바에 다른 annotator envelope 파일명 노출
- A5: IAA 대시보드가 annotation 진행 중에도 접근 가능 (feedback loop)
- A6: annotator ID는 unverified text input
- A7: `n_subs` count도 LLM에서 leak (A1에 종속)
- A8: form widget state가 ID 변경에도 잔존

**Fix**:
1. **Mode 파라미터** (`from_scratch` / `llm_assisted`) — `STAGE_MODE = {1: from_scratch, 2: from_scratch, 3: llm_assisted, 4: llm_assisted, 5: llm_assisted}`. Stage 1/2는 blind, 3-5는 assisted.
2. **함수 시그니처 분리** — `render_criterion_form_blind(criterion, *, existing_record, ...)` 는 **llm_record 파라미터 자체를 받지 않음**. 시그니처 레벨 blinding guarantee.
3. **Phase 1 / Phase 2** — IAA 탭은 (a) phase_2_review AND (b) 현재 annotator가 commit 완료한 경우에만 표시.
4. **Commit 메커니즘** — 별도 "🔒 Commit (final)" 버튼. envelope에 `committed=true, committed_at=...` 기록. IAA dashboard는 committed envelope만 enumerate.
5. **Sidebar 정리** — 다른 annotator 파일 목록 제거. 본인 envelope 상태만 표시.
6. **Honor-system 경고문** — annotator ID 입력 옆에 경고. 풀 인증은 deferred.
7. **LLM envelope 메모리 로드 조건부** — `from_scratch` 모드에서는 `llm_output.json` 파일조차 안 읽음 (in-memory leak 봉쇄).

**검증**:
- 13개 신규 blinding test 추가 (`test_iaa_metrics.py`) → 18 + 13 = **31/31 통과**
- 핵심 test: `test_blind_render_signature_rejects_llm_record` (시그니처 레벨), `test_blind_seed_ignores_llm_record` (data flow), `test_tab_spec_*` (UI surface 차단)
- 8개 leak 모두 reproducibility test 추적 → CRITICAL/MODERATE 6건 closed, MINOR 2건 partial (A6/A8 — production auth 필요)

**산출물**: `iaa_pipeline_spec/audit_streamlit_v1.md` (findings + fix proposal + resolution notes), 새 `iaa_pipeline/streamlit_app.py`, 새 `tests/test_iaa_metrics.py` 블라인딩 섹션.

### 12-10. 2026-05-27 후반후반 — 호스팅 (옵션 F-mini, Streamlit Community Cloud)

**배경**: DYK 노트북에 매번 환경 설치 부담 + Stage 5까지 진행해야 함 → 인터넷 URL로 접근 가능한 호스팅 결정. 무료(Streamlit Community Cloud).

**옵션 비교 거쳐서 옵션 E(로컬) → F-mini(호스팅) 채택 이유**: DYK 환경 설정 마찰 제거가 더 큰 가치. annotation 중 server-side persistence 없는 stateless 디자인으로 cross-annotator leak 차단.

**산출물**:
| 파일 | 역할 |
|---|---|
| `streamlit_apps/stage1_app.py` | 호스팅 전용 Stage 1 앱 (~280 LOC) |
| `streamlit_apps/data/{NCT*}/stage1/{input,llm_output}.json` | 30 trial 데이터 번들 (~530KB, repo에 commit) |
| `.streamlit/secrets.toml.example` | shared password template (.streamlit/secrets.toml은 gitignore) |
| `requirements.txt` | SCC가 자동 인식하는 의존성 (streamlit, typing_extensions, python-dotenv) |
| `docs/hosting_guide.md` | 10단계 배포 + annotator 워크플로우 + IAA out-of-band 가이드 |

**호스팅 디자인**:
- **인증**: `st.secrets["SHARED_PASSWORD"]` shared password 1개. EHJ/DYK 모두 같은 패스워드로 로그인, ID는 사이드바 자체 입력.
- **데이터 흐름**: 30 trial은 repo에 commit (Stage 1 input + LLM 출력). annotator 작업은 `st.session_state`에만 (server 디스크 쓰기 0). Commit 시 `st.download_button` → 다운로드 → 공유 폴더 업로드 (out-of-band).
- **재개**: 다운로드한 draft JSON을 다음 세션에 업로드 → form 복원. annotator/trial mismatch는 거부 (identity guard).
- **Blinding**: Stage 1 = from_scratch hardcoded. LLM expander/tab 미렌더링. `render_criterion_form_blind` 시그니처 레벨 차단 그대로.
- **IAA 계산**: hosted UI 안에 dashboard 없음. 두 사람 다 submit 후 별도 스크립트로 계산 (`compute_stage1_iaa()` from `iaa_pipeline.metrics`).

**검증**: 10개 AppTest 시나리오 통과 (wrong password 차단, 30 trials, no LLM expander, A1 default='none', upload guard, no filesystem writes 등) + 기존 31 unit tests 무회귀.

**배포 액션 (다음 세션 또는 사용자가 직접)**:
1. `git add streamlit_apps/ requirements.txt .streamlit/secrets.toml.example docs/hosting_guide.md` + commit + push
2. https://share.streamlit.io → New app → repo 연결, main file `streamlit_apps/stage1_app.py`
3. Secrets에 `SHARED_PASSWORD = "..."` 설정
4. 배포 URL을 DYK에게 out-of-band로 공유

**한계 / 다음 단계**:
- 현재 Stage 1만. Stage 2-5는 각각 별도 URL로 추가 예정 (stage2_app.py, ...).
- IAA dashboard는 hosted UI 외부 — `scripts/compute_iaa.py` 추후 작성 권장.
- Cold-start 10-30초 (SCC 무료 tier 정상 동작).
- 기관 IRB 정책 확인 완료 (AACT public, annotation은 PHI 아님).

### 12-10b. IAA evaluation trial 선정 (8 of 30) — 2026-05-27 후반후반후반

**결정**: 30 trial 전수 dual-annotator gold 대신 stratified sample 8개로 IAA 측정.

**근거** (`iaa_pipeline_spec/iaa_8trials_selection.md`):
- Stratified purposive sampling (stage / line / biomarker / modality / phase 균형)
- 각 stage별 stress-test 매핑:
  - Stage 1: KEYNOTE-671 (macro_aggregate), KEYNOTE-001 (cohort_scope), eNRGy (basket)
  - Stage 3: ALEX/ASTRIS/GFH925/eNRGy로 variant_type 4종 (rearrangement, protein, KRAS G12C, NRG1 fusion) 커버
  - Stage 4: PACIFIC (patient_event anchor)
- Paper Methods에서 "Why N=8" 정당화 가능 (Cohen κ는 5-20 unit에서 보통 측정)

**선정 8개**:
```
NCT03425643  KEYNOTE-671        (pilot, macro_aggregate)
NCT02125461  PACIFIC            (patient_event anchor)
NCT03728556  GEMSTONE-301       (consolidation)
NCT02075840  ALEX               (ALK rearrangement)
NCT01295827  KEYNOTE-001        (multi-cohort)
NCT02474355  ASTRIS             (EGFR T790M)
NCT05756153  GFH925+cetuximab   (KRAS G12C)
NCT02912949  eNRGy              (NRG1 fusion, basket)
```

**나머지 22 trial 처리 정책** (paper claim 따라 결정):
- (A) Methodology validation only — 22개 사용 안 함
- (B) 30-trial gold corpus 공개 — methodology 검증 후 single-annotator로 22개 처리
- (C) RAG agent end-to-end — 22개는 기존 `pipeline/output/NCT*_annotation.json` 그대로 KG에 투입

대부분 임상 NLP paper는 (A) 또는 (C). 결정은 paper draft 작성 시점에.

**구현**: `iaa_pipeline_spec/iaa_8trials.txt`를 신뢰 소스로 삼아 hosted app dropdown이 자동 8개로 필터링됨 (`stage1_app.py:list_bundled_trials`). 22개 follow-up 작업 필요 시 (B) 또는 (C) 경로로:
- (B): `iaa_8trials.txt`를 rename/remove → app이 30개 전부 표시
- (C): 별도 phase-2 app 작성하여 full bundle 사용

**검증**: 3개 신규 테스트 추가 (`test_iaa_filter_*` in `tests/test_iaa_metrics.py`) → **34/34 통과**.

---

## 13. 2026-05-27 세션 마무리 — 종합 + 다음 세션용 인계

### 13-1. 오늘 push된 commit 6개 (origin/main 최신)
```
317065a align config.py + validators.py to v1.2.2 spec (close HANDOFF §7-H)
0df4736 remove XOR from CHILD_LOGIC enum (v1.2.2 spec alignment)
3ec1a5b restrict hosted app to 8 IAA-evaluation trials + clean secret template
595df04 relocate audit reference + remove unused labelstudio schema
e55b87d fix outdated IAA docs + CLI help references
b2bc9e7 add IAA framework + Streamlit annotation UI (local + hosted)
```
(`43cd72c Added Dev Container Folder`는 사용자가 GitHub UI에서 직접 추가)

### 13-2. 배포 현황
- **Repo**: `eune-jang/graphrag-clinical-screening` — public
- **Hosted app**: Streamlit Community Cloud, custom subdomain (사용자 노트 참조)
- **Secret**: `SHARED_PASSWORD` SCC dashboard에 설정됨. `.example` 파일은 placeholder만.
- **자동 재배포**: GitHub push 감지 → 1-3분 후 SCC가 새 컨테이너로 갱신
- **번들 데이터**: `streamlit_apps/data/{NCT*}/stage1/{input,llm_output}.json` × 30 trials
- **IAA dropdown 필터**: `iaa_pipeline_spec/iaa_8trials.txt` 8개만 노출

### 13-3. ⚠️ 보안 인시던트 + 처리
세션 중 `.streamlit/secrets.toml.example` 파일에 실제 패스워드 `nsclciaa2026`가 입력된 채로 commit 전 단계까지 감 → push 전 발견하여 placeholder로 복원. 사용자에게 SCC Secret 변경 안내. **git history에는 노출 안 됨** (commit 전 단계에서 발견).

다음 세션 시 확인 사항:
- [ ] SCC Secret 실제로 새 패스워드로 변경됐는지 (`nsclciaa2026` 폐기)
- [ ] DYK에게 새 패스워드 out-of-band 전달 완료 여부

### 13-4. 미해결 / 보류 결정사항

#### A. Paper claim 결정 (22 follow-up trials 처리 정책)
22개 비-IAA trial을 어떻게 처리할지는 paper draft 시점에 결정:
- **(A1)** Methodology validation only — 22개 사용 안 함 (가장 단순)
- **(A2)** 30-trial gold corpus 공개 — methodology 검증 후 single-annotator로 22개 처리
- **(A3)** RAG agent end-to-end — 22개는 `pipeline/output/NCT*_annotation.json` 그대로 KG 입력

대부분 임상 NLP paper는 (A1) 또는 (A3). 결정 시점은 IAA 결과 + paper 외곽 잡힌 후.

#### B. Annotator ID 입력 검증 (Option A from "DYK가 EHJ ID 잘못 입력" 토론)
- 현재: free text input, upload-resume 시점에만 identity guard
- 옵션 A: `ALLOWED_ANNOTATORS = {"EHJ", "DYK"}` (또는 SCC secret)로 사전 등록된 ID만 허용
- 5분 작업, 위험 90% 차단 (오타). 다음 세션에 적용 권장.

#### C. Commit/Download UX 개선 (4가지 옵션)
사용자가 "Commit 안 누르고 Draft만 쓰면 안 돼?" 질문 → 현재 design 유지로 답함. 그러나 UX 개선 여지 있음:
- (C1) 그대로 — 현재
- (C2) Commit 버튼 제거 — draft만 사용 (방법론 약화)
- (C3) Commit + Download 합쳐 한 번에
- (C4) Commit 전 confirmation modal

#### D. v1.2.2 spec 잔여 (deferral, 의도된 미해결)
- `variant_notation` 5 enum activation — Stage 3 IAA 작업 시
- `ontology_v1.2.2.json` schema 파일 생성 — Stage 3 downstream validation 필요 시
- 22 trial reprocess (NCT01884285, NCT03219268의 amplification/unknown 5건) — 22 follow-up corpus 정책 결정 시

### 13-5. Annotator guide 작성 TODO
오늘 Q&A에서 나온 annotator 가이드 항목들. `docs/annotator_guide.md` 신설 또는 hosting_guide.md에 추가 권장.

| 주제 | 핵심 내용 |
|---|---|
| **child_logic null 처리** | spec 규칙: inclusion+AND default omit, exclusion+OR default omit. override 케이스만 명시. `(unset)` 선택 = JSON에서 필드 자체 omit |
| **cohort_scope 사용법** | 대부분 비워둠 (모든 cohort 적용). cohort-specific 명시 ("Part F only" 등)일 때만 선택. KEYNOTE-001(15 cohorts)이 가장 주의 필요. ASTRIS/GFH925는 cohort 없음 → multiselect 미표시 |
| **Save draft vs Commit final** | Save = 브라우저 세션만, 새로고침 시 손실. Commit = 잠금 + 다운로드 파일에 `committed=true`. 둘 다 다운로드 권장 |
| **다운로드 필수** | Streamlit Cloud는 서버 영구 저장 없음. 본인 다운로드 파일 = 본인 작업의 유일한 기록 |
| **재개 워크플로우** | 다음 세션: URL 접속 → password → trial 선택 → "Upload a draft you downloaded earlier" → 이전 다운로드 파일 → form 복원 |
| **공유 폴더 업로드** | `📥 Download committed envelope` → `/shared/iaa/submissions/{ID}/NCT*_stage1.json` |
| **honor system** | annotator ID 정확히 입력, 본인 commit 전 다른 annotator 결과 보지 않기 |

### 13-6. 다음 세션 우선순위 후보

#### P0 — DYK annotation 시작 전 확인 (최단 작업)
- [ ] SCC Secret 새 패스워드 적용 확인
- [ ] DYK에게 URL + 새 패스워드 + annotator_guide 전달
- [ ] (옵션 B 적용) Annotator ID 사전 등록 검증 추가 — 5분

#### P1 — Annotation 결과 받기 전 가능한 작업
- [ ] **`scripts/compute_iaa.py`** 작성 — 둘 다 commit 후 κ + 표 생성. 1-2시간.
- [ ] **`docs/annotator_guide.md`** 작성 — 위 §13-5 표 + 예시. 30분.
- [ ] **`iaa_pipeline_spec/05_iaa_metrics.md`** — paper Methods용 metric 공식 문서화. 2-3시간.

#### P2 — Stage 1 결과 받은 후 (다음 주)
- [ ] 8 trial 모두 commit envelope 수신 후 IAA 계산 실행
- [ ] κ 결과 분석 → onto spec / prompt 수정 판단
  - κ ≥ 0.6 → Stage 2 진행
  - κ < 0.6 → 불일치 패턴 분석 → spec 수정 → 재annotation

#### P3 — Stage 1 만족스러우면
- [ ] Stage 2 LLM runner 구현 — `run_stage2_category_relation()`
- [ ] Stage 2 UI form (`streamlit_apps/stage2_app.py`)
- [ ] AACT → Stage1Input 변환 (이미 있음 — 22 trial 추가 시 재활용)

### 13-7. 현재 상태 한 줄 요약

> **Stage 1 IAA 실험 준비 완료.** Hosted app 배포됨, 8 trial 필터링, v1.2.2 spec 정합화, 34/34 tests 통과, 6 commits push 완료. 다음 세션 우선 작업: SCC Secret 변경 확인 + DYK에게 URL/password 공유 + annotator guide 작성 + compute_iaa.py 작성.

### 13-8. 빠른 참조 (다음 세션 첫 명령)
```bash
cd /Users/jang-eunhye/graphrag-clinical-screening

# 환경 확인
git log --oneline -5    # 마지막 commit이 317065a여야 함
git status              # clean이어야 함
python3 tests/test_iaa_metrics.py 2>&1 | tail -3  # 34/34 passed

# 로컬 IAA UI (필요 시)
streamlit run streamlit_apps/stage1_app.py
# 또는 production app은 SCC URL로 직접 (사용자 노트 참조)
```

### 12-10. 한 줄 요약
> **IAA 인프라 0 → 1**. spec 따라 aligners + metrics + Stage 1 UI 완성, 18 tests 통과. 다음 세션은 시범 실행 (후보 I) 또는 Stage 2 runner (후보 J)부터.
