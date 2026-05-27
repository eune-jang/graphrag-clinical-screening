# IAA Pipeline — Design Spec + Status

Inter-annotator agreement evaluation framework for the 5-stage clinical
trial annotation pipeline. Stage 1 (Splitting) is fully wired end-to-end;
Stages 2-5 runners are stubs (form rendering / runners pending).

## What's implemented

| Layer | File | Status |
|---|---|---|
| Schemas | `iaa_pipeline/stage_schemas.py` | TypedDicts + lightweight validators for Stages 1-5 + ErrorTypeAnnotation |
| LLM runner | `iaa_pipeline/stage_runner.py` | `run_stage1_splitting()` ✅. Stages 2-5: `NotImplementedError` stubs |
| Cache | `iaa_pipeline/cache.py` | sha256-keyed disk cache (per-key JSON, prompt+model in key) |
| CLI | `iaa_pipeline/cli.py` | `python -m iaa_pipeline.cli stage1 ...` |
| Alignment | `iaa_pipeline/aligners.py` | Stage 1 (by criterion_id), Stage 2 (fuzzy span), Stage 3-5 (composite key), error_type (record_locator) |
| Metrics | `iaa_pipeline/metrics.py` | Cohen's κ (self-contained), set agreement, per-field F1. `compute_stage{1,2,4}_iaa()`, `compute_error_type_iaa()`. Stage 3/5 stub |
| Annotation UI (local) | `iaa_pipeline/streamlit_app.py` | Stage 1 form with `mode` + `phase` blinding guarantees |
| Annotation UI (hosted) | `streamlit_apps/stage1_app.py` | Streamlit Community Cloud — shared password, ephemeral storage, download workflow |
| Tests | `tests/test_iaa_metrics.py` | 31 unit tests (metrics + alignment + blinding guarantees). All pass. |
| Converter | `scripts/convert_production_to_iaa.py` | Extracts Stage 1 splitting decisions from `pipeline/output/NCT*_annotation.json` into IAA envelope format (zero LLM calls) |

## Design docs

- `03_json_schemas.md` — JSON contracts for each stage's input/output/envelope
- `04_stage_runners.md` — runner implementation pattern (universal contract,
  caching, error handling, per-stage notes)
- `audit_streamlit_v1.md` — self-audit of UI blinding leaks + resolution
  notes (3 critical / 3 moderate / 2 minor; CRITICAL all closed at the
  function-signature level)

## Requirements

`iaa_pipeline/` is a sibling of `pipeline/` and imports from it
(`pipeline.config`, `pipeline.llm_client`, etc.). Layout:

```
graphrag-clinical-screening/
├── pipeline/                       (existing — annotation pipeline)
├── iaa_pipeline/                   (THIS — IAA framework)
│   ├── __init__.py
│   ├── stage_schemas.py
│   ├── cache.py
│   ├── stage_runner.py
│   ├── cli.py
│   ├── aligners.py
│   ├── metrics.py
│   └── streamlit_app.py            (local UI)
├── docs/audit_reference/           (alternative design considered during the audit)
├── streamlit_apps/
│   ├── stage1_app.py               (hosted UI)
│   └── data/{trial_id}/stage1/     (30 trial inputs + LLM outputs bundled)
├── tests/
│   └── test_iaa_metrics.py
└── scripts/
    └── convert_production_to_iaa.py
```

Dependencies (already in root `pyproject.toml`):
- Core: pandas, neo4j, pyyaml, python-dotenv
- IAA UI: `pip install -e ".[iaa]"` adds streamlit + typing_extensions

## Running tests

```bash
# All 31 tests (no LLM / no streamlit runtime needed)
python tests/test_iaa_metrics.py
# Or via pytest
python -m pytest tests/test_iaa_metrics.py -v
```

Test coverage:
- Cohen's kappa edge cases (perfect agreement, undefined single-class, None labels)
- Set agreement (cohort_scope)
- Stage 1/2/4 IAA end-to-end with synthetic envelopes
- Error type alignment (record_locator, multi-label)
- **Blinding guarantees** — `build_form_seed` ignores LLM in from_scratch mode,
  tab spec excludes LLM/IAA tabs in Phase 1, signature-level rejection of
  `llm_record` in blind render function

## Running Stage 1 LLM extraction

Stage 1 input data is bundled at `streamlit_apps/data/{trial_id}/stage1/input.json`
(30 NSCLC trials). To run the LLM on one of them:

```bash
export OPENAI_API_KEY=sk-...

python -m iaa_pipeline.cli stage1 \
    streamlit_apps/data/NCT03425643/stage1/input.json \
    --output-dir output/ \
    --cache-dir cache/
```

Output: `output/NCT03425643/stage1/llm_output.json`

The first run hits the LLM for each criterion. Re-running with the same
`--cache-dir` makes zero LLM calls (sha256-keyed on prompt+input+model).

Note: the 30 trials' Stage 1 LLM output is **already pre-computed and bundled**
at `streamlit_apps/data/{trial_id}/stage1/llm_output.json` (extracted from
the production pipeline's existing Prompt 1 results — see
`scripts/convert_production_to_iaa.py`). You only need to re-run the CLI
to compare a different model or refresh after prompt changes.

## Verifying an envelope

