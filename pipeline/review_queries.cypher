// =====================================================================
// Clinical Trial Annotation Review — Cypher Query Cheat Sheet
//
// Use with: Neo4j Browser (http://localhost:7474)
// Prerequisite: run `python pipeline/07_neo4j_ingest.py` first.
//
// Graph shape (Layer 1 + minimal cross-layer targets):
//   (:Trial {nct_id, trial_acronym, disease_domain})
//     ─[:HAS_INCLUSION|HAS_EXCLUSION]→
//   (:Criterion {criterion_id, type, semantic_category, text,
//                parent_role, child_logic, cohort_scope,
//                _passed, _issues})
//     ─[:IS_PART_OF]→ (:Criterion)
//     ─[:REQUIRES_*|EXCLUDES_*|HAS_*|INCLUDES_*
//        {target_text_span, _passed, _issues, ...}]→
//   (:ConceptRef {preferred_name, subtype})
//
// _passed (bool) and _issues (list<string>) are populated by
// `06_validate_annotation.py` — use them to drive review.
// =====================================================================


// ─────────────────────────────────────────────────────────────────────
// QUICK START — what to look at first
// ─────────────────────────────────────────────────────────────────────

// 0.1  Total criteria/relations per trial, with failure counts
MATCH (t:Trial)
OPTIONAL MATCH (t)--(c:Criterion)
WITH t, count(DISTINCT c) AS n_crit,
     sum(CASE WHEN c._passed = false THEN 1 ELSE 0 END) AS crit_fail
OPTIONAL MATCH (t)--(:Criterion)-[r]->(:ConceptRef)
RETURN t.nct_id AS trial,
       n_crit, crit_fail,
       count(DISTINCT r) AS n_rel,
       sum(CASE WHEN r._passed = false THEN 1 ELSE 0 END) AS rel_fail
ORDER BY rel_fail DESC, crit_fail DESC;


// 0.2  Single-trial deep view (replace $nct)
:param nct => 'NCT03425643';

MATCH (t:Trial {nct_id: $nct})
OPTIONAL MATCH (t)--(c:Criterion)
WITH t, count(DISTINCT c) AS n_crit
OPTIONAL MATCH (t)--(:Criterion)-[r]->(cr:ConceptRef)
RETURN t.nct_id AS trial, n_crit,
       count(DISTINCT r) AS rels,
       collect(DISTINCT type(r))[..15] AS rel_types;


// 0.3  All failing relations in a trial (use this to drive review)
//      — drives Step 3a (validator-flagged review) in REVIEW.md.
MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE r._passed = false
RETURN c.criterion_id AS cid,
       type(r) AS rel_type,
       cr.subtype AS subtype,
       cr.preferred_name AS target,
       r.target_text_span AS span,
       r._issues AS issues
ORDER BY cid, rel_type;


// ─────────────────────────────────────────────────────────────────────
// WALK-THROUGH (clean trial — judgment-only review)
// Use when Q0.1 shows rel_fail = crit_fail = 0 for the target trial.
// Drives Step 3b in REVIEW.md.
// ─────────────────────────────────────────────────────────────────────

// 0.4  Trial overview — every criterion with meta + first 80 chars
MATCH (t:Trial {nct_id: $nct})--(c:Criterion)
RETURN c.criterion_id AS cid,
       c.type AS type,
       c.semantic_category AS category,
       coalesce(c.parent_role, '') AS parent_role,
       coalesce(c.child_logic, '') AS child_logic,
       coalesce(c.parent_criterion_id, '') AS parent_id,
       left(c.text, 80) AS text
ORDER BY cid;

// 0.5  All relations of one criterion (replace criterion_id for deep-dive)
MATCH (c:Criterion {criterion_id: 'NCT03425643_I4'})-[r]->(cr:ConceptRef)
RETURN type(r) AS rel_type,
       cr.subtype AS subtype,
       cr.preferred_name AS target,
       r.target_text_span AS span,
       properties(r) AS props;

