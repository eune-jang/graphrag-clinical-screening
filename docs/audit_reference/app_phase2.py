"""Streamlit Phase 2 (adjudication) UI.

This app is only useful after all required annotators have committed
their Phase 1 work. It refuses to render adjudication if any required
annotator is still in Phase 1.

In Phase 2:
  - All committed annotator envelopes are visible
  - LLM output is visible
  - IAA statistics are computed and displayed (immutable)
  - Adjudicator(s) walk through disagreements and choose the gold value
  - Gold envelope is written; this transitions to PHASE_COMPLETE

Run with:
    streamlit run iaa_pipeline/app_phase2.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st  # type: ignore

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from iaa_pipeline.workspace import (  # noqa: E402
    Workspace,
    Phase,
    PhaseAccessError,
    STAGE_MODES,
)
from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402


DEFAULT_WORKSPACE = str(_PROJECT_ROOT / "iaa_workspace")
DEFAULT_REQUIRED_ANNOTATORS = ["EHJ", "DYK"]


# ──────────────────────────────────────────────────────────────────────
# Sections
# ──────────────────────────────────────────────────────────────────────

def section_iaa_summary(
    *,
    stage_ws,
    annotator: str,
    required_annotators: list[str],
) -> None:
    """Show locked Phase 1 IAA stats. These do NOT change during adjudication."""
    st.markdown("## Phase 1 IAA (locked at end of blind annotation)")

    envelopes: dict[str, dict] = {}
    for ann in required_annotators:
        try:
            env = stage_ws.read_other_committed(
                requesting_annotator=annotator,
                other_annotator=ann,
                required_annotators=required_annotators,
            ) if ann != annotator else stage_ws.read_own_committed(annotator)
        except PhaseAccessError as e:
            st.error(f"Cannot read {ann}: {e}")
            return
        if env is None:
            st.error(f"No committed envelope for annotator {ann}")
            return
        envelopes[ann] = env

    # Compute pairwise IAA. For 2 annotators this is one comparison.
    pairs = [(a, b) for i, a in enumerate(required_annotators)
             for b in required_annotators[i + 1:]]

    for a, b in pairs:
        st.markdown(f"### {a} × {b}")
        try:
            iaa = compute_stage1_iaa(envelopes[a], envelopes[b])
        except Exception as e:
            st.error(f"IAA computation failed: {e}")
            continue

        c1, c2, c3, c4 = st.columns(4)
        al = iaa["alignment"]
        c1.metric("matched", al["n_matched"])
        c2.metric(f"only {a}", al["n_only_a"])
        c3.metric(f"only {b}", al["n_only_b"])
        c4.metric("presence agreement", f"{al['presence_agreement']:.3f}")

        c1, c2, c3 = st.columns(3)
        sd = iaa["splitting_decision"]
        c1.metric("n compared", sd["n"])
        c2.metric("observed agreement", f"{sd['observed_agreement']:.3f}")
        kappa_str = (
            f"{sd['cohens_kappa']:.3f}"
            if sd["cohens_kappa"] is not None
            else "undefined"
        )
        c3.metric("Cohen's κ (splitting)", kappa_str)


def section_adjudicate_disagreements(
    *,
    stage_ws,
    annotator: str,
    required_annotators: list[str],
) -> None:
    """List disagreements and let the adjudicator pick gold values.

    For now this is a stub focused on Stage 1's splitting_decision field.
    Full adjudication UI would cover all judgment fields per stage.
    """
    st.markdown("## Disagreement resolution")

    if stage_ws.read_gold() is not None:
        st.success("Gold has been written for this stage. See gold section below.")
        return

    # Load all committed envelopes
    envelopes: dict[str, dict] = {}
    for ann in required_annotators:
        env = (
            stage_ws.read_own_committed(annotator)
            if ann == annotator
            else stage_ws.read_other_committed(
                requesting_annotator=annotator,
                other_annotator=ann,
                required_annotators=required_annotators,
            )
        )
        envelopes[ann] = env or {"records": []}

    # Load LLM (reference only — does NOT default the gold)
    try:
        llm_env = stage_ws.read_llm_output(
            requesting_annotator=annotator,
            required_annotators=required_annotators,
        ) or {"records": []}
    except PhaseAccessError as e:
        st.error(f"Cannot read LLM: {e}")
        llm_env = {"records": []}

    # Build per-criterion view
    records_by_annotator: dict[str, dict[str, dict]] = {
        ann: {r["criterion_id"]: r for r in env.get("records", [])}
        for ann, env in envelopes.items()
    }
    llm_by_id = {r["criterion_id"]: r for r in llm_env.get("records", [])}

    all_crit_ids = sorted({
        cid
        for recs in records_by_annotator.values()
        for cid in recs.keys()
    })

    # Build draft gold (starts empty, NOT pre-filled with LLM)
    if "draft_gold" not in st.session_state:
        st.session_state["draft_gold"] = {}
    draft_gold: dict[str, dict] = st.session_state["draft_gold"]

    for cid in all_crit_ids:
        annotator_recs = {
            ann: records_by_annotator[ann].get(cid) for ann in required_annotators
        }
        # Check if there's disagreement on splitting_decision
        decisions = {
            ann: (r or {}).get("splitting_decision")
            for ann, r in annotator_recs.items()
        }
        unique = set(d for d in decisions.values() if d is not None)
        all_agree = len(unique) <= 1

        if all_agree and unique:
            # No disagreement — auto-accept (still let user see + change)
            value = unique.pop()
            with st.container(border=True):
                st.markdown(f"**`{cid}`** ✓ All annotators agree: `{value}`")
                if st.checkbox(f"Override for `{cid}`", key=f"override_{cid}"):
                    new_value = st.selectbox(
                        "Gold value",
                        sorted({"composite_split", "macro_aggregate",
                                "nested_exception", "none"}),
                        key=f"gold_{cid}",
                    )
                    draft_gold[cid] = {"splitting_decision": new_value}
                else:
                    draft_gold[cid] = {"splitting_decision": value}
            continue

        # Disagreement
        with st.container(border=True):
            st.markdown(f"### `{cid}` ⚠️ Disagreement")
            cols = st.columns(len(required_annotators) + 1)
            for i, ann in enumerate(required_annotators):
                cols[i].markdown(f"**{ann}**: `{decisions.get(ann)}`")
            cols[-1].markdown(f"**LLM** _(reference)_: `{(llm_by_id.get(cid) or {}).get('splitting_decision', '?')}`")

            # Adjudicator picks. Default to None to force explicit choice.
            options = ["(undecided)"] + sorted({
                "composite_split", "macro_aggregate", "nested_exception", "none"
            })
            previous = (draft_gold.get(cid) or {}).get("splitting_decision")
            idx = options.index(previous) if previous in options else 0
            new_value = st.selectbox(
                "Gold value",
                options,
                index=idx,
                key=f"gold_{cid}",
            )
            if new_value != "(undecided)":
                draft_gold[cid] = {"splitting_decision": new_value}
            elif cid in draft_gold:
                del draft_gold[cid]

    # Build gold envelope
    n_decided = sum(1 for cid in all_crit_ids if cid in draft_gold)
    st.divider()
    st.markdown(f"**Adjudication progress**: {n_decided}/{len(all_crit_ids)} criteria decided")

    if n_decided == len(all_crit_ids) and len(all_crit_ids) > 0:
        if st.button("🏆 Write gold envelope (one-way)", type="primary"):
            gold_records = [
                {"criterion_id": cid, **draft_gold[cid]}
                for cid in all_crit_ids
            ]
            gold_envelope = {
                "trial_id": stage_ws.trial_id,
                "stage": stage_ws.stage,
                "source": "gold",
                "created_at": _utc_now_iso(),
                "adjudicators": [annotator],
                "records": gold_records,
            }
            try:
                stage_ws.write_gold(
                    gold_envelope, adjudicators=[annotator]
                )
                st.success("Gold written. Reload to see read-only view.")
                del st.session_state["draft_gold"]
            except PhaseAccessError as e:
                st.error(str(e))


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="IAA · Phase 2 (Adjudication)", layout="wide")
    st.title("Phase 2 — Adjudication")

    with st.sidebar:
        st.header("Setup")
        workspace_str = st.text_input(
            "Workspace directory", value=DEFAULT_WORKSPACE
        )
        workspace = Workspace(Path(workspace_str).expanduser())

        annotator = st.text_input(
            "Your annotator ID (must have committed)",
            value="",
        ).strip()

        trials = workspace.list_trials()
        if not trials:
            st.info("No trials.")
            trial_id = None
        else:
            trial_id = st.selectbox("Trial", trials)

        stage = st.selectbox(
            "Stage", [1, 2, 3, 4, 5],
            help="Phase 2 is per-stage.",
        )

    if not annotator or not trial_id:
        st.info("Set annotator ID and trial in sidebar.")
        return

    stage_ws = workspace.stage(trial_id, stage)
    phase = stage_ws.current_phase(
        required_annotators=DEFAULT_REQUIRED_ANNOTATORS
    )

    # Gate: phase must be >= PHASE_2
    if phase == Phase.PHASE_1_BLIND:
        st.error(
            f"Phase 2 is not yet available for {stage_ws.trial_id} stage "
            f"{stage}. Required annotators ({DEFAULT_REQUIRED_ANNOTATORS}) "
            "must all commit first."
        )
        # Show who is waiting (this is fine in Phase 2 entry guard)
        for ann in DEFAULT_REQUIRED_ANNOTATORS:
            committed = stage_ws.has_annotator_committed(ann)
            st.markdown(
                f"- `{ann}`: {'✓ committed' if committed else '⏳ pending'}"
            )
        return

    # Annotator must themselves have committed to participate in adjudication
    if not stage_ws.has_annotator_committed(annotator):
        st.error(
            f"You ({annotator}) have not committed Phase 1. "
            "Only annotators who committed can participate in adjudication."
        )
        return

    section_iaa_summary(
        stage_ws=stage_ws,
        annotator=annotator,
        required_annotators=DEFAULT_REQUIRED_ANNOTATORS,
    )
    st.divider()
    section_adjudicate_disagreements(
        stage_ws=stage_ws,
        annotator=annotator,
        required_annotators=DEFAULT_REQUIRED_ANNOTATORS,
    )


if __name__ == "__main__":
    main()
