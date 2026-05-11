# LLM Annotation 검수 워크플로우

LLM이 생성한 30 trial annotation에 대해 사람이 검수할 때 따르는 절차.

## 검수 5개 항목 (사용자 정의)

| # | 항목 | 자동 검출 가능? |
|---|---|---|
| ① | IS_PART_OF로 적절한 span 추출 | 일부 (구조 OK, 의미는 사람) |
| ② | semantic_category 정확성 | 일부 (enum + 의심 페어만) |
| ③ | parent_role 적용 정합성 | 대부분 |
| ④ | Layer 1-3 cross-layer relation 추출 | 일부 (구조 OK) |
| ⑤ | criterion/concept 노드 속성 완전성 | 대부분 |

자동 검출 가능한 부분은 `06_validate_annotation.py`의 6개 패턴(`R1-R4`, `C1-C3`)이 잡아냅니다. 나머지는 사람이 Neo4j 쿼리로 surface된 케이스를 직접 보고 판단.

## 표준 검수 사이클

### Step 1. Annotation 준비

```bash
# (이미 LLM annotation이 완료된 상태에서)
python pipeline/06_validate_annotation.py               # _validation 부착
python pipeline/07_neo4j_ingest.py                      # Neo4j 적재
```

### Step 2. 트리아지 — 어떤 trial부터 볼 것인가

`review_queries.cypher`의 **Quick Start 섹션**을 Neo4j Browser에서 실행:

```cypher
// 0.1  Total per trial, with failure counts
MATCH (t:Trial)
OPTIONAL MATCH (t)--(c:Criterion)
WITH t, count(DISTINCT c) AS n_crit,
     sum(CASE WHEN c._passed = false THEN 1 ELSE 0 END) AS crit_fail
OPTIONAL MATCH (t)--(:Criterion)-[r]->(:ConceptRef)
RETURN t.nct_id, n_crit, crit_fail,
       count(DISTINCT r) AS n_rel,
       sum(CASE WHEN r._passed = false THEN 1 ELSE 0 END) AS rel_fail
ORDER BY rel_fail DESC;
```

**우선 검수 대상**: `rel_fail`이 큰 trial부터.

### Step 3. Trial 단위 deep-dive

Trial 하나를 잡고 (예: `NCT03425643`):

```cypher
// 0.3  All failing relations in this trial
:param nct => 'NCT03425643';

MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE r._passed = false
RETURN c.criterion_id, type(r), cr.subtype, cr.preferred_name,
       r.target_text_span AS span, r._issues AS issues
ORDER BY c.criterion_id;
```

검수자는 각 행에 대해:
- `issues` 컬럼을 보고 어떤 결함인지 식별
- `span` vs criterion text를 비교해서 의미 판단
- 필요시 원본 JSON (`pipeline/output/{nct}_annotation.json`) 열어서 전체 맥락 확인

### Step 4. 항목별 detail 쿼리

5개 검수 항목별 쿼리는 `review_queries.cypher` 섹션 ①~⑤. 예시:

**③ parent_role 정합성 — nested_exception_parent가 carve-out을 안 가지는가:**
```cypher
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role = 'nested_exception_parent'
WITH parent,
     EXISTS { (parent)-[:INCLUDES_EXCEPTION]->() } AS self_has,
     EXISTS { (:Criterion)-[:IS_PART_OF]->(parent)
              -[:INCLUDES_EXCEPTION]->() } AS children_have
WHERE NOT (self_has OR children_have)
RETURN parent.criterion_id, parent.text;
```

### Step 5. 결과 기록

검수자가 발견한 새 패턴(자동 검출 못한 것)은 같은 태그로 여러 번 발견되면 `06_validate_annotation.py`의 새 detection rule 후보. 

예시 기록:
```
KEYNOTE-671 E2 — INCLUDES_EXCEPTION qualifier 누락  [TAG: inc_excp_qualifier_missing]
SEQUOIA E5 — INCLUDES_EXCEPTION qualifier 누락       [TAG: inc_excp_qualifier_missing]
...
```
≥3 trial occurrence → validator R/C rule 후보로 승격.

## Validator issue codes 해석 가이드

`_validation.issues` 필드에 나타나는 코드와 의미:

