"""
Neo4j ingest for review workflow prototype.

Scope (Layer 1 + minimal cross-layer targets):
  - (:Trial {nct_id, trial_acronym, disease_domain, cohorts})
  - (:Criterion {criterion_id, type, semantic_category, text,
                 parent_role, child_logic, cohort_scope})
  - (:ConceptRef {preferred_name, subtype})  ← lightweight target node,
        no preferred_name normalization, no Layer 3 dedup
  - (Trial)-[:HAS_INCLUSION|HAS_EXCLUSION]->(Criterion)
  - (Criterion)-[:IS_PART_OF]->(Criterion)   ← flattened from parent_criterion_id
  - (Criterion)-[<relation_type>]->(ConceptRef)
        with properties: target_text_span, biomarker_details, **props from
        relation.properties spread onto the edge for Cypher convenience

Usage:
  python -m pipeline.07_neo4j_ingest                          # ingest all
  python -m pipeline.07_neo4j_ingest --trial NCT03425643      # one trial
  python -m pipeline.07_neo4j_ingest --reset --trial NCT03425643
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neo4j_ingest")

# ── Env / paths ────────────────────────────────────────────────────────
PIPELINE_DIR = Path(__file__).parent
PROJECT_ROOT = PIPELINE_DIR.parent
OUTPUT_DIR = PIPELINE_DIR / "output"

# Load both env files: root for Neo4j, pipeline for LLM (harmless here)
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PIPELINE_DIR / ".env", override=False)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


# ── Connection ─────────────────────────────────────────────────────────
def get_driver() -> Driver:
    if not NEO4J_PASSWORD:
        logger.error(
            "NEO4J_PASSWORD is empty. Set it in %s/.env", PROJECT_ROOT
        )
        sys.exit(1)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    return driver


# ── Schema bootstrap (constraints + indexes) ──────────────────────────
SCHEMA_QUERIES = [
    "CREATE CONSTRAINT trial_nct_id IF NOT EXISTS "
    "FOR (t:Trial) REQUIRE t.nct_id IS UNIQUE",
    "CREATE CONSTRAINT criterion_id IF NOT EXISTS "
    "FOR (c:Criterion) REQUIRE c.criterion_id IS UNIQUE",
    "CREATE CONSTRAINT conceptref_key IF NOT EXISTS "
    "FOR (cr:ConceptRef) REQUIRE (cr.preferred_name, cr.subtype) IS UNIQUE",
    "CREATE INDEX criterion_trial IF NOT EXISTS "
    "FOR (c:Criterion) ON (c.trial_id)",
]


def bootstrap_schema(driver: Driver):
    with driver.session(database=NEO4J_DATABASE) as session:
        for q in SCHEMA_QUERIES:
            session.run(q)
    logger.info("Schema bootstrap done (%d constraints/indexes)", len(SCHEMA_QUERIES))


# ── Reset (per-trial cleanup) ─────────────────────────────────────────
def reset_trial(driver: Driver, nct_id: str):
    """Delete a single trial and its descendant criteria + dangling refs."""
    with driver.session(database=NEO4J_DATABASE) as session:
        # Delete criteria + their relations (Trial-anchored sub-graph)
        result = session.run(
            """
            MATCH (t:Trial {nct_id: $nct_id})
            OPTIONAL MATCH (t)--(c:Criterion)
            DETACH DELETE c
            WITH t
            DETACH DELETE t
            """,
            nct_id=nct_id,
        )
        result.consume()
        # Orphaned ConceptRef cleanup
        session.run(
            "MATCH (cr:ConceptRef) WHERE NOT (cr)--() DELETE cr"
        ).consume()
    logger.info("Reset complete for %s", nct_id)


# ── Ingest one annotation file ────────────────────────────────────────
def ingest_annotation(driver: Driver, ann: dict) -> dict:
    """Ingest a single trial's annotation JSON. Returns counters."""
    trial_id = ann["trial_id"]
    criteria = ann.get("criteria", []) or []

    counts = Counter()

    with driver.session(database=NEO4J_DATABASE) as session:
        # 1. Trial node
        session.run(
            """
            MERGE (t:Trial {nct_id: $nct_id})
            SET t.trial_acronym  = $trial_acronym,
                t.disease_domain = $disease_domain,
                t.cohorts        = $cohorts
            """,
            nct_id=trial_id,
            trial_acronym=ann.get("trial_acronym"),
            disease_domain=ann.get("disease_domain"),
            cohorts=json.dumps(ann.get("cohorts")) if ann.get("cohorts") else None,
        )
        counts["trial"] += 1

        # 2. Criterion nodes + Trial→Criterion structural edges
        for crit in criteria:
            cid = crit["criterion_id"]
            ctype = crit.get("type")
            rel_label = "HAS_INCLUSION" if ctype == "inclusion" else "HAS_EXCLUSION"

            cv = crit.get("_validation") or {}
            session.run(
                f"""
                MATCH (t:Trial {{nct_id: $nct_id}})
                MERGE (c:Criterion {{criterion_id: $cid}})
                SET c.trial_id          = $nct_id,
                    c.type              = $type,
                    c.semantic_category = $semantic_category,
                    c.text              = $text,
                    c.parent_role       = $parent_role,
                    c.child_logic       = $child_logic,
                    c.cohort_scope      = $cohort_scope,
                    c._passed           = $v_passed,
                    c._issues           = $v_issues
                MERGE (t)-[:{rel_label}]->(c)
                """,
                nct_id=trial_id,
                cid=cid,
                type=ctype,
                semantic_category=crit.get("semantic_category"),
                text=crit.get("text"),
                parent_role=crit.get("parent_role"),
                child_logic=crit.get("child_logic"),
                cohort_scope=crit.get("cohort_scope"),
                v_passed=cv.get("passed", True),
                v_issues=cv.get("issues", []),
            )
            counts["criterion"] += 1
            if cv.get("issues"):
                counts["criterion_with_issues"] += 1

        # 3. IS_PART_OF edges (flattened from parent_criterion_id)
        for crit in criteria:
            parent_id = crit.get("parent_criterion_id")
            if not parent_id:
                continue
            session.run(
                """
                MATCH (child:Criterion {criterion_id: $cid})
                MATCH (parent:Criterion {criterion_id: $pid})
                MERGE (child)-[:IS_PART_OF]->(parent)
                """,
                cid=crit["criterion_id"],
                pid=parent_id,
            )
            counts["is_part_of"] += 1

        # 4. Cross-layer relations
        for crit in criteria:
            cid = crit["criterion_id"]
            for rel in crit.get("relations") or []:
                rtype = rel.get("relation_type")
                subtype = rel.get("target_subtype")
                pname = rel.get("target_preferred_name")
                span = rel.get("target_text_span")
                if not (rtype and subtype and pname):
                    counts["relation_skipped_incomplete"] += 1
                    continue

                # Spread relation.properties onto the edge for Cypher convenience.
                # biomarker_details kept as separate nested JSON (mixed-shape).
                props = rel.get("properties") or {}
                edge_props = {
                    "target_text_span": span,
                    **{k: _scalarize(v) for k, v in props.items()},
                }
                if rel.get("biomarker_details"):
                    edge_props["biomarker_details"] = json.dumps(
                        rel["biomarker_details"], ensure_ascii=False
                    )
                # _validation from 03_validate (flatten to scalar edge props)
                rv = rel.get("_validation") or {}
                edge_props["_passed"] = rv.get("passed", True)
                edge_props["_issues"] = rv.get("issues", [])
                if rv.get("issues"):
                    counts["relation_with_issues"] += 1

                # Relation type cannot be parameterized in plain Cypher.
                # Sanitize against injection: only A-Z and underscore allowed.
                if not _is_safe_rel_type(rtype):
                    counts["relation_skipped_unsafe"] += 1
                    logger.warning("Skipped unsafe relation_type: %r", rtype)
                    continue

                session.run(
                    f"""
                    MATCH (c:Criterion {{criterion_id: $cid}})
                    MERGE (cr:ConceptRef {{preferred_name: $pname, subtype: $subtype}})
                    CREATE (c)-[r:{rtype}]->(cr)
                    SET r += $props
                    """,
                    cid=cid,
                    pname=pname,
                    subtype=subtype,
                    props=edge_props,
                )
                counts[f"rel_{rtype}"] += 1

    return dict(counts)


