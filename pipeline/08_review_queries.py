"""
Review query prototype — 5 검수 항목별 Cypher 쿼리.

검수 항목:
  ① IS_PART_OF span/구조 정합성
  ② semantic_category 정확성
  ③ parent_role 적용 정합성
  ④ Cross-layer relation 추출 완전성
  ⑤ Criterion/Concept 속성 완전성

각 쿼리는 (description, query, params, kind) 튜플로 정의됨.
kind:
  - "distribution": 분포 통계 (참고용, 결함 아님)
  - "warn":         의심 신호 (검수자 판단 필요)
  - "fail":         명백한 schema 위반 (자동 검출 강력 후보)

Usage:
  python pipeline/08_review_queries.py --trial NCT03425643
  python pipeline/08_review_queries.py --trial NCT03425643 --category 3
  python pipeline/08_review_queries.py --trial NCT03425643 --export-cypher
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

# ── Env ────────────────────────────────────────────────────────────────
PIPELINE_DIR = Path(__file__).parent
PROJECT_ROOT = PIPELINE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PW = os.getenv("NEO4J_PASSWORD", "")
DB = os.getenv("NEO4J_DATABASE", "neo4j")


# ── Query library ──────────────────────────────────────────────────────
# Each entry: (id, description, cypher, kind)
# All queries take $nct_id parameter.

QUERIES = {
    # ─────────────── ① IS_PART_OF 구조 ─────────────────────────────────
    "1.1": (
        "IS_PART_OF 자녀 text가 부모 text의 substring이 아님 (span carve-out 실패 의심)",
        """
        MATCH (child:Criterion {trial_id: $nct_id})-[:IS_PART_OF]->(parent:Criterion)
        WHERE NOT (parent.text CONTAINS child.text)
        RETURN child.criterion_id AS child_id,
               child.text         AS child_text,
               parent.criterion_id AS parent_id,
               parent.text        AS parent_text
        ORDER BY child_id
        """,
        "warn",
    ),
    "1.2": (
        "자녀-부모 type 불일치 (inclusion 자녀가 exclusion 부모를 가리키는 등)",
        """
        MATCH (child:Criterion {trial_id: $nct_id})-[:IS_PART_OF]->(parent:Criterion)
        WHERE child.type <> parent.type
        RETURN child.criterion_id AS child_id, child.type AS child_type,
               parent.criterion_id AS parent_id, parent.type AS parent_type
        """,
        "fail",
    ),
    "1.3": (
        "IS_PART_OF 자녀가 있는데 부모의 parent_role이 null (메타 누락)",
        """
        MATCH (child:Criterion {trial_id: $nct_id})-[:IS_PART_OF]->(parent:Criterion)
        WHERE parent.parent_role IS NULL
        RETURN DISTINCT parent.criterion_id AS parent_id,
               parent.text                  AS parent_text,
               count(child)                 AS child_count
        ORDER BY parent_id
        """,
        "fail",
    ),
    "1.4": (
        "parent_role이 설정됐는데 IS_PART_OF 자녀가 없음 (orphan parent)",
        """
        MATCH (parent:Criterion {trial_id: $nct_id})
        WHERE parent.parent_role IS NOT NULL
          AND NOT EXISTS { (:Criterion)-[:IS_PART_OF]->(parent) }
        RETURN parent.criterion_id AS parent_id,
               parent.parent_role  AS parent_role,
               parent.text         AS parent_text
        """,
        "fail",
    ),

    # ─────────────── ② semantic_category ───────────────────────────────
    "2.1": (
        "semantic_category 분포",
        """
        MATCH (c:Criterion {trial_id: $nct_id})
        RETURN c.semantic_category AS category, count(*) AS cnt
        ORDER BY cnt DESC
        """,
        "distribution",
    ),
    "2.2": (
        "비정형 (semantic_category × relation_type) 조합",
        """
        MATCH (c:Criterion {trial_id: $nct_id})-[r]->(:ConceptRef)
        WHERE
          (c.semantic_category = 'comorbidity'        AND type(r) IN ['EXCLUDES_TREATMENT','EXCLUDES_COMEDICATION']) OR
          (c.semantic_category = 'treatment_history'  AND type(r) = 'EXCLUDES_CONDITION') OR
          (c.semantic_category = 'comedication'       AND type(r) IN ['REQUIRES_CONDITION','EXCLUDES_CONDITION'])
        RETURN c.criterion_id    AS cid,
               c.semantic_category AS sc,
               type(r)           AS rel_type,
               c.text            AS text
        """,
        "warn",
    ),
    "2.3": (
        "semantic_category가 null인 criterion (필수 필드 누락)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})
        WHERE c.semantic_category IS NULL
        RETURN c.criterion_id AS cid, c.text AS text
        """,
        "fail",
    ),

    # ─────────────── ③ parent_role 정합성 ─────────────────────────────
    "3.1": (
        "parent_role 분포 (스펙상 3종: composite_split / macro_aggregate / nested_exception_parent)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})
        RETURN coalesce(c.parent_role, '(none)') AS parent_role, count(*) AS cnt
        ORDER BY cnt DESC
        """,
        "distribution",
    ),
    "3.2": (
        "composite_split 부모인데 자녀가 <2개 (composite 분해의 의미 없음)",
        """
        MATCH (parent:Criterion {trial_id: $nct_id})
        WHERE parent.parent_role = 'composite_split'
        OPTIONAL MATCH (child:Criterion)-[:IS_PART_OF]->(parent)
        WITH parent, count(child) AS n
        WHERE n < 2
        RETURN parent.criterion_id AS parent_id,
               n                   AS child_count,
               parent.text         AS parent_text
        """,
        "fail",
    ),
    "3.3": (
        "composite_split 부모인데 child_logic이 null (결합 규칙 미명시)",
        """
        MATCH (parent:Criterion {trial_id: $nct_id})
        WHERE parent.parent_role = 'composite_split'
          AND parent.child_logic IS NULL
        RETURN parent.criterion_id AS parent_id,
               parent.type         AS type,
               parent.text         AS parent_text
        """,
        "warn",
    ),
    "3.4": (
        "nested_exception_parent인데 INCLUDES_EXCEPTION relation을 가진 자녀가 없음",
        """
        MATCH (parent:Criterion {trial_id: $nct_id})
        WHERE parent.parent_role = 'nested_exception_parent'
        OPTIONAL MATCH (child:Criterion)-[:IS_PART_OF]->(parent)
        OPTIONAL MATCH (child)-[ie:INCLUDES_EXCEPTION]->(:ConceptRef)
        WITH parent, count(DISTINCT ie) AS exc_count
        WHERE exc_count = 0
        RETURN parent.criterion_id AS parent_id, parent.text AS parent_text
        """,
        "fail",
    ),

    # ─────────────── ④ Cross-layer relation 추출 ──────────────────────
    "4.1": (
        "relation_type 분포 (spec 11종 모두 등장하는지)",
        """
        MATCH (:Criterion {trial_id: $nct_id})-[r]->(:ConceptRef)
        RETURN type(r) AS rel_type, count(*) AS cnt
        ORDER BY cnt DESC
        """,
        "distribution",
    ),
    "4.2": (
        "target_text_span이 criterion.text 안에 없음 (LLM paraphrase 의심)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})-[r]->(cr:ConceptRef)
        WHERE r.target_text_span IS NOT NULL
          AND NOT (c.text CONTAINS r.target_text_span)
        RETURN c.criterion_id AS cid,
               type(r)        AS rel_type,
               cr.preferred_name AS target,
               r.target_text_span AS span,
               c.text         AS text
        LIMIT 30
        """,
        "warn",
    ),
    "4.3": (
        "Relation이 0개인 criterion (추출 누락, leaf 기준)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})
        WHERE NOT (c)-[:IS_PART_OF]->(:Criterion)   // children only (leaves)
          AND c.parent_role IS NULL                 // not a parent stub
          AND NOT (c)-[]->(:ConceptRef)
        RETURN c.criterion_id AS cid,
               c.type         AS type,
               c.text         AS text
        """,
        "fail",
    ),
    "4.4": (
        "relation_type ↔ target_subtype 부정합 (예: REQUIRES_BIOMARKER → 비-Biomarker)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})-[r]->(cr:ConceptRef)
        WITH c, r, cr,
             CASE type(r)
               WHEN 'REQUIRES_BIOMARKER'   THEN ['Biomarker']
               WHEN 'REQUIRES_CONDITION'   THEN ['Condition','Stage']
               WHEN 'EXCLUDES_CONDITION'   THEN ['Condition','Stage']
               WHEN 'REQUIRES_TREATMENT'   THEN ['Drug']
               WHEN 'EXCLUDES_TREATMENT'   THEN ['Drug']
               WHEN 'EXCLUDES_COMEDICATION' THEN ['Drug']
               WHEN 'REQUIRES_PROCEDURE'   THEN ['Procedure']
               WHEN 'EXCLUDES_PROCEDURE'   THEN ['Procedure']
               WHEN 'REQUIRES_STATUS'      THEN ['Observation','Condition']
               WHEN 'EXCLUDES_STATUS'      THEN ['Observation','Condition']
               WHEN 'INCLUDES_EXCEPTION'   THEN ['Condition','Drug','Procedure','Observation','Stage']
               WHEN 'HAS_VALUE'            THEN ['Observation','Condition']
               WHEN 'HAS_TEMPORAL'         THEN ['Drug','Condition','Procedure','Observation']
               ELSE []
             END AS allowed
        WHERE size(allowed) > 0 AND NOT cr.subtype IN allowed
        RETURN c.criterion_id    AS cid,
               type(r)           AS rel_type,
               cr.subtype        AS subtype,
               cr.preferred_name AS target
        """,
        "fail",
    ),
    "4.5": (
        "INCLUDES_EXCEPTION 0건 여부 (KEYNOTE-671 E20 같은 carve-out 누락 시그널)",
        """
        MATCH (:Criterion {trial_id: $nct_id})
        OPTIONAL MATCH (:Criterion {trial_id: $nct_id})-[ie:INCLUDES_EXCEPTION]->(:ConceptRef)
        RETURN count(DISTINCT ie) AS includes_exception_count
        """,
        "warn",
    ),

    # ─────────────── ⑤ 속성 완전성 ─────────────────────────────────
    "5.1": (
        "REQUIRES_BIOMARKER인데 biomarker_details 없음",
        """
        MATCH (c:Criterion {trial_id: $nct_id})-[r:REQUIRES_BIOMARKER]->(cr:ConceptRef)
        WHERE r.biomarker_details IS NULL
        RETURN c.criterion_id AS cid, cr.preferred_name AS target
        """,
        "fail",
    ),
    "5.2": (
        "HAS_TEMPORAL 필수 properties 누락 (operator/value/unit/anchor)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})-[r:HAS_TEMPORAL]->(cr:ConceptRef)
        WITH c, r, cr,
             [k IN ['operator','value','unit','anchor'] WHERE r[k] IS NULL] AS missing
        WHERE size(missing) > 0
        RETURN c.criterion_id AS cid,
               cr.preferred_name AS target,
               missing          AS missing_keys
        """,
        "fail",
    ),
    "5.3": (
        "HAS_VALUE 필수 properties 누락 (operator/value)",
        """
        MATCH (c:Criterion {trial_id: $nct_id})-[r:HAS_VALUE]->(cr:ConceptRef)
        WITH c, r, cr,
             [k IN ['operator','value'] WHERE r[k] IS NULL] AS missing
        WHERE size(missing) > 0
        RETURN c.criterion_id AS cid,
               cr.preferred_name AS target,
               missing          AS missing_keys
        """,
        "fail",
    ),
    "5.4": (
        "target_preferred_name이 비어있거나 generic placeholder (정규화 실패 신호)",
        """
        MATCH (:Criterion {trial_id: $nct_id})-[r]->(cr:ConceptRef)
        WHERE cr.preferred_name IS NULL OR cr.preferred_name = ''
           OR cr.preferred_name IN ['Unknown','N/A','unspecified','TBD']
        RETURN DISTINCT cr.preferred_name AS pname, cr.subtype AS subtype
        """,
        "fail",
    ),
    "5.5": (
        "HAS_TEMPORAL anchor_type이 null 또는 'unspecified' 비율",
        """
        MATCH (:Criterion {trial_id: $nct_id})-[r:HAS_TEMPORAL]->(:ConceptRef)
        RETURN coalesce(r.anchor_type, '(null)') AS anchor_type, count(*) AS cnt
        ORDER BY cnt DESC
        """,
        "distribution",
    ),
}


# ── Runner ────────────────────────────────────────────────────────────
KIND_ICON = {"distribution": "📊", "warn": "⚠️ ", "fail": "❌"}


def run(driver, query: str, params: dict) -> list[dict]:
    with driver.session(database=DB) as s:
        return [dict(r) for r in s.run(query, **params)]


def fmt_row(row: dict, max_chars: int = 80) -> str:
    parts = []
    for k, v in row.items():
        if isinstance(v, str) and len(v) > max_chars:
            v = v[: max_chars - 1] + "…"
        parts.append(f"{k}={v!r}")
    return "  " + ", ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Run review Cypher queries.")
    parser.add_argument("--trial", required=True, help="NCT id")
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Only run queries starting with this prefix (e.g. '3' for ③)",
    )
    parser.add_argument("--limit", type=int, default=10, help="Max rows shown per query")
    parser.add_argument(
        "--export-cypher",
        action="store_true",
        help="Print just the Cypher queries (for pasting into Neo4j Browser)",
    )
    args = parser.parse_args()

    if args.export_cypher:
        for qid, (desc, cypher, kind) in QUERIES.items():
            if args.category and not qid.startswith(args.category + "."):
                continue
            print(f"// {qid}  [{kind}]  {desc}")
            print(f":param nct_id => '{args.trial}';")
            print(cypher.strip())
            print()
        return

    if not PW:
        print("NEO4J_PASSWORD is empty. Set it in .env first.", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(URI, auth=(USER, PW))
    driver.verify_connectivity()

    summary = []
    try:
        for qid, (desc, cypher, kind) in QUERIES.items():
            if args.category and not qid.startswith(args.category + "."):
                continue
            rows = run(driver, cypher, {"nct_id": args.trial})
            n = len(rows)
            icon = KIND_ICON[kind]
            print(f"\n{icon} {qid} [{kind}]  {desc}")
            print(f"    rows: {n}")
            for row in rows[: args.limit]:
                print(fmt_row(row))
            if n > args.limit:
                print(f"    … {n - args.limit} more")
            summary.append((qid, kind, n))

        # Bottom-line summary
        print("\n" + "═" * 70)
        print(f"SUMMARY ({args.trial})")
        print("═" * 70)
        for qid, kind, n in summary:
            flag = "  " if kind == "distribution" or n == 0 else " ←"
            print(f"  {KIND_ICON[kind]} {qid}  rows={n}{flag}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