| Code | 위치 | 의미 | 처리 |
|---|---|---|---|
| `subtype_mismatch:X->Y` | Relation | relation_type X에 허용되지 않는 target_subtype Y | `04_correct_relation_type.py`로 자동 정정 가능 |
| `span_not_in_text` | Relation | target_text_span이 criterion text에 (fuzzy 포함) 없음 | hallucination 의심 — span 직접 검증 |
| `temporal_props_missing:k1,k2,...` | Relation | HAS_TEMPORAL 필수 키 누락 | `05_reextract_constraints.py`로 LLM 재추출 |
| `value_props_missing:k1,k2,...` | Relation | HAS_VALUE 필수 키 누락 | 동일 |
| `orphan_parent_role:X` | Criterion | parent_role 설정됐는데 IS_PART_OF 자녀 없음 (composite_split/macro_aggregate만) | orchestrator 출력 검토 — 원래는 자녀가 있어야 함 |
| `nested_exception_no_carveout` | Criterion | nested_exception_parent인데 INCLUDES_EXCEPTION이 self/children 어디에도 없음 | Prompt 5 미생성 — 수동 추가 또는 재추출 |
| `duplicate_entry` | Criterion | 같은 criterion_id가 한 trial 내에 여러 번 등장 | `_archive_dedup_nested_exception.py`로 정리 (현재 데이터엔 0건) |

## 검수 데이터의 두 가지 진입점

| 도구 | 강점 | 약점 |
|---|---|---|
| **Neo4j Browser** + `.cypher` | 그래프 traversal, hub 분석, cross-trial 집계 | Property 직접 수정 불가 |
| **원본 JSON 파일** (`pipeline/output/NCT*_annotation.json`) | Property 직접 수정/주석, git diff로 변경 추적 | 집계/조인 어려움 |

검수자는 양쪽을 함께 씁니다 — Neo4j에서 surface된 의심 케이스를 JSON에서 수정.

## "사람만 잡을 수 있는" 항목 (자동화 불가)

자동 검출이 어려운 검수 관점:
- **Span의 의미적 적절성**: "non-infectious pneumonitis"를 span으로 잡았는데 spec상 더 좁은 표현이 정답일 수 있음
- **preferred_name 정규화**: "ECOG performance status"와 "Eastern Cooperative Oncology Group performance status"가 같은 개념인지
- **drug class vs specific drug**: "platinum-containing regimen" → drug class? 특정 drug?
- **Implicit context**: "in past 5 years"의 5년 기준이 randomization인지 informed consent인지 (anchor 추론)
- **Negation scope**: "no significant history of..." — what's the scope of "no"?

이런 케이스는 검수자 메모로 남기고, 패턴이 반복되면 spec/guideline에 반영.

## 새 trial 추가 시 동일 사이클 재현

```bash
# 1. 새 trial annotation 생성
python pipeline/02_llm_annotation.py --trial NCT_NEW

# 2. cleanup (필요시 — 새 annotation은 03/05만 주로 유용. 04는 Prompt 2 분류 오류 발생 시)
python pipeline/03_recover_has_value.py --trial NCT_NEW      # regex post-hoc
python pipeline/04_correct_relation_type.py --trial NCT_NEW  # subtype↔relation 정정
python pipeline/05_reextract_constraints.py --trial NCT_NEW  # LLM Prompt 4 (비용 발생)

# 3. validate + ingest
python pipeline/06_validate_annotation.py --trial NCT_NEW
python pipeline/07_neo4j_ingest.py --trial NCT_NEW --reset

# 4. 검수 — review_queries.cypher 사용 with :param nct => 'NCT_NEW'
```

## 관련 문서

- [`PIPELINE.md`](PIPELINE.md) — 스크립트 인벤토리 + 데이터 흐름
- [`review_queries.cypher`](review_queries.cypher) — Neo4j Browser용 쿼리 모음
- [`schema/ontology_full_specification_unified_v1_2_2_ko.md`](schema/ontology_full_specification_unified_v1_2_2_ko.md) — 4-layer ontology 전체 스펙
- [`schema/annotation_guideline_v0_2_stage1 (1).md`](schema/annotation_guideline_v0_2_stage1%20(1).md) — annotation guideline (현재 stage 1)
