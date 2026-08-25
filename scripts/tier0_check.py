#!/usr/bin/env python3
"""Tier 0 hygiene check on committed Stage 1 envelopes (handover §A-2).

Flags labels that violate a STRUCTURAL constraint of spec v1.2.2 — the kind of
error where the spec itself settles that the label is wrong, no judgement
needed. Ported from the Neo4j review queries (`pipeline/08_review_queries.py`
3.2 / 3.3) to direct JSON checks, because Stage 1 envelopes never reach Neo4j.

    python scripts/tier0_check.py                        # round 2, print only
    python scripts/tier0_check.py --round 2 --out results/adjudication

Scope is deliberately narrow (handover §0.2-④): only the two rules that Stage 1
envelope fields can actually decide. Queries 2.2/2.3 need `semantic_category`,
which is Stage 2 data and absent here (§9-4) — do NOT infer it.

This is hygiene, NOT gating: measured violations are ~5 across 32 envelopes
(§9-9), so it does not shrink the adjudication queue. Its job is to let the
adjudicator enter an item already knowing "this label is spec-wrong", which
keeps that case from being scored as a judgement disagreement in D-3.

**It never decides what the correct label is** — that stays with the
adjudicator (handover §5).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Reuse the content-based envelope discovery from the main IAA script.
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))
from compute_iaa import discover_sources  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# Rules
# ──────────────────────────────────────────────────────────────────────
#
# violation_code -> (spec clause, human description)
RULES: dict[str, tuple[str, str]] = {
    "T0_COMPOSITE_LT2_CHILDREN": (
        "spec v1.2.2 composite_split / review query 3.2",
        "composite_split인데 sub_criteria < 2 (분해의 의미가 없음)",
    ),
    "T0_COMPOSITE_NULL_CHILD_LOGIC": (
        "spec v1.2.2 composite_split / review query 3.3",
        "composite_split인데 child_logic이 null/공백 (결합 규칙 미명시)",
    ),
}


def check_record(record: dict) -> list[tuple[str, str]]:
    """Return [(violation_code, detail)] for one Stage 1 record.

    Only structural constraints — nothing that requires reading the criterion
    text or judging the annotator's intent.
    """
    out: list[tuple[str, str]] = []
    if record.get("splitting_decision") != "composite_split":
        return out

    subs = record.get("sub_criteria") or []
    if len(subs) < 2:
        out.append(("T0_COMPOSITE_LT2_CHILDREN", f"n_sub_criteria={len(subs)}"))

    cl = record.get("child_logic")
    if cl is None or (isinstance(cl, str) and not cl.strip()):
        out.append(("T0_COMPOSITE_NULL_CHILD_LOGIC", f"child_logic={cl!r}"))
    return out


def scan(workspace: Path, round_num: int | None) -> tuple[list[dict], dict[str, int]]:
    """Scan every committed envelope of a round. Returns (violations, counters)."""
    violations: list[dict] = []
    counters = {"envelopes": 0, "records": 0, "composite_split": 0}

    for trial_dir in sorted(p for p in workspace.iterdir() if p.is_dir()):
        stage_dir = trial_dir / "stage1"
        if not stage_dir.is_dir():
            continue
        round_dir = stage_dir / f"round{round_num}" if round_num else None
        if round_dir is not None and not round_dir.is_dir():
            continue
        annotators, _llm = discover_sources(stage_dir, round_dir)
        for actor, env in sorted(annotators.items()):
            counters["envelopes"] += 1
            for rec in env.get("records", []):
                counters["records"] += 1
                if rec.get("splitting_decision") == "composite_split":
                    counters["composite_split"] += 1
                for code, detail in check_record(rec):
                    violations.append({
                        "trial": trial_dir.name,
                        "criterion_id": rec.get("criterion_id"),
                        "actor": actor,
                        "violation_code": code,
                        "spec_clause": RULES[code][0],
                        "detail": detail,
                    })
    return violations, counters


_FIELDS = ["trial", "criterion_id", "actor", "violation_code", "spec_clause", "detail"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Tier 0 structural hygiene check (handover §A-2).")
    ap.add_argument("--workspace", default=str(_PROJECT_ROOT / "iaa_workspace"))
    ap.add_argument("--round", type=int, default=2, dest="round_num",
                    help="read committed envelopes from stage1/round{R}/ (default 2; "
                         "0 = stage dir itself)")
    ap.add_argument("--out", default=None,
                    help="directory to write tier0_violations.csv (default: print only)")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser()
    if not workspace.is_absolute():
        workspace = (_PROJECT_ROOT / workspace).resolve()
    if not workspace.exists():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 2

    round_num = args.round_num or None
    violations, counters = scan(workspace, round_num)

    print(f"Workspace: {workspace}")
    print(f"Round: {round_num or '(stage dir)'}")
    print(f"Scanned: {counters['envelopes']} envelopes / {counters['records']} records "
          f"/ {counters['composite_split']} composite_split")
    print(f"Violations: {len(violations)}\n")

    if violations:
        w = max(len(v["criterion_id"] or "") for v in violations)
        for v in violations:
            print(f"  {v['actor']:<5} {v['criterion_id']:<{w}}  "
                  f"{v['violation_code']:<32} {v['detail']}")
        print()
        by_code: dict[str, int] = {}
        for v in violations:
            by_code[v["violation_code"]] = by_code.get(v["violation_code"], 0) + 1
        for code, n in sorted(by_code.items()):
            print(f"  {code}: {n}  — {RULES[code][1]}")
    else:
        print("  (none)")

    print("\nNOTE: Tier 0 = 'this label is spec-wrong'. What the correct label IS "
          "remains the adjudicator's call (handover §5).")

    if args.out:
        out_dir = Path(args.out).expanduser()
        if not out_dir.is_absolute():
            out_dir = (_PROJECT_ROOT / out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "tier0_violations.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=_FIELDS)
            wr.writeheader()
            wr.writerows(violations)
        print(f"\nSaved: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
