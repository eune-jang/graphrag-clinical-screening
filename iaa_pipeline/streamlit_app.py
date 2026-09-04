"""Streamlit UI for the IAA annotation workflow.

Stage-aware design with explicit blinding guarantees:

    | Stage | Mode         | Annotator sees LLM? | IAA tab? |
    |-------|--------------|---------------------|----------|
    | 1, 2  | from_scratch | NO                  | only after commit |
    | 3-5   | llm_assisted | YES                 | always (LLM-assisted) |

The split is enforced at the function-signature level: from-scratch render
functions do not accept `llm_record` parameters, so any future code that
tries to leak the LLM into a from-scratch form will fail at the call site.

See `iaa_pipeline_spec/audit_streamlit_v1.md` for the leaks this design
addresses and the methodological rationale.

Run with:
    pip install -e ".[iaa]"
    streamlit run iaa_pipeline/streamlit_app.py

Workspace layout (per trial, per stage):
    {workspace}/{trial_id}/stage{N}/
        input.json                Stage N input — required
        llm_output.json           LLM Stage N output — used only in llm_assisted mode
        annotator_{id}.json       per-annotator envelope (this annotator's only)
        round{R}/                 committed envelopes for one IAA round
            {ID}_{trial}_stage{N}_committed.json
            gap_tickets.json      tier-3 adjudication items (not an envelope)

Adjudication (role = "adjudicator") reuses the same envelope I/O and the same
blinding architecture, with peers (EHJ/DYK) in the position the LLM occupies
for annotation: a blind first pass, then a revealed second pass. See
`iaa_pipeline_spec/adjudication_handover.md` §B.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import streamlit as st  # type: ignore

# Make the project root importable so we can use iaa_pipeline.*
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402
from iaa_pipeline.stage_schemas import (  # noqa: E402
    SPLITTING_DECISIONS,
    CHILD_LOGIC,
    validate_stage1_record,
    validate_envelope,
)
from iaa_pipeline.adjudication import (  # noqa: E402
    RULE_STATUSES,
    SPLIT_DECISIONS,
    TIER_LABELS,
    TIERS,
    build_gap_ticket,
    build_gold_envelope,
    build_gold_record,
    committed_envelope_name,
    envelope_dir,
    gap_tickets_path,
    load_queue,
    merge_gap_tickets,
    nearest_span,
    normalize_text_span,
    peer_summary,
    queue_index,
    span_violations,
    validate_adjudication,
)

# ──────────────────────────────────────────────────────────────────────
# Mode / Phase machinery
# ──────────────────────────────────────────────────────────────────────

Mode = Literal["from_scratch", "llm_assisted"]
Phase = Literal["phase_1_annotate", "phase_2_review"]
Role = Literal["annotator", "adjudicator"]

# The adjudicator writes under this actor id. It lands in the same round folder
# as EHJ/DYK so compute_iaa.py's single-directory discovery yields E-D/E-G/D-G
# (handover §7.4-🔴1).
GOLD_ACTOR = "GOLD"
DEFAULT_QUEUE_PATH = str(_PROJECT_ROOT / "results" / "adjudication"
                         / "adjudication_queue.csv")

STAGE_MODE: dict[int, Mode] = {
    1: "from_scratch",   # Splitting
    2: "from_scratch",   # Category / Relation
    3: "llm_assisted",   # Preferred name
    4: "llm_assisted",   # Constraints
    5: "llm_assisted",   # Alternative
}

SPLITTING_OPTIONS = sorted(SPLITTING_DECISIONS)
CHILD_LOGIC_OPTIONS = ["(unset)"] + sorted(CHILD_LOGIC)
DEFAULT_WORKSPACE = str(_PROJECT_ROOT / "iaa_workspace")


# ──────────────────────────────────────────────────────────────────────
# Pure helpers (unit-testable without streamlit)
# ──────────────────────────────────────────────────────────────────────

def build_form_seed(
    *,
    mode: Mode,
    existing_record: dict | None,
    llm_record: dict | None,
) -> dict:
    """The single chokepoint through which form default values are derived.

    In `from_scratch` mode, the LLM record is **never** consulted, even if
    provided. This is the blinding guarantee — every default in the form
    flows from the annotator's own prior work (or empty).

    In `llm_assisted` mode (Stages 3-5), the LLM record is the fallback
    when the annotator has no prior work. This is appropriate because the
    annotator's task in those stages is to correct LLM output, not produce
    an independent baseline.
    """
    if mode == "from_scratch":
        return dict(existing_record) if existing_record else {}
    if mode == "llm_assisted":
        if existing_record:
            return dict(existing_record)
        if llm_record:
            return dict(llm_record)
        return {}
    raise ValueError(f"unknown mode: {mode!r}")


def build_tab_spec(
    *,
    mode: Mode,
    phase: Phase,
    annotator_committed: bool,
) -> list[str]:
    """Decide which tabs to render based on mode + phase + commit status.

    - LLM Output tab is appended only in llm_assisted mode (covers leak A3).
    - IAA tab is appended only after the current annotator has committed
      AND the phase is post-commit review (covers leak A5).
    - Annotate and Upload are always present.
    """
    tabs = ["📝 Annotate"]
    if mode == "llm_assisted":
        tabs.append("🤖 LLM Output")
    if phase == "phase_2_review" and annotator_committed:
        tabs.append("📊 IAA")
    tabs.append("⬆️ Upload")
    return tabs


def build_adjudication_tab_spec(*, blind: bool) -> list[str]:
    """Tab list for the adjudicator.

    The peer tab is appended only when blind is OFF — the same gating shape as
    the LLM tab in `build_tab_spec` (audit leak A3), applied to the peer labels
    the adjudicator must not see during the first pass (handover §B-2).
    """
    tabs = ["⚖️ Adjudicate"]
    if not blind:
        tabs.append("👥 Peer labels")
    tabs.append("📊 IAA")
    tabs.append("⬆️ GOLD Upload")
    return tabs


def is_blind_pass_record(record: object) -> bool:
    """True iff `record` was last written by the blind (pass 1) adjudication.

    A record with no `adjudication.pass` is treated as NOT blind: unknown
    provenance falls to the conservative side, where it cannot seed a blind
    form.
    """
    if not isinstance(record, dict):
        return False
    return (record.get("adjudication") or {}).get("pass") == "blind"


def build_adjudication_seed(
    *,
    blind: bool,
    existing_gold: dict | None,
    blind_label: dict | None,
) -> dict:
    """Form defaults for the adjudication form — the single chokepoint.

    Peer records are NOT a parameter here, which is the structural guarantee
    that no EHJ/DYK value can seed an adjudication default (the adjudication
    analogue of audit leaks A1/A7).

    In blind mode the seed is the adjudicator's own blind-pass work only. A
    record whose `adjudication.pass` is `"blind"` *is* that work, so it seeds
    in FULL: `blind_label` is a decision-only snapshot kept for D-3 and never
    carried the per-child `rationale`/`cohort_scope`, the record-level
    `cohort_scope`, `confidence` or `notes` — seeding a blind re-open from it
    alone blanks all of those on screen, and the next save writes the blanks
    back over the stored gold. A `"revealed"` record is peer-influenced and
    must not leak back into a blind pass, so it still falls through to the
    snapshot.
    """
    if blind:
        if is_blind_pass_record(existing_gold):
            return dict(existing_gold)  # type: ignore[arg-type]
        return dict(blind_label) if blind_label else {}
    if existing_gold:
        return dict(existing_gold)
    return dict(blind_label) if blind_label else {}


def envelope_is_committed(envelope: object) -> bool:
    """An envelope is committed iff it carries the explicit flag.

    The isinstance check is load-bearing, not defensive noise: the round
    folder also holds `gap_tickets.json`, whose top level is a JSON ARRAY.
    Anything scanning the folder will hand that list in here.
    """
    return isinstance(envelope, dict) and envelope.get("committed") is True


def parse_adjudication_upload(raw: bytes) -> dict[str, dict[str, list[dict]]]:
    """Parse a trial GOLD envelope or the combined adjudication JSONL export.

    The return shape is ``{trial_id: {"gold": [...], "gaps": [...]}}``.
    Tier-3 gap tickets stay separate by construction, so importing a combined
    publication export cannot accidentally turn a gap into a GOLD label.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"UTF-8 파일이 아닙니다: {exc}") from exc
    if not text.strip():
        raise ValueError("빈 파일입니다.")

    parsed: list[Any]
    try:
        parsed = [json.loads(text)]
    except json.JSONDecodeError:
        parsed = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL {line_no}번 줄을 파싱할 수 없습니다: {exc}") from exc

    result: dict[str, dict[str, list[dict]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError("최상위 JSON은 object여야 합니다.")

        # Native per-trial committed GOLD envelope.
        if "records" in item:
            if item.get("annotator") != GOLD_ACTOR or item.get("stage") != 1:
                raise ValueError("Stage 1 GOLD envelope(annotator='GOLD')만 업로드할 수 있습니다.")
            trial_id = item.get("trial_id")
            records = item.get("records")
            if not trial_id or not isinstance(records, list):
                raise ValueError("GOLD envelope에 trial_id 또는 records list가 없습니다.")
            bucket = result.setdefault(str(trial_id), {"gold": [], "gaps": []})
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError(f"{trial_id}: GOLD record가 object가 아닙니다.")
                bucket["gold"].append(record)
            continue

        # Combined JSONL export: one wrapped gold/gap record per line.
        record_type = item.get("record_type")
        trial_id = item.get("trial_id")
        record = item.get("record")
        if record_type not in ("gold", "gap_ticket") or not trial_id or not isinstance(record, dict):
            raise ValueError("JSONL은 record_type, trial_id, record object를 포함해야 합니다.")
        if item.get("stage", 1) != 1:
            raise ValueError("Stage 1 adjudication 파일만 업로드할 수 있습니다.")
        bucket = result.setdefault(str(trial_id), {"gold": [], "gaps": []})
        bucket["gold" if record_type == "gold" else "gaps"].append(record)

    for trial_id, groups in result.items():
        for kind, records in groups.items():
            for record in records:
                cid = record.get("criterion_id")
                if not cid:
                    raise ValueError(f"{trial_id}: {kind} record에 criterion_id가 없습니다.")
                key = (trial_id, kind, str(cid))
                if key in seen:
                    raise ValueError(f"중복 criterion_id: {trial_id} / {kind} / {cid}")
                seen.add(key)
        overlap = ({r["criterion_id"] for r in groups["gold"]}
                   & {r["criterion_id"] for r in groups["gaps"]})
        if overlap:
            raise ValueError(f"{trial_id}: GOLD와 gap에 동시에 있는 criterion_id: {sorted(overlap)}")
    return result


# ──────────────────────────────────────────────────────────────────────
# I/O helpers
# ──────────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse {path.name}: {e}")
        return None


def save_envelope(envelope: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_trials(workspace: Path, *, stage: int,
                round_num: int | None = None) -> list[str]:
    """Trials with a Stage N input file.

    With `round_num`, restrict to trials that actually have that round folder.
    The workspace holds 31 trials but only the 8 IAA trials have round1/round2,
    so without this filter the adjudicator's dropdown is mostly dead ends.
    """
    if not workspace.exists():
        return []
    out = []
    for d in sorted(workspace.iterdir()):
        if not d.is_dir():
            continue
        stage_dir = d / f"stage{stage}"
        if not (stage_dir / "input.json").exists():
            continue
        if round_num is not None and not (stage_dir / f"round{round_num}").is_dir():
            continue
        out.append(d.name)
    return out


def list_committed_annotator_envelopes(stage_dir: Path) -> list[Path]:
    """Return committed annotator envelopes in stage_dir, identified by
    CONTENT (committed + source=="annotator") rather than by filename.

    This accepts files dropped in with their hosted-app download name
    (e.g. `EHJ_NCT01295827_stage1_committed.json`) just as well as the local
    `annotator_{id}.json` — no renaming required. `input.json`,
    `llm_output.json` and `gap_tickets.json` are skipped (none of them are
    annotator envelopes; the last one is a JSON array, not even a dict).

    Used by the IAA dashboard. In Phase 1 (annotation), this list is
    intentionally not surfaced anywhere except the IAA tab — and the IAA
    tab itself is hidden until the current annotator commits.
    """
    if not stage_dir.exists():
        return []
    paths = []
    for p in sorted(stage_dir.glob("*.json")):
        if p.name in ("input.json", "llm_output.json", "gap_tickets.json"):
            continue
        env = load_json(p)
        if envelope_is_committed(env) and env.get("source") == "annotator":
            paths.append(p)
    return paths


def annotator_envelope_path(stage_dir: Path, annotator: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in annotator).strip("_")
    return stage_dir / f"annotator_{safe or 'unknown'}.json"


def find_actor_envelope(env_dir: Path, actor: str) -> Path | None:
    """Locate an existing envelope written by `actor`, identified by CONTENT.

    The round folders were assembled by hand and hold hosted-app download
    names (`EHJ_NCT..._committed.json`), so matching on filename would miss
    them. Mirrors `compute_iaa.discover_sources` except that drafts count too.
    """
    if not env_dir.exists():
        return None
    for p in sorted(env_dir.glob("*.json")):
        if p.name in ("input.json", "llm_output.json", "gap_tickets.json"):
            continue
        env = load_json(p)
        if isinstance(env, dict) and env.get("annotator") == actor:
            return p
    return None


def resolve_envelope_path(env_dir: Path, actor: str, *, trial_id: str,
                          stage: int) -> Path:
    """Where to write `actor`'s envelope: reuse its file if one exists.

    Without the reuse step a second save would create a duplicate file for the
    same actor in the same directory, and `discover_sources` would keep only
    whichever sorted last ("last write wins on duplicate annotator id").
    """
    found = find_actor_envelope(env_dir, actor)
    if found is not None:
        return found
    return env_dir / committed_envelope_name(actor, trial_id, stage)


def load_peer_records(env_dir: Path, peers: list[str]) -> dict[str, dict[str, dict]]:
    """{actor: {criterion_id: record}} for the peer annotators.

    Callers MUST NOT invoke this while blind — the blind path skips the read
    entirely rather than loading and hiding, because Streamlit session state
    would otherwise keep the data alive across a blind/revealed toggle (same
    reasoning as the `llm_envelope` read in `main`).
    """
    out: dict[str, dict[str, dict]] = {}
    for actor in peers:
        p = find_actor_envelope(env_dir, actor)
        if p is None:
            continue
        env = load_json(p) or {}
        out[actor] = {r.get("criterion_id"): r for r in env.get("records", [])
                      if r.get("criterion_id")}
    return out


def discover_peer_actors(env_dir: Path, *, exclude: str) -> list[str]:
    """Committed actor ids in a round folder, minus `exclude` (i.e. GOLD)."""
    actors: list[str] = []
    if not env_dir.exists():
        return actors
    for p in sorted(env_dir.glob("*.json")):
        if p.name in ("input.json", "llm_output.json", "gap_tickets.json"):
            continue
        env = load_json(p)
        if not isinstance(env, dict):
            continue
        actor = env.get("annotator")
        if (env.get("source") == "annotator" and env.get("committed") is True
                and actor and actor != exclude and actor not in actors):
            actors.append(actor)
    return actors


# ──────────────────────────────────────────────────────────────────────
# Form rendering — TWO functions, one per mode
# ──────────────────────────────────────────────────────────────────────
#
# The blind variant does NOT accept `llm_record`. This is the
# function-signature-level guarantee that no LLM data can leak into the
# Stage 1/2 annotation form. If a future maintainer tries to pass LLM
# data here, Python will raise TypeError.
# ──────────────────────────────────────────────────────────────────────

def render_criterion_form_blind(
    criterion: dict,
    *,
    existing_record: dict | None,
    cohort_options: list[str],
    key_prefix: str,
) -> dict:
    """from_scratch mode form. Sees only the annotator's own prior work."""
    seed = build_form_seed(
        mode="from_scratch",
        existing_record=existing_record,
        llm_record=None,
    )
    return _render_form_with_seed(
        criterion,
        seed=seed,
        cohort_options=cohort_options,
        key_prefix=key_prefix,
        show_llm_suggestion=None,
    )


def render_criterion_form_assisted(
    criterion: dict,
    *,
    existing_record: dict | None,
    llm_record: dict | None,
    cohort_options: list[str],
    key_prefix: str,
) -> dict:
    """llm_assisted mode form. Stages 3-5 only."""
    seed = build_form_seed(
        mode="llm_assisted",
        existing_record=existing_record,
        llm_record=llm_record,
    )
    return _render_form_with_seed(
        criterion,
        seed=seed,
        cohort_options=cohort_options,
        key_prefix=key_prefix,
        show_llm_suggestion=llm_record,
    )


def _render_form_with_seed(
    criterion: dict,
    *,
    seed: dict,
    cohort_options: list[str],
    key_prefix: str,
    show_llm_suggestion: dict | None,
) -> dict:
    """Internal: render widgets given a fully-resolved seed.

    `show_llm_suggestion` controls whether to render the LLM expander.
    Callers in blind mode must pass `None`. The blind render function
    above does this; never call this internal function directly from
    a from-scratch code path with a non-None value.
    """
    crit_id = criterion["criterion_id"]
    crit_type = criterion.get("type", "?")
    root_text = criterion.get("text", "") or ""
    st.markdown(f"### `{crit_id}` _({crit_type})_")
    # Copy-safe rendering. `st.code` does not run the text through the markdown
    # renderer, so a drag-copy returns the source bytes unchanged and gets a
    # built-in copy button. Copying out of `st.markdown` can silently
    # substitute characters (non-breaking space, µ vs μ, en/em dashes, runs of
    # whitespace collapsed) and every one of those turns a correctly-selected
    # span into a NOT_SUBSTRING violation — i.e. it manufactures exactly the
    # `span_override` uses we want to be rare.
    st.code(root_text, language=None, wrap_lines=True)

    if show_llm_suggestion is not None:
        with st.expander("🤖 LLM suggestion", expanded=False):
            st.json({k: v for k, v in show_llm_suggestion.items() if not k.startswith("_")})

    col1, col2 = st.columns(2)
    with col1:
        decision = st.selectbox(
            "splitting_decision",
            SPLITTING_OPTIONS,
            index=_safe_index(SPLITTING_OPTIONS, seed.get("splitting_decision"),
                              default=SPLITTING_OPTIONS.index("none")),
            key=f"{key_prefix}_decision",
        )
    with col2:
        # guideline v1.2.1 변경 #2 / spec v1.2.3 변경 1: the default-omission
        # rule was retired, and macro_aggregate can be OR ("at least one of the
        # following"), so BOTH split decisions carry an explicit child_logic.
        if decision in SPLIT_DECISIONS:
            cl_value = seed.get("child_logic") or "(unset)"
            child_logic_choice = st.selectbox(
                "child_logic *",
                CHILD_LOGIC_OPTIONS,
                index=_safe_index(CHILD_LOGIC_OPTIONS, cl_value, default=0),
                key=f"{key_prefix}_child_logic",
            )
            child_logic_val: str | None = (
                None if child_logic_choice == "(unset)" else child_logic_choice
            )
            if child_logic_val is None:
                st.caption("⚠️ AND/OR 명시 필수 — 표면 접속사가 아니라 의미로 판정")
        else:
            child_logic_val = None
            st.markdown("_child_logic은 composite_split · macro_aggregate에만 부여_")

    has_children = decision in ("composite_split", "macro_aggregate", "nested_exception")

    # cohort_scope placement:
    #   - split decisions  → per-child (rendered inside each sub-criterion)
    #   - non-split ("none") → a single record-level multiselect, since there
    #     are no children to attach the scope to.
    # Backward compatibility: drafts saved before cohort_scope became per-child
    # carry a single record-level `cohort_scope`. For split criteria we reuse
    # that legacy value as the default for EVERY child (see `legacy_scope`).
    record_cohort_scope: list[str] | None = None
    if cohort_options and not has_children:
        cohort_default = seed.get("cohort_scope") or []
        record_cohort_scope = st.multiselect(
            "cohort_scope (leave empty = applies to all cohorts)",
            cohort_options,
            default=[c for c in cohort_default if c in cohort_options],
            key=f"{key_prefix}_cohorts",
        )

    sub_criteria: list[dict] = []
    if has_children:
        st.caption(
            "Sub-criteria — child_id는 자동 배정 (a, b, c, ...). "
            "text_span은 **원문의 연속 구간 세그먼트 배열**입니다 "
            "(spec v1.2.3 변경 6): 떨어져 있는 표현은 이어붙이지 말고 "
            "세그먼트를 늘려 나눠 담으세요. cohort_scope는 child별로 지정합니다."
        )
        seed_subs = seed.get("sub_criteria") or []
        # Legacy record-level scope: default for any child lacking its own
        # (covers drafts created before cohort_scope moved per-child).
        legacy_scope = seed.get("cohort_scope") or []
        n_subs = st.number_input(
            "Number of sub-criteria",
            min_value=1, max_value=20,
            value=max(1, len(seed_subs)),
            key=f"{key_prefix}_n_subs",
        )
        for i in range(int(n_subs)):
            child_id = chr(ord("a") + i)
            seed_sub = seed_subs[i] if i < len(seed_subs) else {}
            # normalize_text_span accepts the legacy string form, so drafts and
            # round1/2 envelopes saved before 변경 6 still seed the form.
            seed_segments = normalize_text_span(seed_sub.get("text_span"))
            default_rat = seed_sub.get("rationale", "")
            # per-child scope: the child's own value if present, else the
            # legacy record-level value (applied to all children).
            child_scope_seed = seed_sub.get("cohort_scope")
            if child_scope_seed is None:
                child_scope_seed = legacy_scope
            with st.container(border=True):
                st.markdown(f"**child `{child_id}`**")
                n_segs = st.number_input(
                    "세그먼트 수", min_value=1, max_value=8,
                    value=max(1, len(seed_segments)),
                    key=f"{key_prefix}_sub_{i}_nsegs",
                    help='떨어진 표현은 별도 세그먼트로. 예: '
                         '["locally advanced", "Stage III"]',
                )
                segments: list[str] = []
                for j in range(int(n_segs)):
                    seg_key = f"{key_prefix}_sub_{i}_seg_{j}"
                    default_seg = seed_segments[j] if j < len(seed_segments) else ""
                    seg = st.text_input(
                        f"text_span[{j}]", value=default_seg, key=seg_key,
                    ).strip()
                    if seg:
                        segments.append(seg)
                        _render_segment_check(root_text, seg, seg_key=seg_key)
                rationale = st.text_input("rationale (optional)", value=default_rat,
                                          key=f"{key_prefix}_sub_{i}_rat")
                if cohort_options:
                    child_scope = st.multiselect(
                        "cohort_scope (leave empty = applies to all cohorts)",
                        cohort_options,
                        default=[c for c in child_scope_seed if c in cohort_options],
                        key=f"{key_prefix}_sub_{i}_cohorts",
                    )
                else:
                    child_scope = None
                # Always an array, even for one segment (spec v1.2.3 변경 6).
                entry: dict[str, Any] = {"child_id": child_id, "text_span": segments}
                if rationale.strip():
                    entry["rationale"] = rationale.strip()
                if child_scope:
                    entry["cohort_scope"] = child_scope
                sub_criteria.append(entry)

    confidence = st.select_slider(
        "confidence", options=["low", "medium", "high"],
        value=seed.get("confidence", "medium"),
        key=f"{key_prefix}_confidence",
    )
    notes = st.text_area("notes (optional)", value=seed.get("notes", ""),
                         key=f"{key_prefix}_notes", height=68)

    record: dict[str, Any] = {
        "criterion_id": crit_id,
        "splitting_decision": decision,
        "sub_criteria": sub_criteria,
    }
    if child_logic_val is not None:
        record["child_logic"] = child_logic_val
    if record_cohort_scope:
        record["cohort_scope"] = record_cohort_scope
    if confidence:
        record["confidence"] = confidence
    if notes.strip():
        record["notes"] = notes.strip()
    return record


def _render_segment_check(root_text: str, segment: str, *, seg_key: str) -> None:
    """Live substring check for one segment, with one-click correction.

    Two things keep `span_override` an error path rather than a routine one:
    the copy-safe rendering above (so the segment usually matches to begin
    with) and this button (so a segment that drifted gets fixed in place
    instead of overridden). The candidate is never applied automatically —
    accepting it is the adjudicator's action, which keeps it auditable.

    The button uses `on_click` rather than assigning inside the `if` body:
    Streamlit refuses to mutate a widget's session_state entry after that
    widget has been instantiated in the same run, and callbacks fire at the
    start of the next run, before the widgets are built.
    """
    if not root_text or segment in root_text:
        return
    suggestion = nearest_span(root_text, segment)
    st.markdown(
        f"<span style='color:#c62828'>⚠️ 원문에 없는 문자열 — "
        f"세그먼트를 원문 그대로 잘라내세요.</span>",
        unsafe_allow_html=True,
    )
    if not suggestion:
        return
    cols = st.columns([5, 2])
    with cols[0]:
        st.code(suggestion, language=None, wrap_lines=True)
    with cols[1]:
        def _adopt(k: str = seg_key, v: str = suggestion) -> None:
            st.session_state[k] = v
        st.button("↩︎ 후보로 교체", key=f"{seg_key}_fix", on_click=_adopt,
                  use_container_width=True,
                  help="가장 가까운 원문 구간으로 이 세그먼트를 교체합니다.")


def _safe_index(options: list[str], value: Any, default: int) -> int:
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return default


# ──────────────────────────────────────────────────────────────────────
# Adjudication forms — TWO functions, one per pass
# ──────────────────────────────────────────────────────────────────────
#
# The blind variant does NOT accept `peer_records`. Same
# function-signature-level guarantee the annotation forms use for `llm_record`:
# the first adjudication pass must be an independent third opinion, because
# the case this whole exercise hunts for is "both annotators were wrong"
# (handover §B-2). If a future maintainer tries to pass peer labels into the
# blind form, Python raises TypeError.
# ──────────────────────────────────────────────────────────────────────

def render_adjudication_form_blind(
    criterion: dict,
    *,
    existing_gold: dict | None,
    blind_label: dict | None,
    cohort_options: list[str],
    key_prefix: str,
) -> dict:
    """Pass 1. Sees the criterion text and the adjudicator's own prior blind work.

    `existing_gold` is that prior work and nothing else: `build_adjudication_seed`
    drops it unless `adjudication.pass == "blind"`, so handing a revealed-pass
    record in here still cannot surface a peer-influenced edit. It is what
    makes a re-opened blind item show the rationale/notes/scope the
    adjudicator already wrote instead of an empty form.
    """
    seed = build_adjudication_seed(
        blind=True, existing_gold=existing_gold, blind_label=blind_label,
    )
    return _render_form_with_seed(
        criterion,
        seed=seed,
        cohort_options=cohort_options,
        key_prefix=key_prefix,
        show_llm_suggestion=None,
    )


def render_adjudication_form_open(
    criterion: dict,
    *,
    existing_gold: dict | None,
    blind_label: dict | None,
    peer_records: dict[str, dict],
    cohort_options: list[str],
    key_prefix: str,
) -> dict:
    """Pass 2. Peer labels and notes are revealed, then gold is confirmed."""
    seed = build_adjudication_seed(
        blind=False, existing_gold=existing_gold, blind_label=blind_label,
    )
    _render_peer_panel(peer_records, blind_label=blind_label)
    return _render_form_with_seed(
        criterion,
        seed=seed,
        cohort_options=cohort_options,
        key_prefix=key_prefix,
        show_llm_suggestion=None,
    )


def _render_peer_panel(peer_records: dict[str, dict], *,
                       blind_label: dict | None) -> None:
    """C-1: show each peer's label and their note VERBATIM.

    Notes exist for only ~7% of records (§9-1), so "(no note)" is the normal
    case and is stated explicitly rather than left blank. Notes are never
    summarised or rewritten — the wording is the evidence.
    """
    if blind_label:
        st.caption(
            f"🔒 Your blind label: `{blind_label.get('splitting_decision')}` · "
            f"{len(blind_label.get('sub_criteria') or [])} child(ren)"
        )
    if not peer_records:
        st.info("No peer envelopes found in this round folder.")
        return
    cols = st.columns(len(peer_records))
    for col, (actor, rec) in zip(cols, sorted(peer_records.items())):
        with col:
            if rec is None:
                st.markdown(f"**{actor}** — _no record_")
                continue
            s = peer_summary(rec)
            st.markdown(
                f"**{actor}** · `{s['splitting_decision']}`"
                + (f" · child_logic `{s['child_logic']}`" if s.get("child_logic") else "")
                + f" · {s['n_children']} child(ren)"
            )
            note = s.get("notes") or ""
            if note.strip():
                st.markdown(f"> {note}")
            else:
                st.caption("(no note)")
            # Peer envelopes are round 1/2, i.e. still the pre-변경6 string
            # form; normalize so both storage shapes render identically.
            spans = [normalize_text_span(x.get("text_span"))
                     for x in (rec.get("sub_criteria") or [])]
            if spans:
                with st.expander(f"{actor} spans", expanded=False):
                    for i, segs in enumerate(spans):
                        st.markdown(f"`{chr(ord('a') + i)}` " + " ⋯ ".join(segs))


def render_adjudication_meta(
    *,
    key_prefix: str,
    existing_adj: dict | None,
    span_problems: list[dict],
) -> dict:
    """C-2 fields — the actual deliverable of this exercise.

    No `rule_id` autocomplete on purpose: suggesting a rule pushes the
    adjudicator to force-fit an existing one and hides the `new` / `gap`
    findings that guideline v1.2 has to be induced from (§C-2 주의).
    """
    seed = existing_adj or {}
    st.markdown("##### 판정 기록 (C-2)")
    c1, c2 = st.columns([2, 3])
    with c1:
        tier = st.selectbox(
            "tier *", TIERS,
            index=_safe_index(list(TIERS), seed.get("tier"), default=2),
            format_func=lambda t: TIER_LABELS[t],
            key=f"{key_prefix}_tier",
        )
    with c2:
        rationale_short = st.text_input(
            "rationale_short *  — 왜 그렇게 정했는가 (한 줄)",
            value=seed.get("rationale_short", ""),
            key=f"{key_prefix}_rationale",
        )

    c3, c4, c5 = st.columns([2, 2, 1])
    with c3:
        rule_id = st.text_input(
            "rule_id (기존 규칙으로 설명 안 되면 공란)",
            value=seed.get("rule_id") or "",
            key=f"{key_prefix}_rule_id",
        )
    with c4:
        rs_options = ["(unset)"] + list(RULE_STATUSES)
        rule_status_choice = st.selectbox(
            "rule_status", rs_options,
            index=_safe_index(rs_options, seed.get("rule_status"), default=0),
            key=f"{key_prefix}_rule_status",
        )
        rule_status = None if rule_status_choice == "(unset)" else rule_status_choice
    with c5:
        escalate_pi = st.checkbox(
            "escalate PI", value=bool(seed.get("escalate_pi")),
            key=f"{key_prefix}_escalate",
        )

    conflicting_rule = ""
    if rule_status == "conflict":
        conflicting_rule = st.text_input(
            "conflicting_rule — 오답을 유도한 기존 규칙 (예외 조항 폐쇄의 직접 재료)",
            value=seed.get("conflicting_rule", ""),
            key=f"{key_prefix}_conflicting",
        )

    # 보류 플래그 (guide v2 §3-3). Mixed-logic criteria — "A AND (B1 OR B2)" —
    # would need several levels under guideline v1.2.1, but the annotators
    # laballed in a FLAT frame, so this pass records the top level plus its
    # direct fragments and defers the rest. Flagging is what builds the
    # exclusion list for the abstract's both-wrong counts; reconstructing it
    # after the fact is not possible once the judgement context is gone.
    needs_recursion = st.checkbox(
        "🔁 needs_recursion — 혼합 로직이라 하위 계층 판정을 보류함",
        value=bool(seed.get("needs_recursion")),
        key=f"{key_prefix}_needs_recursion",
        help='"A이고 그리고 (B1 또는 B2)" 유형. 최상위 라벨 + 직계 조각까지만 '
             "확정하고 켜두세요. 이 항목은 초록 오답 집계에서 제외되고 "
             "(라벨 차이가 아니라 표기 프레임 차이), 마감 후 계층 완성 대상이 됩니다.",
    )
    recursion_note = ""
    if needs_recursion:
        recursion_note = st.text_input(
            "recursion_note — 어떤 계층이 남았는지 한 줄",
            value=seed.get("recursion_note", ""),
            key=f"{key_prefix}_recursion_note",
        )

    span_override = ""
    if span_problems:
        # With text_span as a segment array (spec v1.2.3 변경 6), every case the
        # guideline used to treat as a deliberate exception is expressible as a
        # substring: 떨어진 표현 → separate segments, 공통 전제 → 상위 AND 계층
        # (v1.2.1에서 복제 폐지), 예외 조각 → 트리거부터의 연속 구간. So an
        # override here means a segment was cut wrong, not that the guideline
        # needed an escape.
        st.error(
            "**세그먼트가 원문과 일치하지 않습니다.** 세그먼트 배열에서는 "
            "가이드라인의 모든 케이스가 부분문자열로 표현되므로, override는 "
            "예외가 아니라 **잘못 잘랐다는 신호**입니다. 위 입력란의 "
            "`↩︎ 후보로 교체` 버튼으로 고치는 것이 정상 경로입니다."
        )
        for p in span_problems:
            st.markdown(f"- child `{p['child_id']}` seg[{p.get('seg_index', 0)}] "
                        f"— {p['code']}")
        span_override = st.text_input(
            "span_override 사유 — 고칠 수 없는 경우에만 (기록되며 few-shot에서 제외됩니다)",
            value=seed.get("span_override") or "",
            key=f"{key_prefix}_span_override",
        )

    return {
        "tier": tier,
        "rationale_short": rationale_short,
        "rule_id": rule_id,
        "rule_status": rule_status,
        "conflicting_rule": conflicting_rule,
        "escalate_pi": escalate_pi,
        "span_override": span_override,
        "needs_recursion": needs_recursion,
        "recursion_note": recursion_note,
    }


# ──────────────────────────────────────────────────────────────────────
# Page sections
# ──────────────────────────────────────────────────────────────────────

def section_annotate(
    *,
    mode: Mode,
    trial_input: dict,
    llm_envelope: dict | None,
    existing_envelope: dict | None,
    cohort_options: list[str],
    save_path: Path,
    annotator: str,
) -> None:
    """Annotate tab. Dispatches to blind or assisted render per mode.

    Note: `llm_envelope` is accepted at this layer for type uniformity, but
    is dropped on the floor when `mode == "from_scratch"` — see the
    `if mode == "from_scratch"` branch below. The data does not reach the
    render layer.
    """
    criteria = trial_input.get("criteria", [])
    existing_by_id = (
        {r.get("criterion_id"): r for r in (existing_envelope or {}).get("records", [])}
        if existing_envelope else {}
    )
    llm_by_id: dict[str, dict] = {}
    if mode == "llm_assisted":
        llm_by_id = (
            {r.get("criterion_id"): r for r in (llm_envelope or {}).get("records", [])}
            if llm_envelope else {}
        )

    committed = envelope_is_committed(existing_envelope)
    committed_at = (existing_envelope or {}).get("committed_at", "")

    head_cols = st.columns([3, 2])
    with head_cols[0]:
        st.markdown(
            f"**{len(criteria)} criteria** in `{trial_input.get('trial_id')}` · "
            f"annotator: `{annotator}` · mode: `{mode}` · "
            f"destination: `{save_path.name}`"
        )
    with head_cols[1]:
        if committed:
            st.success(f"🔒 Committed at {committed_at}")
        else:
            st.info("Not yet committed — IAA dashboard hidden until commit.")

    if not criteria:
        st.warning("Input file has no criteria.")
        return

    records: list[dict] = []
    validation_errors: list[tuple[str, list[str]]] = []
    for i, crit in enumerate(criteria):
        with st.container(border=True):
            existing_rec = existing_by_id.get(crit["criterion_id"])
            if mode == "from_scratch":
                rec = render_criterion_form_blind(
                    crit,
                    existing_record=existing_rec,
                    cohort_options=cohort_options,
                    key_prefix=f"crit_{i}",
                )
            else:
                rec = render_criterion_form_assisted(
                    crit,
                    existing_record=existing_rec,
                    llm_record=llm_by_id.get(crit["criterion_id"]),
                    cohort_options=cohort_options,
                    key_prefix=f"crit_{i}",
                )
            errs = validate_stage1_record(rec)
            if errs:
                validation_errors.append((crit["criterion_id"], errs))
                st.warning(" · ".join(errs))
            records.append(rec)

    st.divider()
    col_save, col_commit, col_status = st.columns([1, 1, 3])
    with col_save:
        save_clicked = st.button(
            "💾 Save (draft)",
            type="primary",
            use_container_width=True,
            disabled=committed,
            help="Save an in-progress envelope. You can keep editing.",
        )
    with col_commit:
        commit_clicked = st.button(
            "🔒 Commit (final)",
            use_container_width=True,
            disabled=committed,
            help="Lock this envelope. Required before the IAA tab unlocks. "
                 "Cannot be undone from the UI.",
        )
    with col_status:
        if validation_errors:
            st.error(f"{len(validation_errors)} record(s) have validation issues — fix before saving/committing.")
        elif committed:
            st.success("This envelope is committed. Open the 📊 IAA tab (Phase 2) to view metrics.")
        else:
            st.success("All records pass lightweight validation.")

    if save_clicked or commit_clicked:
        envelope: dict[str, Any] = {
            "trial_id": trial_input["trial_id"],
            "stage": trial_input.get("_stage", 1),
            "source": "annotator",
            "annotator": annotator,
            "created_at": _utc_now_iso(),
            "records": records,
        }
        if commit_clicked:
            if validation_errors:
                st.error("Cannot commit while validation errors are present.")
                return
            envelope["committed"] = True
            envelope["committed_at"] = _utc_now_iso()
        env_errs = validate_envelope(envelope)
        if env_errs:
            envelope["_validation_errors"] = env_errs
            st.warning(f"Envelope validation warnings: {env_errs}")
        save_envelope(envelope, save_path)
        if commit_clicked:
            st.success(f"🔒 Committed → {save_path}. Reload the page to access 📊 IAA tab.")
        else:
            st.success(f"💾 Draft saved → {save_path}")


def section_adjudicate(
    *,
    trial_input: dict,
    env_dir: Path,
    stage_dir: Path,
    round_num: int | None,
    blind: bool,
    queue: list[dict],
    cohort_options: list[str],
    peers: list[str],
    stage: int,
) -> None:
    """Adjudication tab (handover §B/§C).

    Two passes over the same form: blind first (independent third opinion),
    then revealed. `tier == 3` items are diverted to `gap_tickets.json` so the
    gold envelope holds only settled answers.
    """
    trial_id = trial_input["trial_id"]
    criteria = {c["criterion_id"]: c for c in trial_input.get("criteria", [])}
    q_by_id = queue_index(queue)

    gold_path = resolve_envelope_path(env_dir, GOLD_ACTOR,
                                      trial_id=trial_id, stage=stage)
    gold_env = load_json(gold_path) or {}
    gold_by_id = {r.get("criterion_id"): r for r in gold_env.get("records", [])
                  if r.get("criterion_id")}
    gap_path = gap_tickets_path(stage_dir, round_num)
    gap_existing = load_json(gap_path)
    if gap_existing is None and gap_path.exists():
        # a JSON array parses fine through load_json only if it is a dict;
        # read it directly so we never silently drop existing tickets.
        try:
            gap_existing = json.loads(gap_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            gap_existing = None
    gap_list = merge_gap_tickets(gap_existing, [])
    gap_by_id = {t.get("criterion_id"): t for t in gap_list}

    # Peer data is read ONLY when revealed. In blind mode we skip the read
    # entirely rather than load-and-hide (see load_peer_records docstring).
    peer_records_all: dict[str, dict[str, dict]] = {}
    if not blind:
        peer_records_all = load_peer_records(env_dir, peers)

    # ── worklist ─────────────────────────────────────────────────────
    if q_by_id:
        items = [cid for cid in q_by_id if cid in criteria]
        if not items:
            st.info(
                f"판정 큐에 `{trial_id}` 항목이 없습니다. "
                "다른 trial을 선택하거나 큐를 다시 생성하세요."
            )
            return
    else:
        items = sorted(criteria)
        st.caption(
            "판정 큐 파일이 없어 전체 criterion을 순서대로 보여줍니다. "
            "`python scripts/build_adjudication_queue.py --out results/adjudication` "
            "를 실행하면 우선순위 순서로 정렬됩니다."
        )

    done = sum(1 for cid in items if cid in gold_by_id or cid in gap_by_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("queue (this trial)", len(items))
    c2.metric("adjudicated", done)
    c3.metric("gap tickets", sum(1 for cid in items if cid in gap_by_id))
    c4.metric("pass", "blind" if blind else "revealed")
    st.progress(done / len(items) if items else 0.0)

    only_pending = st.checkbox("미판정 항목만 보기", value=False, key="adj_pending_only")
    view = [cid for cid in items
            if not (only_pending and (cid in gold_by_id or cid in gap_by_id))]
    if not view:
        st.success("이 trial의 큐 항목을 모두 판정했습니다.")
        return

    def _recursion_flagged(cid: str) -> bool:
        rec = gold_by_id.get(cid) or {}
        if (rec.get("adjudication") or {}).get("needs_recursion"):
            return True
        return bool((gap_by_id.get(cid) or {}).get("needs_recursion"))

    idx_labels = [
        f"{q_by_id.get(cid, {}).get('priority', '?')} · {cid}"
        f"{'  ✅' if cid in gold_by_id else ''}{'  🎫' if cid in gap_by_id else ''}"
        f"{'  🔁' if _recursion_flagged(cid) else ''}"
        for cid in view
    ]
    pick = st.selectbox("판정 항목", range(len(view)),
                        format_func=lambda i: idx_labels[i], key="adj_pick")
    cid = view[pick]
    crit = criteria[cid]
    qrow = q_by_id.get(cid, {})

    st.divider()
    if qrow:
        bits = [f"stratum **{qrow.get('stratum','?')}**"]
        if qrow.get("s1_kind"):
            bits.append(f"({qrow['s1_kind']})")
        if str(qrow.get("is_72_conflict") or "") in ("1", "True", "true"):
            bits.append("· ⚠️ §7.2 예외조항 충돌 — 최우선")
        if qrow.get("tier0_flag"):
            bits.append(f"· 🚩 Tier 0 위반: `{qrow['tier0_flag']}`")
        st.markdown(" ".join(bits))
        if qrow.get("risk_signals"):
            with st.expander("S2 위험 신호", expanded=False):
                st.code(qrow["risk_signals"], language=None)

    existing_gold = gold_by_id.get(cid)
    blind_label = (existing_gold or {}).get("blind_label")
    key_prefix = f"adj_{trial_id}_{cid}"

    if blind:
        st.info(
            "🔒 **1차 통과 (blind)** — EHJ/DYK 라벨을 보지 않고 독립 판정합니다. "
            "두 사람이 모두 틀린 경우를 발견하려면 제3의 독립 라벨이 먼저 있어야 합니다."
        )
        if existing_gold is not None and not is_blind_pass_record(existing_gold):
            st.warning(
                "⚠️ 이 항목은 **revealed 패스**에서 확정된 gold입니다. blind 폼은 "
                "peer 공개 이후의 편집을 되살리지 않으므로(되살리면 blind가 깨집니다) "
                "지금 저장하면 확정 gold를 blind 스냅샷 값으로 덮어씁니다. "
                "수정하려면 사이드바에서 🔒 Blind pass를 끄세요."
            )
        gold_draft = render_adjudication_form_blind(
            crit,
            existing_gold=existing_gold,
            blind_label=blind_label,
            cohort_options=cohort_options,
            key_prefix=key_prefix,
        )
    else:
        peer_records = {a: peer_records_all.get(a, {}).get(cid) for a in peers}
        gold_draft = render_adjudication_form_open(
            crit,
            existing_gold=existing_gold,
            blind_label=blind_label,
            peer_records=peer_records,
            cohort_options=cohort_options,
            key_prefix=key_prefix,
        )

    problems = span_violations(crit.get("text", ""), gold_draft.get("sub_criteria") or [])
    meta = render_adjudication_meta(
        key_prefix=key_prefix,
        existing_adj=(existing_gold or {}).get("adjudication")
                     or (gap_by_id.get(cid) or None),
        span_problems=problems,
    )

    errs = validate_adjudication(
        splitting_decision=gold_draft.get("splitting_decision"),
        sub_criteria=gold_draft.get("sub_criteria") or [],
        tier=meta["tier"],
        rationale_short=meta["rationale_short"],
        rule_status=meta["rule_status"],
        span_override=meta["span_override"],
        span_problems=problems,
        child_logic=gold_draft.get("child_logic"),
    )
    is_gap = meta["tier"] == 3
    if is_gap:
        # A gap ticket records that no tier settled the answer; the gold-label
        # requirements do not apply to it (and must not, or tier 3 would be
        # unreachable). Only the rationale is still needed.
        errs = [e for e in errs
                if "rationale_short" in e or "rule_status" in e]
        st.warning(
            "**tier 3 → gap ticket.** 이 항목은 GOLD envelope에 저장되지 않고 "
            "`gap_tickets.json`으로 분리됩니다 — gold set에 `null` 라벨이 들어가면 "
            "κ 계산에서 별도 클래스로 계수되어 GOLD 축 지표가 오염됩니다 (§7.4-🔴2)."
        )

    st.divider()
    col_save, col_status = st.columns([1, 4])
    with col_save:
        save_clicked = st.button(
            "🎫 gap ticket 저장" if is_gap else "⚖️ 판정 저장",
            type="primary", use_container_width=True, disabled=bool(errs),
        )
    with col_status:
        if errs:
            for e in errs:
                st.error(e)
        elif blind:
            st.success("저장 시 `blind_label`로 보존됩니다 (2차에서 gold를 바꿔도 유지).")
        else:
            st.success("저장 시 record 최상위 gold + `adjudication` 메타로 기록됩니다.")

    if not save_clicked:
        return

    now = _utc_now_iso()
    compared = {a: (peer_records_all.get(a, {}).get(cid) or {}).get("splitting_decision")
                for a in peers} if not blind else {}
    compared = {k: v for k, v in compared.items() if v is not None}

    if is_gap:
        ticket = build_gap_ticket(
            criterion_id=cid,
            reason=meta["rationale_short"],
            blind_label=blind_label or (_blind_snapshot(gold_draft) if blind else None),
            compared=compared,
            escalate_pi=meta["escalate_pi"],
            note=gold_draft.get("notes"),
            queue_stratum=qrow.get("stratum"),
            adjudicated_at=now,
            needs_recursion=meta["needs_recursion"],
            recursion_note=meta["recursion_note"],
        )
        gap_list = merge_gap_tickets(gap_list, [ticket])
        gap_path.parent.mkdir(parents=True, exist_ok=True)
        gap_path.write_text(json.dumps(gap_list, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        # If this criterion had previously been gold, drop it — an item cannot
        # be both a settled answer and an open gap.
        if cid in gold_by_id:
            records = [r for r in gold_env.get("records", [])
                       if r.get("criterion_id") != cid]
            _write_gold(gold_path, gold_env, records, trial_id, stage, now)
            st.info(f"이전 gold 라벨을 제거했습니다: `{cid}`")
        st.success(f"🎫 gap ticket 저장 → {gap_path}")
        return

    if blind:
        # Pass 1: persist ONLY blind_label. The gold label is not settled yet,
        # but the record needs a top-level decision to stay schema-valid, so we
        # seed it from the blind pass and let pass 2 confirm or overwrite it.
        snapshot = _blind_snapshot(gold_draft)
    else:
        snapshot = blind_label

    record = build_gold_record(
        criterion_id=cid,
        gold=gold_draft,
        blind_label=snapshot,
        tier=meta["tier"],
        rationale_short=meta["rationale_short"],
        rule_id=meta["rule_id"],
        rule_status=meta["rule_status"],
        conflicting_rule=meta["conflicting_rule"],
        escalate_pi=meta["escalate_pi"],
        span_override=meta["span_override"],
        adjudicated_at=now,
        queue_stratum=qrow.get("stratum"),
        compared=compared or None,
        needs_recursion=meta["needs_recursion"],
        recursion_note=meta["recursion_note"],
    )
    record["adjudication"]["pass"] = "blind" if blind else "revealed"

    records = [r for r in gold_env.get("records", [])
               if r.get("criterion_id") != cid]
    records.append(record)
    records.sort(key=lambda r: r.get("criterion_id") or "")
    _write_gold(gold_path, gold_env, records, trial_id, stage, now)

    # Leaving gold and gap in sync: a settled answer clears any prior ticket.
    if cid in gap_by_id:
        gap_list = [t for t in gap_list if t.get("criterion_id") != cid]
        gap_path.write_text(json.dumps(gap_list, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        st.info(f"이전 gap ticket을 해소 처리했습니다: `{cid}`")

    st.success(f"⚖️ 저장 → {gold_path.name} ({len(records)} records)")


def _blind_snapshot(record: dict) -> dict:
    """The blind-pass label preserved for D-3 — and the blind form's fallback.

    D-3 only compares the decision (splitting_decision / child_logic / spans),
    but the snapshot also keeps each child's `rationale` and `cohort_scope`
    plus the record-level scope/confidence/notes. Once an item moves to the
    revealed pass this is the only surviving copy of what the blind pass
    actually wrote, and it is what re-seeds the form if the adjudicator flips
    back to blind — a decision-only snapshot silently blanked those fields.
    """
    subs: list[dict[str, Any]] = []
    for s in (record.get("sub_criteria") or []):
        child: dict[str, Any] = {
            "child_id": s.get("child_id"),
            "text_span": normalize_text_span(s.get("text_span")),
        }
        if s.get("rationale"):
            child["rationale"] = s["rationale"]
        if s.get("cohort_scope"):
            child["cohort_scope"] = s["cohort_scope"]
        subs.append(child)
    snap: dict[str, Any] = {
        "splitting_decision": record.get("splitting_decision"),
        "sub_criteria": subs,
    }
    if record.get("child_logic") is not None:
        snap["child_logic"] = record["child_logic"]
    if record.get("cohort_scope"):
        snap["cohort_scope"] = record["cohort_scope"]
    if record.get("confidence"):
        snap["confidence"] = record["confidence"]
    if (record.get("notes") or "").strip():
        snap["notes"] = record["notes"].strip()
    return snap


def _write_gold(path: Path, prev_env: dict, records: list[dict],
                trial_id: str, stage: int, now: str) -> None:
    """Write the GOLD envelope, keeping `committed` so discovery still sees it.

    GOLD is committed from the first save on purpose: `compute_iaa.py` only
    discovers `committed is True` envelopes, and the adjudicator needs the
    E-G / D-G numbers while the work is still in progress. Unlike the
    annotators, there is no anchoring risk in letting them look.
    """
    env = build_gold_envelope(
        trial_id=trial_id,
        stage=stage,
        annotator=GOLD_ACTOR,
        records=records,
        created_at=prev_env.get("created_at") or now,
        committed=True,
    )
    env["committed_at"] = now
    save_envelope(env, path)


def section_iaa_dashboard(stage_dir: Path, *, current_annotator: str,
                          env_dir: Path | None = None) -> None:
    """Phase 2 only. Enumerates committed envelopes only.

    `env_dir` selects the round folder to read envelopes from; `llm_output.json`
    always comes from the stage dir because it is shared across rounds (same
    split as `compute_iaa.discover_sources`).
    """
    ann_dir = env_dir or stage_dir
    committed_files = list_committed_annotator_envelopes(ann_dir)
    llm_file = stage_dir / "llm_output.json"
    sources: list[tuple[str, Path]] = []
    seen: dict[str, int] = {}
    for f in committed_files:
        env = load_json(f) or {}
        # Label by the envelope's annotator id (filename-independent), so a
        # download-named file like `EHJ_..._committed.json` shows as "EHJ".
        label = env.get("annotator") or f.stem.replace("annotator_", "")
        if label in seen:
            seen[label] += 1
            label = f"{label}#{seen[label]}"
        else:
            seen[label] = 1
        sources.append((label, f))
    if llm_file.exists():
        sources.append(("__llm__", llm_file))

    if len(sources) < 2:
        st.info(
            "Need at least 2 committed sources (annotator and/or LLM) to "
            f"compute IAA. Found {len(sources)} committed in {ann_dir}.\n\n"
            "Other annotators in progress are not listed — only committed work is shown."
        )
        return

    labels = [name for name, _ in sources]
    col_a, col_b = st.columns(2)
    with col_a:
        # Default A to current annotator if available
        try:
            default_a = labels.index(current_annotator)
        except ValueError:
            default_a = 0
        idx_a = st.selectbox("Source A", range(len(labels)), index=default_a,
                             format_func=lambda i: labels[i], key="iaa_a")
    with col_b:
        default_b = 1 if len(labels) > 1 else 0
        if default_b == idx_a and len(labels) > 1:
            default_b = (idx_a + 1) % len(labels)
        idx_b = st.selectbox("Source B", range(len(labels)), index=default_b,
                             format_func=lambda i: labels[i], key="iaa_b")

    if idx_a == idx_b:
        st.warning("Pick two different sources.")
        return

    env_a = load_json(sources[idx_a][1]) or {}
    env_b = load_json(sources[idx_b][1]) or {}
    try:
        iaa = compute_stage1_iaa(env_a, env_b)
    except Exception as e:
        st.error(f"IAA computation failed: {type(e).__name__}: {e}")
        return

    # Handover §0.4-🟠1: a GOLD-axis pair is computed over the adjudicated
    # subset only (disagreement-oversampled), so its κ is NOT comparable to the
    # all-172 EHJ-vs-DYK κ shown in the same layout. Say so where the number is.
    if GOLD_ACTOR in (labels[idx_a], labels[idx_b]):
        st.warning(
            f"**GOLD 축 지표 해석 주의 (§0.4-🟠1)** — GOLD envelope에는 판정한 항목만 "
            f"들어 있고 그 표본은 불일치가 과대표집된 층화 표본입니다. 따라서 이 κ는 "
            f"구조적으로 낮게 나오며, 전수 172건 기준 어노테이터 간 κ와 **직접 비교하거나 "
            f"논문에 병렬 인용하면 안 됩니다.** 정확도 보고는 층별 분모를 명시해서 "
            f"수행하세요 (D-1)."
        )

    st.markdown("#### Alignment")
    al = iaa["alignment"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("matched", al["n_matched"])
    c2.metric(f"only {labels[idx_a]}", al["n_only_a"])
    c3.metric(f"only {labels[idx_b]}", al["n_only_b"])
    c4.metric("presence agreement", f"{al['presence_agreement']:.3f}")

    st.markdown("#### splitting_decision (primary κ)")
    sd = iaa["splitting_decision"]
    c1, c2, c3 = st.columns(3)
    c1.metric("n compared", sd["n"])
    c2.metric("observed agreement", f"{sd['observed_agreement']:.3f}")
    c3.metric("Cohen's κ",
              f"{sd['cohens_kappa']:.3f}" if sd["cohens_kappa"] is not None else "undefined")

    st.markdown("#### child_logic (composite_split subset)")
    cl = iaa["child_logic"]
    c1, c2, c3 = st.columns(3)
    c1.metric("n compared", cl["n"])
    c2.metric("observed agreement",
              f"{cl['observed_agreement']:.3f}" if cl["n"] else "—")
    c3.metric("Cohen's κ",
              f"{cl['cohens_kappa']:.3f}" if cl["cohens_kappa"] is not None else "undefined")

    st.markdown("#### cohort_scope")
    cs = iaa["cohort_scope"]
    c1, c2, c3 = st.columns(3)
    c1.metric("n pairs", cs["n_pairs"])
    c2.metric("exact match rate", f"{cs['exact_match_rate']:.3f}")
    c3.metric("mean Jaccard", f"{cs['mean_jaccard']:.3f}")

    with st.expander("Raw metric output (JSON)"):
        st.json(iaa)


def section_peer_overview(env_dir: Path, *, peers: list[str],
                          trial_input: dict) -> None:
    """Revealed-pass reference table of peer labels for the whole trial.

    Only reachable when blind is OFF — `build_adjudication_tab_spec` omits this
    tab entirely during the blind pass, so the read cannot happen there.
    """
    records = load_peer_records(env_dir, peers)
    if not records:
        st.info(f"No peer envelopes in `{env_dir}`.")
        return
    st.caption(
        "판정 참고용 대조표. notes는 원문 그대로 표시하며 요약·재작성하지 않습니다 "
        "(§C-1). 실측상 notes는 약 7% 항목에만 존재하므로 공란이 정상입니다."
    )
    rows = []
    for crit in trial_input.get("criteria", []):
        cid = crit["criterion_id"]
        row: dict[str, Any] = {"criterion_id": cid}
        labels = []
        for actor in sorted(records):
            rec = records[actor].get(cid)
            s = peer_summary(rec)
            row[f"{actor}"] = s.get("splitting_decision") or "—"
            row[f"{actor}_n"] = s.get("n_children", "—")
            row[f"{actor}_note"] = s.get("notes") or ""
            labels.append(s.get("splitting_decision"))
        row["agree"] = "✅" if len(set(labels)) == 1 else "⚠️"
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)


def clear_adjudication_widget_state(trial_ids: Iterable[str]) -> None:
    """Drop the adjudication form's widget state for `trial_ids`.

    Streamlit honours a widget's `value=` argument only while its key is
    ABSENT from session_state; once the form has rendered in this session the
    keys are set, so freshly imported records keep showing whatever was on
    screen before the upload — the import looks like it did nothing. Every
    form key is `adj_{trial_id}_{criterion_id}_*` (`key_prefix` in
    `section_adjudicate`), so clearing that prefix makes the next run re-seed
    from disk. The sidebar keys (`adj_blind`, `adj_pick`, …) do not match the
    prefix and are left alone.
    """
    prefixes = tuple(f"adj_{t}_" for t in trial_ids)
    if not prefixes:
        return
    for key in [k for k in st.session_state if k.startswith(prefixes)]:
        del st.session_state[key]


def section_gold_upload(workspace: Path, *, round_num: int, stage: int) -> None:
    """Import native GOLD envelopes or the combined adjudication JSONL export."""
    st.markdown("#### Adjudication GOLD 업로드")
    st.caption(
        "trial별 `GOLD_*_committed.json` 또는 통합 `.jsonl`을 받습니다. "
        "기존 record와 criterion_id가 겹치면 아래 확인 후에만 업로드 값으로 교체하고, "
        "파일에 없는 기존 record는 유지합니다. gap ticket은 별도 파일로 복원됩니다."
    )
    done_msg = st.session_state.pop("gold_upload_result", None)
    if done_msg:
        st.success(done_msg)
    # Bumped after every import so the uploader and its confirm box reset —
    # otherwise the just-applied file sits there re-offering itself.
    nonce = st.session_state.get("gold_upload_nonce", 0)
    uploaded = st.file_uploader(
        "GOLD JSON / adjudication JSONL", type=["json", "jsonl"],
        key=f"gold_upload_file_{nonce}",
    )
    if uploaded is None:
        return
    try:
        imported = parse_adjudication_upload(uploaded.getvalue())
    except ValueError as exc:
        st.error(str(exc))
        return

    rows = []
    conflicts = 0
    missing_inputs: list[str] = []
    unknown_ids: list[str] = []
    for trial_id, groups in imported.items():
        stage_dir = workspace / trial_id / f"stage{stage}"
        trial_input = load_json(stage_dir / "input.json")
        if not trial_input:
            missing_inputs.append(trial_id)
            continue
        env_dir = envelope_dir(stage_dir, round_num)
        old_path = find_actor_envelope(env_dir, GOLD_ACTOR)
        old_env = load_json(old_path) if old_path else {}
        old_gold_ids = {r.get("criterion_id") for r in (old_env or {}).get("records", [])}
        gp = gap_tickets_path(stage_dir, round_num)
        try:
            old_gaps = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else []
        except json.JSONDecodeError:
            st.error(f"기존 gap ticket을 파싱할 수 없습니다: {gp}")
            return
        old_gap_ids = {r.get("criterion_id") for r in merge_gap_tickets(old_gaps, [])}
        incoming_ids = {r["criterion_id"] for r in groups["gold"]}
        incoming_gap_ids = {r["criterion_id"] for r in groups["gaps"]}
        # A record whose criterion_id is not in input.json would be written to
        # the gold envelope and then be invisible in the queue — but still be
        # counted by compute_iaa.py. Block it rather than import it blind.
        known = {c.get("criterion_id")
                 for c in (trial_input.get("criteria") or [])}
        unknown_ids += sorted((incoming_ids | incoming_gap_ids) - known)
        n_conflict = len((incoming_ids & old_gold_ids) | (incoming_gap_ids & old_gap_ids))
        conflicts += n_conflict
        rows.append({"trial_id": trial_id, "GOLD": len(incoming_ids),
                     "gap": len(incoming_gap_ids), "conflicts": n_conflict})

    if missing_inputs:
        st.error(
            f"다음 trial은 workspace에 stage{stage}/input.json이 없어(또는 읽을 수 없어) "
            "업로드할 수 없습니다: " + ", ".join(sorted(missing_inputs))
        )
        return
    if unknown_ids:
        st.error(
            "input.json에 없는 criterion_id가 있어 업로드를 중단했습니다 "
            f"({len(unknown_ids)}건): " + ", ".join(unknown_ids[:10])
            + (" …" if len(unknown_ids) > 10 else "")
        )
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)
    confirm = st.checkbox(
        f"위 내용을 round{round_num}에 반영합니다"
        + (f" (기존 {conflicts}건 교체)" if conflicts else ""),
        key=f"gold_upload_confirm_{nonce}",
    )
    if not st.button("⬆️ GOLD 업로드", type="primary", disabled=not confirm):
        return

    now = _utc_now_iso()
    total_gold = total_gaps = 0
    for trial_id, groups in imported.items():
        stage_dir = workspace / trial_id / f"stage{stage}"
        env_dir = envelope_dir(stage_dir, round_num)
        gold_path = resolve_envelope_path(env_dir, GOLD_ACTOR,
                                          trial_id=trial_id, stage=stage)
        old_env = load_json(gold_path) or {}
        by_id = {r.get("criterion_id"): r for r in old_env.get("records", [])
                 if r.get("criterion_id")}
        for record in groups["gold"]:
            by_id[record["criterion_id"]] = record
        # A newly imported gap supersedes old gold, and vice versa.
        for ticket in groups["gaps"]:
            by_id.pop(ticket["criterion_id"], None)
        records = sorted(by_id.values(), key=lambda r: r.get("criterion_id") or "")
        _write_gold(gold_path, old_env, records, trial_id, stage, now)

        gp = gap_tickets_path(stage_dir, round_num)
        try:
            old_gaps = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else []
        except json.JSONDecodeError:
            old_gaps = []  # already validated above; unreachable unless file changed mid-click
        merged_gaps = merge_gap_tickets(old_gaps, groups["gaps"])
        gold_ids = {r["criterion_id"] for r in groups["gold"]}
        merged_gaps = [t for t in merged_gaps if t.get("criterion_id") not in gold_ids]
        if merged_gaps or gp.exists():
            gp.parent.mkdir(parents=True, exist_ok=True)
            gp.write_text(json.dumps(merged_gaps, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        total_gold += len(groups["gold"])
        total_gaps += len(groups["gaps"])
    # The Adjudicate tab already rendered this run against the pre-import
    # files, and its widgets are pinned to those values in session_state.
    # Clear them and rerun so the form actually shows what was imported.
    clear_adjudication_widget_state(imported)
    st.session_state["gold_upload_nonce"] = nonce + 1
    st.session_state["gold_upload_result"] = (
        f"업로드 완료: {len(imported)} trials · GOLD {total_gold} records · "
        f"gap tickets {total_gaps}."
    )
    st.rerun()


def section_llm_view(llm_envelope: dict | None) -> None:
    """llm_assisted stages only. Never shown in from_scratch."""
    if llm_envelope is None:
        st.info(
            "No `llm_output.json` for this trial. Run\n"
            "`python -m iaa_pipeline.cli stage<N> <input.json> --output-dir <workspace>` "
            "to generate it."
        )
        return
    n = len(llm_envelope.get("records", []))
    st.markdown(
        f"**model**: `{llm_envelope.get('model', '?')}` · "
        f"**created**: `{llm_envelope.get('created_at', '?')}` · "
        f"**records**: {n}"
    )
    st.json(llm_envelope)


def section_upload(workspace: Path, *, stage: int) -> None:
    st.markdown(
        f"Upload a Stage {stage} input JSON. Will be saved to "
        f"`{{workspace}}/{{trial_id}}/stage{stage}/input.json`."
    )
    uploaded = st.file_uploader(f"Stage {stage} input JSON", type=["json"],
                                key="upload_input")
    if uploaded is None:
        return
    try:
        data = json.loads(uploaded.read().decode("utf-8"))
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        return
    trial_id = data.get("trial_id")
    if not trial_id:
        st.error("File missing 'trial_id' field.")
        return
    if not isinstance(data.get("criteria"), list):
        st.error("File must have 'criteria' as a list.")
        return
    target = workspace / trial_id / f"stage{stage}" / "input.json"
    if target.exists() and not st.checkbox(
        f"Overwrite existing `{target}`?", key="upload_overwrite"
    ):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    st.success(f"Saved → {target}. Reload trial list in sidebar.")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="IAA Annotation", layout="wide")

    # ── Sidebar ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Workspace")
        workspace_str = st.text_input("Workspace directory", value=DEFAULT_WORKSPACE)
        workspace = Path(workspace_str).expanduser()

        stage = st.selectbox("Stage", list(STAGE_MODE.keys()),
                              format_func=lambda s: f"Stage {s} ({STAGE_MODE[s]})",
                              key="stage_pick")
        mode: Mode = STAGE_MODE[stage]

        role: Role = st.radio(
            "Role",
            options=["annotator", "adjudicator"],
            format_func=lambda r: ("Annotator — blind annotation"
                                   if r == "annotator"
                                   else "Adjudicator — gold set (GOLD)"),
            key="role_pick",
            help="Adjudicator writes the GOLD envelope for an existing round. "
                 "See adjudication_handover.md §B.",
        )

        round_num: int | None = None
        if role == "adjudicator" or st.checkbox(
            "Use round subfolder", value=False, key="round_toggle",
            help="Read/write committed envelopes under stage{N}/round{R}/.",
        ):
            round_num = int(st.number_input(
                "Round", min_value=1, max_value=9,
                value=2, step=1, key="round_pick",
            ))

        phase: Phase = "phase_2_review"
        blind = True
        queue_path_str = DEFAULT_QUEUE_PATH
        if role == "annotator":
            phase = st.radio(
                "Phase",
                options=["phase_1_annotate", "phase_2_review"],
                format_func=lambda p: (
                    "Phase 1 — Annotate (IAA hidden)" if p == "phase_1_annotate"
                    else "Phase 2 — Review (post-commit IAA)"
                ),
                key="phase_pick",
                help="Phase 1 is blind annotation. Phase 2 unlocks the IAA tab "
                     "but only after you have committed your envelope.",
            )
        else:
            st.divider()
            st.subheader("Adjudication")
            blind = st.toggle(
                "🔒 Blind pass (1차)", value=True, key="adj_blind",
                help="ON: EHJ/DYK 라벨·notes·span을 전부 숨기고 독립 판정. "
                     "OFF: 공개 후 최종 gold 확정. 1차 라벨은 blind_label로 보존됩니다.",
            )
            if blind:
                st.caption("🔒 peer 라벨을 **읽지 않습니다** (숨기는 것이 아니라 미로드).")
            else:
                st.caption("👥 peer 라벨 공개 — blind_label은 그대로 유지됩니다.")
            queue_path_str = st.text_input(
                "판정 큐 파일", value=DEFAULT_QUEUE_PATH, key="adj_queue_path",
                help="scripts/build_adjudication_queue.py 산출물. 없으면 전체 criterion을 표시.",
            )

        st.divider()
        st.subheader("Identity")
        if role == "adjudicator":
            annotator = GOLD_ACTOR
            st.markdown(f"Actor: **`{GOLD_ACTOR}`** (고정)")
            st.caption(
                "판정자의 blind 라벨은 제3의 독립 의견이며 **투표권이 아닙니다.** "
                "2:1 다수결 자동 판정은 구현되어 있지 않습니다 (§5)."
            )
        else:
            annotator = st.text_input("Your annotator ID", value="",
                                      key="annotator_id").strip()
            st.caption(
                "⚠️ Honor system. Typing another annotator's ID will load and "
                "**permanently contaminate** your view of their work. The IAA "
                "statistic depends on your independence."
            )

        st.divider()
        st.subheader("Trial")
        # The adjudicator works on an existing round, so only trials that have
        # that round folder are selectable — the other 23 workspace trials
        # would just dead-end.
        trials = list_trials(
            workspace, stage=stage,
            round_num=round_num if role == "adjudicator" else None,
        )
        if not trials:
            st.info(f"No trials in `{workspace}` for stage {stage}"
                    + (f" with a round{round_num}/ folder." if role == "adjudicator"
                       else ". Use Upload tab."))
        trial_id = st.selectbox("Trial", trials, key="trial_pick") if trials else None
        if role == "adjudicator" and trials:
            st.caption(f"{len(trials)} trial(s) with `round{round_num}/` labels.")

        if trial_id and annotator:
            stage_dir = workspace / trial_id / f"stage{stage}"
            env_dir_sb = envelope_dir(stage_dir, round_num)
            if role == "adjudicator":
                own_path = find_actor_envelope(env_dir_sb, GOLD_ACTOR)
                own_env = load_json(own_path) if own_path else None
                st.markdown("**GOLD envelope:**")
                if own_env is None:
                    st.markdown(f"- _not started_ (`round{round_num}/`)")
                else:
                    st.markdown(f"- ⚖️ {len(own_env.get('records', []))} records "
                                f"({own_env.get('committed_at', '?')})")
                gp = gap_tickets_path(stage_dir, round_num)
                if gp.exists():
                    try:
                        n_gap = len(json.loads(gp.read_text(encoding="utf-8")) or [])
                    except (json.JSONDecodeError, TypeError):
                        n_gap = 0
                    st.markdown(f"- 🎫 gap tickets: {n_gap}")
            else:
                own_path = annotator_envelope_path(stage_dir, annotator)
                own_env = load_json(own_path)
                st.markdown("**Your envelope status:**")
                if own_env is None:
                    st.markdown("- _not started_")
                elif envelope_is_committed(own_env):
                    st.markdown(f"- 🔒 **committed** ({own_env.get('committed_at','?')})")
                else:
                    st.markdown(f"- 💾 draft saved ({own_env.get('created_at','?')})")
            # NOTE: we intentionally do NOT enumerate other annotators'
            # files here. Only the current annotator's own status is shown.
            # See audit_streamlit_v1.md issue A4.

    # ── Header ───────────────────────────────────────────────────────
    st.title(f"IAA · Stage {stage}")
    if role == "adjudicator":
        st.caption(
            f"Role: **adjudicator** (`{GOLD_ACTOR}`) · round **{round_num}** · "
            f"pass: **{'blind' if blind else 'revealed'}**. "
            f"See `adjudication_handover.md` §B/§C. Gold labels sit at the record "
            f"top level so `compute_iaa.py` picks GOLD up as an actor (§7.4)."
        )
    else:
        st.caption(
            f"Mode: **{mode}** · Phase: **{phase}**. "
            f"See `iaa_pipeline_spec/03_json_schemas.md` for the data contract "
            f"and `audit_streamlit_v1.md` for the blinding rationale."
        )

    if not trial_id:
        section_upload(workspace, stage=stage)
        return

    stage_dir = workspace / trial_id / f"stage{stage}"
    env_dir = envelope_dir(stage_dir, round_num)
    trial_input = load_json(stage_dir / "input.json")
    if trial_input is None:
        st.error(f"Missing input file: {stage_dir / 'input.json'}")
        return
    trial_input["_stage"] = stage  # used by save_envelope

    # Load LLM envelope ONLY if mode permits it. Even loading it here in
    # from_scratch mode would be a risk because of session-state caching,
    # so we skip the read entirely.
    llm_envelope: dict | None = None
    if mode == "llm_assisted":
        llm_envelope = load_json(stage_dir / "llm_output.json")

    cohort_options = [
        c.get("cohort_id") for c in (trial_input.get("cohorts") or [])
        if isinstance(c, dict) and c.get("cohort_id")
    ]

    # ── Adjudicator: separate tab set, separate section ──────────────
    if role == "adjudicator":
        if stage != 1:
            st.warning("Adjudication is wired for Stage 1 (Splitting) only.")
            return
        if not env_dir.is_dir():
            st.error(
                f"Round folder not found: `{env_dir}`. "
                f"판정은 기존 라운드 라벨을 대상으로 하므로 해당 폴더가 있어야 합니다."
            )
            return
        peers = discover_peer_actors(env_dir, exclude=GOLD_ACTOR)
        if not peers:
            st.warning(
                f"`{env_dir.name}/`에 committed 어노테이터 envelope이 없습니다. "
                f"peer 라벨 없이도 판정은 가능하지만 2차 통과가 무의미합니다."
            )
        queue = load_queue(Path(queue_path_str).expanduser(), trial_id=trial_id)
        adj_tabs = build_adjudication_tab_spec(blind=blind)
        for label, tab in zip(adj_tabs, st.tabs(adj_tabs)):
            with tab:
                if label == "⚖️ Adjudicate":
                    section_adjudicate(
                        trial_input=trial_input,
                        env_dir=env_dir,
                        stage_dir=stage_dir,
                        round_num=round_num,
                        blind=blind,
                        queue=queue,
                        cohort_options=cohort_options,
                        peers=peers,
                        stage=stage,
                    )
                elif label == "👥 Peer labels":
                    section_peer_overview(env_dir, peers=peers,
                                          trial_input=trial_input)
                elif label == "📊 IAA":
                    section_iaa_dashboard(stage_dir, current_annotator=GOLD_ACTOR,
                                          env_dir=env_dir)
                elif label == "⬆️ GOLD Upload":
                    section_gold_upload(workspace, round_num=round_num or 2,
                                        stage=stage)
        return

    if annotator:
        save_path = (annotator_envelope_path(stage_dir, annotator)
                     if round_num is None
                     else resolve_envelope_path(env_dir, annotator,
                                                trial_id=trial_id, stage=stage))
        existing = load_json(save_path)
    else:
        save_path = stage_dir / "annotator_unknown.json"
        existing = None

    annotator_committed = envelope_is_committed(existing)
    if not annotator_committed and annotator:
        # Also open the IAA tab when this annotator's committed envelope was
        # dropped in under its hosted-app download name (annotator field
        # matches) rather than `annotator_{id}.json` — no renaming required.
        for p in list_committed_annotator_envelopes(env_dir):
            env = load_json(p)
            if env and env.get("annotator") == annotator:
                annotator_committed = True
                break
    tab_labels = build_tab_spec(
        mode=mode, phase=phase, annotator_committed=annotator_committed
    )
    tabs = st.tabs(tab_labels)

    for label, tab in zip(tab_labels, tabs):
        with tab:
            if label == "📝 Annotate":
                if not annotator:
                    st.info("Enter an annotator ID in the sidebar to start.")
                elif stage != 1:
                    st.warning(
                        f"Stage {stage} runner / form is not yet implemented. "
                        "Only Stage 1 (Splitting) is wired up in this prototype."
                    )
                else:
                    section_annotate(
                        mode=mode,
                        trial_input=trial_input,
                        llm_envelope=llm_envelope,
                        existing_envelope=existing,
                        cohort_options=cohort_options,
                        save_path=save_path,
                        annotator=annotator,
                    )
            elif label == "🤖 LLM Output":
                section_llm_view(llm_envelope)
            elif label == "📊 IAA":
                section_iaa_dashboard(stage_dir, current_annotator=annotator,
                                      env_dir=env_dir)
            elif label == "⬆️ Upload":
                section_upload(workspace, stage=stage)


if __name__ == "__main__":
    main()