// 0.6  Relation type distribution within the trial — spot anomalies
MATCH (:Criterion {trial_id: $nct})-[r]->(:ConceptRef)
RETURN type(r) AS rel_type, count(*) AS n
ORDER BY n DESC;


// ─────────────────────────────────────────────────────────────────────
// ① Criterion 분해 구조 (split + parent_role + child_logic + duplicate)
//    Covers REVIEW.md item ①
// ─────────────────────────────────────────────────────────────────────

// 1.1  parent_role distribution per trial — overview
MATCH (c:Criterion {trial_id: $nct})
RETURN coalesce(c.parent_role, '(none)') AS parent_role, count(*) AS n
ORDER BY n DESC;

// 1.2  Children whose text isn't covered by parent text (strict tier;
//      validator R2 uses 3-tier check — strict / normalized / token recall)
MATCH (child:Criterion {trial_id: $nct})-[:IS_PART_OF]->(parent:Criterion)
WHERE NOT (parent.text CONTAINS child.text)
RETURN child.criterion_id AS child_id, child.text AS child_text,
       parent.criterion_id AS parent_id, parent.text AS parent_text;

// 1.3  Type mismatch parent/child (inclusion child → exclusion parent 등)
MATCH (child:Criterion {trial_id: $nct})-[:IS_PART_OF]->(parent:Criterion)
WHERE child.type <> parent.type
RETURN child.criterion_id, child.type, parent.criterion_id, parent.type;

// 1.4  IS_PART_OF children exist but parent has no parent_role (메타 누락)
MATCH (child:Criterion {trial_id: $nct})-[:IS_PART_OF]->(parent:Criterion)
WHERE parent.parent_role IS NULL
RETURN DISTINCT parent.criterion_id, parent.text, count(child) AS n_children;

// 1.5  parent_role set without IS_PART_OF children — orphan parent (C1)
//      legitimate for nested_exception_parent; flagged for split types
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role IN ['composite_split', 'macro_aggregate']
  AND NOT EXISTS { (:Criterion)-[:IS_PART_OF]->(parent) }
RETURN parent.criterion_id, parent.parent_role, parent.text;

// 1.6  composite_split parent with <2 children — split lacks decomposition
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role = 'composite_split'
OPTIONAL MATCH (child:Criterion)-[:IS_PART_OF]->(parent)
WITH parent, count(child) AS n
WHERE n < 2
RETURN parent.criterion_id, n, parent.text;

// 1.7  nested_exception_parent without INCLUDES_EXCEPTION on self/children (C2)
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role = 'nested_exception_parent'
WITH parent,
     EXISTS { (parent)-[:INCLUDES_EXCEPTION]->() } AS self_has,
     EXISTS { (:Criterion)-[:IS_PART_OF]->(parent)
              -[:INCLUDES_EXCEPTION]->() } AS children_have
WHERE NOT (self_has OR children_have)
RETURN parent.criterion_id, parent.text;

// 1.8  Duplicate criterion_id detection (C3) — should be 0 after orchestrator fix
MATCH (c:Criterion {trial_id: $nct})
WITH c.criterion_id AS cid, count(c) AS n
WHERE n > 1
RETURN cid, n;


// ─────────────────────────────────────────────────────────────────────
// ② Criterion 메타 분류 (semantic_category + type + cohort_scope)
//    Covers REVIEW.md item ②
// ─────────────────────────────────────────────────────────────────────

// 2.1  semantic_category distribution (per trial)
MATCH (c:Criterion {trial_id: $nct})
RETURN c.semantic_category AS category, count(*) AS n
ORDER BY n DESC;

// 2.2  semantic_category distribution (across all 30 trials) — sanity check
MATCH (c:Criterion)
RETURN c.semantic_category AS category, count(*) AS n,
       count(DISTINCT c.trial_id) AS trials
