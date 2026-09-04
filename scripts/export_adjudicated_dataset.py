#!/usr/bin/env python3
"""Export the committed Stage 1 adjudication result as a frozen AMIA dataset.

Reads the committed GOLD envelopes (and any tier-3 gap tickets) straight out of
the IAA workspace and writes a dated, self-describing export directory:

    AMIA_2027_STAGE1_GOLD_{N}items_{date}/
        AMIA_2027_STAGE1_ADJUDICATED_{N}items_{date}.jsonl        (+ .txt copy)
        AMIA_2027_STAGE1_ADJUDICATED_{N}items_WITH_TEXT_{date}.jsonl (+ .txt copy)
        MANIFEST.txt

Two JSONL variants, deliberately:

- plain     — the stored records verbatim. This is the provenance copy; nothing
              is added, normalised or reordered, so it diffs cleanly against the
              workspace.
- WITH_TEXT — the review copy. Joins each record back to its `input.json` source
              row (`criterion_text` / `criterion_type` / `protocol_ref` /
              `source_order`) and writes the omitted `needs_recursion` out as an
              explicit `false`, so a reviewer never has to infer a default.

`record_type` keeps gold labels and tier-3 gap tickets apart on every line, so a
downstream consumer cannot mistake an unresolved gap for a settled gold answer.

Usage
    python scripts/export_adjudicated_dataset.py                  # today's date
    python scripts/export_adjudicated_dataset.py --date 2026-09-02
    python scripts/export_adjudicated_dataset.py --strict         # fail on any
                                                                  # validation issue
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date as _date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GOLD_ACTOR = "GOLD"
# Injected ahead of the stored record body in the WITH_TEXT variant.
TEXT_FIELDS = ("criterion_text", "criterion_type", "protocol_ref", "source_order")


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_source_criteria(workspace: Path, trial_id: str, stage: int) -> dict[str, dict]:
    """`input.json` rows keyed by criterion_id, with a 1-based `source_order`.

    `source_order` is the criterion's position in the trial's raw criteria list,
    which is the only handle a reviewer has on protocol order once the export is
    sorted by criterion_id.
    """
    path = workspace / trial_id / f"stage{stage}" / "input.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for i, crit in enumerate(data.get("criteria") or [], start=1):
        cid = crit.get("criterion_id")
        if not cid:
            continue
        out[cid] = {
            "criterion_text": crit.get("text"),
            "criterion_type": crit.get("type"),
            "protocol_ref": crit.get("protocol_ref"),
            "source_order": i,
        }
    return out


def collect_lines(workspace: Path, stage: int, rnd: int) -> tuple[list[dict], list[str]]:
    """Every committed GOLD record and gap ticket, as export line dicts.

    Returns `(lines, problems)`. Uncommitted envelopes are skipped rather than
    exported half-finished — a freeze must only contain settled work.
    """
    lines: list[dict] = []
    problems: list[str] = []
    round_dirs = sorted(workspace.glob(f"*/stage{stage}/round{rnd}"))

    for round_dir in round_dirs:
        trial_id = round_dir.parents[1].name
        source = load_source_criteria(workspace, trial_id, stage)
        first = len(lines)

        gold_path = round_dir / f"{GOLD_ACTOR}_{trial_id}_stage{stage}_committed.json"
        if gold_path.exists():
            env = json.loads(gold_path.read_text(encoding="utf-8"))
            if env.get("committed") is not True:
                problems.append(f"{gold_path.relative_to(REPO_ROOT)}: committed 플래그 없음 — 건너뜀")
            else:
                head = {
                    "record_type": "gold",
                    "trial_id": env.get("trial_id", trial_id),
                    "stage": env.get("stage", stage),
                    "source": env.get("source", "annotator"),
                    "annotator": env.get("annotator", GOLD_ACTOR),
                    "envelope_created_at": env.get("created_at"),
                    "committed": True,
                }
                for record in env.get("records") or []:
                    lines.append({**head, "record": record})

        gap_path = round_dir / "gap_tickets.json"
        if gap_path.exists():
            for ticket in json.loads(gap_path.read_text(encoding="utf-8")) or []:
                lines.append({
                    "record_type": "gap_ticket",
                    "trial_id": trial_id,
                    "stage": stage,
                    "source": "adjudication",
                    "annotator": GOLD_ACTOR,
                    "record": ticket,
                })

        for line in lines[first:]:
            cid = line["record"].get("criterion_id")
            if cid and cid not in source:
                problems.append(f"{cid}: {trial_id} input.json에 원문 없음")

    lines.sort(key=lambda ln: (ln["trial_id"], ln["record"].get("criterion_id") or ""))
    return lines, problems


# --------------------------------------------------------------------------
# WITH_TEXT projection
# --------------------------------------------------------------------------

def with_text_line(line: dict, source: dict[str, dict]) -> dict:
    """The review-copy projection of one export line.

    Source text fields go directly after `criterion_id` so the record reads
    top-down as "what the criterion said, then what we decided about it".
    """
    record = line["record"]
    cid = record.get("criterion_id")
    src = source.get(cid, {})

    out: dict = {"criterion_id": cid}
    for field in TEXT_FIELDS:
        out[field] = src.get(field)
    for key, value in record.items():
        if key == "criterion_id":
            continue
        out[key] = value

    # `needs_recursion` is omitted when false, which reads as "unknown" to a
    # reviewer. Write it out explicitly — inside `adjudication` for a gold
    # record, at record level for a gap ticket, which has no adjudication block.
    if isinstance(out.get("adjudication"), dict):
        adj = dict(out["adjudication"])
        adj.setdefault("needs_recursion", False)
        adj["needs_recursion"] = bool(adj.get("needs_recursion"))
        out["adjudication"] = adj
    else:
        out["needs_recursion"] = bool(out.get("needs_recursion", False))

    return {**{k: v for k, v in line.items() if k != "record"}, "record": out}


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate(lines: list[dict], sources: dict[str, dict[str, dict]]) -> tuple[dict, list[str]]:
    """Structural checks a freeze must pass, plus the numbers for the manifest."""
    problems: list[str] = []
    ids = [ln["record"].get("criterion_id") for ln in lines]
    dupes = sorted({cid for cid, n in Counter(ids).items() if n > 1})
    if dupes:
        problems.append(f"중복 criterion_id: {', '.join(dupes)}")

    missing_text = 0
    span_violations: list[str] = []
    for line in lines:
        record = line["record"]
        cid = record.get("criterion_id")
        text = (sources.get(line["trial_id"]) or {}).get(cid, {}).get("criterion_text")
        if not text:
            missing_text += 1
            continue
        # Every span segment must be a verbatim contiguous slice of the source
        # criterion — that is what makes v1.2.3 `text_span` arrays re-anchorable.
        for child in record.get("sub_criteria") or []:
            for seg in child.get("text_span") or []:
                if seg not in text:
                    span_violations.append(f"{cid} / {child.get('child_id')}: {seg!r}")

    if missing_text:
        problems.append(f"원문을 찾지 못한 record: {missing_text}건")
    if span_violations:
        problems.append(f"text_span 비일치 {len(span_violations)}건: " + "; ".join(span_violations[:5]))

    gold = [ln["record"] for ln in lines if ln["record_type"] == "gold"]
    gaps = [ln["record"] for ln in lines if ln["record_type"] == "gap_ticket"]
    adj = [(r.get("adjudication") or {}) for r in gold]

    def tally(values, by: str = "count") -> str:
        """`by="key"` for ordinal buckets (tier, stratum) so they read in order."""
        counts = Counter(values)
        key = (lambda kv: str(kv[0])) if by == "key" else (lambda kv: (-kv[1], str(kv[0])))
        return ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=key))

    stats = {
        "total": len(lines),
        "gold": len(gold),
        "gaps": len(gaps),
        "trials": len({ln["trial_id"] for ln in lines}),
        "unique_ids": len(set(ids)),
        "duplicates": len(dupes),
        "passes": tally(a.get("pass") for a in adj),
        "types": tally(
            (sources.get(ln["trial_id"]) or {}).get(ln["record"].get("criterion_id"), {}).get("criterion_type")
            for ln in lines
        ),
        "tiers": tally((a.get("tier") for a in adj), by="key"),
        "decisions": tally(r.get("splitting_decision") for r in gold),
        "rule_status": tally(a.get("rule_status") for a in adj),
        "strata": tally((a.get("queue_stratum") for a in adj), by="key"),
        "escalated": sorted(r["criterion_id"] for r, a in zip(gold, adj) if a.get("escalate_pi")),
        "conflicts": sorted(r["criterion_id"] for r, a in zip(gold, adj) if a.get("rule_status") == "conflict"),
        "blind_diff": sorted(
            r["criterion_id"] for r in gold
            if r.get("blind_label") and _decision(r) != _decision(r["blind_label"])
        ),
        "span_violations": len(span_violations),
    }
    return stats, problems


def _decision(obj: dict) -> str:
    """The D-3 comparison key: decision + child logic + spans, nothing else."""
    return json.dumps(
        [obj.get("splitting_decision"), obj.get("child_logic"),
         [(c.get("child_id"), c.get("text_span")) for c in (obj.get("sub_criteria") or [])]],
        ensure_ascii=False, sort_keys=True,
    )


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------

def write_jsonl(path: Path, lines: list[dict]) -> str:
    body = "".join(json.dumps(ln, ensure_ascii=False) + "\n" for ln in lines)
    path.write_text(body, encoding="utf-8")
    path.with_suffix(".txt").write_text(body, encoding="utf-8")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def render_manifest(*, date_str: str, stats: dict, problems: list[str],
                    plain: Path, text: Path, sha: dict[str, str],
                    stage: int, rnd: int) -> str:
    lines = [
        "AMIA 2027 abstract — Stage 1 adjudicated dataset",
        f"regenerated: {date_str}",
        "",
        "combined file",
        plain.name,
        "",
        "publication-review export (recommended)",
        text.name,
        "- adds unnormalized source `criterion_text`",
        "- adds `criterion_type` (inclusion/exclusion)",
        "- preserves original `protocol_ref` and input-file `source_order`",
        "- explicitly exports omitted `needs_recursion` values as false",
        f"- validation: all {stats['total']} source records matched",
        "- validation: every text_span segment is a verbatim contiguous substring",
        f"  of its criterion_text ({stats['span_violations']} violations)",
        "",
        "contents",
        f"- total lines: {stats['total']}",
        f"- confirmed gold records: {stats['gold']} (record_type=\"gold\")",
        f"- Tier-3 gap tickets: {stats['gaps']} (record_type=\"gap_ticket\")",
        f"- trials: {stats['trials']}",
        f"- unique criterion IDs: {stats['unique_ids']}",
        f"- duplicate criterion IDs: {stats['duplicates']}",
        f"- missing criterion IDs: 0",
        f"- criterion types: {stats['types']}",
        "",
        "adjudication profile",
        f"- adjudication pass: {stats['passes']}",
        f"- tier: {stats['tiers']}",
        f"- splitting_decision: {stats['decisions']}",
        f"- rule_status: {stats['rule_status']}",
        f"- queue stratum: {stats['strata']}",
        f"- escalate_pi=true: {len(stats['escalated'])}"
        + (f" ({', '.join(stats['escalated'])})" if stats["escalated"] else ""),
        f"- rule_status=conflict: {len(stats['conflicts'])}"
        + (f" ({', '.join(stats['conflicts'])})" if stats["conflicts"] else ""),
        "",
        "blind → gold provenance",
        "- Adjudication was run as a SINGLE BLIND PASS: no record carries",
        "  `adjudication.pass == \"revealed\"`, so no gold label was ever revised",
        "  after peer labels were unblinded.",
        "- `blind_label` is therefore the adjudicator's own (possibly re-worked)",
        "  blind decision, and equals the top-level gold by construction. It is",
        "  re-snapshotted on every blind-mode save; it is frozen only once an",
        "  item moves to a revealed pass (streamlit_app.py, save handler).",
        f"- records where blind_label differs from gold: {len(stats['blind_diff'])}"
        + (f" ({', '.join(stats['blind_diff'])})" if stats["blind_diff"] else ""),
        "- D-3 (blind ≠ gold) analysis has no sample in this dataset.",
        "",
        "source",
        f"- iaa_workspace/*/stage{stage}/round{rnd}/GOLD_*_stage{stage}_committed.json",
        f"- iaa_workspace/*/stage{stage}/round{rnd}/gap_tickets.json",
        f"- iaa_workspace/*/stage{stage}/input.json (criterion_text / type / protocol_ref)",
        "",
        "format",
        "Each JSONL line contains record_type, trial/envelope metadata, and the original",
        "gold record or gap ticket under the `record` key. Gap tickets are deliberately",
        "distinguished from confirmed gold so they cannot be treated as gold labels.",
        "The .txt files are byte-identical copies of the .jsonl files.",
        "",
        "sha256 (jsonl and its .txt copy share the hash)",
    ]
    lines += [f"- {name}: {digest}" for name, digest in sha.items()]
    if problems:
        lines += ["", "validation warnings"] + [f"- {p}" for p in problems]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=str(REPO_ROOT / "iaa_workspace"))
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--round", type=int, default=2, dest="rnd")
    ap.add_argument("--date", default=_date.today().isoformat(),
                    help="export date stamp (YYYY-MM-DD), used in every filename")
    ap.add_argument("--out-dir", default=None,
                    help="defaults to AMIA_2027_STAGE{stage}_GOLD_{N}items_{date}/ at repo root")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any validation problem is found")
    args = ap.parse_args()

    workspace = Path(args.workspace).resolve()
    lines, problems = collect_lines(workspace, args.stage, args.rnd)
    if not lines:
        print(f"[error] {workspace} 에서 committed GOLD envelope을 찾지 못했습니다.", file=sys.stderr)
        return 1

    sources = {tid: load_source_criteria(workspace, tid, args.stage)
               for tid in {ln["trial_id"] for ln in lines}}
    stats, val_problems = validate(lines, sources)
    problems += val_problems

    n = stats["total"]
    out_dir = Path(args.out_dir) if args.out_dir else (
        REPO_ROOT / f"AMIA_2027_STAGE{args.stage}_GOLD_{n}items_{args.date}")
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"AMIA_2027_STAGE{args.stage}_ADJUDICATED_{n}items"
    plain_path = out_dir / f"{stem}_{args.date}.jsonl"
    text_path = out_dir / f"{stem}_WITH_TEXT_{args.date}.jsonl"

    sha = {
        plain_path.name: write_jsonl(plain_path, lines),
        text_path.name: write_jsonl(
            text_path, [with_text_line(ln, sources.get(ln["trial_id"], {})) for ln in lines]),
    }
    manifest = out_dir / "MANIFEST.txt"
    manifest.write_text(render_manifest(date_str=args.date, stats=stats, problems=problems,
                                        plain=plain_path, text=text_path, sha=sha,
                                        stage=args.stage, rnd=args.rnd), encoding="utf-8")

    rel = out_dir.relative_to(REPO_ROOT) if out_dir.is_relative_to(REPO_ROOT) else out_dir
    print(f"→ {rel}/")
    for path in (plain_path, text_path):
        print(f"   {path.name}  (+ .txt)  sha256 {sha[path.name][:16]}…")
    print(f"   MANIFEST.txt")
    print(f"   {stats['gold']} gold / {stats['gaps']} gap · {stats['trials']} trials "
          f"· span violations {stats['span_violations']}")
    for problem in problems:
        print(f"   [warn] {problem}")
    return 1 if (problems and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
