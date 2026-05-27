# 04 · Stage Runners

This file specifies how to implement `iaa_pipeline/stage_runner.py`. Each
stage has one runner function. All runners follow the same pattern:

```
load input → call existing pipeline functions → assemble output envelope → save → return path
```

## Universal contract

Every runner has signature:
```python
def run_stage_N(
    trial_input: dict | Path,           # in-memory dict or path to input file
    *,
    upstream_gold: dict[int, Path] | None = None,  # gold files from previous stages
    output_dir: Path,
    cache_dir: Path | None = None,      # if set, cache LLM responses here
    model_override: str | None = None,  # for testing with different models
) -> Path:
    """
    Returns: path to written output file
    """
```

### Caching contract

If `cache_dir` is provided, runners MUST cache LLM responses keyed by:
```
sha256(prompt_template + input_text + model_name)
```

Cache files are JSON with structure:
```json
{"prompt_hash": "...", "model": "...", "response": {...}, "cached_at": "..."}
```

This is critical: running all 5 stages on 8 trials without caching means
paying for the same prompt_1 call 5 times if the user re-runs stages.

### Error handling

Runners must NOT crash on individual criterion failures. Pattern:

```python
results = []
for criterion in input_criteria:
    try:
        record = process_one(criterion)
        results.append(record)
    except Exception as e:
        results.append({
            "criterion_id": criterion["criterion_id"],
            "_error": str(e),
            "_traceback": traceback.format_exc(),
        })
        logger.warning(f"Failed {criterion['criterion_id']}: {e}")
```

The output file then contains both successful records and error placeholders.
The IAA computation later filters out `_error`-tagged records.

## Stage 1 Runner

### Signature
```python
def run_stage1_splitting(
    trial_input: dict | Path,
    *,
    output_dir: Path,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> Path:
    """Run Prompt 1 (splitting) on every criterion in the trial.

    Stage 1 has no upstream gold (it's the first stage).

    Output file: {output_dir}/{trial_id}/stage1/llm_output.json
    """
```

### Implementation steps

1. **Load input**
   - If `trial_input` is a `Path`, read it as JSON
   - Validate it matches `Stage1Input` schema from `03_json_schemas.md`

2. **For each criterion**:
   - Build prompt 1 inputs:
     ```python
     prompt_inputs = {
         "criterion_text": criterion["text"],
         "cohort_list_or_null": criterion.get("cohort_list"),
         "neighboring_criteria": format_neighbors(criterion.get("neighboring_criteria", [])),
     }
     ```
   - Call `pipeline.llm_client.call_llm("prompt_1", prompt_inputs, model=model_override)`
   - Apply `pipeline.transforms.strip_nested()` to normalize output
   - Build `Stage1Record`:
     ```python
     record = {
         "criterion_id": criterion["criterion_id"],
         "splitting_decision": llm_output["splitting_decision"],
         "child_logic": llm_output.get("child_logic"),
         "cohort_scope": llm_output.get("cohort_scope"),
         "sub_criteria": llm_output.get("sub_criteria", []),
         "confidence": llm_output.get("confidence"),
         "notes": llm_output.get("notes"),
     }
     ```

3. **Assemble envelope**:
   ```python
   envelope = {
       "trial_id": trial_input["trial_id"],
       "stage": 1,
       "source": "llm",
       "model": resolved_model_name,
       "created_at": utc_now_iso(),
       "records": all_records,
   }
   ```

4. **Write output**:
   - Path: `{output_dir}/{trial_id}/stage1/llm_output.json`
   - Create parent dirs if needed
   - Return the path

### Acceptance criteria
- [ ] Running on KEYNOTE-671 input produces 25-50 records (matches criterion count)
- [ ] Output file passes `Stage1Record` TypedDict validation for every record
- [ ] Re-running with same input + cache produces zero LLM calls
- [ ] If LLM returns invalid JSON, the record gets `_error` field, not crash

### Anti-patterns
- ❌ Calling Prompt 2 inside Stage 1 runner
- ❌ Storing LLM raw response in the envelope (only the parsed/normalized record)
- ❌ Hardcoding model name (use config.py MODELS dict + override parameter)

