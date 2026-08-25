"""Pure logic for Stage 1 adjudication (gold set construction).

Everything here is streamlit-free so it can be unit-tested directly; the UI
layer in `streamlit_app.py` only renders widgets and calls into this module.

Design constraints that come straight from `iaa_pipeline_spec/adjudication_handover.md`:

- Gold labels live at the record TOP LEVEL, because `compute_stage1_iaa` reads
  `splitting_decision` / `child_logic` / `sub_criteria` / `cohort_scope` from
  there (§7.4-①). Nesting them under a `gold_label` key would silently produce
  None for every GOLD-axis metric.
- The GOLD envelope is saved into `stage1/round2/` alongside EHJ/DYK so that
  `compute_iaa.py`'s single-directory discovery finds all three actors and
  emits E-D / E-G / D-G (§7.4-🔴1). A separate `adjudication/` folder would
  yield one actor and therefore zero pairs.
- `tier == 3` (undecidable) records are written to `gap_tickets.json`, NOT the
  GOLD envelope: `cohens_kappa` normalizes None to a `"__NONE__"` sentinel and
  counts it as its own class, so a null `splitting_decision` in the gold
  envelope would corrupt the GOLD-axis κ (§7.4-🔴2).
- `text_span` is an ARRAY of contiguous segments (spec v1.2.3 변경 6), each of
  which must be an exact substring of the criterion text. With segments
  available, every deliberate exception the guideline used to need
  (떨어진 병기 표현, 공통 전제) is expressible as a substring, so
  `span_override` is now an ERROR path rather than a sanctioned exception —
  see `validate_adjudication`.
- `child_logic` is required for BOTH `composite_split` and `macro_aggregate`
  and forbidden for `nested_exception` / `none` (guideline v1.2.1 변경 #2,
  spec v1.2.3 변경 1 — the default-omission rule was retired).
"""
from __future__ import annotations

import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

TIERS: tuple[int, ...] = (0, 1, 2, 3)

# Decisions that produce child Criterion nodes and therefore carry a
# combination rule. Kept as a tuple here (rather than imported) so this module
# stays dependency-free; the enum source of truth is `pipeline.config`.
SPLIT_DECISIONS: tuple[str, ...] = ("composite_split", "macro_aggregate")
NO_LOGIC_DECISIONS: tuple[str, ...] = ("nested_exception", "none")

TIER_LABELS: dict[int, str] = {
    0: "Tier 0 — spec v1.2.2 구조 제약 (논의 불가)",
    1: "Tier 1 — 임상 권위 (NCCN NSCLC)",
    2: "Tier 2 — CRC EMR 조회 단위 (판정자 권한)",
    3: "Tier 3 — 판정 불가 → gap ticket",
}

RULE_STATUSES: tuple[str, ...] = ("existing", "new", "conflict", "gap")

GAP_TIER = 3

_WS_RE = re.compile(r"\s+")


# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────

def envelope_dir(stage_dir: Path, round_num: int | None) -> Path:
    """Directory holding committed annotator envelopes for a round.

    `None` means the legacy flat layout (envelopes directly under the stage
    dir). This mirrors `compute_iaa.discover_sources`, which scans exactly one
    directory — the reason GOLD has to live next to EHJ/DYK.
    """
    return stage_dir if round_num is None else stage_dir / f"round{round_num}"


def committed_envelope_name(annotator: str, trial_id: str, stage: int) -> str:
    """Canonical envelope filename (handover §7.1 convention).

    Discovery is content-based, so the name is cosmetic — but matching the
    convention keeps the round folders readable.
    """
    return f"{annotator}_{trial_id}_stage{stage}_committed.json"


def gap_tickets_path(stage_dir: Path, round_num: int | None) -> Path:
    """Where tier-3 items go. Sits beside the envelopes but is NOT one.

    Safe to keep in the round folder: `discover_sources` requires
    `source == "annotator"` and `committed is True`, and a gap-ticket file has
    neither, so it can never be mistaken for an actor.
    """
    return envelope_dir(stage_dir, round_num) / "gap_tickets.json"


# ──────────────────────────────────────────────────────────────────────
# Queue
# ──────────────────────────────────────────────────────────────────────

