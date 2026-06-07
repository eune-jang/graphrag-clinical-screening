"""Hosted Stage 1 (Splitting) annotation app — Streamlit Community Cloud deploy.

Designed for ephemeral filesystem (Streamlit Cloud restarts wipe disk):
  - No server-side file writes for annotator data
  - In-progress drafts live in `st.session_state` (per-browser-tab)
  - Commit produces a downloadable JSON envelope (annotator uploads to
    shared submission folder out-of-band)
  - Resume across sessions: annotator can re-upload a previously downloaded
    draft to restore their state

Blinding (Stage 1 = from_scratch per spec §246-254):
  - LLM Output tab is NOT rendered (this app is from_scratch only)
  - Form defaults never seeded by LLM (uses build_form_seed with mode="from_scratch")
  - Other annotators' work is never loaded (no server-side persistence to load from)
  - Auth: single shared password gates URL access. Annotator identity is by
    self-declared ID (honor system within session; cross-session contamination
    is structurally impossible because nothing persists)

To run locally:
    cd <project root>
    streamlit run streamlit_apps/stage1_app.py

To deploy:
    See docs/hosting_guide.md.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st  # type: ignore

# Make the project root importable so we can use iaa_pipeline.*
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Reuse the blinding-safe form rendering from the local app
from iaa_pipeline.streamlit_app import (  # noqa: E402
    render_criterion_form_blind,
    build_form_seed,
    envelope_is_committed,
)
from iaa_pipeline.stage_schemas import (  # noqa: E402
    validate_stage1_record,
    validate_envelope,
)

DATA_DIR = _THIS_DIR / "data"
IAA_TRIAL_LIST = _PROJECT_ROOT / "iaa_pipeline_spec" / "iaa_8trials.txt"
STAGE = 1
MODE = "from_scratch"


# ──────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────

def _get_shared_password() -> str | None:
    """Read the shared password from Streamlit secrets.

    Returns None if no secret is configured (development convenience —
    a deployed app should ALWAYS have the secret set).
    """
    try:
        return st.secrets["SHARED_PASSWORD"]
    except (FileNotFoundError, KeyError):
        return None


def gate_password() -> bool:
    """Render password gate. Returns True iff the user is authenticated."""
    expected = _get_shared_password()
    if expected is None:
        st.warning(
            "⚠️ No `SHARED_PASSWORD` in Streamlit secrets — running in "
            "**unauthenticated mode** (development only). For deployment, set "
            "the secret via the Streamlit Cloud dashboard."
        )
        return True

    if st.session_state.get("authenticated"):
        return True

    st.title("Stage 1 — Splitting · Authentication")
    st.markdown("Enter the shared annotation password to continue.")
    pw = st.text_input("Password", type="password", key="pw_input")
    if st.button("Sign in", type="primary"):
        if pw == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ──────────────────────────────────────────────────────────────────────
# Data access (read-only, bundled in repo)
# ──────────────────────────────────────────────────────────────────────

def _load_iaa_trial_filter() -> set[str] | None:
    """Read the IAA evaluation subset from iaa_pipeline_spec/iaa_8trials.txt.

    Returns a set of NCT IDs (one per non-comment, non-blank line) or None
    if the file is missing (caller then shows all bundled trials).
    """
    if not IAA_TRIAL_LIST.exists():
        return None
    ids = set()
    for line in IAA_TRIAL_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(line)
    return ids or None


def list_bundled_trials() -> list[str]:
    """Return the trial IDs the annotator can pick.

    Restricted to the IAA evaluation subset (`iaa_8trials.txt`) when that
    file is present; otherwise falls back to every bundled trial. The
    restriction prevents annotators from wasting blind-annotation effort
    on trials outside the IAA stratified sample.
    """
    if not DATA_DIR.exists():
        return []
    all_trials = sorted(
        d.name for d in DATA_DIR.iterdir()
        if d.is_dir() and (d / f"stage{STAGE}" / "input.json").exists()
    )
    iaa_filter = _load_iaa_trial_filter()
    if iaa_filter is None:
        return all_trials
    return [t for t in all_trials if t in iaa_filter]


def load_bundled_input(trial_id: str) -> dict | None:
    path = DATA_DIR / trial_id / f"stage{STAGE}" / "input.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────────
# Session-state helpers
# ──────────────────────────────────────────────────────────────────────

def _session_key(trial_id: str, annotator: str) -> str:
    return f"draft::{annotator}::{trial_id}::stage{STAGE}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _build_envelope(
    *,
    trial_id: str,
    annotator: str,
    records: list[dict],
    committed: bool = False,
) -> dict:
    env: dict[str, Any] = {
        "trial_id": trial_id,
        "stage": STAGE,
        "source": "annotator",
        "annotator": annotator,
        "created_at": _utc_now_iso(),
        "records": records,
    }
    if committed:
        env["committed"] = True
        env["committed_at"] = _utc_now_iso()
    return env


# ──────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────

def _seed_widget_state(trial_id: str, envelope: dict) -> None:
    """Write each saved record's values directly into widget session_state
    keys so the criterion forms reflect the uploaded envelope on next render.

    Widget keys mirror those built in `_render_form_with_seed`
    (`crit_{i}_decision`, `crit_{i}_sub_{j}_span`, …). The index `i` is the
    position of the criterion in `input.json`, NOT the record's position in
    the envelope, so we map by `criterion_id`.
    """
    trial_input = load_bundled_input(trial_id) or {}
    criteria_order = [
        c.get("criterion_id") for c in trial_input.get("criteria", [])
    ]
    records_by_id = {
        r.get("criterion_id"): r for r in envelope.get("records", [])
    }
    for i, crit_id in enumerate(criteria_order):
        rec = records_by_id.get(crit_id)
        if not rec:
            continue
        prefix = f"crit_{i}"
        if rec.get("splitting_decision"):
            st.session_state[f"{prefix}_decision"] = rec["splitting_decision"]
        if rec.get("child_logic"):
            st.session_state[f"{prefix}_child_logic"] = rec["child_logic"]
        subs = rec.get("sub_criteria") or []
        # Legacy drafts stored a single record-level cohort_scope shared by all
        # children. cohort_scope is now per-child for split criteria and only
        # record-level for non-split ("none"). Seed accordingly so old drafts
        # import without loss.
        legacy_scope = rec.get("cohort_scope")
        if subs:
            st.session_state[f"{prefix}_n_subs"] = max(1, len(subs))
            for j, sub in enumerate(subs):
                if sub.get("text_span") is not None:
                    st.session_state[f"{prefix}_sub_{j}_span"] = sub["text_span"]
                if sub.get("rationale") is not None:
                    st.session_state[f"{prefix}_sub_{j}_rat"] = sub["rationale"]
                # per-child scope: own value if present, else legacy
                # record-level value copied to every child.
                sub_scope = sub.get("cohort_scope")
                if sub_scope is None:
                    sub_scope = legacy_scope
                if sub_scope is not None:
                    st.session_state[f"{prefix}_sub_{j}_cohorts"] = list(sub_scope)
        elif legacy_scope is not None:
            # non-split criterion: keep cohort_scope at record level.
            st.session_state[f"{prefix}_cohorts"] = list(legacy_scope)
        if rec.get("confidence"):
            st.session_state[f"{prefix}_confidence"] = rec["confidence"]
        if rec.get("notes"):
            st.session_state[f"{prefix}_notes"] = rec["notes"]


def render_sidebar() -> tuple[str | None, str]:
    """Returns (trial_id, annotator_id). Either may be empty."""
    with st.sidebar:
        st.header("Session")
        annotator = st.text_input(
            "Your annotator ID",
            value=st.session_state.get("annotator_id", ""),
            key="annotator_input",
            help="A short identifier (initials, etc.) used to label your downloads.",
        ).strip()
        if annotator:
            st.session_state["annotator_id"] = annotator
        st.caption(
            "⚠️ Honor system within this hosted session. The app saves NO "
            "annotator data on the server — your work lives only in this "
            "browser tab until you download it."
        )

        st.divider()
        st.subheader("Trial")
        trials = list_bundled_trials()
        if not trials:
            st.error("No trials bundled in `streamlit_apps/data/`.")
            return None, annotator
        is_filtered = _load_iaa_trial_filter() is not None
        label = f"Pick a trial ({len(trials)} IAA subset)" if is_filtered \
                else f"Pick a trial ({len(trials)} total)"
        trial_id = st.selectbox(label, trials, key="trial_pick")
        if is_filtered:
            st.caption(
                f"📋 Showing only the {len(trials)} IAA evaluation trials "
                "(stratified sample). See "
                "`iaa_pipeline_spec/iaa_8trials_selection.md` for the rationale."
            )

        st.divider()
        st.subheader("Resume previous draft")
        uploaded = st.file_uploader(
            "Upload a draft you downloaded earlier",
            type=["json"],
            key="resume_upload",
            help="If you saved a draft last session, upload it here to continue.",
        )
        if uploaded is not None and annotator and trial_id:
            # file_uploader retains the file across reruns; gate processing so
            # we only apply each uploaded file once.
            uploaded_id = getattr(uploaded, "file_id", None) \
                or (uploaded.name, uploaded.size)
            if st.session_state.get("_resume_loaded_id") != uploaded_id:
                try:
                    data = json.loads(uploaded.read().decode("utf-8"))
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
                else:
                    # Sanity checks before restoring
                    if data.get("trial_id") != trial_id:
                        st.error(
                            f"Uploaded draft is for `{data.get('trial_id')}`, "
                            f"but you selected `{trial_id}`. Switch trials or pick "
                            "a matching draft."
                        )
                    elif data.get("annotator") != annotator:
                        st.error(
                            f"Uploaded draft was created by annotator "
                            f"`{data.get('annotator')!r}`, not `{annotator!r}`. "
                            "Refusing to load to prevent identity mix-up."
                        )
                    else:
                        # Clear stale per-criterion widget keys, then write
                        # each saved value DIRECTLY into st.session_state.
                        # Streamlit's selectbox honors session_state[key]
                        # over `index=`; this is the reliable way to
                        # programmatically populate it.
                        for k in list(st.session_state.keys()):
                            if k.startswith("crit_"):
                                del st.session_state[k]
                        _seed_widget_state(trial_id, data)
                        st.session_state[_session_key(trial_id, annotator)] = data
                        st.session_state["_resume_loaded_id"] = uploaded_id
                        # Stash flash messages to show after the rerun below
                        # (st.rerun discards anything rendered before it).
                        if envelope_is_committed(data):
                            st.session_state["_resume_flash"] = [
                                ("warning",
                                 "Uploaded envelope is already committed. "
                                 "Loading into the form is allowed but you "
                                 "cannot re-commit."),
                                ("success",
                                 "Committed envelope loaded (read-only)."),
                            ]
                        else:
                            st.session_state["_resume_flash"] = [
                                ("success",
                                 f"Draft restored: "
                                 f"{len(data.get('records', []))} records."),
                            ]
                        st.rerun()

        # Show any flash messages queued by a prior upload (consumed once).
        for level, msg in st.session_state.pop("_resume_flash", []):
            getattr(st, level)(msg)

        st.divider()
        st.caption(
            f"**Stage**: {STAGE} · **Mode**: `{MODE}` · "
            f"hosted ephemeral (no server-side persistence)"
        )
    return trial_id, annotator


# ──────────────────────────────────────────────────────────────────────
# Annotation page
# ──────────────────────────────────────────────────────────────────────

def render_annotation_page(trial_id: str, annotator: str) -> None:
    trial_input = load_bundled_input(trial_id)
    if trial_input is None:
        st.error(f"Could not load input for trial {trial_id}.")
        return

    cohort_options = [
        c.get("cohort_id") for c in (trial_input.get("cohorts") or [])
        if isinstance(c, dict) and c.get("cohort_id")
    ]
    criteria = trial_input.get("criteria", [])
    if not criteria:
        st.warning("This trial has no criteria.")
        return

    sess_key = _session_key(trial_id, annotator)

    # Detect (trial, annotator) switch: criterion widget keys (`crit_{i}_*`)
    # are not scoped by trial_id, so without clearing them they bleed values
    # from the previously-viewed trial into the new trial's form. Clear and
    # reseed from the new trial's saved draft (if any).
    current_key = (trial_id, annotator)
    if st.session_state.get("_current_trial_key") != current_key:
        for k in list(st.session_state.keys()):
            if k.startswith("crit_"):
                del st.session_state[k]
        saved_for_new = st.session_state.get(sess_key)
        if saved_for_new:
            _seed_widget_state(trial_id, saved_for_new)
        st.session_state["_current_trial_key"] = current_key

    saved = st.session_state.get(sess_key)
    is_committed_already = envelope_is_committed(saved)
    existing_by_id = (
        {r.get("criterion_id"): r for r in (saved or {}).get("records", [])}
        if saved else {}
    )

    header_cols = st.columns([3, 2])
    with header_cols[0]:
        st.markdown(
            f"**Trial**: `{trial_id}` · **Annotator**: `{annotator}` · "
            f"**{len(criteria)} criteria** · Stage {STAGE} (from-scratch, blind)"
        )
    with header_cols[1]:
        if is_committed_already:
            st.success(f"🔒 Already committed at {saved.get('committed_at', '?')}")
        elif saved:
            st.info(f"💾 Draft in session ({len(saved.get('records', []))} records).")
        else:
            st.info("New session — no draft yet.")

    st.info(
        "**Phase 1 — blind annotation.** This app does not show LLM "
        "suggestions or other annotators' work. Make your independent "
        "judgment, then commit + download. Upload the downloaded JSON to "
        "your shared submission folder."
    )

    # Render forms
    records: list[dict] = []
    validation_errors: list[tuple[str, list[str]]] = []
    for i, crit in enumerate(criteria):
        with st.container(border=True):
            existing_rec = existing_by_id.get(crit["criterion_id"])
            rec = render_criterion_form_blind(
                crit,
                existing_record=existing_rec,
                cohort_options=cohort_options,
                key_prefix=f"crit_{i}",
            )
            errs = validate_stage1_record(rec)
            if errs:
                validation_errors.append((crit["criterion_id"], errs))
                st.warning(" · ".join(errs))
            records.append(rec)

    st.divider()

    # Action buttons + downloads
    col_save, col_commit, col_status = st.columns([1, 1, 2])

    with col_save:
        save_clicked = st.button(
            "💾 Save draft (in session)",
            use_container_width=True,
            disabled=is_committed_already,
            help="Stores the current form values in the browser session. "
                 "To preserve across sessions, also download below.",
        )

    with col_commit:
        commit_clicked = st.button(
            "🔒 Commit (final)",
            type="primary",
            use_container_width=True,
            disabled=is_committed_already or bool(validation_errors),
            help="Lock the envelope as final. After this, your downloads "
                 "will be labelled `committed`.",
        )

    with col_status:
        if validation_errors:
            st.error(
                f"{len(validation_errors)} record(s) have validation issues "
                "— fix before committing."
            )
        elif is_committed_already:
            st.success("This envelope is committed. Download it below.")
        else:
            st.success("All records pass lightweight validation.")

    if save_clicked and not is_committed_already:
        envelope = _build_envelope(
            trial_id=trial_id, annotator=annotator,
            records=records, committed=False,
        )
        st.session_state[sess_key] = envelope
        st.success(
            f"Draft saved in session ({len(records)} records). "
            "Download below to preserve across browser refreshes."
        )

    if commit_clicked and not is_committed_already and not validation_errors:
        envelope = _build_envelope(
            trial_id=trial_id, annotator=annotator,
            records=records, committed=True,
        )
        env_errs = validate_envelope(envelope)
        if env_errs:
            envelope["_validation_errors"] = env_errs
            st.warning(f"Envelope validation warnings: {env_errs}")
        st.session_state[sess_key] = envelope
        st.success(
            "🔒 Committed. Download below and upload to your shared "
            "submission folder."
        )

    # Always-available download(s) reflecting current session state
    current_env = st.session_state.get(sess_key)
    if current_env is None:
        # No draft saved yet — also offer a "current form contents" download
        current_env = _build_envelope(
            trial_id=trial_id, annotator=annotator,
            records=records, committed=False,
        )

    st.divider()
    st.subheader("Download")
    is_committed_now = envelope_is_committed(current_env)
    suffix = "_committed" if is_committed_now else "_draft"
    file_name = f"{annotator}_{trial_id}_stage{STAGE}{suffix}.json"
    json_bytes = json.dumps(current_env, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        label=f"📥 Download {'committed envelope' if is_committed_now else 'draft'}",
        data=json_bytes,
        file_name=file_name,
        mime="application/json",
        type="primary" if is_committed_now else "secondary",
        use_container_width=True,
    )
    if is_committed_now:
        st.caption(
            "After downloading, upload this file to your shared submission "
            "folder. Both annotators' committed files are needed before IAA "
            "can be computed (out-of-band script)."
        )


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="IAA · Stage 1 (hosted)", layout="wide")

    if not gate_password():
        return

    trial_id, annotator = render_sidebar()

    st.title("Stage 1 — Splitting · Annotation")
    st.caption(
        "Blind from-scratch annotation. Server stores no annotator data — "
        "download your envelope and submit it via your shared folder. "
        "See docs/hosting_guide.md for the deployment and submission flow."
    )

    if not annotator:
        st.info("Enter your annotator ID in the sidebar to begin.")
        return
    if not trial_id:
        st.info("Select a trial in the sidebar to begin.")
        return

    render_annotation_page(trial_id, annotator)


if __name__ == "__main__":
    main()