## Stage 2 Runner

### Signature
```python
def run_stage2_category_relation(
    trial_input: dict | Path,
    *,
    upstream_gold: dict[int, Path],     # MUST contain {1: path_to_stage1_gold}
    output_dir: Path,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> Path:
    """Run Prompt 2 on every (sub-)criterion using Stage 1 GOLD splitting.

    Output: {output_dir}/{trial_id}/stage2/llm_output.json
    """
```

### Implementation steps

1. **Load Stage 1 gold**:
   ```python
   stage1_gold_path = upstream_gold[1]
   stage1 = json.loads(stage1_gold_path.read_text())
   if stage1["source"] != "gold":
       raise ValueError(f"Expected gold for stage 1, got source={stage1['source']}")
   ```

2. **Expand each criterion into sub-criteria based on Stage 1 gold**:
   ```python
   sub_criteria_inputs = []
   for stage1_rec in stage1["records"]:
       criterion_id = stage1_rec["criterion_id"]
       decision = stage1_rec["splitting_decision"]
       if decision == "none" or not stage1_rec.get("sub_criteria"):
           # single sub-criterion = the parent itself
           sub_criteria_inputs.append({
               "sub_criterion_id": criterion_id,
               "parent_criterion_id": criterion_id,
               "parent_role": "none",
               "type": original_criterion["type"],
               "text_span": original_criterion["text"],
           })
       else:
           for sub in stage1_rec["sub_criteria"]:
               sub_criteria_inputs.append({
                   "sub_criterion_id": f"{criterion_id}{sub['child_id']}",
                   "parent_criterion_id": criterion_id,
                   "parent_role": decision,
                   "type": original_criterion["type"],
                   "text_span": sub["text_span"],
               })
   ```

3. **For each sub_criterion**, call Prompt 2 with appropriate context:
   ```python
   prompt_inputs = {
       "criterion_text": sub["text_span"],
       "inclusion_or_exclusion": sub["type"],
       "parent_id_and_role_or_null": (
           json.dumps({"parent_id": sub["parent_criterion_id"], "parent_role": sub["parent_role"]})
           if sub["parent_role"] != "none" else "null"
       ),
   }
   ```

4. **Strip output fields** that should not be stored:
   ```python
   from pipeline.config import LLM_OUTPUT_STRIP_FIELDS
   record = {k: v for k, v in llm_output.items() if k not in LLM_OUTPUT_STRIP_FIELDS}
   ```

5. **Write output**

### Acceptance criteria
- [ ] Sub-criterion count matches Stage 1 gold (e.g., if Stage 1 split I1 into 3, Stage 2 has 3 records for I1)
- [ ] Every record has valid `semantic_category` (in SEMANTIC_CATEGORIES enum)
- [ ] Every relation has valid `relation_type` (in RELATION_TYPES enum)
- [ ] Refusing to run if `upstream_gold[1]["source"] != "gold"` (must be human-confirmed gold)

## Stage 3 Runner

### Signature
```python
def run_stage3_preferred_name(
    trial_input: dict | Path,
    *,
    upstream_gold: dict[int, Path],     # MUST contain {1: ..., 2: ...}
    output_dir: Path,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> Path:
```

### Implementation steps

1. Load Stage 1 gold (for context) and Stage 2 gold (for relations).
2. For each relation in Stage 2 gold, call Prompt 3:
   ```python
   prompt_inputs = {
       "target_text_span": rel["target_text_span"],
       "target_subtype": rel["target_subtype"],
       "full_criterion_text": ...,  # original criterion text from trial_input
   }
   ```
3. Apply fan-out logic from existing `pipeline.transforms.fanout_additional_targets()`.
4. Assemble `Stage3Record` per relation.

### Acceptance criteria
- [ ] Every Stage 2 relation has a corresponding Stage 3 record (1:1 by relation_id, plus fan-outs)
- [ ] For `target_subtype == "Biomarker"`, output includes `variants` field
- [ ] For drug classes, output includes `is_drug_class: true` and `class_members`

