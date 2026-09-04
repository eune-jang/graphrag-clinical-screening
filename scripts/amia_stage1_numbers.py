#!/usr/bin/env python3
"""Recompute the AMIA 2027 Stage 1 abstract numbers from a frozen export.

Everything here is derived from the frozen JSONL, never from the live
workspace, so the numbers in the abstract and the numbers in the dataset can
only ever move together. The annotator envelopes are still read from the
workspace — they are the *inputs* the gold was adjudicated against and were
frozen back in round 2.

Reports, in order:

  1. dataset composition of the adjudicated set
  2. baseline EHJ–DYK agreement, on the full round-2 corpus and on the
     adjudicated subset (the two are NOT comparable — the subset over-samples
     disagreement by construction, which is what §D-1/D-2 of the handover warns
     about, so both are printed side by side rather than one alone)
  3. gold-axis agreement (EHJ–GOLD, DYK–GOLD) with the same caveat
  4. the outcome pattern that motivates adjudication: how often gold matched
     one annotator, both, or neither
  5. guideline outcomes (rule_status, escalations, blind→gold revisions)

Usage
    python scripts/amia_stage1_numbers.py                       # newest export
    python scripts/amia_stage1_numbers.py --export <dir-or-jsonl>
    python scripts/amia_stage1_numbers.py --out docs/amia_stage1_numbers.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402


def newest_export(root: Path) -> Path:
    """The most recent `AMIA_*_GOLD_*items_{date}/` export directory.

    Sorted on the trailing date, not the whole name: the item count sits earlier
    in the name and sorts lexicographically ("113items" < "61items"), so a plain
    name sort would silently pick an older freeze once the set grows.
    """
    candidates = sorted(root.glob("AMIA_*_GOLD_*items_*"), key=lambda p: p.name.rsplit("_", 1)[-1])
    if not candidates:
        raise SystemExit("[error] AMIA_*_GOLD_*items_*/ export 디렉터리를 찾지 못했습니다.")
    return candidates[-1]


def load_export(target: Path) -> list[dict]:
    """Export lines from a directory (plain variant preferred) or a JSONL file."""
    if target.is_dir():
        plain = [p for p in sorted(target.glob("*.jsonl")) if "WITH_TEXT" not in p.name]
        path = plain[0] if plain else sorted(target.glob("*.jsonl"))[0]
    else:
        path = target
    lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"export: {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}")
    return lines


def load_annotators(workspace: Path, stage: int, rnd: int) -> dict[str, list[dict]]:
    """Committed annotator records for the round, pooled across trials."""
    out: dict[str, list[dict]] = {}
    for round_dir in sorted(workspace.glob(f"*/stage{stage}/round{rnd}")):
        for path in sorted(round_dir.glob("*.json")):
            try:
                env = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(env, dict) or env.get("committed") is not True:
                continue
            if env.get("source") != "annotator" or env.get("annotator") == "GOLD":
                continue
            out.setdefault(env["annotator"], []).extend(env.get("records") or [])
    return out


def kappa_panel(recs_a: list[dict], recs_b: list[dict]) -> dict:
    iaa = compute_stage1_iaa({"records": recs_a}, {"records": recs_b})
    sd = iaa["splitting_decision"]
    return {
        "n": sd["n"],
        "kappa": sd.get("cohens_kappa"),
        "observed": sd.get("observed_agreement"),
        "n_agree": sd.get("n_agree"),
    }


def fmt(value, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def tally(values, by: str = "count") -> str:
    counts = Counter(values)
    key = (lambda kv: str(kv[0])) if by == "key" else (lambda kv: (-kv[1], str(kv[0])))
    return ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=key))


def build_report(export_lines: list[dict], annotators: dict[str, list[dict]],
                 stage: int, rnd: int) -> str:
    gold = [ln["record"] for ln in export_lines if ln["record_type"] == "gold"]
    gaps = [ln["record"] for ln in export_lines if ln["record_type"] == "gap_ticket"]
    gold_by_id = {r["criterion_id"]: r for r in gold}
    adj = [(r.get("adjudication") or {}) for r in gold]

    ehj = {r["criterion_id"]: r for r in annotators.get("EHJ", [])}
    dyk = {r["criterion_id"]: r for r in annotators.get("DYK", [])}
    subset = sorted(set(gold_by_id) & set(ehj) & set(dyk))

    full = kappa_panel(annotators.get("EHJ", []), annotators.get("DYK", []))
    sub_ed = kappa_panel([ehj[c] for c in subset], [dyk[c] for c in subset])
    sub_eg = kappa_panel([ehj[c] for c in subset], [gold_by_id[c] for c in subset])
    sub_dg = kappa_panel([dyk[c] for c in subset], [gold_by_id[c] for c in subset])

    # Which annotator did the settled answer land on? `splitting_decision` only
    # — the same label the primary κ compares, so the two views agree on what
    # counts as "the same answer".
    pattern = Counter()
    for cid in subset:
        e = ehj[cid].get("splitting_decision")
        d = dyk[cid].get("splitting_decision")
        g = gold_by_id[cid].get("splitting_decision")
        if e == d:
            pattern["annotators agreed, gold confirmed" if g == e
                    else "annotators agreed, gold OVERRODE both"] += 1
        elif g == e:
            pattern["annotators split, gold sided with EHJ"] += 1
        elif g == d:
            pattern["annotators split, gold sided with DYK"] += 1
        else:
            pattern["annotators split, gold chose a third answer"] += 1

    overrode = [cid for cid in subset
                if ehj[cid].get("splitting_decision") == dyk[cid].get("splitting_decision")
                and gold_by_id[cid].get("splitting_decision") != ehj[cid].get("splitting_decision")]

    lines = [
        "# AMIA 2027 — Stage 1 adjudicated gold: abstract numbers",
        "",
        f"Recomputed from the frozen export. Annotator inputs: "
        f"`iaa_workspace/*/stage{stage}/round{rnd}/`.",
        "",
        "## 1. Dataset",
        "",
        f"- adjudicated items: **{len(gold)} gold**, {len(gaps)} open tier-3 gap",
        f"- trials: {len({ln['trial_id'] for ln in export_lines})}",
        f"- queue stratum: {tally((a.get('queue_stratum') for a in adj), by='key')}",
        f"- tier: {tally((a.get('tier') for a in adj), by='key')}",
        f"- gold splitting_decision: {tally(r.get('splitting_decision') for r in gold)}",
        "",
        "## 2. Annotator agreement (EHJ vs DYK), splitting_decision",
        "",
        "| corpus | n | agreed | κ | observed |",
        "|---|--:|--:|--:|--:|",
        f"| full round-{rnd} | {full['n']} | {full['n_agree']} | {fmt(full['kappa'])} | {fmt(full['observed'])} |",
        f"| adjudicated subset | {sub_ed['n']} | {sub_ed['n_agree']} | {fmt(sub_ed['kappa'])} | {fmt(sub_ed['observed'])} |",
        "",
        "> The adjudicated subset was intentionally enriched for disagreement and is",
        "> therefore **not representative** of the full round-2 corpus. Its κ is",
        "> descriptive only and should not be read as a second estimate of",
        "> corpus-level agreement. Note that κ depends on the marginal distribution",
        "> as well as on raw agreement, so disagreement-enriched sampling does not",
        "> bound the corpus value in either direction — the two rows simply measure",
        "> different samples.",
        "",
        "## 3. Gold-axis agreement (adjudicated subset only)",
        "",
        "| pair | n | agreed | observed | κ |",
        "|---|--:|--:|--:|--:|",
        f"| EHJ vs GOLD | {sub_eg['n']} | {sub_eg['n_agree']} | {fmt(sub_eg['observed'])} | {fmt(sub_eg['kappa'])} |",
        f"| DYK vs GOLD | {sub_dg['n']} | {sub_dg['n_agree']} | {fmt(sub_dg['observed'])} | {fmt(sub_dg['kappa'])} |",
        f"| EHJ vs DYK | {sub_ed['n']} | {sub_ed['n_agree']} | {fmt(sub_ed['observed'])} | {fmt(sub_ed['kappa'])} |",
        "",
        "> Same caveat: all three are measured on the disagreement-enriched subset,",
        "> so they compare to each other but not to the corpus figures above.",
        ">",
        "> These are **agreement against a reference**, not accuracy. κ is",
        "> chance-corrected, so it is not the proportion of criteria an annotator",
        "> got right; the accuracy-shaped figure is the raw `agreed` column. In",
        "> prose, prefer:",
        ">",
        f"> *Against adjudicated gold, EHJ and DYK agreed on {sub_eg['n_agree']}/{sub_eg['n']} "
        f"({sub_eg['observed'] * 100:.1f}%) and {sub_dg['n_agree']}/{sub_dg['n']} "
        f"({sub_dg['observed'] * 100:.1f}%) of criteria, respectively"
        f" (κ = {fmt(sub_eg['kappa'])} and {fmt(sub_dg['kappa'])}).*",
        "",
        "## 4. What adjudication actually changed",
        "",
        "| outcome | n |",
        "|---|--:|",
    ]
    lines += [f"| {label} | {n} |" for label, n in pattern.most_common()]
    lines += [
        "",
        f"Gold overrode a **unanimous** annotator pair on {len(overrode)} item(s)"
        + (f": {', '.join(overrode)}." if overrode else "."),
        "This is the case a 2-of-3 majority vote cannot produce, and the reason",
        "the adjudicator's label is not treated as a third vote.",
        "",
        "## 5. Guideline outcomes",
        "",
        f"- rule_status: {tally(a.get('rule_status') for a in adj)}",
        f"- escalate_pi=true: {sum(1 for a in adj if a.get('escalate_pi'))}"
        + (f" ({', '.join(r['criterion_id'] for r, a in zip(gold, adj) if a.get('escalate_pi'))})"
           if any(a.get("escalate_pi") for a in adj) else ""),
        f"- rule_status=conflict: "
        + (", ".join(r["criterion_id"] for r, a in zip(gold, adj) if a.get("rule_status") == "conflict")
           or "none"),
        f"- adjudication pass: {tally(a.get('pass') for a in adj)}",
        "",
        "Adjudication ran as a single blind pass, so there is no revealed-pass",
        "revision to report: `blind_label` equals the gold label on every record",
        "and the D-3 (blind ≠ gold) analysis has no sample in this dataset.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", default=None,
                    help="export directory or .jsonl (default: newest AMIA_*_GOLD_*items_*/)")
    ap.add_argument("--workspace", default=str(REPO_ROOT / "iaa_workspace"))
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--round", type=int, default=2, dest="rnd")
    ap.add_argument("--out", default=None, help="write the report to this markdown file")
    args = ap.parse_args()

    target = Path(args.export) if args.export else newest_export(REPO_ROOT)
    export_lines = load_export(target)
    annotators = load_annotators(Path(args.workspace).resolve(), args.stage, args.rnd)
    if not annotators:
        print("[error] committed annotator envelope을 찾지 못했습니다.", file=sys.stderr)
        return 1

    report = build_report(export_lines, annotators, args.stage, args.rnd)
    print()
    print(report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
