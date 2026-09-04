#!/usr/bin/env python3
"""Round 1 → round 2 agreement trajectories for the AMIA 2027 Table 1.

Every criterion in the round-2 corpus took one of four paths across the two
annotation rounds, judged on the 4-class `splitting_decision`:

    stable agreement   agree  → agree
    resolved           differ → agree
    persistent         differ → differ
    newly emerged      agree  → differ

This script is the frozen source for those numbers. It is **read-only**: it
touches nothing under `AMIA_2027_STAGE1_GOLD_*/`, and it re-uses
`iaa_pipeline.metrics` rather than reimplementing κ, so the trajectory panel and
the IAA panel can never drift apart.

Cross-validation ties the trajectories back to the adjudication queue that was
built from them, and to the measured values recorded in the handover:

    S1 stratum (49)  ==  resolved ∪ persistent ∪ newly emerged
                                                   — every non-stable trajectory
    S4 stratum (25)  ⊆   stable agreement          — sampled from settled criteria
    stable 123 / resolved 15 / persistent 21 / newly emerged 13
    κ 0.608 → 0.650,  observed 136/172 → 138/172

A `--strict` run exits non-zero if any of those disagree with what the
envelopes actually say.

Usage
    python scripts/amia_stage1_trajectories.py --strict
    python scripts/amia_stage1_trajectories.py --out docs/amia_stage1_trajectories.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402

ANNOTATORS = ("EHJ", "DYK")

# Measured anchors — adjudication_handover.md §9-6 and the queue build.
EXPECTED_TRAJECTORY = {
    "stable agreement": 123,
    "resolved": 15,
    "persistent": 21,
    "newly emerged": 13,
}
EXPECTED_ROUNDS = {
    1: {"kappa": 0.608, "n_agree": 136, "n": 172},
    2: {"kappa": 0.650, "n_agree": 138, "n": 172},
}
EXPECTED_CHILD_LOGIC = {"cohort": 31, 1: 28, 2: 31}

BUCKETS = ("stable agreement", "resolved", "persistent", "newly emerged")


# --------------------------------------------------------------------------
# loading (read-only)
# --------------------------------------------------------------------------

def load_round(workspace: Path, stage: int, rnd: int) -> dict[str, dict[str, dict]]:
    """`{annotator: {criterion_id: record}}` for one round's committed envelopes.

    GOLD envelopes are skipped: a trajectory is a property of the two
    independent annotators, and the adjudicated answer is not a third round.
    """
    out: dict[str, dict[str, dict]] = {a: {} for a in ANNOTATORS}
    for round_dir in sorted(workspace.glob(f"*/stage{stage}/round{rnd}")):
        for path in sorted(round_dir.glob("*.json")):
            try:
                env = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(env, dict) or env.get("committed") is not True:
                continue
            if env.get("source") != "annotator":
                continue
            annotator = env.get("annotator")
            if annotator not in out:
                continue
            for record in env.get("records") or []:
                cid = record.get("criterion_id")
                if cid:
                    out[annotator][cid] = record
    return out


def newest_export(root: Path) -> Path:
    """WITH_TEXT jsonl of the most recent `AMIA_*_GOLD_*items_{date}/` export.

    Sorted on the trailing date, not the whole name: the item count sits earlier
    in the name and sorts lexicographically ("113items" < "61items"), so a plain
    name sort would silently pick an older freeze once the set grows.
    """
    candidates = sorted(root.glob("AMIA_*_GOLD_*items_*"), key=lambda p: p.name.rsplit("_", 1)[-1])
    if not candidates:
        raise SystemExit("[error] AMIA_*_GOLD_*items_*/ export 디렉터리를 찾지 못했습니다.")
    matches = sorted(candidates[-1].glob("*_WITH_TEXT_*.jsonl"))
    if not matches:
        raise SystemExit(f"[error] {candidates[-1].name} 에 WITH_TEXT jsonl이 없습니다.")
    return matches[-1]


def load_frozen_strata(export_path: Path) -> dict[str, set[str]]:
    """`{stratum: {criterion_id}}` from the frozen adjudication export."""
    strata: dict[str, set[str]] = {}
    for line in export_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("record_type") != "gold":
            continue
        record = entry["record"]
        stratum = (record.get("adjudication") or {}).get("queue_stratum")
        if stratum:
            strata.setdefault(stratum, set()).add(record["criterion_id"])
    return strata


# --------------------------------------------------------------------------
# trajectories
# --------------------------------------------------------------------------

def classify_trajectories(r1: dict[str, dict[str, dict]],
                          r2: dict[str, dict[str, dict]]) -> tuple[dict[str, list[str]], list[str]]:
    """Bucket every criterion both annotators labelled in both rounds.

    The corpus is the intersection of all four label sets — a criterion missing
    from any one of them has no trajectory to report, and silently bucketing it
    would inflate whichever bucket the default lands in.
    """
    corpus = sorted(
        set(r1["EHJ"]) & set(r1["DYK"]) & set(r2["EHJ"]) & set(r2["DYK"])
    )
    buckets: dict[str, list[str]] = {b: [] for b in BUCKETS}
    for cid in corpus:
        agreed_1 = r1["EHJ"][cid].get("splitting_decision") == r1["DYK"][cid].get("splitting_decision")
        agreed_2 = r2["EHJ"][cid].get("splitting_decision") == r2["DYK"][cid].get("splitting_decision")
        if agreed_1 and agreed_2:
            buckets["stable agreement"].append(cid)
        elif not agreed_1 and agreed_2:
            buckets["resolved"].append(cid)
        elif not agreed_1 and not agreed_2:
            buckets["persistent"].append(cid)
        else:
            buckets["newly emerged"].append(cid)
    return buckets, corpus


def round_panel(rnd: dict[str, dict[str, dict]], corpus: list[str]) -> dict:
    """splitting_decision κ for one round, over the shared corpus only."""
    sd = compute_stage1_iaa(
        {"records": [rnd["EHJ"][cid] for cid in corpus]},
        {"records": [rnd["DYK"][cid] for cid in corpus]},
    )["splitting_decision"]
    return {
        "n": sd["n"],
        "n_agree": sd["n_agree"],
        "observed": sd["observed_agreement"],
        "kappa": sd["cohens_kappa"],
    }


def child_logic_cohort(r1: dict[str, dict[str, dict]], r2: dict[str, dict[str, dict]],
                       corpus: list[str]) -> dict:
    """child_logic agreement on a cohort fixed across both rounds.

    The cohort is every criterion BOTH annotators called `composite_split` in
    BOTH rounds. Fixing it this way is the point: child_logic only exists on a
    split, so a cohort recomputed per round would change membership between the
    two numbers and the comparison would measure the membership change rather
    than the agreement change.
    """
    cohort = [
        cid for cid in corpus
        if all(rnd[a][cid].get("splitting_decision") == "composite_split"
               for rnd in (r1, r2) for a in ANNOTATORS)
    ]
    agree = {}
    for label, rnd in ((1, r1), (2, r2)):
        agree[label] = sum(
            1 for cid in cohort
            if rnd["EHJ"][cid].get("child_logic") == rnd["DYK"][cid].get("child_logic")
        )
    reproduced = (
        len(cohort) == EXPECTED_CHILD_LOGIC["cohort"]
        and agree[1] == EXPECTED_CHILD_LOGIC[1]
        and agree[2] == EXPECTED_CHILD_LOGIC[2]
    )
    return {"cohort": cohort, "agree": agree, "reproduced": reproduced}


# --------------------------------------------------------------------------
# cross-validation
# --------------------------------------------------------------------------

def cross_validate(buckets: dict[str, list[str]], rounds: dict[int, dict],
                   strata: dict[str, set[str]]) -> list[tuple[bool, str]]:
    """Every check as `(ok, message)`, in report order."""
    checks: list[tuple[bool, str]] = []

    # S1 is every criterion whose round-2 label was not a stable agreement:
    # `resolved` and `persistent` (differed in round 1) plus `newly emerged`
    # (agreed in round 1, differed in round 2). The queue calls those three
    # `s1_kind` = resolved / persist / new.
    open_ids = (set(buckets["resolved"]) | set(buckets["persistent"])
                | set(buckets["newly emerged"]))
    s1 = strata.get("S1", set())
    checks.append((
        s1 == open_ids,
        f"S1 stratum ({len(s1)}) == resolved ∪ persistent ∪ newly emerged ({len(open_ids)})"
        + ("" if s1 == open_ids else
           f" — S1-only {sorted(s1 - open_ids)}, trajectory-only {sorted(open_ids - s1)}"),
    ))

    stable = set(buckets["stable agreement"])
    s4 = strata.get("S4", set())
    checks.append((
        s4 <= stable,
        f"S4 stratum ({len(s4)}) ⊆ stable agreement ({len(stable)})"
        + ("" if s4 <= stable else f" — outside stable: {sorted(s4 - stable)}"),
    ))

    for name, expected in EXPECTED_TRAJECTORY.items():
        actual = len(buckets[name])
        checks.append((actual == expected,
                       f"{name}: {actual} (expected {expected})"))

    for rnd, expected in EXPECTED_ROUNDS.items():
        panel = rounds[rnd]
        checks.append((panel["n"] == expected["n"],
                       f"round {rnd} n: {panel['n']} (expected {expected['n']})"))
        checks.append((panel["n_agree"] == expected["n_agree"],
                       f"round {rnd} observed: {panel['n_agree']}/{panel['n']} "
                       f"(expected {expected['n_agree']}/{expected['n']})"))
        checks.append((round(panel["kappa"], 3) == expected["kappa"],
                       f"round {rnd} κ: {panel['kappa']:.3f} (expected {expected['kappa']:.3f})"))

    return checks


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def id_block(ids: list[str], per_line: int = 4) -> str:
    """criterion IDs as a fenced block, wrapped so the page stays readable."""
    rows = [", ".join(ids[i:i + per_line]) for i in range(0, len(ids), per_line)]
    return "```\n" + ("\n".join(rows) if rows else "(none)") + "\n```"


def build_report(buckets: dict[str, list[str]], corpus: list[str], rounds: dict[int, dict],
                 child: dict, checks: list[tuple[bool, str]], export_path: Path) -> str:
    n = len(corpus)
    rel = (export_path.relative_to(REPO_ROOT)
           if export_path.is_relative_to(REPO_ROOT) else export_path)

    lines = [
        "# AMIA 2027 — Stage 1 round 1 → round 2 trajectories (Table 1)",
        "",
        "Generated by `scripts/amia_stage1_trajectories.py` from the committed",
        "annotator envelopes in `iaa_workspace/*/stage1/round{1,2}/`.",
        f"Cross-validated against `{rel}`.",
        "",
        "> **Interpretation guard.** Every bucket below is decided on the 4-class",
        "> `splitting_decision` alone. Two annotators can land in *stable agreement*",
        "> and still differ on how they carved the children (`child_logic`,",
        "> `sub_criteria`, spans) — child-level agreement is a separate axis and is",
        "> reported separately in §4. Do not describe a trajectory bucket as",
        "> \"fully agreed\".",
        "",
        "---",
        "",
        "## 1. Trajectories",
        "",
        f"Corpus: **{n} criteria** labelled by both annotators in both rounds.",
        "",
        "| trajectory | round 1 | round 2 | n | % |",
        "|---|---|---|--:|--:|",
        f"| stable agreement | agree | agree | {len(buckets['stable agreement'])} "
        f"| {100 * len(buckets['stable agreement']) / n:.1f}% |",
        f"| resolved | differ | agree | {len(buckets['resolved'])} "
        f"| {100 * len(buckets['resolved']) / n:.1f}% |",
        f"| persistent | differ | differ | {len(buckets['persistent'])} "
        f"| {100 * len(buckets['persistent']) / n:.1f}% |",
        f"| newly emerged | agree | differ | {len(buckets['newly emerged'])} "
        f"| {100 * len(buckets['newly emerged']) / n:.1f}% |",
        f"| **total** | | | **{n}** | 100.0% |",
        "",
        "Net movement: "
        f"{len(buckets['resolved'])} resolved − {len(buckets['newly emerged'])} newly emerged "
        f"= **{len(buckets['resolved']) - len(buckets['newly emerged']):+d}** criteria in agreement.",
        "",
        "## 2. Agreement per round (splitting_decision)",
        "",
        "| round | n | agreed | observed | κ |",
        "|---|--:|--:|--:|--:|",
    ]
    for rnd in sorted(rounds):
        panel = rounds[rnd]
        lines.append(
            f"| round {rnd} | {panel['n']} | {panel['n_agree']} | "
            f"{panel['observed']:.3f} | {panel['kappa']:.3f} |"
        )
    lines += [
        "",
        "> κ is computed by `iaa_pipeline.metrics.compute_stage1_iaa` over the same",
        "> shared corpus as §1, so the two panels describe one population.",
        "",
        "## 3. Cross-validation",
        "",
        "| check | result |",
        "|---|---|",
    ]
    lines += [f"| {msg} | {'✅' if ok else '❌'} |" for ok, msg in checks]
    lines += [
        "",
        f"{sum(1 for ok, _ in checks if ok)}/{len(checks)} checks passed.",
        "",
        "## 4. child_logic agreement (fixed cohort)",
        "",
    ]
    if child["reproduced"]:
        size = len(child["cohort"])
        lines += [
            f"Cohort: **{size} criteria** that BOTH annotators labelled",
            "`composite_split` in BOTH rounds. Membership is fixed across the two",
            "rounds on purpose — a per-round cohort would change composition between",
            "the two numbers, and the comparison would measure that change rather",
            "than the change in agreement.",
            "",
            "| round | child_logic agreed | cohort |",
            "|---|--:|--:|",
            f"| round 1 | {child['agree'][1]} | {size} |",
            f"| round 2 | {child['agree'][2]} | {size} |",
            "",
            f"Change: **{child['agree'][1]}/{size} → {child['agree'][2]}/{size}**.",
            "",
            "Cohort IDs:",
            "",
            id_block(child["cohort"]),
        ]
    else:
        lines += [
            "**Not reproduced — excluded from the abstract.**",
            "",
            "The measured anchors for this section were cohort "
            f"{EXPECTED_CHILD_LOGIC['cohort']}, agreement "
            f"{EXPECTED_CHILD_LOGIC[1]} → {EXPECTED_CHILD_LOGIC[2]}. This run"
            " produced:",
            "",
            "| quantity | expected | this run |",
            "|---|--:|--:|",
            f"| cohort size | {EXPECTED_CHILD_LOGIC['cohort']} | {len(child['cohort'])} |",
            f"| round 1 agreed | {EXPECTED_CHILD_LOGIC[1]} | {child['agree'][1]} |",
            f"| round 2 agreed | {EXPECTED_CHILD_LOGIC[2]} | {child['agree'][2]} |",
            "",
            "Reported as-is, without diagnosis. Do not cite these numbers until the",
            "discrepancy is investigated separately.",
        ]

    lines += ["", "---", "", "## Appendix — criterion IDs by trajectory", ""]
    for bucket in BUCKETS:
        lines += [f"### {bucket} ({len(buckets[bucket])})", "", id_block(buckets[bucket]), ""]

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=str(REPO_ROOT / "iaa_workspace"))
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--export", default=None,
                    help="frozen adjudication export used for the stratum cross-checks "
                         "(default: WITH_TEXT jsonl of the newest AMIA_*_GOLD_*items_*/)")
    ap.add_argument("--out", default=None, help="write the report to this markdown file")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any cross-validation check fails")
    args = ap.parse_args()

    workspace = Path(args.workspace).resolve()
    export_path = (Path(args.export) if args.export else newest_export(REPO_ROOT)).resolve()
    if not export_path.exists():
        print(f"[error] frozen export를 찾지 못했습니다: {export_path}", file=sys.stderr)
        return 1

    r1 = load_round(workspace, args.stage, 1)
    r2 = load_round(workspace, args.stage, 2)
    if not all(r1[a] and r2[a] for a in ANNOTATORS):
        print("[error] round1/round2의 EHJ·DYK committed envelope을 찾지 못했습니다.",
              file=sys.stderr)
        return 1

    buckets, corpus = classify_trajectories(r1, r2)
    rounds = {1: round_panel(r1, corpus), 2: round_panel(r2, corpus)}
    child = child_logic_cohort(r1, r2, corpus)
    strata = load_frozen_strata(export_path)
    checks = cross_validate(buckets, rounds, strata)

    print(f"corpus: {len(corpus)} criteria (EHJ ∩ DYK, round 1 ∩ round 2)")
    for bucket in BUCKETS:
        print(f"  {bucket:<18} {len(buckets[bucket]):>4}")
    for rnd in sorted(rounds):
        panel = rounds[rnd]
        print(f"  round {rnd}: {panel['n_agree']}/{panel['n']} observed "
              f"{panel['observed']:.3f} · κ {panel['kappa']:.3f}")
    print(f"  child_logic cohort {len(child['cohort'])}: "
          f"{child['agree'][1]} → {child['agree'][2]} "
          f"({'reproduced' if child['reproduced'] else 'NOT reproduced'})")

    failed = [msg for ok, msg in checks if not ok]
    print(f"\ncross-validation: {len(checks) - len(failed)}/{len(checks)} passed")
    for msg in failed:
        print(f"  [fail] {msg}")

    report = build_report(buckets, corpus, rounds, child, checks, export_path)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\n→ {out}")
    else:
        print()
        print(report)

    return 1 if (failed and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