ORDER BY n DESC;

// 2.3  type distribution (inclusion vs exclusion balance)
MATCH (c:Criterion {trial_id: $nct})
RETURN c.type AS type, count(*) AS n;

// 2.4  cohort_scope coverage (multi-cohort trial — 기대값과 비교)
//      KEYNOTE-001 (NCT01295827) 처럼 multi-cohort trial에서 부분적용 criterion 검토
MATCH (c:Criterion {trial_id: $nct})
WHERE c.cohort_scope IS NOT NULL AND size(c.cohort_scope) > 0
RETURN c.criterion_id, c.cohort_scope, left(c.text, 80) AS text;


// ─────────────────────────────────────────────────────────────────────
// ③ Cross-layer relation 식별 (relation_type + target_subtype + 누락)
//    Covers REVIEW.md item ③
// ─────────────────────────────────────────────────────────────────────

// 3.1  Relation type distribution within the trial
MATCH (:Criterion)-[r]->(:ConceptRef)
WHERE startNode(r).trial_id = $nct
RETURN type(r) AS rel_type, count(*) AS n
ORDER BY n DESC;

// 3.2  relation_type ↔ target_subtype mismatch (validator R1)
MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE 'subtype_mismatch' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, type(r), cr.subtype, cr.preferred_name;

// 3.3  Relations with span_not_in_text issue (validator R2 — fuzzy 통과 실패)
MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE 'span_not_in_text' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, type(r), cr.preferred_name,
       r.target_text_span AS span, c.text AS criterion_text;

// 3.4  Leaf criteria with no outgoing cross-layer relations (extraction 누락 의심)
//      validator 사각지대 — "있는 게 잘못됐는지"만 봄. 누락은 여기로 surface.
MATCH (c:Criterion {trial_id: $nct})
WHERE NOT (c)-[:IS_PART_OF]->(:Criterion)
  AND c.parent_role IS NULL
  AND NOT (c)-[]->(:ConceptRef)
RETURN c.criterion_id, c.type, c.text;


// ─────────────────────────────────────────────────────────────────────
// ④ Relation 속성 완전성
//    Covers REVIEW.md item ④
// ─────────────────────────────────────────────────────────────────────

// 4.1  HAS_VALUE with missing operator/value (validator R4)
MATCH (c:Criterion {trial_id: $nct})-[r:HAS_VALUE]->(cr:ConceptRef)
WHERE 'value_props_missing' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, cr.preferred_name, r.target_text_span;

// 4.2  HAS_TEMPORAL with missing required keys (validator R3)
MATCH (c:Criterion {trial_id: $nct})-[r:HAS_TEMPORAL]->(cr:ConceptRef)
WHERE 'temporal_props_missing' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, cr.preferred_name, r.target_text_span,
       r.operator, r.value, r.unit, r.anchor;

// 4.3  REQUIRES_BIOMARKER without biomarker_details
MATCH (c:Criterion {trial_id: $nct})-[r:REQUIRES_BIOMARKER]->(cr:ConceptRef)
WHERE r.biomarker_details IS NULL
RETURN c.criterion_id, cr.preferred_name;

// 4.4  HAS_TEMPORAL anchor_type distribution (spec 3 enum 중 누락 확인)
MATCH (:Criterion {trial_id: $nct})-[r:HAS_TEMPORAL]->(:ConceptRef)
RETURN coalesce(r.anchor_type, '(null)') AS anchor_type, count(*) AS n
ORDER BY n DESC;

// 4.5  alternative_constraint usage — 적용된 relation list (의미 검증)
MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE r.alternative_constraint IS NOT NULL
RETURN c.criterion_id, type(r), cr.preferred_name,
       r.value AS primary_value, r.unit AS primary_unit,
       r.alternative_constraint AS alt;

