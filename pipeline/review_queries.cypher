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
// ① IS_PART_OF (split structure)
// ─────────────────────────────────────────────────────────────────────

// 1.1  Children whose text isn't covered by parent text (after fuzzy match)
//      — validator R2 uses a 3-tier check (strict / normalized / token recall)
MATCH (child:Criterion {trial_id: $nct})-[:IS_PART_OF]->(parent:Criterion)
WHERE NOT (parent.text CONTAINS child.text)   // strict tier here
RETURN child.criterion_id AS child_id, child.text AS child_text,
       parent.criterion_id AS parent_id, parent.text AS parent_text;

// 1.2  Type mismatch parent/child (inclusion child → exclusion parent etc.)
MATCH (child:Criterion {trial_id: $nct})-[:IS_PART_OF]->(parent:Criterion)
WHERE child.type <> parent.type
RETURN child.criterion_id, child.type, parent.criterion_id, parent.type;

// 1.3  IS_PART_OF children exist but parent has no parent_role (meta missing)
MATCH (child:Criterion {trial_id: $nct})-[:IS_PART_OF]->(parent:Criterion)
WHERE parent.parent_role IS NULL
RETURN DISTINCT parent.criterion_id, parent.text, count(child) AS n_children;

// 1.4  parent_role set without IS_PART_OF children — orphan parent
//      (legitimate for nested_exception_parent; flagged for others)
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role IN ['composite_split', 'macro_aggregate']
  AND NOT EXISTS { (:Criterion)-[:IS_PART_OF]->(parent) }
RETURN parent.criterion_id, parent.parent_role, parent.text;


// ─────────────────────────────────────────────────────────────────────
// ② semantic_category
// ─────────────────────────────────────────────────────────────────────

// 2.1  Distribution (per trial)
MATCH (c:Criterion {trial_id: $nct})
RETURN c.semantic_category AS category, count(*) AS n
ORDER BY n DESC;

// 2.2  Distribution (across all 30 trials)
MATCH (c:Criterion)
RETURN c.semantic_category AS category, count(*) AS n,
       count(DISTINCT c.trial_id) AS trials
ORDER BY n DESC;


// ─────────────────────────────────────────────────────────────────────
// ③ parent_role consistency
// ─────────────────────────────────────────────────────────────────────

// 3.1  parent_role distribution per trial
MATCH (c:Criterion {trial_id: $nct})
RETURN coalesce(c.parent_role, '(none)') AS parent_role, count(*) AS n
ORDER BY n DESC;

// 3.2  composite_split parent with <2 children — split lacks decomposition
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role = 'composite_split'
OPTIONAL MATCH (child:Criterion)-[:IS_PART_OF]->(parent)
WITH parent, count(child) AS n
WHERE n < 2
RETURN parent.criterion_id, n, parent.text;

// 3.3  nested_exception_parent without INCLUDES_EXCEPTION on self/children
MATCH (parent:Criterion {trial_id: $nct})
WHERE parent.parent_role = 'nested_exception_parent'
WITH parent,
     EXISTS { (parent)-[:INCLUDES_EXCEPTION]->() } AS self_has,
     EXISTS { (:Criterion)-[:IS_PART_OF]->(parent)
              -[:INCLUDES_EXCEPTION]->() } AS children_have
WHERE NOT (self_has OR children_have)
RETURN parent.criterion_id, parent.text;


// ─────────────────────────────────────────────────────────────────────
// ④ Cross-layer relations
// ─────────────────────────────────────────────────────────────────────

// 4.1  Relation type distribution
MATCH (:Criterion)-[r]->(:ConceptRef)
WHERE startNode(r).trial_id = $nct
RETURN type(r) AS rel_type, count(*) AS n
ORDER BY n DESC;

// 4.2  Relations with span_not_in_text issue (after fuzzy match)
MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE 'span_not_in_text' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, type(r), cr.preferred_name,
       r.target_text_span AS span, c.text AS criterion_text;

// 4.3  Leaf criteria with no outgoing cross-layer relations (extraction miss)
MATCH (c:Criterion {trial_id: $nct})
WHERE NOT (c)-[:IS_PART_OF]->(:Criterion)
  AND c.parent_role IS NULL
  AND NOT (c)-[]->(:ConceptRef)
RETURN c.criterion_id, c.type, c.text;

// 4.4  relation_type ↔ target_subtype mismatch (validator R1)
MATCH (c:Criterion {trial_id: $nct})-[r]->(cr:ConceptRef)
WHERE 'subtype_mismatch' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, type(r), cr.subtype, cr.preferred_name;


// ─────────────────────────────────────────────────────────────────────
// ⑤ Property completeness
// ─────────────────────────────────────────────────────────────────────

// 5.1  HAS_VALUE with missing operator/value
MATCH (c:Criterion {trial_id: $nct})-[r:HAS_VALUE]->(cr:ConceptRef)
WHERE 'value_props_missing' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, cr.preferred_name, r.target_text_span;

// 5.2  HAS_TEMPORAL with missing required keys
MATCH (c:Criterion {trial_id: $nct})-[r:HAS_TEMPORAL]->(cr:ConceptRef)
WHERE 'temporal_props_missing' IN [x IN r._issues | split(x,':')[0]]
RETURN c.criterion_id, cr.preferred_name, r.target_text_span,
       r.operator, r.value, r.unit, r.anchor;

// 5.3  REQUIRES_BIOMARKER without biomarker_details
MATCH (c:Criterion {trial_id: $nct})-[r:REQUIRES_BIOMARKER]->(cr:ConceptRef)
WHERE r.biomarker_details IS NULL
RETURN c.criterion_id, cr.preferred_name;

// 5.4  HAS_TEMPORAL anchor_type distribution
MATCH (:Criterion {trial_id: $nct})-[r:HAS_TEMPORAL]->(:ConceptRef)
RETURN coalesce(r.anchor_type, '(null)') AS anchor_type, count(*) AS n
ORDER BY n DESC;


// ─────────────────────────────────────────────────────────────────────
// HUB ANALYSIS — Layer 3 normalization preview
// ─────────────────────────────────────────────────────────────────────

// 6.1  ConceptRef hubs (preferred_name appearing in ≥3 trials)
MATCH (c:Criterion)-[r]->(cr:ConceptRef)
WITH cr, count(DISTINCT c.trial_id) AS trials, count(r) AS mentions
WHERE trials >= 3
RETURN cr.subtype, cr.preferred_name, trials, mentions
ORDER BY trials DESC, mentions DESC
LIMIT 25;

// 6.2  Hub-centric subgraph: a single ConceptRef and all referring criteria
MATCH (cr:ConceptRef {preferred_name: 'Non-small cell lung cancer'})<-[r]-(c:Criterion)
RETURN cr, r, c LIMIT 50;


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