def _scalarize(v):
    """Neo4j edge property values must be scalar or list-of-scalar.
    Serialize dicts/objects to JSON for storage; lists pass through if scalar."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v):
        return v
    return json.dumps(v, ensure_ascii=False)


_SAFE_REL = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ_")


def _is_safe_rel_type(s: str) -> bool:
    return bool(s) and all(ch in _SAFE_REL for ch in s)


# ── Main ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Ingest LLM annotation JSON(s) into Neo4j for review."
    )
    parser.add_argument(
        "--trial",
        type=str,
        default=None,
        help="Specific NCT id to ingest (default: all *_annotation.json in output)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory containing *_annotation.json (default: pipeline/output)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the trial sub-graph before ingest",
    )
    args = parser.parse_args()

    json_files = sorted(args.input.glob("*_annotation.json"))
    json_files = [f for f in json_files if "_backup" not in f.name]
    if args.trial:
        json_files = [f for f in json_files if args.trial in f.name]
    if not json_files:
        logger.error("No annotation JSONs matched in %s", args.input)
        sys.exit(1)

    driver = get_driver()
    try:
        bootstrap_schema(driver)
        for jf in json_files:
            with open(jf, encoding="utf-8") as f:
                ann = json.load(f)
            nct = ann["trial_id"]
            if args.reset:
                reset_trial(driver, nct)
            counts = ingest_annotation(driver, ann)
            logger.info(
                "  ✓ %s  trial:%d criteria:%d is_part_of:%d relations:%d  "
                "(failed crit:%d / rel:%d)",
                nct,
                counts.get("trial", 0),
                counts.get("criterion", 0),
                counts.get("is_part_of", 0),
                sum(v for k, v in counts.items() if k.startswith("rel_")),
                counts.get("criterion_with_issues", 0),
                counts.get("relation_with_issues", 0),
            )
            # Log per-relation-type breakdown for transparency
            rel_breakdown = {
                k.replace("rel_", ""): v
                for k, v in sorted(counts.items())
                if k.startswith("rel_")
            }
            logger.info("     by type: %s", rel_breakdown)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
