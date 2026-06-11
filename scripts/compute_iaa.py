#!/usr/bin/env python3
"""Compute Stage 1 IAA from committed annotator envelopes — run in VS Code.

No Streamlit. Just open this file in VS Code and hit ▶ Run, or:

    python scripts/compute_iaa.py
    python scripts/compute_iaa.py --workspace iaa_workspace --stage 1
    python scripts/compute_iaa.py --include-llm
    python scripts/compute_iaa.py --out results/iaa            # save JSON + MD

It discovers committed annotator envelopes per trial (by CONTENT — any
filename, e.g. `EHJ_NCT..._committed.json` or `annotator_EHJ.json`), computes
pairwise IAA for every annotator pair (plus annotator-vs-LLM with
--include-llm), prints a table per pair (per-trial + pooled), and optionally
writes a JSON + Markdown report.

Metrics (see iaa_pipeline/metrics.py):
  - splitting_decision : Cohen's κ (primary)
  - child_logic        : Cohen's κ (pairs where both = composite_split)
  - cohort_scope       : union set exact-match + mean Jaccard (ignores child_id)
  - split_degree       : child-count exact (among split) + span-alignment F1
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

# Make the project root importable regardless of the current working dir.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# Discovery
# ──────────────────────────────────────────────────────────────────────

def _load(p: Path) -> dict | None:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def discover_sources(stage_dir: Path) -> tuple[dict[str, dict], dict | None]:
    """Return ({annotator_id: committed_envelope}, llm_envelope_or_None)."""
    annotators: dict[str, dict] = {}
    llm: dict | None = None
    for p in sorted(stage_dir.glob("*.json")):
        env = _load(p)
        if not env:
            continue
        if env.get("source") == "annotator" and env.get("committed") is True:
            label = env.get("annotator") or p.stem
            annotators[label] = env  # last write wins on duplicate annotator id
        elif env.get("source") == "llm" or p.name == "llm_output.json":
            llm = env
    return annotators, llm


# ──────────────────────────────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────────────────────────────

def _row(trial: str, iaa: dict) -> dict:
    sd = iaa["splitting_decision"]
    cl = iaa["child_logic"]
    cs = iaa["cohort_scope"]
    sg = iaa.get("split_degree", {})
    return {
        "trial": trial,
        "n_matched": iaa["alignment"]["n_matched"],
        "sd_kappa": sd["cohens_kappa"],
        "cl_kappa": cl["cohens_kappa"],
        "cohort_exact": cs["exact_match_rate"],
        "cohort_jaccard": cs["mean_jaccard"],
        "childcnt_exact_split": sg.get("child_count_exact_among_split"),
        "span_f1": sg.get("span_alignment_f1"),
    }


def _fmt(x) -> str:
    return f"{x:.3f}" if isinstance(x, (int, float)) else "—"


_COLS = [
    ("trial", "trial", 14),
    ("n_matched", "matched", 8),
    ("sd_kappa", "SD κ", 8),
    ("cl_kappa", "CL κ", 8),
    ("cohort_exact", "cohort.ex", 10),
    ("cohort_jaccard", "cohort.J", 9),
    ("childcnt_exact_split", "child#.ex", 10),
    ("span_f1", "spanF1", 8),
]


def _print_table(pair_label: str, rows: list[dict], pooled: dict) -> None:
    print(f"\n=== {pair_label} ===")
    header = "".join(f"{h:>{w}}" if k != "trial" else f"{h:<{w}}"
                     for k, h, w in _COLS)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("".join(
            (f"{r[k]:<{w}}" if k == "trial" else f"{_fmt(r[k]):>{w}}")
            for k, _, w in _COLS
        ))
    print("-" * len(header))
    pr = _row("POOLED", pooled)
    print("".join(
        (f"{pr[k]:<{w}}" if k == "trial" else f"{_fmt(pr[k]):>{w}}")
        for k, _, w in _COLS
    ))


def _md_table(pair_label: str, rows: list[dict], pooled: dict) -> str:
    head = "| trial | matched | SD κ | CL κ | cohort.exact | cohort.J | child#.exact(split) | spanF1 |"
    sep = "|---|--:|--:|--:|--:|--:|--:|--:|"
    lines = [f"### {pair_label}", "", head, sep]
    for r in list(rows) + [_row("**POOLED**", pooled)]:
        lines.append(
            f"| {r['trial']} | {r['n_matched']} | {_fmt(r['sd_kappa'])} | "
            f"{_fmt(r['cl_kappa'])} | {_fmt(r['cohort_exact'])} | "
            f"{_fmt(r['cohort_jaccard'])} | {_fmt(r['childcnt_exact_split'])} | "
            f"{_fmt(r['span_f1'])} |"
        )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Compute Stage 1 IAA (no Streamlit).")
    ap.add_argument("--workspace", default=str(_PROJECT_ROOT / "iaa_workspace"),
                    help="workspace dir holding {trial}/stage{N}/ (default: iaa_workspace)")
    ap.add_argument("--stage", type=int, default=1, help="stage number (default 1)")
    ap.add_argument("--include-llm", action="store_true",
                    help="also compute annotator-vs-LLM pairs")
    ap.add_argument("--out", default=None,
                    help="directory to write iaa_stage{N}.json + .md (default: print only)")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser()
    if not workspace.is_absolute():
        workspace = (_PROJECT_ROOT / workspace).resolve()
    stage = args.stage
    if stage != 1:
        print(f"Only stage 1 is implemented (got --stage {stage}).", file=sys.stderr)
        return 2
    if not workspace.exists():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 2

    # trial -> {label: envelope}, plus the LLM envelope if present
    per_trial: dict[str, tuple[dict[str, dict], dict | None]] = {}
    for trial_dir in sorted(p for p in workspace.iterdir() if p.is_dir()):
        stage_dir = trial_dir / f"stage{stage}"
        if not stage_dir.is_dir():
            continue
        annotators, llm = discover_sources(stage_dir)
        if annotators:
            per_trial[trial_dir.name] = (annotators, llm)

    if not per_trial:
        print(f"No committed annotator envelopes found under {workspace}.")
        return 1

    # Collect the set of annotator labels seen anywhere.
    all_annotators = sorted({a for (anns, _) in per_trial.values() for a in anns})
    print(f"Workspace: {workspace}")
    print(f"Trials with committed work: {len(per_trial)}")
    print(f"Annotators: {', '.join(all_annotators) or '(none)'}")

    # Build the list of pairs to evaluate: every annotator-annotator pair, plus
    # annotator-vs-__llm__ when --include-llm.
    pairs: list[tuple[str, str]] = list(itertools.combinations(all_annotators, 2))
    if args.include_llm:
        pairs += [(a, "__llm__") for a in all_annotators]

    if not pairs:
        print("\nNeed at least 2 sources to compute IAA "
              "(one annotator + --include-llm, or two annotators).")
        return 1

    report: dict = {"workspace": str(workspace), "stage": stage, "pairs": {}}
    md_sections: list[str] = []

    for (la, lb) in pairs:
        rows: list[dict] = []
        recs_a: list[dict] = []
        recs_b: list[dict] = []
        per_trial_detail: dict[str, dict] = {}
        for trial, (anns, llm) in per_trial.items():
            env_a = anns.get(la) if la != "__llm__" else llm
            env_b = anns.get(lb) if lb != "__llm__" else llm
            if not env_a or not env_b:
                continue  # this trial lacks one side of the pair
            iaa = compute_stage1_iaa(env_a, env_b)
            rows.append(_row(trial, iaa))
            per_trial_detail[trial] = iaa
            recs_a += env_a.get("records", [])
            recs_b += env_b.get("records", [])
        if not rows:
            continue
        pooled = compute_stage1_iaa({"records": recs_a}, {"records": recs_b})
        pair_label = f"{la} vs {lb}"
        _print_table(pair_label, rows, pooled)
        report["pairs"][pair_label] = {
            "per_trial": per_trial_detail,
            "pooled": pooled,
        }
        md_sections.append(_md_table(pair_label, rows, pooled))

    if args.out:
        out_dir = Path(args.out).expanduser()
        if not out_dir.is_absolute():
            out_dir = (_PROJECT_ROOT / out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"iaa_stage{stage}.json"
        md_path = out_dir / f"iaa_stage{stage}.md"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        md_path.write_text(
            f"# Stage {stage} IAA report\n\n"
            f"Workspace: `{workspace}`\n\n" + "\n\n".join(md_sections) + "\n",
            encoding="utf-8",
        )
        print(f"\nSaved: {json_path}\n       {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