```python
import json
from pathlib import Path

data = json.loads(
    Path("streamlit_apps/data/NCT03425643/stage1/llm_output.json").read_text()
)

assert data["trial_id"] == "NCT03425643"
assert data["stage"] == 1
assert data["source"] == "llm"

for record in data["records"]:
    print(record["criterion_id"], "→", record["splitting_decision"])
    if record.get("_error"):
        print(f"  ERROR: {record['_error']}")
    if record.get("_validation_errors"):
        print(f"  VALIDATION: {record['_validation_errors']}")
```

## What's in each module

### `stage_schemas.py`

Imports enums from `pipeline.config` (no duplication). Defines:

- `Stage1Input`, `CriterionInput` — input schema
- `Stage1Record`, `Stage1SubCriterion` — output schema
- `Stage{2,3,4,5}Record` — stubs (full definitions in `03_json_schemas.md`)
- `StageOutputEnvelope` — universal top-level structure
- `ERROR_TYPES` — the 9 standardized error codes + PASS
- `validate_stage1_record()`, `validate_envelope()` — lightweight validators

### `cache.py`

```python
cache = LLMCache(Path("cache/"))
cached = cache.get(prompt_template, input_payload, model)
if cached is None:
    response = call_llm(...)
    cache.put(prompt_template, input_payload, model, response)
print(cache.stats())  # {'hits': ..., 'misses': ..., 'hit_rate': ...}
```

Key principles:
- Cache key includes prompt template content, so changing the prompt
  invalidates the cache automatically.
- Cache key includes model name, so switching models doesn't poison cache.
- Cache files are per-key JSON (easy to inspect/delete individually).

### `stage_runner.py`

```python
from pathlib import Path
from iaa_pipeline.stage_runner import run_stage1_splitting

out_path = run_stage1_splitting(
    trial_input=Path("streamlit_apps/data/NCT03425643/stage1/input.json"),
    output_dir=Path("output/"),
    cache_dir=Path("cache/"),
    model_override=None,
)
```

Key behaviors:
- **Per-criterion error isolation**: if one criterion crashes, others
  still process. Failed ones get `_error` and `_traceback` in their record.
- **Validation does not block writes**: invalid records are tagged with
  `_validation_errors` and still written. Annotators see and fix them.
- **Idempotent with cache**: same input + same cache dir → zero LLM calls
  on re-runs.

### `aligners.py`

Stage-aware record alignment between two annotators (or LLM vs annotator).
`AlignmentResult` has `matched / only_a / only_b`. Stage 2 uses
`SequenceMatcher.ratio() ≥ 0.85` for fuzzy span match (exact normalized
match takes precedence).

### `metrics.py`

```python
from iaa_pipeline.metrics import compute_stage1_iaa

iaa = compute_stage1_iaa(envelope_a, envelope_b)
# {'alignment': {...}, 'splitting_decision': {...}, 'child_logic': {...}, ...}
```

Cohen's κ is implemented self-contained (no sklearn dependency). For
single-class agreement (both annotators always picked the same label),
κ is `None` (undefined); observed agreement is still reported.

### `streamlit_app.py` (local)

Filesystem-backed annotation UI. `STAGE_MODE` maps stage → `from_scratch`
or `llm_assisted`. The blind render function (`render_criterion_form_blind`)
does not accept an `llm_record` parameter — signature-level blinding.
Commit unlocks the IAA tab in Phase 2.

### `streamlit_apps/stage1_app.py` (hosted)

Same blinding guarantees, but stateless — no server-side persistence.
Shared password gate (`st.secrets["SHARED_PASSWORD"]`), session-state-only
drafts, `st.download_button` for committed envelopes. Annotators upload
downloads to a shared submission folder out-of-band, where IAA is computed
separately (`scripts/compute_iaa.py` planned; meanwhile call
`compute_stage1_iaa()` from a Python shell).

## Next steps (in priority order)

1. **`scripts/compute_iaa.py`** — read committed envelopes from a folder,
   compute Stage 1 IAA report (markdown + CSV)
2. **Stage 2 runner** — pattern identical to Stage 1, accepts Stage 1 gold
   as upstream
3. **Stage 2 UI form** — semantic_category + relations[] form fields
   (separate file `streamlit_apps/stage2_app.py`, mode = `from_scratch`)
4. **Stage 3-5 runners + UIs** — `llm_assisted` mode reuses
   `render_criterion_form_assisted` from `streamlit_app.py`
5. **`iaa_pipeline_spec/05_iaa_metrics.md`** — formal documentation of
   the metric definitions (Cohen's κ formula, set agreement, per-field F1)
   for the paper Methods section

## Known limitations

- **Stages 2-5 LLM runners are stubs** — `NotImplementedError`. Only Stage 1
  runs end-to-end. Stage 2-5 UI forms also not yet built.
- **`compute_stage3_iaa` / `compute_stage5_iaa` raise NotImplementedError** —
  Stage 3 needs the four-way α/β/γ/δ LLM-assisted metric; Stage 5 needs
  the adjudication file format which is not yet defined.
- **Validation is lightweight** — `validate_stage1_record()` checks enums
  and sub_criteria cardinality but not text-span containment. Deeper
  validation is a follow-up.
- **Honor-system annotator identity** (hosted app) — annotator ID is a
  self-declared text input. Mitigated by: download workflow (no server
  persistence to peek into), upload guard refusing identity mismatches.
  Real per-user auth deferred to a possible production deployment milestone.
- **`_read_prompt_template` heuristic** — the path lookup in
  `stage_runner.py` tries common naming patterns; if your prompts are
  organized differently, adjust accordingly.
