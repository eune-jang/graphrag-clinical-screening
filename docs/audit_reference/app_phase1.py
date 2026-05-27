"""Streamlit Phase 1 (blind from-scratch) annotation UI.

This file deliberately does NOT import any function that can read LLM
output or other annotators' work. The data access layer (workspace.py)
will raise PhaseAccessError if such access is attempted during Phase 1,
but defense-in-depth: we don't even surface those functions here.

Run with:
    streamlit run iaa_pipeline/app_phase1.py

Each annotator should run this app SEPARATELY on their own machine, or
with a different `--workspace` argument. They never see each other's
in-progress work.

Workflow:
    1. Annotator selects their identity, trial, and stage
    2. App refuses to load if stage mode is not "from_scratch" (Stages 1, 2)
    3. App refuses to load if annotator has already committed (read-only)
    4. Annotator fills in form for each criterion (no LLM defaults)
    5. Annotator clicks "Save draft" repeatedly during the session
    6. When done, annotator clicks "Commit (one-way)" to lock the envelope
    7. Phase 2 app must be used after commit — this app shows read-only view
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st  # type: ignore

# Add project root to sys.path so we can use iaa_pipeline.*
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# IMPORTANT: This file imports ONLY from-scratch-safe functions.
# We do NOT import read_llm_output or read_other_committed here.
# Even if accidentally called, the workspace layer will refuse.
from iaa_pipeline.workspace import (  # noqa: E402
    Workspace,
    Phase,
    PhaseAccessError,
    STAGE_MODES,
)
from iaa_pipeline.stage_schemas import (  # noqa: E402
    SPLITTING_DECISIONS,
    CHILD_LOGIC,
    validate_stage1_record,
    validate_envelope,
)


# ──────────────────────────────────────────────────────────────────────
# Configuration (would normally come from a config file or env vars)
# ──────────────────────────────────────────────────────────────────────

DEFAULT_WORKSPACE = str(_PROJECT_ROOT / "iaa_workspace")

# Who counts as "required to commit" before Phase 2 can begin.
# In a real deployment this comes from a trial config file.
DEFAULT_REQUIRED_ANNOTATORS = ["EHJ", "DYK"]


# ──────────────────────────────────────────────────────────────────────
# Utility: render Stage 1 form for ONE criterion
#
# Note: this function does NOT accept an `llm_record` argument. It
# cannot leak LLM data because the data simply isn't passed in.
# ──────────────────────────────────────────────────────────────────────

def render_criterion_form_phase1(
    criterion: dict,
    *,
    existing_draft: dict | None,
    cohort_options: list[str],
    key_prefix: str,
) -> dict:
    """Render Phase 1 form for one criterion.

    Defaults come ONLY from the annotator's own draft, never from LLM output.
    If existing_draft is None, all fields start blank.
    """
    crit_id = criterion["criterion_id"]
    crit_type = criterion.get("type", "?")

    st.markdown(f"### `{crit_id}` _({crit_type})_")
    st.markdown(f"> {criterion.get('text', '')}")

    # Defaults ONLY from own draft, never from LLM
    seed = existing_draft or {}

    splitting_options = sorted(SPLITTING_DECISIONS)
    # Default position: "none" if no draft (a deliberate neutral default
    # that does NOT bias toward any particular decision)
    default_idx = (
        splitting_options.index(seed["splitting_decision"])
        if seed.get("splitting_decision") in splitting_options
        else splitting_options.index("none")
    )

    col1, col2 = st.columns(2)
    with col1:
        decision = st.selectbox(
            "splitting_decision",
            splitting_options,
            index=default_idx,
            key=f"{key_prefix}_decision",
            help="How does this criterion decompose? See spec §Stage 1.",
        )
    with col2:
        if decision == "composite_split":
            child_logic_options = ["(unset)"] + sorted(CHILD_LOGIC)
            cl_seed = seed.get("child_logic") or "(unset)"
            cl_idx = (
                child_logic_options.index(cl_seed)
                if cl_seed in child_logic_options
                else 0
            )
            child_logic_choice = st.selectbox(
                "child_logic",
                child_logic_options,
                index=cl_idx,
                key=f"{key_prefix}_child_logic",
            )
            child_logic_val = (
                None if child_logic_choice == "(unset)" else child_logic_choice
            )
        else:
            child_logic_val = None
            st.caption("_child_logic only applies to composite_split_")

    if cohort_options:
        cohort_default = seed.get("cohort_scope") or []
        cohort_scope = st.multiselect(
            "cohort_scope (leave empty = applies to all cohorts)",
            cohort_options,
            default=[c for c in cohort_default if c in cohort_options],
            key=f"{key_prefix}_cohorts",
        )
    else:
        cohort_scope = None

    sub_criteria: list[dict] = []
    if decision in ("composite_split", "macro_aggregate", "nested_exception"):
        st.caption(
            "Sub-criteria — child_id auto-assigned (a, b, c, ...). "
            "text_span must come from the parent text."
        )
        seed_subs = seed.get("sub_criteria") or []
        n_subs = st.number_input(
            "Number of sub-criteria",
            min_value=1,
            max_value=20,
            value=max(1, len(seed_subs)),
            key=f"{key_prefix}_n_subs",
        )
        for i in range(int(n_subs)):
            child_id = chr(ord("a") + i)
            default_span = seed_subs[i].get("text_span", "") if i < len(seed_subs) else ""
            default_rat = seed_subs[i].get("rationale", "") if i < len(seed_subs) else ""
            with st.container(border=True):
                st.markdown(f"**child `{child_id}`**")
                span = st.text_area(
                    "text_span",
                    value=default_span,
                    key=f"{key_prefix}_sub_{i}_span",
                    height=68,
                )
                rationale = st.text_input(
                    "rationale (optional)",
                    value=default_rat,
                    key=f"{key_prefix}_sub_{i}_rat",
                )
                sub_entry: dict[str, Any] = {
                    "child_id": child_id,
                    "text_span": span.strip(),
                }
                if rationale.strip():
                    sub_entry["rationale"] = rationale.strip()
                sub_criteria.append(sub_entry)

    confidence = st.select_slider(
        "confidence",
        options=["low", "medium", "high"],
        value=seed.get("confidence", "medium"),
        key=f"{key_prefix}_confidence",
    )
    notes = st.text_area(
        "notes (optional)",
        value=seed.get("notes", ""),
        key=f"{key_prefix}_notes",
        height=68,
    )

    record: dict[str, Any] = {
        "criterion_id": crit_id,
        "splitting_decision": decision,
        "sub_criteria": sub_criteria,
    }
    if child_logic_val is not None:
        record["child_logic"] = child_logic_val
    if cohort_scope:
        record["cohort_scope"] = cohort_scope
    if confidence:
        record["confidence"] = confidence
    if notes.strip():
        record["notes"] = notes.strip()
    return record


# ──────────────────────────────────────────────────────────────────────
# Page sections
# ──────────────────────────────────────────────────────────────────────

def section_annotate(
    *,
    stage_ws,
    annotator: str,
    required_annotators: list[str],
) -> None:
    """Phase 1 annotation form. Available only when annotator has not committed."""
    # Refuse to render if mode is not from-scratch
    if STAGE_MODES.get(stage_ws.stage) != "from_scratch":
        st.error(
            f"Stage {stage_ws.stage} is not a from-scratch stage. "
            f"Use the Phase 2 / LLM-assisted UI instead."
        )
        return

    # Refuse to render if annotator already committed
    if stage_ws.has_annotator_committed(annotator):
        st.warning(
            f"You ({annotator}) have already committed Stage {stage_ws.stage} "
            f"for trial {stage_ws.trial_id}. The work is locked. "
            "Use the Phase 2 app to view results and participate in adjudication."
        )
        committed = stage_ws.read_own_committed(annotator)
        if committed:
            st.markdown(f"**Committed at**: `{committed.get('_committed_at', '?')}`")
            with st.expander("View your committed work (read-only)"):
                st.json(committed)
        return

    # Load input + own draft (NEVER LLM, NEVER other annotators)
    try:
        trial_input = stage_ws.read_input()
    except FileNotFoundError as e:
        st.error(str(e))
        return

    draft = stage_ws.read_own_draft(annotator) or {}
    draft_by_id = {r.get("criterion_id"): r for r in draft.get("records", [])}

    criteria = trial_input.get("criteria", [])
    if not criteria:
        st.warning("Input file has no criteria.")
        return

    st.info(
        f"**Phase 1 (blind annotation)** — You are annotating from scratch. "
        f"LLM suggestions and other annotators' work are not available "
        f"until you commit."
    )
    st.markdown(
        f"**Trial**: `{stage_ws.trial_id}` · "
        f"**Stage**: {stage_ws.stage} · "
        f"**You**: `{annotator}` · "
        f"**Criteria**: {len(criteria)}"
    )

    cohort_options = _extract_cohort_ids(trial_input)

    # Render form
    records: list[dict] = []
    validation_errors: list[tuple[str, list[str]]] = []
    for i, crit in enumerate(criteria):
        with st.container(border=True):
            existing = draft_by_id.get(crit["criterion_id"])
            rec = render_criterion_form_phase1(
                crit,
                existing_draft=existing,
                cohort_options=cohort_options,
                key_prefix=f"crit_{i}",
            )
            errs = validate_stage1_record(rec)
            if errs:
                validation_errors.append((crit["criterion_id"], errs))
                st.warning(" · ".join(errs))
            records.append(rec)

    st.divider()

    # Action buttons
    col_draft, col_commit, col_status = st.columns([1, 1, 2])

    with col_draft:
        save_draft = st.button(
            "💾 Save draft",
            type="secondary",
            use_container_width=True,
            help="Save progress. You can come back to edit later.",
        )

    with col_commit:
        # Commit is gated: only allowed if no validation errors
        commit_disabled = bool(validation_errors)
        commit_clicked = st.button(
            "🔒 Commit (one-way)",
            type="primary",
            use_container_width=True,
            disabled=commit_disabled,
            help=(
                "Lock your annotation. After this, you cannot modify "
                "your work. LLM output and other annotators' work "
                "will become visible in the Phase 2 app."
            ),
        )

    with col_status:
        if validation_errors:
            st.error(
                f"{len(validation_errors)} record(s) have validation issues. "
                "Fix before committing."
            )
        else:
            st.success("All records pass validation.")

    if save_draft:
        envelope = _build_envelope(
            trial_id=stage_ws.trial_id,
            stage=stage_ws.stage,
            annotator=annotator,
            records=records,
        )
        stage_ws.write_own_draft(annotator, envelope)
        st.success("Draft saved.")

    if commit_clicked:
        # Confirmation gate
        st.session_state.setdefault("commit_confirm", False)
        if not st.session_state["commit_confirm"]:
            st.session_state["commit_confirm"] = True
            st.warning(
                "⚠️ Commit is one-way. After committing you cannot edit "
                "this stage. Click Commit again to confirm."
            )
            st.stop()
        envelope = _build_envelope(
            trial_id=stage_ws.trial_id,
            stage=stage_ws.stage,
            annotator=annotator,
            records=records,
        )
        try:
            stage_ws.commit(annotator, envelope)
            st.success(
                "Committed. Reload the page to see read-only view, "
                "or open the Phase 2 app for adjudication."
            )
            st.session_state["commit_confirm"] = False
        except PhaseAccessError as e:
            st.error(f"Commit failed: {e}")


def section_phase_status(
    *,
    stage_ws,
    annotator: str,
    required_annotators: list[str],
) -> None:
    """Show phase status. Phase 1 deliberately hides everyone else's progress.

    To prevent "DYK already committed → I should hurry" anchoring, we
    do NOT show whether other annotators have committed during Phase 1.
    We only tell the current annotator:
      - "you have not committed yet" or "you have committed"
      - phase will be visible after you commit
    """
    phase = stage_ws.current_phase(required_annotators=required_annotators)

    if phase == Phase.PHASE_1_BLIND:
        st.markdown(
            "**Current phase**: Phase 1 (blind annotation in progress)"
        )
        st.caption(
            "Other annotators' progress is intentionally hidden to prevent "
            "anchoring. You will see everyone's work in Phase 2."
        )
        if stage_ws.has_annotator_committed(annotator):
            st.success("You have committed your work.")
        else:
            st.info("You have not yet committed.")
    elif phase == Phase.PHASE_2_ADJUDICATION:
        st.markdown("**Current phase**: Phase 2 (adjudication)")
        st.info("Open the Phase 2 app to view all annotators' work and resolve disagreements.")
    elif phase == Phase.PHASE_COMPLETE:
        st.markdown("**Current phase**: Complete (gold standard finalized)")


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _build_envelope(
    *, trial_id: str, stage: int, annotator: str, records: list[dict]
) -> dict:
    return {
        "trial_id": trial_id,
        "stage": stage,
        "source": "annotator",
        "annotator": annotator,
        "created_at": _utc_now_iso(),
        "records": records,
    }


def _extract_cohort_ids(trial_input: dict) -> list[str]:
    cohorts = trial_input.get("cohorts") or []
    return [
        c.get("cohort_id")
        for c in cohorts
        if isinstance(c, dict) and c.get("cohort_id")
    ]


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="IAA · Phase 1 (Blind)", layout="wide")
    st.title("Phase 1 — Blind annotation")

    with st.sidebar:
        st.header("Setup")
        workspace_str = st.text_input(
            "Workspace directory", value=DEFAULT_WORKSPACE
        )
        workspace = Workspace(Path(workspace_str).expanduser())

        annotator = st.text_input("Your annotator ID", value="").strip()
        if not annotator:
            st.warning("Enter your annotator ID to proceed.")

        trials = workspace.list_trials()
        if not trials:
            st.info(f"No trials found in workspace.")
            trial_id = None
        else:
            trial_id = st.selectbox("Trial", trials)

        stage = st.selectbox(
            "Stage",
            [s for s, mode in STAGE_MODES.items() if mode == "from_scratch"],
            help="Only from-scratch stages (1, 2) appear here.",
        )

        # NOTE: We deliberately do NOT list other annotators in the sidebar.
        # During Phase 1, even seeing "EHJ.json exists" can bias DYK
        # ("EHJ already finished, I should hurry / agree more").

    if not annotator or not trial_id:
        st.info("Set annotator ID and select a trial in the sidebar.")
        return

    stage_ws = workspace.stage(trial_id, stage)

    section_phase_status(
        stage_ws=stage_ws,
        annotator=annotator,
        required_annotators=DEFAULT_REQUIRED_ANNOTATORS,
    )

    st.divider()

    section_annotate(
        stage_ws=stage_ws,
        annotator=annotator,
        required_annotators=DEFAULT_REQUIRED_ANNOTATORS,
    )


if __name__ == "__main__":
    main()
