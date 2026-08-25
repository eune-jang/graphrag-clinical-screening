#!/usr/bin/env python3
"""Round-over-round Δ table for Stage 1 IAA (adjudication_handover.md §A-1).

Compares POOLED IAA between two annotators across two rounds, with the
splitting_decision decomposed into its two axes (split-vs-none / split type),
so it is visible WHICH decision improved and which stalled.

    python scripts/compare_rounds.py                       # EHJ vs DYK, r1 -> r2
    python scripts/compare_rounds.py --pair EHJ DYK --rounds 1 2

Expected values (regression anchors, measured 2026-07-30 — handover §9-6):
  round1: matched 172, SD agree 136 (disagr 36), direction EHJ9/DYK20/type7
  round2: matched 172, SD agree 138 (disagr 34), direction EHJ3/DYK24/type7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402

# Reuse the content-based envelope discovery from the main IAA script.
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))
from compute_iaa import discover_sources  # noqa: E402


def pooled_iaa(workspace: Path, round_num: int, actor_a: str, actor_b: str) -> dict | None:
    """POOLED Stage 1 IAA for (actor_a, actor_b) over all trials of a round.

    Order matters for direction_bias: actor_a is the `a` side.
    """
    recs_a: list[dict] = []
    recs_b: list[dict] = []
    for trial_dir in sorted(p for p in workspace.iterdir() if p.is_dir()):
        stage_dir = trial_dir / "stage1"
        round_dir = stage_dir / f"round{round_num}"
        if not round_dir.is_dir():
            continue
        annotators, _llm = discover_sources(stage_dir, round_dir)
        env_a, env_b = annotators.get(actor_a), annotators.get(actor_b)
        if not env_a or not env_b:
            continue
        recs_a += env_a.get("records", [])
        recs_b += env_b.get("records", [])
    if not recs_a or not recs_b:
        return None
    return compute_stage1_iaa({"records": recs_a}, {"records": recs_b})


def _metric_rows(iaa: dict, actor_a: str, actor_b: str) -> dict[str, float | int | None]:
    sd = iaa["splitting_decision"]
    sdb = iaa["sd_binary"]
    sdt = iaa["sd_type"]
    db = iaa["direction_bias"]
    sg = iaa["split_degree"]
    return {
        "matched": iaa["alignment"]["n_matched"],
        "SD κ (4-class)": sd["cohens_kappa"],
        "SD observed": sd["observed_agreement"],
        "SD expected (chance)": sd["expected_agreement"],
        "SD binary κ (split vs none)": sdb["cohens_kappa"],
        "SD binary observed": sdb["observed_agreement"],
        "SD type κ (both split, 3-class)": sdt["cohens_kappa"],
        "SD type observed": sdt["observed_agreement"],
        "SD type n (both split)": sdt["n"],
        "CL κ": iaa["child_logic"]["cohens_kappa"],
        "child#.exact (among split)": sg["child_count_exact_among_split"],
        "span F1": sg["span_alignment_f1"],
        f"{actor_a}-only-split": db["n_a_only_split"],
        f"{actor_b}-only-split": db["n_b_only_split"],
        "type-mismatch": db["n_type_mismatch"],
    }


def _fmt(x) -> str:
    if x is None:
        return "—"
    if isinstance(x, int):
        return str(x)
    return f"{x:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 1 IAA Δ table across rounds.")
    ap.add_argument("--workspace", default=str(_PROJECT_ROOT / "iaa_workspace"))
    ap.add_argument("--pair", nargs=2, default=["EHJ", "DYK"], metavar=("A", "B"))
    ap.add_argument("--rounds", nargs=2, type=int, default=[1, 2], metavar=("R1", "R2"))
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser()
    if not workspace.is_absolute():
        workspace = (_PROJECT_ROOT / workspace).resolve()
    actor_a, actor_b = args.pair
    r1, r2 = args.rounds

    iaa_1 = pooled_iaa(workspace, r1, actor_a, actor_b)
    iaa_2 = pooled_iaa(workspace, r2, actor_a, actor_b)
    if iaa_1 is None or iaa_2 is None:
        missing = [str(r) for r, x in ((r1, iaa_1), (r2, iaa_2)) if x is None]
        print(f"No committed envelopes for {actor_a}/{actor_b} in round(s) "
              f"{', '.join(missing)} under {workspace}", file=sys.stderr)
        return 1

    m1 = _metric_rows(iaa_1, actor_a, actor_b)
    m2 = _metric_rows(iaa_2, actor_a, actor_b)

    name_w = max(len(k) for k in m1) + 2
    print(f"\n{actor_a} vs {actor_b} — POOLED, round {r1} → round {r2}\n")
    print(f"{'metric':<{name_w}}{f'round{r1}':>10}{f'round{r2}':>10}{'Δ':>10}")
    print("-" * (name_w + 30))
    for k in m1:
        v1, v2 = m1[k], m2[k]
        delta = (v2 - v1) if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else None
        d_str = (f"{delta:+d}" if isinstance(delta, int)
                 else f"{delta:+.3f}" if delta is not None else "—")
        print(f"{k:<{name_w}}{_fmt(v1):>10}{_fmt(v2):>10}{d_str:>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
