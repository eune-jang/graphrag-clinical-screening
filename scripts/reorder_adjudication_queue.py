#!/usr/bin/env python3
"""Reassign `priority` in an EXISTING adjudication queue — no re-sampling.

Why this is a separate script rather than a flag on `build_adjudication_queue.py`:
rebuilding the queue redraws the S4 audit sample. The seed is fixed
(`--seed 20260730`), but the sampling FRAME is "round-2 agreement minus S2
minus S3", so anything that shifts S2 assignment — a different `--s2-filter`,
changed workspace data — silently produces a different 25. That sample is
reported in the paper's Methods, so it has to be immutable once drawn.

This script only rewrites the `priority` column of rows that already exist.
Strata, S4 membership, risk signals and flags are untouched, and the row set
is asserted identical before anything is written.

Ordering for the AMIA abstract scope (adjudication_guide_v2_notion.md §4-1):

    ① 해소  S1 / s1_kind=resolved   15   "합의가 정답으로 수렴했나" [X/15 vs Y/15]
    ② 감사  S4                      25   "일치 항목 속 숨은 오답" [X/25]  ← 핵심
    ③ 지속  S1 / s1_kind=persist    21   갈린 기전 3가지 + LLM 비교
    ─────────────────────────────────── 61건
    ④ 나머지 (S1-new 13, S3 4, S2)      마감 후. 기존 상대 순서 유지.

① first is deliberate: those items are label-AGREEMENT, so they are the
lowest-risk warm-up, and the adjudicator reaches the hardest block (③) with
calibrated judgement.

Usage:
    python scripts/reorder_adjudication_queue.py                    # dry run
    python scripts/reorder_adjudication_queue.py --write
    python scripts/reorder_adjudication_queue.py --scope full --write   # revert
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

DEFAULT_DIR = _PROJECT_ROOT / "results" / "adjudication"

# Block order for --scope abstract61. Lower rank runs first.
ABSTRACT_BLOCKS: list[tuple[str, str]] = [
    ("S1:resolved", "① 해소 — 1차엔 갈렸다가 2차에 같아진 항목"),
    ("S4:", "② 무작위 감사 — 계속 일치했던 항목 표본"),
    ("S1:persist", "③ 지속 — 두 라운드 다 갈린 항목"),
]


def block_key(row: dict) -> str:
    """`S1:resolved`, `S4:`, … — stratum plus the S1 sub-kind."""
    stratum = (row.get("stratum") or "").strip()
    kind = (row.get("s1_kind") or "").strip() if stratum == "S1" else ""
    return f"{stratum}:{kind}"


def abstract_rank(row: dict) -> int:
    """Block rank; everything not in the abstract scope sorts after it."""
    key = block_key(row)
    for i, (block, _) in enumerate(ABSTRACT_BLOCKS):
        if key == block:
            return i
    return len(ABSTRACT_BLOCKS)


def reorder(rows: list[dict], scope: str) -> list[dict]:
    """Return rows in the new order, with `priority` renumbered from 1.

    Within a block the pre-existing order is preserved (stable sort on the
    current priority), so §7.2 exception-clause conflicts stay at the front of
    their block exactly as `build_adjudication_queue.sort_queue` placed them.
    """
    def current_priority(row: dict) -> int:
        try:
            return int(row.get("priority") or 10 ** 6)
        except (TypeError, ValueError):
            return 10 ** 6

    ordered = sorted(rows, key=current_priority)
    if scope == "abstract61":
        ordered = sorted(ordered, key=abstract_rank)  # stable → keeps inner order
    out = []
    for i, row in enumerate(ordered, start=1):
        new = dict(row)
        new["priority"] = i
        out.append(new)
    return out


def summarize(rows: list[dict]) -> None:
    by_block: dict[str, list[dict]] = {}
    for r in rows:
        by_block.setdefault(block_key(r), []).append(r)

    print(f"\n{'순서':<4} {'블록':<14} {'건수':>4}  {'priority 범위':<14} 설명")
    print("─" * 92)
    seen = set()
    for block, label in ABSTRACT_BLOCKS:
        items = by_block.get(block, [])
        seen.add(block)
        if not items:
            continue
        lo = min(int(r["priority"]) for r in items)
        hi = max(int(r["priority"]) for r in items)
        print(f"{'①②③'[len(seen) - 1]:<4} {block:<14} {len(items):>4}  "
              f"{f'{lo}–{hi}':<14} {label}")
    rest = [r for r in rows if block_key(r) not in seen]
    if rest:
        lo = min(int(r["priority"]) for r in rest)
        hi = max(int(r["priority"]) for r in rest)
        blocks = ", ".join(sorted({block_key(r) for r in rest}))
        print(f"{'④':<4} {'(나머지)':<14} {len(rest):>4}  "
              f"{f'{lo}–{hi}':<14} 마감 후 — {blocks}")
    print("─" * 92)
    n61 = sum(len(by_block.get(b, [])) for b, _ in ABSTRACT_BLOCKS)
    print(f"초록 스코프 합계: {n61}건 / 전체 {len(rows)}건\n")


def check_unchanged(before: list[dict], after: list[dict]) -> list[str]:
    """Everything except `priority` must be byte-identical, and so must the
    row set. This is the guard that makes "no re-sampling" checkable rather
    than merely intended."""
    errs: list[str] = []
    if len(before) != len(after):
        errs.append(f"row count changed: {len(before)} → {len(after)}")
    b_by_id = {r.get("criterion_id"): r for r in before}
    a_by_id = {r.get("criterion_id"): r for r in after}
    if set(b_by_id) != set(a_by_id):
        missing = sorted(set(b_by_id) - set(a_by_id))
        added = sorted(set(a_by_id) - set(b_by_id))
        errs.append(f"row set changed — dropped {missing}, added {added}")
        return errs
    for cid, b in b_by_id.items():
        a = a_by_id[cid]
        for k in b:
            if k == "priority":
                continue
            if b.get(k) != a.get(k):
                errs.append(f"{cid}: column {k!r} changed "
                            f"({b.get(k)!r} → {a.get(k)!r})")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reassign priority in an existing adjudication queue "
                    "(no re-sampling).")
    ap.add_argument("--dir", default=str(DEFAULT_DIR),
                    help="directory holding adjudication_queue.{csv,json}")
    ap.add_argument("--scope", choices=["abstract61", "full"],
                    default="abstract61",
                    help="abstract61: 해소→감사→지속 순 (default). "
                         "full: 기존 층 우선 순서로 되돌림")
    ap.add_argument("--write", action="store_true",
                    help="actually write; omit for a dry run")
    args = ap.parse_args()

    qdir = Path(args.dir).expanduser()
    csv_path = qdir / "adjudication_queue.csv"
    if not csv_path.exists():
        print(f"큐 파일이 없습니다: {csv_path}", file=sys.stderr)
        print("먼저 scripts/build_adjudication_queue.py를 실행하세요.",
              file=sys.stderr)
        return 1

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]

    if "s1_kind" not in fields:
        print("큐에 s1_kind 컬럼이 없습니다 — 예전 버전의 큐입니다.", file=sys.stderr)
        return 1

    new_rows = reorder(rows, args.scope)
    errs = check_unchanged(rows, new_rows)
    if errs:
        print("❌ priority 외의 값이 바뀌었습니다 — 쓰지 않습니다:", file=sys.stderr)
        for e in errs[:10]:
            print(f"  - {e}", file=sys.stderr)
        return 2

    summarize(new_rows)
    print(f"✅ priority만 재부여됨 · 층·S4 표본·flags 전부 보존 "
          f"({len(rows)}행 동일)")

    if not args.write:
        print("\n(dry run — 반영하려면 --write)")
        return 0

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(new_rows)
    print(f"→ {csv_path}")

    json_path = qdir / "adjudication_queue.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        prio = {r["criterion_id"]: r["priority"] for r in new_rows}
        items = data.get("items") if isinstance(data, dict) else data
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("criterion_id") in prio:
                    it["priority"] = prio[it["criterion_id"]]
            items.sort(key=lambda r: r.get("priority", 10 ** 6))
        if isinstance(data, dict):
            data.setdefault("meta", {})["priority_scope"] = args.scope
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print(f"→ {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
