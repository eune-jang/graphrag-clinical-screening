# Audit · `iaa_pipeline/streamlit_app.py` v1 (blinding violations)

**Date**: 2026-05-27
**Auditor**: Claude (Opus 4.7)
**Subject**: `iaa_pipeline/streamlit_app.py` as committed earlier in 2026-05-27
session — same author as the auditor (self-audit triggered by external
methodological review).

**Premise**: Stage 1 (Splitting) is a **from-scratch** annotation mode per
`iaa_pipeline_spec/03_json_schemas.md §246-254` (Stage 3 is described as
"the first LLM-assisted stage", which means Stage 1 and 2 are NOT). In
from-scratch mode, annotators must reach their judgement independently of
any LLM output or any other annotator's work. Anchoring bias in this mode
would inflate Cohen's κ artificially, because both annotators would partially
be measuring "how often they accept the same LLM suggestion".

> **Scope note**: this audit covers only the data-flow / blinding question.
> UI aesthetics, error messages, code style — all out of scope.

---

## Audit findings

### 🔴 CRITICAL — A1. LLM output seeds form default values

**Location**: `render_criterion_form()` line 128
```python
seed = existing_record or llm_record or {}
```
Plus the downstream usage at lines 135 (`splitting_decision` default),
140 (`child_logic` default), 154 (`cohort_scope` default), 168
(`sub_criteria` defaults), 201 (`confidence` default), 206 (`notes` default).

**Mechanism**: When no prior annotator envelope exists for the current
annotator, `seed` falls back to the LLM record. Every form widget below
uses `seed.get(...)` to set its default value, so the entire form is
pre-populated with the LLM's answers. An annotator who clicks "💾 Save"
without changing anything produces an envelope **identical** to the LLM's,
trivially.

**Severity**: critical. This is the most direct form of anchoring bias —
the LLM literally writes the annotator's first draft. The annotator's
keystrokes become "decide whether to override LLM" rather than "decide
splitting independently".

**Reproducibility test**:
1. Convert NCT03425643 with `scripts/convert_production_to_iaa.py`
   (creates both `input.json` and `llm_output.json`).
2. Launch the UI as a new annotator (any ID, no existing envelope).
3. Open the Annotate tab and immediately click "💾 Save annotator
   envelope" without changing anything.
4. Diff `iaa_workspace/NCT03425643/stage1/annotator_<id>.json` against
   `iaa_workspace/NCT03425643/stage1/llm_output.json`. The `records[].splitting_decision`,
   `child_logic`, and `sub_criteria` arrays will be identical, even though
   the annotator ostensibly made independent judgments.

---

### 🔴 CRITICAL — A2. LLM suggestion expander inline with each form

**Location**: `render_criterion_form()` lines 123-125
```python
if llm_record is not None:
    with st.expander("🤖 LLM suggestion", expanded=False):
        st.json(_strip_internal_keys(llm_record))
```

**Mechanism**: For every criterion, a collapsible "🤖 LLM suggestion"
expander is rendered directly above the input widgets. `expanded=False`
makes the LLM data hidden by default but not absent — a single click
reveals the LLM's full record (`splitting_decision`, `child_logic`,
`sub_criteria`, etc.). The expander label itself signals the LLM's
existence and entices inspection.

**Severity**: critical. Even disciplined annotators have moments of
uncertainty; the one-click reveal is calibrated to be tempting precisely
at the moment anchoring would do the most damage.

**Reproducibility test**:
1. Same setup as A1.
2. As the annotator, when uncertain on any criterion (which will happen
   for ~30% of criteria for any non-trivial trial), click the 🤖
   expander.
3. The full LLM record is shown verbatim. Memory contamination is now
   permanent for this session; the annotator's "independent" decision
   has been irreversibly influenced.

---

### 🔴 CRITICAL — A3. "LLM Output" tab unconditionally rendered

**Location**: `main()` lines 474-476 and 489-490
```python
tab_annotate, tab_llm, tab_iaa, tab_upload = st.tabs(
    ["📝 Annotate", "🤖 LLM Output", "📊 IAA", "⬆️ Upload"]
)
...
with tab_llm:
    section_llm_view(llm_envelope)
```

**Mechanism**: The `🤖 LLM Output` tab is always rendered for every stage.
In `section_llm_view()` (line 380-390), the LLM envelope is displayed in
full JSON. Stage 1 annotators can simply switch to this tab before (or
during) annotation and read the entire LLM output for the trial.

**Severity**: critical. Unlike A2 which requires per-criterion intent,
this exposes the entire LLM output in one move. An annotator who simply
"wants to see what the LLM did" has now compromised every criterion
they will annotate.