// 4.6  INCLUDES_EXCEPTION의 exception_qualifier/type 분포 (carve-out 의미 검증)
MATCH (c:Criterion {trial_id: $nct})-[r:INCLUDES_EXCEPTION]->(cr:ConceptRef)
RETURN c.criterion_id, cr.preferred_name,
       r.exception_type AS exc_type, r.exception_qualifier AS exc_qual;


// ─────────────────────────────────────────────────────────────────────
// ⑤ Concept 정규화 (preferred_name 일관성 + hub 식별)
//    Covers REVIEW.md item ⑤ — Layer 3 dedup 준비
//    (자동 검출 없음 — 전수 사람 검토 항목)
// ─────────────────────────────────────────────────────────────────────

// 5.1  ConceptRef hubs (preferred_name appearing in ≥3 trials)
//      Layer 3 정규화 후보 — 같은 개념이 30 trial 전반에 반복 등장
MATCH (c:Criterion)-[r]->(cr:ConceptRef)
WITH cr, count(DISTINCT c.trial_id) AS trials, count(r) AS mentions
WHERE trials >= 3
RETURN cr.subtype, cr.preferred_name, trials, mentions
ORDER BY trials DESC, mentions DESC
LIMIT 25;

// 5.2  Hub-centric subgraph: 한 ConceptRef와 거기 연결된 모든 criterion
//      preferred_name 일관성 검증 — 같은 hub 안의 criterion들이 의미적으로 일치하나?
MATCH (cr:ConceptRef {preferred_name: 'Non-small cell lung cancer'})<-[r]-(c:Criterion)
RETURN cr, r, c LIMIT 50;

// 5.3  같은 subtype + 비슷한 단어 포함하는 ConceptRef pair 찾기 (정규화 후보)
//      예: "ECOG performance status" vs "Eastern Cooperative Oncology Group performance status"
MATCH (cr1:ConceptRef), (cr2:ConceptRef)
WHERE cr1.subtype = cr2.subtype
  AND cr1.preferred_name < cr2.preferred_name
  AND (cr1.preferred_name CONTAINS 'ECOG' OR cr1.preferred_name CONTAINS 'Eastern Cooperative')
  AND (cr2.preferred_name CONTAINS 'ECOG' OR cr2.preferred_name CONTAINS 'Eastern Cooperative')
RETURN cr1.preferred_name, cr2.preferred_name, cr1.subtype;

// 5.4  Concept별 trial 분포 — 1 trial에만 등장 vs 광범위 등장 비교
//      광범위 등장 hub: 표준 개념 (정규화 우선순위 고려)
//      1 trial 등장: trial-specific 또는 정규화 누락 후보
MATCH (c:Criterion)-[r]->(cr:ConceptRef)
WITH cr, count(DISTINCT c.trial_id) AS trial_count
WITH cr.subtype AS subtype, trial_count, count(*) AS n_concepts
RETURN subtype, trial_count, n_concepts
ORDER BY subtype, trial_count;


// ─────────────────────────────────────────────────────────────────────
// MAINTENANCE & TROUBLESHOOTING
// ─────────────────────────────────────────────────────────────────────

// M.1  Detect duplicate criterion_id (should be 0 post-fix)
MATCH (c:Criterion {trial_id: $nct})
WITH c.criterion_id AS cid, count(c) AS n
WHERE n > 1
RETURN cid, n;

// M.2  Issue prevalence across all trials
MATCH ()-[r]->(:ConceptRef)
WHERE r._issues IS NOT NULL AND size(r._issues) > 0
UNWIND r._issues AS issue
WITH split(issue,':')[0] AS kind, startNode(r).trial_id AS trial
RETURN kind, count(*) AS occurrences, count(DISTINCT trial) AS trials_affected
ORDER BY occurrences DESC;

// M.3  Total graph scale
MATCH (n)
RETURN labels(n)[0] AS label, count(*) AS n
ORDER BY n DESC;

// M.4  Wipe everything (use only when starting fresh)
// MATCH (n) DETACH DELETE n;
