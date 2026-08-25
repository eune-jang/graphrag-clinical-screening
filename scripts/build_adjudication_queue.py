#!/usr/bin/env python3
"""Build the Stage 1 adjudication worklist (handover §A-3).

    python scripts/build_adjudication_queue.py                        # print summary
    python scripts/build_adjudication_queue.py --out results/adjudication

Why stratified rather than "all disagreements": the adjudication target is NOT
just the 49 SD disagreements. Cases where BOTH annotators agreed and both were
wrong are real — §7.2 confirms 2 of them — so excluding agreed items would
leave wrong labels in the gold set. Full adjudication of all 172 matched
criteria costs too much time, hence risk-based stratification.

Strata, in assignment priority order (handover §0.4-🟡4 — each item lands in
EXACTLY one stratum, so the S4 sampling frame is well defined):

  S1  SD disagreement in round 1 OR round 2      -> all (49: 21 persist,
                                                    15 resolved, 13 new)
  S2  round-2 agreement + risk pattern           -> keyword + umbrella/
                                                    enumeration filter, plus
                                                    the 4 hardcoded §7.2 items
  S3  round-2 SD agreement, child-count/span differs
  S4  everything else                            -> random sample (seed fixed)

The queue is a worklist ONLY: no gold column. Adjudication results are written
by the Streamlit app to the GOLD envelope (handover §A-3 주의 — double storage
would create a sync problem).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from iaa_pipeline.metrics import (  # noqa: E402
    SPLIT_DECISIONS,
    _greedy_span_matches,
)

sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))
from compute_iaa import discover_sources  # noqa: E402
from tier0_check import check_record  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# S2 risk patterns
# ──────────────────────────────────────────────────────────────────────
#
# Two DIFFERENT risks, deliberately kept separate (handover §0.3-🟠3):
#
# 1. diagnosis/biomarker keywords -> Tier 1 risk (NCCN 3-way granularity).
# 2. umbrella / enumeration signals -> Tier 2 risk. This is the mechanism the
#    disagreement analysis actually pinned down for the confirmed both-wrong
#    cases: one sentence listing conditions joined by commas / "or" /
#    "including" in an exclusion criterion (umbrella vs none). NCT02474355_E8
#    is neither a diagnosis nor a biomarker, so keyword matching alone MISSES
#    it — it would only be caught by the §7.2 hardcode. Hence this second
#    filter exists to catch that class by RULE.

_DIAGNOSIS_STAGING = [
    r"histologic", r"cytologic", r"pathologically confirmed",
    r"stage\s+(?:I{1,3}V?|IV)\b", r"locally advanced", r"metastatic",
    r"\bresectable", r"unresectable", r"NSCLC", r"adenocarcinoma",
]
_BIOMARKER = [
    r"\bEGFR", r"\bALK\b", r"\bKRAS", r"\bROS1", r"\bNRG1", r"\bT790M",
    r"\bPD-L1", r"\bMET\b", r"\bRET\b", r"\bBRAF", r"mutation", r"mutated",
]
_UMBRELLA = [
    r"\bincluding\b", r"such as", r"e\.g\.", r"other than", r"evidence of",
    r"uncontrolled", r"adequate", r"abnormalities", r"any factors",
    r"risk factors",
]

_RX_DIAGNOSIS = [re.compile(p, re.IGNORECASE) for p in _DIAGNOSIS_STAGING]
_RX_BIOMARKER = [re.compile(p, re.IGNORECASE) for p in _BIOMARKER]
_RX_UMBRELLA = [re.compile(p, re.IGNORECASE) for p in _UMBRELLA]
_RX_OR = re.compile(r"\bor\b", re.IGNORECASE)

# The 4 exception-clause conflict items (handover §7.2). Kept as a SAFETY NET
# only — the rule-based filters above should catch them on their own; the
# `s2_by_rule_only` counter in the summary reports whether they did.
HARDCODED_72 = {
    "NCT02474355_I6", "NCT05756153_E6", "NCT03728556_E6", "NCT02474355_E8",
}


def enumeration_signals(text: str) -> list[str]:
    """Comma/or/semicolon enumeration inside a single criterion sentence."""
    out = []
    if text.count(",") >= 3:
        out.append(f"commas={text.count(',')}")
    n_or = len(_RX_OR.findall(text))
    if n_or >= 2:
        out.append(f"or={n_or}")
    if ";" in text:
        out.append("semicolon")
    return out


def signal_families(text: str) -> dict[str, list[str]]:
    """Group S2 signals by family so filter variants can combine them."""
    text = text or ""
    return {
        "dx": [f"dx:{rx.pattern}" for rx in _RX_DIAGNOSIS if rx.search(text)],
        "bm": [f"bm:{rx.pattern}" for rx in _RX_BIOMARKER if rx.search(text)],
        "umb": [f"umb:{rx.pattern}" for rx in _RX_UMBRELLA if rx.search(text)],
        "enum": [f"enum:{s}" for s in enumeration_signals(text)],
    }


# S2 filter variants. Measured over the 123 round-2-agreed criteria, with
# "misses" = how many of the 6 items the handover requires the filter to catch
# by rule (§0.3-🟠3, §7.2): NCT02474355 E8/I6/E9, NCT01295827 E6,
# NCT05756153 E6, NCT03728556 E6.
#
#   spec       umb | dx/bm | enum(any)        S2=47  misses 0
#   strong     umb | dx/bm | enum(no ";")     S2=35  misses 0   <- default
#   umbrella   umb | dx/bm                    S2=26  misses 0
#   keyword    dx/bm only (pre-v2.2 scope)    S2=14  misses 4
#
# Why `strong` (the default) drops the semicolon branch — measured, not a
# judgement call: the branch has ZERO independent discriminating power here.
#   - It adds 12 items over `strong`, all 12 label-AGREEMENT (both rounds),
#     all 12 with `enum:semicolon` as their ONLY signal, and all 12 with
#     exactly one semicolon sitting at the very end of the text — a leftover
#     list separator from the source formatting, not an in-sentence
#     enumeration. 11 of the 12 come from one trial (NCT02912949), e.g.
#     "Pregnant or lactating;" / "Performance status of ECOG 0 - 2;".
#   - Across all 8 trials only 5 criteria have a TRUE in-sentence semicolon
#     enumeration, and none of them needs this branch: 3 are SD disagreements
#     (already S1 by definition) and 2 already match on commas/or/umbrella.
#   So refining the rule to "semicolon after stripping a trailing one" would
#   add 0 items over `strong`. Dropping the branch loses no coverage.
#
# `keyword` is what the handover's "~15건" estimate actually described — it
# predates the v2.2 umbrella filter and misses 4 of the 6 required items,
# including "Adequate organ function." (NCT01295827_I6, both `none`) and
# NCT02125461_E4, which is near-verbatim the guideline's macro_aggregate
# example yet agreed — exactly the both-wrong class S2 exists to catch.
# Kept selectable for comparison, NOT recommended.
S2_FILTERS = {
    "spec": lambda f: bool(f["umb"] or f["dx"] or f["bm"] or f["enum"]),
    "strong": lambda f: bool(
        f["umb"] or f["dx"] or f["bm"]
        or [s for s in f["enum"] if not s.startswith("enum:semicolon")]
    ),
    "umbrella": lambda f: bool(f["umb"] or f["dx"] or f["bm"]),
    "keyword": lambda f: bool(f["dx"] or f["bm"]),
}


def risk_signals(text: str) -> list[str]:
    """All S2 risk signals present in a criterion text (empty = not at risk)."""
    fams = signal_families(text)
    return fams["dx"] + fams["bm"] + fams["umb"] + fams["enum"]


# ──────────────────────────────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────────────────────────────

def _spans(record: dict) -> list[str]:
    return [s.get("text_span", "") for s in (record.get("sub_criteria") or [])]


def load_trial(workspace: Path, trial: str, actor_a: str, actor_b: str
               ) -> tuple[dict[str, str], dict[int, dict[str, dict]]] | None:
    """Return (criterion_text_by_id, {round: {actor: {criterion_id: record}}}).

    Returns None when the trial lacks either annotator in round 2 (the round
    being adjudicated) — such a trial cannot produce queue items.
    """
    stage_dir = workspace / trial / "stage1"
    input_path = stage_dir / "input.json"
    texts: dict[str, str] = {}
    if input_path.exists():
        data = json.loads(input_path.read_text(encoding="utf-8"))
        texts = {c["criterion_id"]: c.get("text", "")
                 for c in data.get("criteria", [])}

    by_round: dict[int, dict[str, dict]] = {}
    for rnd in (1, 2):
        round_dir = stage_dir / f"round{rnd}"
        if not round_dir.is_dir():
            continue
        annotators, _llm = discover_sources(stage_dir, round_dir)
        recs: dict[str, dict] = {}
        for actor in (actor_a, actor_b):
            env = annotators.get(actor)
            if env:
                recs[actor] = {r["criterion_id"]: r for r in env.get("records", [])
                               if r.get("criterion_id")}
        by_round[rnd] = recs

    r2 = by_round.get(2, {})
    if actor_a not in r2 or actor_b not in r2:
        return None
    return texts, by_round


# ──────────────────────────────────────────────────────────────────────
# Stratification
# ──────────────────────────────────────────────────────────────────────

_STRATUM_RANK = {"S1": 0, "S2": 1, "S3": 2, "S4": 3}


def build_rows(workspace: Path, actor_a: str, actor_b: str,
               *, span_threshold: float = 0.5,
               s2_filter: str = "strong") -> tuple[list[dict], dict]:
    """Classify every round-2 matched criterion into exactly one stratum."""
    is_at_risk = S2_FILTERS[s2_filter]
    rows: list[dict] = []
    counters = {"trials": 0, "matched": 0, "r1_disagree": 0, "r2_disagree": 0,
                "s1_persist": 0, "s1_resolved": 0, "s1_new": 0,
                "s2_by_rule": 0, "s2_hardcode_only": 0, "missing_text": 0}

    # Tier 0 violations, keyed by (criterion_id, actor).
    tier0: dict[tuple[str, str], list[str]] = {}

    for trial_dir in sorted(p for p in workspace.iterdir() if p.is_dir()):
        trial = trial_dir.name
        loaded = load_trial(workspace, trial, actor_a, actor_b)
        if loaded is None:
            continue
        texts, by_round = loaded
        counters["trials"] += 1
        r2 = by_round[2]
        r1 = by_round.get(1, {})

        for cid in sorted(set(r2[actor_a]) & set(r2[actor_b])):
            counters["matched"] += 1
            ra, rb = r2[actor_a][cid], r2[actor_b][cid]
            sd_a, sd_b = ra.get("splitting_decision"), rb.get("splitting_decision")
            text = texts.get(cid, "")
            if not text:
                counters["missing_text"] += 1

            for rec, actor in ((ra, actor_a), (rb, actor_b)):
                codes = [c for c, _ in check_record(rec)]
                if codes:
                    tier0.setdefault((cid, actor), []).extend(codes)

            r2_disagree = sd_a != sd_b
            r1_disagree = False
            if r1.get(actor_a, {}).get(cid) and r1.get(actor_b, {}).get(cid):
                r1_disagree = (r1[actor_a][cid].get("splitting_decision")
                               != r1[actor_b][cid].get("splitting_decision"))
            counters["r1_disagree"] += bool(r1_disagree)
            counters["r2_disagree"] += bool(r2_disagree)

            # ── stratum assignment: S1 > S2 > S3 > S4, one stratum only ──
            fams = signal_families(text)
            at_risk = is_at_risk(fams)
            signals = risk_signals(text)
            spans_a, spans_b = _spans(ra), _spans(rb)
            n_matched_spans = _greedy_span_matches(spans_a, spans_b, span_threshold)
            span_mismatch = n_matched_spans < max(len(spans_a), len(spans_b))
            child_mismatch = len(spans_a) != len(spans_b)

            s1_kind = ""
            if r1_disagree or r2_disagree:
                stratum = "S1"
                if r1_disagree and r2_disagree:
                    s1_kind = "persist"
                elif r1_disagree:
                    s1_kind = "resolved"
                else:
                    s1_kind = "new"
                counters[f"s1_{s1_kind}"] += 1
            elif at_risk or cid in HARDCODED_72:
                stratum = "S2"
                if at_risk:
                    counters["s2_by_rule"] += 1
                else:
                    counters["s2_hardcode_only"] += 1
            elif child_mismatch or span_mismatch:
                stratum = "S3"
            else:
                stratum = "S4"

            # binary axis = split-vs-none, the stalled decision (§A-1); these
            # rank above type-only disagreements within a stratum.
            binary_mismatch = ((sd_a in SPLIT_DECISIONS) != (sd_b in SPLIT_DECISIONS))

            rows.append({
                "stratum": stratum,
                "s1_kind": s1_kind,
                "trial": trial,
                "criterion_id": cid,
                "criterion_text": text,
                "E_label": sd_a, "E_child_n": len(spans_a),
                "E_notes": ra.get("notes") or "",
                "D_label": sd_b, "D_child_n": len(spans_b),
                "D_notes": rb.get("notes") or "",
                "binary_mismatch": int(binary_mismatch),
                "span_mismatch": int(span_mismatch),
                "risk_signals": "; ".join(signals),
                "is_72_conflict": int(cid in HARDCODED_72),
                "tier0_flag": "",  # filled below
            })

    for r in rows:
        flags = []
        for actor in (actor_a, actor_b):
            codes = tier0.get((r["criterion_id"], actor))
            if codes:
                flags.append(f"{actor}:{','.join(sorted(set(codes)))}")
        r["tier0_flag"] = "; ".join(flags)

    return rows, counters


def sample_s4(rows: list[dict], n: int, seed: int) -> list[dict]:
    """Keep a fixed-seed random sample of S4; drop the rest from the queue.

    The frame is "round-2 agreement minus S2 minus S3" (handover §0.4-🟡4).
    Sampling method and seed must be reported in the paper, so both are
    recorded in the queue metadata.
    """
    s4 = [r for r in rows if r["stratum"] == "S4"]
    others = [r for r in rows if r["stratum"] != "S4"]
    if len(s4) <= n:
        return rows
    keep = random.Random(seed).sample(sorted(s4, key=lambda r: r["criterion_id"]), n)
    keep_ids = {r["criterion_id"] for r in keep}
    for r in s4:
        if r["criterion_id"] in keep_ids:
            others.append(r)
    return others


def sort_queue(rows: list[dict]) -> list[dict]:
    """§7.2 exception-clause conflicts first, then stratum, then binary axis."""
    rows = sorted(rows, key=lambda r: (
        -r["is_72_conflict"],
        _STRATUM_RANK[r["stratum"]],
        -r["binary_mismatch"],
        r["trial"],
        r["criterion_id"],
    ))
    for i, r in enumerate(rows, start=1):
        r["priority"] = i
    return rows


_FIELDS = [
    "priority", "stratum", "s1_kind", "trial", "criterion_id", "criterion_text",
    "E_label", "E_child_n", "E_notes", "D_label", "D_child_n", "D_notes",
    "binary_mismatch", "span_mismatch", "risk_signals", "is_72_conflict",
    "tier0_flag",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Stage 1 adjudication queue (§A-3).")
    ap.add_argument("--workspace", default=str(_PROJECT_ROOT / "iaa_workspace"))
    ap.add_argument("--pair", nargs=2, default=["EHJ", "DYK"], metavar=("A", "B"),
                    help="annotator pair (default EHJ DYK; E_* columns = A)")
    ap.add_argument("--s2-filter", choices=sorted(S2_FILTERS), default="strong",
                    help="S2 risk-pattern variant (see S2_FILTERS; default strong). "
                         "'keyword' reproduces the pre-v2.2 scope and misses 4 of the "
                         "6 items the handover requires — comparison only")
    ap.add_argument("--s4-size", type=int, default=25,
                    help="S4 first-wave sample size (default 25; expand per §A-3-④)")
    ap.add_argument("--seed", type=int, default=20260730,
                    help="S4 sampling seed — FIXED and reported (default 20260730)")
    ap.add_argument("--out", default=None,
                    help="directory to write adjudication_queue.{csv,json}")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser()
    if not workspace.is_absolute():
        workspace = (_PROJECT_ROOT / workspace).resolve()
    if not workspace.exists():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 2

    actor_a, actor_b = args.pair
    rows, counters = build_rows(workspace, actor_a, actor_b, s2_filter=args.s2_filter)
    if not rows:
        print("No matched round-2 criteria found.", file=sys.stderr)
        return 1

    full_s4 = sum(1 for r in rows if r["stratum"] == "S4")
    rows = sort_queue(sample_s4(rows, args.s4_size, args.seed))

    by_stratum: dict[str, int] = {}
    for r in rows:
        by_stratum[r["stratum"]] = by_stratum.get(r["stratum"], 0) + 1

    print(f"Workspace: {workspace}")
    print(f"Pair: {actor_a} (E_*) vs {actor_b} (D_*)   trials={counters['trials']}  "
          f"matched={counters['matched']}")
    print(f"SD disagreements: round1={counters['r1_disagree']}  "
          f"round2={counters['r2_disagree']}")
    print(f"S1 composition: persist={counters['s1_persist']} "
          f"resolved={counters['s1_resolved']} new={counters['s1_new']}\n")

    print("Queue by stratum")
    for s in ("S1", "S2", "S3", "S4"):
        n = by_stratum.get(s, 0)
        extra = ""
        if s == "S4":
            extra = f"  (sampled from {full_s4}, seed={args.seed})"
        print(f"  {s}: {n}{extra}")
    print(f"  TOTAL: {len(rows)}")
    print(f"\nS2 filter={args.s2_filter}  caught by rule={counters['s2_by_rule']}  "
          f"by §7.2 hardcode only={counters['s2_hardcode_only']}")
    est_h = (len(rows) * 5 / 60, len(rows) * 8 / 60)
    print(f"Estimated adjudication time: {est_h[0]:.1f}~{est_h[1]:.1f}h "
          f"(5~8 min/item, §7.5)")
    if counters["missing_text"]:
        print(f"⚠️  criteria with no source text: {counters['missing_text']} "
              f"(input.json missing — see §A-4)")

    print("\nTop of queue (§7.2 exception-clause conflicts first):")
    for r in rows[:8]:
        print(f"  {r['priority']:>3} {r['stratum']}/{r['s1_kind'] or '-':<8} "
              f"{r['criterion_id']:<18} {str(r['E_label']):<16} {str(r['D_label']):<16}"
              f"{' [72]' if r['is_72_conflict'] else ''}"
              f"{' [T0]' if r['tier0_flag'] else ''}")

    # S4 sampling is a bounded sample by design; say so out loud rather than
    # letting the queue read as full coverage (§A-3-④).
    if full_s4 > by_stratum.get("S4", 0):
        print(f"\nNOTE: S4 covers {by_stratum.get('S4', 0)}/{full_s4} agreed items. "
              f"Expand per the count trigger in §A-3-④ (0 / 1 / 2+ both-wrong).")

    if args.out:
        out_dir = Path(args.out).expanduser()
        if not out_dir.is_absolute():
            out_dir = (_PROJECT_ROOT / out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "adjudication_queue.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=_FIELDS, extrasaction="ignore")
            wr.writeheader()
            wr.writerows(rows)
        json_path = out_dir / "adjudication_queue.json"
        json_path.write_text(json.dumps({
            "pair": [actor_a, actor_b],
            "workspace": str(workspace),
            "round": 2,
            "s2_filter": args.s2_filter,
            "s4": {"size": args.s4_size, "seed": args.seed, "frame": full_s4,
                   "method": "random.Random(seed).sample over criterion_id-sorted frame"},
            "counters": counters,
            "by_stratum": by_stratum,
            "items": rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSaved: {csv_path}\n       {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
