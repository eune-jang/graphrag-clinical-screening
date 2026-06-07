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
"""
from __future__ import annotations

import json
import sys
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

# ──────────────────────────────────────────────────────────────────────
# Mode / Phase machinery
# ──────────────────────────────────────────────────────────────────────

Mode = Literal["from_scratch", "llm_assisted"]
Phase = Literal["phase_1_annotate", "phase_2_review"]

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


def envelope_is_committed(envelope: dict | None) -> bool:
    """An envelope is committed iff it carries the explicit flag."""
    return bool(envelope and envelope.get("committed") is True)


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


def list_trials(workspace: Path, *, stage: int) -> list[str]:
    if not workspace.exists():
        return []
    return sorted(
        d.name for d in workspace.iterdir()
        if d.is_dir() and (d / f"stage{stage}" / "input.json").exists()
    )


def list_committed_annotator_envelopes(stage_dir: Path) -> list[Path]:
    """Return only envelopes with `committed: true`.

    Used by the IAA dashboard. In Phase 1 (annotation), this list is
    intentionally not surfaced anywhere except the IAA tab — and the IAA
    tab itself is hidden until the current annotator commits.
    """
    if not stage_dir.exists():
        return []
    paths = []
    for p in sorted(stage_dir.glob("annotator_*.json")):
        env = load_json(p)
        if envelope_is_committed(env):
            paths.append(p)
    return paths


def annotator_envelope_path(stage_dir: Path, annotator: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in annotator).strip("_")
    return stage_dir / f"annotator_{safe or 'unknown'}.json"


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
    st.markdown(f"### `{crit_id}` _({crit_type})_")
    st.markdown(f"> {criterion.get('text', '')}")

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
        if decision == "composite_split":
            cl_value = seed.get("child_logic") or "(unset)"
            child_logic_choice = st.selectbox(
                "child_logic",
                CHILD_LOGIC_OPTIONS,
                index=_safe_index(CHILD_LOGIC_OPTIONS, cl_value, default=0),
                key=f"{key_prefix}_child_logic",
            )
            child_logic_val: str | None = (
                None if child_logic_choice == "(unset)" else child_logic_choice
            )
        else:
            child_logic_val = None
            st.markdown("_child_logic only applies to composite_split_")

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
        st.caption("Sub-criteria — child_id auto-assigned (a, b, c, ...). "
                   "text_span must come from the parent text. "
                   "cohort_scope is set per child.")
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
            default_span = seed_sub.get("text_span", "")
            default_rat = seed_sub.get("rationale", "")
            # per-child scope: the child's own value if present, else the
            # legacy record-level value (applied to all children).
            child_scope_seed = seed_sub.get("cohort_scope")
            if child_scope_seed is None:
                child_scope_seed = legacy_scope
            with st.container(border=True):
                st.markdown(f"**child `{child_id}`**")
                span = st.text_area("text_span", value=default_span,
                                    key=f"{key_prefix}_sub_{i}_span", height=68)
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
                entry: dict[str, Any] = {"child_id": child_id, "text_span": span.strip()}
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


def _safe_index(options: list[str], value: Any, default: int) -> int:
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return default


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


def section_iaa_dashboard(stage_dir: Path, *, current_annotator: str) -> None:
    """Phase 2 only. Enumerates committed envelopes only."""
    committed_files = list_committed_annotator_envelopes(stage_dir)
    llm_file = stage_dir / "llm_output.json"
    sources: list[tuple[str, Path]] = [
        (f.stem.replace("annotator_", ""), f) for f in committed_files
    ]
    if llm_file.exists():
        sources.append(("__llm__", llm_file))

    if len(sources) < 2:
        st.info(
            "Need at least 2 committed sources (annotator and/or LLM) to "
            f"compute IAA. Found {len(sources)} committed in {stage_dir}.\n\n"
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

        phase: Phase = st.radio(
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

        st.divider()
        st.subheader("Identity")
        annotator = st.text_input("Your annotator ID", value="", key="annotator_id").strip()
        st.caption(
            "⚠️ Honor system. Typing another annotator's ID will load and "
            "**permanently contaminate** your view of their work. The IAA "
            "statistic depends on your independence."
        )

        st.divider()
        st.subheader("Trial")
        trials = list_trials(workspace, stage=stage)
        if not trials:
            st.info(f"No trials in `{workspace}` for stage {stage}. Use Upload tab.")
        trial_id = st.selectbox("Trial", trials, key="trial_pick") if trials else None

        if trial_id and annotator:
            stage_dir = workspace / trial_id / f"stage{stage}"
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
    st.caption(
        f"Mode: **{mode}** · Phase: **{phase}**. "
        f"See `iaa_pipeline_spec/03_json_schemas.md` for the data contract "
        f"and `audit_streamlit_v1.md` for the blinding rationale."
    )

    if not trial_id:
        section_upload(workspace, stage=stage)
        return

    stage_dir = workspace / trial_id / f"stage{stage}"
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

    if annotator:
        save_path = annotator_envelope_path(stage_dir, annotator)
        existing = load_json(save_path)
    else:
        save_path = stage_dir / "annotator_unknown.json"
        existing = None

    annotator_committed = envelope_is_committed(existing)
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
                section_iaa_dashboard(stage_dir, current_annotator=annotator)
            elif label == "⬆️ Upload":
                section_upload(workspace, stage=stage)


if __name__ == "__main__":
    main()