## Stage 4 Runner

### Signature
```python
def run_stage4_constraints(
    trial_input: dict | Path,
    *,
    upstream_gold: dict[int, Path],     # MUST contain {1: ..., 2: ...}
    output_dir: Path,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> Path:
```

### Implementation steps

1. Load Stage 2 gold.
2. **Filter to constraint relations only**: `relation_type in ("HAS_VALUE", "HAS_TEMPORAL")`.
3. For each constraint relation, **try regex first**:
   ```python
   from pipeline.regex_extractor import extract_constraints
   regex_result = extract_constraints(target_text_span, relation_type)
   if regex_result and regex_result.is_complete():
       record["extraction_source"] = "regex"
       record.update(regex_result.to_dict())
   else:
       # Fallback to Prompt 4
       llm_result = call_llm("prompt_4", {...})
       record["extraction_source"] = "llm"
       record.update(llm_result)
   ```
4. Write output.

### Acceptance criteria
- [ ] Records partition cleanly into `extraction_source: regex` and `extraction_source: llm`
- [ ] On KEYNOTE-671, regex coverage should be >60% (informational metric)
- [ ] Every record has `operator`, `value`, `unit` (or explicit nulls if not applicable)

## Stage 5 Runner

### Signature
```python
def run_stage5_alternatives(
    trial_input: dict | Path,
    *,
    upstream_gold: dict[int, Path],     # MUST contain {1: ..., 2: ..., 4: ...}
    output_dir: Path,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> Path:
```

### Implementation steps

1. Load Stage 1, 2, 4 gold.
2. **Identify candidates** that need Stage 5 processing:
   - Stage 1 `splitting_decision == "nested_exception"`, OR
   - Stage 4 constraint has `alternative_constraint` mentioned in regex result, OR
   - Criterion text matches alternative keyword regex (see `orchestrator._ALT_KEYWORDS`)
3. For each candidate, call Prompt 5.
4. Write output.

### Acceptance criteria
- [ ] Candidate selection logic matches existing `orchestrator._has_alternative_or_exception()` semantics
- [ ] On KEYNOTE-671, expect 3-8 Stage 5 records (10-20% of criteria)
- [ ] `needs_human_review: true` is set when Prompt 5 instructs it (math formula, subjective approval)

## Orchestration helper

To run all stages with gold cascade:

```python
def run_all_stages_with_gold_cascade(
    trial_input: dict | Path,
    *,
    output_dir: Path,
    gold_provider: Callable[[int, Path], Path],  # given stage N llm_output, returns gold path
    cache_dir: Path | None = None,
) -> dict[int, Path]:
    """Run all 5 stages, waiting for gold confirmation between each.

    gold_provider is typically a UI prompt or a function reading
    {output_dir}/{trial_id}/stageN/gold.json when annotators commit.
    """
    paths = {}
    upstream_gold = {}
    for stage in [1, 2, 3, 4, 5]:
        runner = STAGE_RUNNERS[stage]
        llm_path = runner(
            trial_input,
            upstream_gold=upstream_gold,
            output_dir=output_dir,
            cache_dir=cache_dir,
        )
        gold_path = gold_provider(stage, llm_path)  # blocks until annotators commit
        upstream_gold[stage] = gold_path
        paths[stage] = (llm_path, gold_path)
    return paths
```

This is for the **end-to-end pipeline** mode. The IAA experiment uses a
different orchestration where Stage 1 LLM, Stage 1 annotator A, Stage 1
annotator B all run before any Stage 2 work begins.

## Batch driver

For 8 trials, the typical entry point:

```python
def run_stage_on_all_trials(
    stage: int,
    trial_inputs: list[dict | Path],
    *,
    output_root: Path,
    upstream_gold_root: Path | None = None,
    cache_dir: Path,
) -> dict[str, Path]:
    """Run one stage on multiple trials. Returns trial_id -> output_path."""
```

This is what the annotator workflow uses: "run Stage 1 on all 8 trials,
hand off to annotators, wait for gold, run Stage 2 on all 8 trials, ..."