**Reproducibility test**:
1. Same setup as A1.
2. As the annotator, switch to the `🤖 LLM Output` tab immediately after
   opening the app, before any annotation.
3. Full LLM envelope (25 records for NCT03425643) is shown.
4. Switch back to Annotate tab and proceed: every decision is now anchored.

---

### 🟡 MODERATE — A4. Sidebar lists other annotators' envelope filenames

**Location**: `main()` lines 444-450
```python
stage_dir = workspace / trial_id / "stage1"
existing_files = list_annotator_envelopes(stage_dir)
st.markdown("**Existing annotator envelopes:**")
if existing_files:
    for f in existing_files:
        st.markdown(f"- `{f.name}`")
```

**Mechanism**: For every trial, the sidebar enumerates all
`annotator_*.json` files in the stage1 directory — including those
belonging to other annotators. This leaks existence + identity information.
It doesn't leak content directly, but combined with A6 (identity is
honor-system) and A1 (envelope content becomes form defaults), it
becomes a content leak.

**Severity**: moderate on its own; promotes to critical when chained
with A1 + A6.

**Reproducibility test**:
1. Annotator EHJ has saved `annotator_EHJ.json`.
2. Annotator KIM opens the UI on the same workspace.
3. KIM's sidebar shows `annotator_EHJ.json` exists — KIM now knows EHJ
   is working on this trial. (Chain to A6 for content leak.)

---

### 🟡 MODERATE — A5. IAA dashboard available during ongoing annotation

**Location**: `main()` line 491-492 and `section_iaa_dashboard()` lines 314-377
```python
with tab_iaa:
    section_iaa_dashboard(stage_dir)
```

**Mechanism**: The `📊 IAA` tab is rendered for all stages and at all
times. Once at least 2 envelopes (annotator + annotator, or annotator
+ LLM) exist, Cohen's κ is computed in real time. The dashboard pulls
*any* `annotator_*.json` regardless of who saved it or whether the
annotator has finished. This creates a feedback loop: annotator A's
in-progress envelope gets compared against the LLM (or another annotator),
the κ is displayed, and A unconsciously adjusts subsequent decisions to
move κ in a preferred direction.

**Severity**: moderate. The bias is indirect (statistic-mediated rather
than content-mediated) but real, especially over long sessions.

**Reproducibility test**:
1. After saving the first 5 criteria of an annotation in progress,
   switch to 📊 IAA tab.
2. Select "annotator_self" vs "__llm__". A partial κ score appears,
   computed only over the 5 saved criteria.
3. If κ is low, the annotator's next 20 criteria are influenced by the
   knowledge "I'm currently disagreeing with the LLM a lot".

---

### 🟡 MODERATE — A6. Annotator identity is unverified text input

**Location**: `main()` line 435 + line 472
```python
annotator = st.text_input("Your annotator ID", value="").strip()
...
existing = load_json(save_path)   # save_path derived from annotator string
```

**Mechanism**: The annotator's identity is established purely by what
they type in the sidebar. No authentication, no session lock, no
detection of typing a different person's ID. If user "KIM" types
"EHJ" instead of their own ID, line 472 will load
`annotator_EHJ.json` and — via A1 — pre-populate the Annotate tab with
EHJ's saved answers. KIM has now read EHJ's annotation in full.

**Severity**: moderate. Requires intent (curiosity), but the only deterrent
is honor. Promotes to critical when A1 and A4 are present — A4 tells the
curious user that other envelopes exist, A1 surfaces their content.

**Reproducibility test**:
1. Annotator EHJ saves `annotator_EHJ.json` with 25 records.
2. Annotator KIM, suspecting they want to peek, types `EHJ` in the ID
   field of their own session.
3. The Annotate tab loads with all of EHJ's decisions as defaults.
4. KIM types their own ID back. Memory is contaminated; KIM's subsequent
   annotation cannot honestly claim independence from EHJ's.

---

### 🟢 MINOR — A7. `n_subs` count leaks LLM's splitting cardinality

**Location**: `render_criterion_form()` lines 168-175
```python
seed_subs = seed.get("sub_criteria") or []
n_subs = st.number_input(
    "Number of sub-criteria",
    min_value=1,
    max_value=20,
    value=max(1, len(seed_subs)),   # ← leak
    key=f"{key_prefix}_n_subs",
)
```

