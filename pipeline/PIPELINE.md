# Pipeline 개요

LLM-assisted clinical trial annotation 파이프라인 + Neo4j 기반 검수 워크플로우.

## 스테이지 그래프

```
   raw ClinicalTrials.gov criteria
              │
              ▼
   ┌──────────────────────────────┐
   │ 01_criteria_extraction       │  Stage A: text 파싱
   └──────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ 02_llm_annotation            │  orchestrator.process_trial 실행
   │   └─ orchestrator.py         │    Prompt 1 → 2 → 3 → regex+4 → 5
   │       ├─ llm_client.py       │
   │       ├─ regex_extractor.py  │
   │       ├─ transforms.py       │
   │       └─ validators.py       │
   └──────────────────────────────┘
              │
              ▼  output/NCT*_annotation.json
   ┌──────────────────────────────┐
   │ 03_recover_has_value         │  Cleanup ①: regex post-hoc (no LLM)
   │ 04_correct_relation_type     │  Cleanup ②: subtype→relation 자동정정
   │ 05_reextract_constraints     │  Cleanup ③: selective LLM (Prompt 4만)
   └──────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ 06_validate_annotation       │  _validation 메타데이터 부착
   └──────────────────────────────┘
              │
              ▼  output/NCT*_annotation.json (with _validation)
   ┌──────────────────────────────┐
   │ 07_neo4j_ingest              │  Neo4j 로드 (Trial/Criterion/ConceptRef)
   └──────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ 08_review_queries            │  21개 Cypher 쿼리 일괄 실행
   │ review_queries.cypher        │  Neo4j Browser용 cheat sheet
   │ REVIEW.md                    │  검수자 가이드
   └──────────────────────────────┘

   (별도 보관 (_archive_ prefix, 파이프라인 순서 제외):
     - _archive_labelstudio_export.py        — 과거 LS export 경로
     - _archive_dedup_nested_exception.py    — orchestrator source-fix 됨
     - _archive_rename_observation.py        — orchestrator source-fix 됨
    활성 검수 경로는 위 07_neo4j_ingest + 08_review_queries.)
```

## 스크립트별 역할

### Core (annotation pipeline)

| 스크립트 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `01_criteria_extraction.py` | AACT raw text → criterion 리스트 추출 | AACT XML | `output/input_trials.json` |
| `02_llm_annotation.py` | orchestrator wrapper, 30 trial 배치 실행 | input_trials.json | `output/NCT*_annotation.json` |
| `orchestrator.py` | 5-stage 파이프라인 (Prompt 1→5 + regex) | criterion text | criterion record + relations |
| `llm_client.py` | OpenAI/Anthropic 호출 + 재시도 + 검증 | prompt_key + params | parsed JSON |
| `regex_extractor.py` | HAS_VALUE / HAS_TEMPORAL regex (자연어/Unicode 정규화 포함) | criterion text | RegexResult |
| `transforms.py` | criterion/relation record 조립 | stage 출력 | schema-compliant dict |
| `validators.py` | 각 prompt 출력의 enum/구조 검증 | prompt output | error list |
| `config.py` | 모델 preset, schema enum, gap-handling 규칙 | — | — |

### Cleanup (one-shot data fixes, idempotent)

| 스크립트 | 처리하는 결함 |
|---|---|
| `03_recover_has_value.py` | 빈 HAS_VALUE/HAS_TEMPORAL에 개선 regex 후처리 적용 (LLM 호출 없음) |
| `04_correct_relation_type.py` | (relation_type, subtype) 부정합 자동정정 (예: REQUIRES_STATUS→Stage → REQUIRES_CONDITION→Stage) |
| `05_reextract_constraints.py` | regex로도 못 잡힌 케이스에 Prompt 4 선택적 재호출 (LLM 사용) |

### Validation & Review

| 스크립트 | 역할 |
|---|---|
| `06_validate_annotation.py` | 6개 검출 패턴으로 `_validation: {passed, issues}` 부착 |
| `07_neo4j_ingest.py` | annotation JSON → Neo4j (Layer 1 + lightweight Layer 3 ref) |
| `08_review_queries.py` | 21개 Cypher 쿼리 일괄 실행 + cross-trial 비교 |
| `review_queries.cypher` | Neo4j Browser에 붙여넣을 수 있는 쿼리집 (검수자용) |

### Archived (파이프라인에서 제외, 백업 보관)

| 스크립트 | 사유 |
|---|---|
| `_archive_labelstudio_export.py` | (구) annotation JSON → Label Studio task 포맷. 검수 도구를 Neo4j+JSON으로 이동 |
| `_archive_dedup_nested_exception.py` | orchestrator.py:357 source-fix 후 새 데이터에 재발 가능성 없음. 외부 구 데이터 import용 safety net |
| `_archive_rename_observation.py` | orchestrator.py:320,330 source-fix (LabTest→Observation) 후 동일 |

## 데이터 흐름 요약

```
AACT XML
   │  pipeline 01
   ▼
input_trials.json   (trial_id, criteria[].text)
   │  pipeline 02  (LLM annotation)
   ▼
NCT*_annotation.json  (criteria[].relations[] 포함)
   │  cleanup 03/04/05  (one-shot fixes)
   ▼
NCT*_annotation.json  (cleaned)
   │  pipeline 06
   ▼
NCT*_annotation.json  (with _validation)
   │  pipeline 07
   ▼
Neo4j graph
   │  pipeline 08 / review_queries.cypher
   ▼
검수 결과 (Cypher 출력)
```

## 30-trial 적용 결과 (현 시점)

| 단계 | 누적 issue |
|---|---|
| Original LLM annotation | 599 |
| orchestrator nested_exception bug fix | 384 |
| orchestrator regex fallback fix + regex 강화 | 304 |
| validator span fuzzy match | 188 |
| relation_type 자동정정 | 127 |
| LLM 재추출 (Prompt 4) | 40 |

남은 40건은:
- **Prompt 5 미생성** 5건 (`nested_exception_no_carveout`)
- **진짜 hallucination** 3건 (`span_not_in_text`)
- **추출 결함 unicode mangling** 3건 (`span_not_in_text`)
- **Biomarker negation** 3건 (`subtype_mismatch` Pattern D — relation type + property 변경 필요)
- **Prompt 4도 못 추출** 26건 (HAS_VALUE/HAS_TEMPORAL이 numeric 없는 target에 부착됨)

## 의존성

- Python 3.11+
- `neo4j>=5.0`, `openai`, `python-dotenv`, `pandas`, `pyyaml`
- Neo4j Desktop 2.x (또는 호환 Neo4j 5.1+ / 2025.x / 2026.x)
- 환경변수 (`./.env`):
  ```
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=<set>
  NEO4J_DATABASE=neo4j
  ```
- LLM API key (`pipeline/.env`):
  ```
  OPENAI_API_KEY=<set>
  ```
