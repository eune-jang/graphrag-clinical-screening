# IAA Pipeline — Stage 1 Implementation

Stage 1 (Splitting) runner for the IAA evaluation framework.

## What this implements

- `iaa_pipeline/stage_schemas.py` — TypedDict definitions + validation helpers
- `iaa_pipeline/cache.py` — Disk-backed LLM response cache (sha256-keyed)
- `iaa_pipeline/stage_runner.py` — `run_stage1_splitting()` runner
- `iaa_pipeline/cli.py` — Command-line entry point
- `tests/test_stage1.py` — 31 unit + integration tests (LLM mocked)
- `examples/keynote_671_input.json` — KEYNOTE-671 sample input

## Requirements

This package depends on the existing `pipeline/` package being importable.
Place the `iaa_pipeline/` directory as a sibling of `pipeline/`:

```
your_project_root/
├── pipeline/                  (existing — do not modify)
│   ├── __init__.py
│   ├── config.py
│   ├── llm_client.py
│   ├── transforms.py
│   ├── validators.py
│   └── prompts/
│       ├── prompt_1_splitting.txt
│       └── examples.json
└── iaa_pipeline/              (NEW)
    ├── __init__.py
    ├── stage_schemas.py
    ├── cache.py
    ├── stage_runner.py
    └── cli.py
```

Dependencies:
```bash
pip install typing_extensions pytest
# (openai or anthropic SDK as needed by your pipeline)
```

## Running tests (no LLM needed)

```bash
cd your_project_root
python -m pytest tests/test_stage1.py -v
```

All 31 tests should pass without any API key — they use a mocked LLM.

## Running Stage 1 on KEYNOTE-671 (real LLM)

```bash
# Set your API key (whichever pipeline/config.py uses)
export OPENAI_API_KEY=sk-...

# Run Stage 1
python -m iaa_pipeline.cli stage1 \
    examples/keynote_671_input.json \
    --output-dir output/ \
    --cache-dir cache/
```

Output: `output/NCT03425643/stage1/llm_output.json`

The first run hits the LLM for each criterion. Re-running with the same
`--cache-dir` makes zero LLM calls (sha256-keyed).

## Verifying the output

```python
import json
from pathlib import Path

data = json.loads(Path("output/NCT03425643/stage1/llm_output.json").read_text())

# Top-level envelope
assert data["trial_id"] == "NCT03425643"
assert data["stage"] == 1
assert data["source"] == "llm"

# Records: one per input criterion
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
    trial_input=Path("examples/keynote_671_input.json"),
    output_dir=Path("output/"),
    cache_dir=Path("cache/"),  # optional but recommended
    model_override=None,        # optional: use config default
)
```

Key behaviors:
- **Per-criterion error isolation**: if one criterion crashes, others
  still process. Failed ones get `_error` and `_traceback` in their record.
- **Validation does not block writes**: invalid records are tagged with
  `_validation_errors` and still written. Lets annotators see and fix them.
- **Idempotent with cache**: same input + same cache dir → zero LLM calls
  on re-runs.

## Test suite walkthrough

Run individual test classes:

```bash
# Schema validation only
pytest tests/test_stage1.py::TestValidateStage1Record -v

# Envelope structure
pytest tests/test_stage1.py::TestValidateEnvelope -v

# End-to-end with mocked LLM
pytest tests/test_stage1.py::TestRunnerIntegration -v
```

The integration tests verify:
1. Stage 1 output structure matches the spec
2. Cache reduces LLM calls to zero on re-run
3. LLM failures produce error records (not crashes)

## Next steps (not in this commit)

1. **Stage 2 runner** — pattern is identical to Stage 1, accepts Stage 1 gold as upstream
2. **Gold file format** — annotators need a way to commit Stage 1 gold
3. **Streamlit UI** — Stage 1 from-scratch annotation interface
4. **IAA metrics module** — Cohen's κ for splitting_decision

See `iaa_pipeline_spec/` for the full design.

## Known limitations of this commit

- Only Stage 1 is implemented; Stages 2-5 are stubs that raise `NotImplementedError`
- No Streamlit UI yet
- No IAA metrics computation yet
- Validation is lightweight; deeper schema validation comes later
- The prompt template path lookup in `_read_prompt_template` is heuristic;
  if your prompts are organized differently, adjust accordingly