**Mechanism**: When `seed` falls back to the LLM record (A1), the default
`n_subs` shown in the number_input widget is the LLM's chosen
sub-criterion count. Even an annotator who ignores the per-field defaults
will see "the LLM thought there were 3 sub-criteria here" pre-filled.
The cardinality alone is a non-trivial anchoring signal for `composite_split`
decisions (more sub-criteria correlates with finer splitting).

**Severity**: minor on its own; subsumed by A1's fix in practice, but
worth listing because the fix for A1 must also clean this code path
(not just the field-default lookups).

**Reproducibility test**: subsumed by A1's reproducibility test — diff
of the `sub_criteria` arrays will reveal identical lengths and contents.

---

### 🟢 MINOR — A8. `existing_record` and `llm_record` share the same form key namespace

**Location**: `render_criterion_form()` calls in `section_annotate()` line 274
plus form widget keys like `key=f"{key_prefix}_decision"` at line 136

**Mechanism**: Streamlit's `key=` arguments scope widget state to the
session. If an annotator switches their ID mid-session (per A6), the
form widgets retain their previous values until rerun. This means
even after typing the correct ID back, the form may show contaminated
state from the previously-loaded envelope. Not a fresh leak — it's a
persistence of A6's leak.

**Severity**: minor. The contamination is already permanent once read
(human memory). State leakage just makes the audit harder to recover from.

**Reproducibility test**: same as A6, then observe the form does not
reset to "blank" when ID is changed without a hard page reload.

---

## Summary of audit findings

| ID | Severity | Issue (one-line) | Fix scope |
|---|---|---|---|
| A1 | 🔴 CRITICAL | LLM record seeds all form defaults | refactor (mode parameter) |
| A2 | 🔴 CRITICAL | Per-criterion LLM expander in form | refactor (mode parameter) |
| A3 | 🔴 CRITICAL | "LLM Output" tab always present | refactor (mode parameter) |
| A4 | 🟡 MODERATE | Sidebar lists other annotators | local patch |
| A5 | 🟡 MODERATE | IAA dashboard live during annotation | refactor (phase commit) |
| A6 | 🟡 MODERATE | Annotator ID is unverified text input | local patch + UX |
| A7 | 🟢 MINOR | `n_subs` count leak (subsumed by A1) | cleaned by A1 fix |
| A8 | 🟢 MINOR | Form state persists across ID change | follow-up only |

**Critical chain**: A1 + A2 + A3 produce direct content anchoring.
A4 + A6 chain into an indirect content leak (curious user can become
direct leak via A1). A5 is a separate statistic-mediated bias.

---

## Step 2 — Fix proposal

### Architectural changes

#### F-Mode. Add `mode: Literal["from_scratch", "llm_assisted"]` parameter

Source the mode from a stage→mode mapping that mirrors the spec:
```python
STAGE_MODE = {
    1: "from_scratch",      # Splitting (this PR)
    2: "from_scratch",      # Category / Relation
    3: "llm_assisted",      # Preferred name
    4: "llm_assisted",      # Constraints
    5: "llm_assisted",      # Alternative constraint
}
```

The mode parameter must be **propagated through function signatures** —
not derived implicitly from "is `llm_record` present?". Functions that
operate in `from_scratch` mode must not accept `llm_record` arguments;
the compiler / type-checker should make leak attempts visible.

Two-function pattern:
```python
def render_criterion_form_blind(criterion, *, existing_record, ...) -> dict: ...
def render_criterion_form_assisted(criterion, *, existing_record, llm_record, ...) -> dict: ...
```
The blind variant never receives `llm_record`. Dispatch from `section_annotate()`
based on mode.

**Resolves**: A1, A2, A3, A7.

#### F-Phase. Introduce explicit commit mechanism for IAA dashboard

Add `committed: bool` and `committed_at: str` fields to annotator envelopes.
The 📊 IAA tab:
  - In Phase 1 (annotation in progress): hidden entirely from the tab list.
    Or, only available after the current annotator has clicked "Commit my
    work" and at least one other source (annotator or LLM) is also committed.
  - In Phase 2 (post-commit): visible. Only enumerates envelopes where
    `committed=True`.

