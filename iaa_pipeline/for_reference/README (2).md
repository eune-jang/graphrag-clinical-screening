# Reference Implementation: Phase-Aware Streamlit UI

This is a reference design for the IAA annotation UI, showing how to
prevent blinding violations by construction rather than by careful
discipline.

## The problem with the original `streamlit_app.py`

A single-file UI tried to support both blind annotation and adjudication
in the same form. Three concrete leaks resulted:

1. **LLM output seeded form defaults**: `seed = existing_record or llm_record`
   pre-filled every dropdown with the LLM's answer. Clicking Save without
   editing recorded the LLM's decision as the annotator's.

2. **LLM expander was always present**: even with `expanded=False`, a single
   click revealed the LLM answer. Self-discipline is not a safeguard.

3. **Sidebar listed other annotators' files**: seeing "EHJ.json exists"
   told DYK that EHJ had already finished, which biases pace and confidence.

These were not bugs in the sense that someone wrote wrong code — they
were the natural result of having one file try to serve two incompatible
modes. **The fix is structural, not patch-by-patch.**

## Design principles

### 1. Separate apps for separate phases

`app_phase1.py` and `app_phase2.py` are different files. The Phase 1
file does not import any function that can return LLM output or another
annotator's work. It cannot accidentally show what it does not have.

### 2. Access control in the data layer, not the UI

`workspace.py` is the only module that reads or writes annotation files.
Every read function takes the requesting annotator and required-annotators
list as arguments, and raises `PhaseAccessError` if the access violates
the phase invariants. The UI cannot bypass this — there is no other way
to load the data.

### 3. Phase is filesystem state, not UI state

`current_phase()` is computed from commit marker files. There is no
button to "enter Phase 2" — Phase 2 begins automatically when all
required annotators have written their commit markers. An annotator
cannot accidentally enter Phase 2 by clicking the wrong thing, and
cannot stay in Phase 1 after committing.

### 4. Per-annotator file isolation

Each annotator's drafts and committed work live in
`stage{N}/annotator/{annotator_id}/`. A directory listing of the stage
directory does not reveal another annotator's filename. To find someone
else's work, you have to specifically request it (and the workspace
layer refuses during Phase 1).

### 5. Commit is one-way

Once an annotator commits, they cannot edit their draft. This prevents
"I'll go back and revise after I see what EHJ wrote" — by the time you
can see EHJ's work, your own is locked.

### 6. Gold defaults are explicit, never LLM-seeded

In `app_phase2.py`, the adjudication form does NOT pre-fill the gold
value with the LLM's answer. The adjudicator must explicitly choose.
The LLM answer is shown as a reference (a column labeled "LLM
(reference)"), not as the default selection. This matters because
adjudication bias is symmetric to annotation bias — if the gold value
silently defaults to the LLM answer, agreement statistics are inflated.

## File map

```
iaa_pipeline/
├── workspace.py              ← Data access layer (THE critical file)
├── app_phase1.py             ← Blind annotation UI (Stages 1, 2)
├── app_phase2.py             ← Adjudication UI (after all annotators commit)
└── stage_schemas.py          ← (existing) JSON schema definitions

tests/
└── test_workspace.py         ← 19 tests verifying the access-control guarantees
```

## How to use this reference

### To audit the existing `streamlit_app.py`

Compare against this reference and identify:
  - Where does the existing code load LLM output? Is that access gated
    by phase?
  - Where do form defaults come from? Could LLM data reach a default value?
  - What is visible in the sidebar? Could it reveal another annotator's
    progress?
  - Is there any path for an annotator to undo a commit?

### To re-implement the UI

You don't need to use this exact code, but the structure should be
equivalent:
  - One data-access module that owns all phase-aware reads/writes
  - Separate UI entry points for Phase 1 vs Phase 2
  - Tests that explicitly verify Phase 1 cannot read LLM or other
    annotators

### To extend to Stages 2-5

Stages 2 (from_scratch) and Stages 3-5 (llm_assisted) follow the same
pattern:
  - Stage 2 has its own copy of `app_phase1.py` form logic, with form
    fields appropriate to Stage 2 (semantic_category, relation_type, etc.)
  - Stages 3-5 use a different form style where LLM output IS visible
    (because they are llm_assisted) — but the LLM output still goes
    through `read_llm_output()`, which now succeeds because the
    upstream stages have completed and gone through Phase 2
  - Phase 1 / Phase 2 distinction still applies within each stage

## Test coverage

The `tests/test_workspace.py` suite covers:

| Test class | What it verifies |
|---|---|
| TestPhase1Blinding | LLM read blocked, other-annotator read blocked, own draft allowed |
| TestPhaseTransition | Phase 1 → 2 transition on all-committed; Phase 2 → Complete on gold |
| TestPhase2Access | LLM and other-annotator reads succeed after own commit |
| TestCommitImmutability | Cannot commit twice, cannot modify after commit |
| TestGoldImmutability | Gold is written once, cannot be overwritten |
| TestFileIsolation | Each annotator's files in separate subdirectory |
| TestStageModes | Stages 1,2 = from_scratch; 3,4,5 = llm_assisted |
| TestOriginalBugsAreFixed | The 3 specific leaks from streamlit_app.py cannot recur |

Run with: `python -m pytest tests/test_workspace.py -v`

All 19 tests must pass for the IAA framework's blinding guarantees to hold.

## What's NOT in this reference

This is a focused reference for the blinding architecture, not a complete
production app. Things deferred:

- Multi-trial dashboards (the reference is per-trial)
- IAA dashboard inside Phase 1 (intentionally — see Design principle 1)
- Stage 2-5 form rendering (same pattern, different form fields)
- Authentication (the reference assumes annotators run separate instances)
- Conflict resolution between drafts when an annotator opens the app
  on multiple devices simultaneously
- Internationalization of the UI text

The blinding architecture is the part that's hard to add later, which is
why this reference focuses on it.