def load_queue(path: Path, *, trial_id: str | None = None) -> list[dict]:
    """Load the A-3 worklist (CSV or JSON), optionally filtered to one trial.

    Returns [] when the file is absent — the adjudication UI still works
    without a queue, it just loses the priority ordering.
    """
    if not path.exists():
        return []
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", data) if isinstance(data, dict) else data
    else:
        with path.open(newline="", encoding="utf-8") as f:
            items = list(csv.DictReader(f))
    rows = [r for r in items if isinstance(r, dict)]
    if trial_id:
        rows = [r for r in rows if r.get("trial") == trial_id]

    def _prio(r: dict) -> int:
        try:
            return int(r.get("priority") or 10**6)
        except (TypeError, ValueError):
            return 10**6

    return sorted(rows, key=_prio)


def queue_index(queue: list[dict]) -> dict[str, dict]:
    return {r["criterion_id"]: r for r in queue if r.get("criterion_id")}


# ──────────────────────────────────────────────────────────────────────
# Span validation (B-3)
# ──────────────────────────────────────────────────────────────────────

def _collapse(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


def normalize_text_span(value: Any) -> list[str]:
    """`text_span` as a list of segments, accepting both storage forms.

    v1.1 stored a single string; spec v1.2.3 변경 6 makes it an array of
    contiguous segments. Round 1/2 annotator envelopes are still strings, so
    every reader goes through here rather than touching `text_span` directly.
    Blank segments are dropped.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [s.strip() for s in value if isinstance(s, str) and s.strip()]
    return []


def text_span_join(value: Any, sep: str = " ") -> str:
    """Flatten a segment array into one string for display or comparison."""
    return sep.join(normalize_text_span(value))


def span_violations(criterion_text: str, sub_criteria: list[dict]) -> list[dict]:
    """Check every child span SEGMENT against the criterion text.

    Returns one dict per offending segment:
        {child_id, seg_index, code, span, suggestion}

    Codes:
      EMPTY_SPAN          — no segment entered for this child
      NOT_SUBSTRING       — not an exact contiguous substring of the criterion
      WHITESPACE_ONLY_DIFF— matches after collapsing whitespace; the raw text
                            does not. Reported separately because it is almost
                            always a stray double space, and because we must
                            NOT auto-normalize (§B-3: 원문 그대로가 원칙).

    Each segment is checked independently: a span made of two segments that are
    each substrings is valid even though their concatenation is not. That is
    the whole point of 변경 6 — "locally advanced" + "Stage III" no longer
    needs an override.
    """
    text = criterion_text or ""
    collapsed_text = _collapse(text)
    out: list[dict] = []
    for i, sub in enumerate(sub_criteria or []):
        child_id = sub.get("child_id") or chr(ord("a") + i)
        segments = normalize_text_span(sub.get("text_span"))
        if not segments:
            out.append({"child_id": child_id, "seg_index": 0,
                        "code": "EMPTY_SPAN", "span": "", "suggestion": ""})
            continue
        for j, span in enumerate(segments):
            if span in text:
                continue
            code = ("WHITESPACE_ONLY_DIFF" if _collapse(span) in collapsed_text
                    else "NOT_SUBSTRING")
            out.append({"child_id": child_id, "seg_index": j, "code": code,
                        "span": span, "suggestion": _nearest_span(text, span)})
    return out


def nearest_span(criterion_text: str, span: str) -> str:
    """Public wrapper for the UI's "did you mean" hint.

    Never applied automatically — the adjudicator has to accept it, which is
    what makes the correction auditable.
    """
    return _nearest_span(criterion_text, span)


def _nearest_span(criterion_text: str, span: str) -> str:
    """Best-guess contiguous region of the parent text for a bad span.

    A hint for the adjudicator only — never applied automatically.
    """
    text = criterion_text or ""
    if not text or not span:
        return ""
    sm = SequenceMatcher(None, text, span, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not blocks:
        return ""
    start = min(b.a for b in blocks)
    end = max(b.a + b.size for b in blocks)
    # expand to word boundaries so the hint is copy-pasteable
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[start:end]


# ──────────────────────────────────────────────────────────────────────
# Required-field enforcement (C-2)
# ──────────────────────────────────────────────────────────────────────

def validate_adjudication(
    *,
    splitting_decision: str | None,
    sub_criteria: list[dict],
    tier: int | None,
    rationale_short: str,
    rule_status: str | None,
    span_override: str | None,
    span_problems: list[dict],
    child_logic: str | None = None,
) -> list[str]:
    """Block saving until the adjudication record is usable as gold.

    `tier` and `rationale_short` are hard requirements because C-2's
    `rationale_short` is effectively the ONLY source for inducing guideline
    v1.3 — the annotators' own notes exist for ~7% of records and
    `sub_criteria[].rationale` for none at all (§9-1).

    `child_rationale` is required whenever the decision is a split: which
    items become few-shot examples is decided later (D-4), so "required only
    for few-shot candidates" is not enforceable at adjudication time
    (§0.3-🟡4).

    `child_logic` is checked in BOTH directions. Requiring it for splits
    without forbidding it elsewhere would leave a path for a stale value to
    ride along into a `nested_exception` / `none` gold record — the UI clears
    it, but the validator is what the record contract rests on.
    """
    errs: list[str] = []
    if tier not in TIERS:
        errs.append("tier는 필수 (0/1/2/3)")
    if not (rationale_short or "").strip():
        errs.append("rationale_short는 필수 — v1.2 귀납의 유일한 논거 소스 (§C-2)")
    if rule_status is not None and rule_status not in RULE_STATUSES:
        errs.append(f"rule_status가 유효하지 않음: {rule_status!r}")

    # guideline v1.2.1 변경 #2 / spec v1.2.3 변경 1 — 기본값 생략 규칙 폐지.
    if splitting_decision in SPLIT_DECISIONS:
        if not (child_logic or "").strip():
            errs.append(
                f"{splitting_decision}은 child_logic(AND/OR) 명시가 필수 — "
                f"생략 시 omit/default 의도를 구분할 수 없음 "
                f"(guideline v1.2.1 #2 / spec v1.2.3 변경 1)"
            )
    elif splitting_decision in NO_LOGIC_DECISIONS:
        if child_logic:
            errs.append(
                f"{splitting_decision}에는 child_logic을 부여하지 않습니다 "
                f"(현재 {child_logic!r})"
            )

    if splitting_decision and splitting_decision != "none":
        if not sub_criteria:
            errs.append(f"{splitting_decision}인데 sub_criteria가 없음")
        for i, sub in enumerate(sub_criteria):
            child_id = sub.get("child_id") or chr(ord("a") + i)
            if not (sub.get("rationale") or "").strip():
                errs.append(
                    f"child `{child_id}`의 rationale 필수 "
                    f"(분해 라벨은 무조건 필수 — §C-2-🟡4)"
                )

    # Tier 0 structural constraints, same rules A-2 applies to EHJ/DYK.
    if splitting_decision == "composite_split" and len(sub_criteria) < 2:
        errs.append("composite_split인데 sub_criteria < 2 (spec v1.2.2 위반)")

    if span_problems and not (span_override or "").strip():
        codes = ", ".join(sorted({p["code"] for p in span_problems}))
        errs.append(
            f"text_span이 원문과 불일치 ({codes}) — 세그먼트를 원문 그대로 "
            f"고치세요. 세그먼트 배열(spec v1.2.3 변경 6)이 있으면 가이드라인의 "
            f"모든 케이스가 부분문자열로 표현되므로, override는 예외가 아니라 "
            f"오류 경로입니다 (§B-3)"
        )
    return errs


# ──────────────────────────────────────────────────────────────────────
# Record construction (§7.4)
# ──────────────────────────────────────────────────────────────────────

def build_gold_record(
    *,
    criterion_id: str,
    gold: dict,
    blind_label: dict | None,
    tier: int,
    rationale_short: str,
    rule_id: str | None,
    rule_status: str | None,
    conflicting_rule: str | None,
    escalate_pi: bool,
    span_override: str | None,
    adjudicated_at: str,
    queue_stratum: str | None,
    compared: dict[str, Any] | None,
    needs_recursion: bool = False,
    recursion_note: str | None = None,
) -> dict:
    """Assemble one GOLD record: gold at top level, meta in `adjudication`.

    `blind_label` is kept verbatim so D-3 can measure where the adjudicator
    changed their mind once the peer labels were revealed (§B-2).

    `needs_recursion` marks a mixed-logic criterion — "A AND (B1 OR B2)" —
    where guideline v1.2.1 would require several levels but this pass records
    only the top level plus its direct fragments. The annotators labelled in a
    FLAT frame, so a top-level mismatch on such an item is a frame difference,
    not an error: the abstract's both-wrong counts exclude these. The flag is
    the exclusion list, which is why it has to be captured at judgement time
    rather than reconstructed afterwards (guide v2 §3-3).
    """
    record: dict[str, Any] = {"criterion_id": criterion_id}
    # Top level = the gold label itself. Order mirrors the annotator envelopes.
    record["splitting_decision"] = gold.get("splitting_decision")
    if gold.get("child_logic") is not None:
        record["child_logic"] = gold["child_logic"]
    if gold.get("cohort_scope"):
        record["cohort_scope"] = gold["cohort_scope"]
    record["sub_criteria"] = gold.get("sub_criteria") or []
    if gold.get("confidence"):
        record["confidence"] = gold["confidence"]
    if (gold.get("notes") or "").strip():
        record["notes"] = gold["notes"].strip()

    if blind_label:
        record["blind_label"] = blind_label

    adj: dict[str, Any] = {
        "tier": tier,
        "rationale_short": rationale_short.strip(),
        "rule_id": (rule_id or None) and rule_id.strip() or None,
        "rule_status": rule_status or None,
        "escalate_pi": bool(escalate_pi),
        "span_override": (span_override or "").strip() or None,
        "adjudicated_at": adjudicated_at,
    }
    if conflicting_rule and conflicting_rule.strip():
        adj["conflicting_rule"] = conflicting_rule.strip()
    if needs_recursion:
        adj["needs_recursion"] = True
        if (recursion_note or "").strip():
            adj["recursion_note"] = recursion_note.strip()
    if queue_stratum:
        adj["queue_stratum"] = queue_stratum
    if compared:
        adj["compared"] = compared
    record["adjudication"] = adj
    return record


def build_gap_ticket(
    *,
    criterion_id: str,
    reason: str,
    blind_label: dict | None,
    compared: dict[str, Any] | None,
    escalate_pi: bool,
    note: str | None,
    queue_stratum: str | None,
    adjudicated_at: str,
    needs_recursion: bool = False,
    recursion_note: str | None = None,
) -> dict:
    """A tier-3 item. Deliberately NOT a gold record.

    Carries `tier` and `blind_label` (§0.4-⚪5): tier-3 items are the
    intrinsically hard ones, so dropping the adjudicator's blind opinion would
    remove the most informative sample from D-3's blind≠gold analysis.
    """
    ticket: dict[str, Any] = {
        "criterion_id": criterion_id,
        "tier": GAP_TIER,
        "reason": reason.strip(),
        "escalate_pi": bool(escalate_pi),
        "adjudicated_at": adjudicated_at,
    }
    if blind_label:
        ticket["blind_label"] = blind_label
    if compared:
        ticket.update(compared)
    if queue_stratum:
        ticket["queue_stratum"] = queue_stratum
    if needs_recursion:
        # A tier-3 item can also be a mixed-logic one; the exclusion list has to
        # cover gap tickets too or the flag stops being a complete index.
        ticket["needs_recursion"] = True
        if (recursion_note or "").strip():
            ticket["recursion_note"] = recursion_note.strip()
    if note and note.strip():
        ticket["note"] = note.strip()
    return ticket


def merge_gap_tickets(existing: Any, new_tickets: list[dict]) -> list[dict]:
    """Upsert tickets by criterion_id, preserving the order first seen."""
    out: list[dict] = []
    if isinstance(existing, list):
        out = [t for t in existing if isinstance(t, dict)]
    elif isinstance(existing, dict) and isinstance(existing.get("tickets"), list):
        out = [t for t in existing["tickets"] if isinstance(t, dict)]

    by_id = {t.get("criterion_id"): i for i, t in enumerate(out)}
    for t in new_tickets:
        cid = t.get("criterion_id")
        if cid in by_id:
            out[by_id[cid]] = t
        else:
            by_id[cid] = len(out)
            out.append(t)
    return out


def build_gold_envelope(
    *,
    trial_id: str,
    stage: int,
    annotator: str,
    records: list[dict],
    created_at: str,
    committed: bool,
) -> dict:
    """GOLD envelope in the SAME shape annotator envelopes use.

    `source="annotator"` + `committed=True` is what makes `compute_iaa.py`
    pick GOLD up as an actor automatically (§9-3) — it is not a lie about
    provenance so much as the discovery contract; `annotator: "GOLD"` is what
    distinguishes it in the report.
    """
    env: dict[str, Any] = {
        "trial_id": trial_id,
        "stage": stage,
        "source": "annotator",
        "annotator": annotator,
        "created_at": created_at,
        "records": records,
    }
    if committed:
        env["committed"] = True
        env["committed_at"] = created_at
    return env


def peer_summary(record: dict | None) -> dict[str, Any]:
    """Compact view of one peer's label, for the `compared` block and the UI."""
    if not record:
        return {}
    return {
        "splitting_decision": record.get("splitting_decision"),
        "child_logic": record.get("child_logic"),
        "n_children": len(record.get("sub_criteria") or []),
        "notes": record.get("notes") or "",
    }