The commit action is irreversible from the UI (a second Streamlit run
can re-edit by manually editing JSON, but the UI itself doesn't allow it).

**Resolves**: A5.

#### F-Sidebar. Remove other-annotator listing

Replace the "Existing annotator envelopes" block with a single line:
"Your envelope: `annotator_<your_id>.json` (saved / unsaved)". No
enumeration of files belonging to others. The annotator only sees
their own work's state.

**Resolves**: A4.

#### F-Identity. Soft separation, honor-system disclaimer

Streamlit prototype cannot do real auth. Mitigations:
  - Remove A4's UI hint that other envelopes exist (already covered by F-Sidebar)
  - Add a one-line disclaimer near the ID field: "Honor system. Typing
    another annotator's ID will load and contaminate your view of their work."
  - For Phase 2, lock identity at session start via a "Begin session"
    button that disables further edits to the ID input. Phase 1 still
    allows ID change (with a session reset warning).

This does NOT plug A6 fully — that requires real auth (out of scope for
a prototype). It reduces the surface area where curiosity can lead to
contamination.

**Partial mitigation**: A6, A8.

---

### Per-issue mapping

| Issue | Fix |
|---|---|
| A1 | `from_scratch` render function does not accept `llm_record`. `seed = existing_record or {}`. |
| A2 | LLM expander is rendered only by `render_criterion_form_assisted`. |
| A3 | "🤖 LLM Output" tab is added to the tab list only when `mode == "llm_assisted"`. |
| A4 | Sidebar shows only the current annotator's own envelope state. |
| A5 | "📊 IAA" tab added to tab list only when (a) phase = post-commit AND (b) the current annotator's envelope has `committed=True`. |
| A6 | Honor-system disclaimer + locked ID after "Begin session" in Phase 2. Full fix requires real auth, deferred. |
| A7 | Same render-function split as A1: blind function does not see seed_subs from LLM. |
| A8 | Documented in disclaimer; full fix would require Streamlit session-state reset on ID change. Deferred. |

### What data flow IS preserved

  - Annotator sees their **own** in-progress envelope (resume across
    sessions) — load `annotator_<my_id>.json` whose `annotator` field
    matches the typed ID.
  - Annotator sees the input criteria (`input.json`) — that's the
    annotation target, not a leak.
  - Annotator sees their own validation errors in real time.
  - LLM output IS visible in `llm_assisted` mode (Stages 3-5) — that's
    the whole point of those stages.
  - IAA dashboard becomes visible after commit (Phase 2).

---

## Step 3 — Implementation notes

See updated `iaa_pipeline/streamlit_app.py`.

Key extraction for testability: the seed-construction logic moves into
a pure function `build_form_seed(mode, existing_record, llm_record)` that
can be unit tested without a Streamlit runtime. The function is the
**single chokepoint** through which the form's default values are derived,
so a test that exercises it covers all field-default leak paths at once.

---

## Step 4 — Resolution (filled after implementation)

| ID | Resolution |
|---|---|
| A1 | ✅ `build_form_seed(mode="from_scratch", ...)` returns `existing_record or {}` ignoring `llm_record`. `render_criterion_form_blind()` does not take an `llm_record` parameter. Test: `test_blind_seed_ignores_llm_record`. |
| A2 | ✅ LLM expander is rendered only in `render_criterion_form_assisted()`. Blind form does not call `st.expander("🤖 LLM suggestion", ...)`. |
| A3 | ✅ Tab list assembled by `_build_tab_spec(mode, phase)`. "🤖 LLM Output" tab is appended only when `mode == "llm_assisted"`. Test: `test_tab_spec_from_scratch_excludes_llm_tab`. |
| A4 | ✅ Sidebar shows only `annotator_<my_id>.json` state ("saved YYYY-MM-DD" or "not yet saved"). No `glob("annotator_*.json")` in main UI path. |
| A5 | ✅ "📊 IAA" tab appended only when `phase == "phase_2_review"` AND current annotator's envelope has `committed=True`. Test: `test_tab_spec_phase1_excludes_iaa_tab`. |
| A6 | ⚠️ Partial. Disclaimer added; full auth deferred. Documented in §"Known limitations" of the audit. |
| A7 | ✅ Subsumed by A1 fix — `n_subs` defaults to `max(1, len(seed.get("sub_criteria") or []))` where `seed` comes from `build_form_seed()`. |
| A8 | ⚠️ Documented. Full fix requires Streamlit session-state purge on ID change, deferred. |

### Known limitations (carried forward)

- **No real auth** (A6 / A8): Streamlit prototype is honor-system. Real
  deployments need either (a) per-annotator separate workspace dirs
  enforced at OS level, or (b) actual login. Listed for the eventual
  production deployment milestone.
- **Streamlit session state** (A8): widget state persists across ID
  changes within a single browser session. A hard page reload (Cmd+R)
  clears it. Documented in disclaimer.
- **Commit irreversibility**: the commit action sets `committed=True`
  in the JSON file. The UI does not provide an "uncommit" path; an
  annotator who needs to retract a commit must edit the JSON manually
  or delete the file. This is intentional — commit is a methodological
  checkpoint, not a casual button.
