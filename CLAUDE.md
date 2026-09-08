# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

GraphRAG-based AI agent for clinical trial eligibility screening (NSCLC primary domain). The current phase is **Phase 1: LLM-assisted annotation of clinical trial eligibility criteria** + a manual review workflow, plus an **inter-annotator agreement (IAA) evaluation track**. The downstream 4-layer medical ontology (Neo4j) and RAG agent are scaffolded but not the active work.

There are **three tracks** that share code but serve different goals:
- `pipeline/` — **production annotation pipeline**. Turns raw ClinicalTrials.gov / AACT criteria text into annotated JSON, loads it into Neo4j, and runs Cypher review queries.
- `iaa_pipeline/` + `streamlit_apps/` — **IAA evaluation framework**. Imports `pipeline/` as a library, re-runs stages for dual-annotator comparison, and computes Cohen's κ. Only **Stage 1 (Splitting)** is wired end-to-end; Stages 2–5 are stubs.
- `iaa_pipeline/adjudication.py` + `scripts/` — **adjudication → gold set**, the currently active work (AMIA 2027 abstract). Turns the IAA disagreements into a single adjudicated gold standard and freezes it as a hashed, dated export.

`src/graphrag_screening/` is an empty scaffold for a future folder restructure — not used yet.

## Key documentation (read these first)

**Start with `docs/CURRENT_STATUS.md`** — research state, latest evidence-set numbers, and known deferred drift. Then `docs/repository/SOURCE_OF_TRUTH.md` tells you which path is authoritative for each category (implementation contract, ontology basis, guideline basis, frozen evidence, generated output), and `docs/guidelines/stage1/CURRENT.md` fixes the Stage 1 normative precedence. Do not infer current truth from the highest-looking filename.

The two design docs below are kept current and contain far more detail than is summarized here. Read them before substantial work:
- `pipeline/PIPELINE.md` — script inventory, stage graph, data flow, current 30-trial results
- `pipeline/HANDOFF.md` — session handoff log: source-fix history, open work items, conventions, gotchas, user preferences
- `iaa_pipeline_spec/README.md` — IAA framework status, what's implemented vs stubbed
- `pipeline/REVIEW.md` / `pipeline/REVIEW_notion.md` — reviewer workflow (these two are kept in sync; edit both)

### Annotation schema — read the spec AND the patch

- `pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md` — v1.2.2 spec body
- `pipeline/schema/ontology_spec_v1_2_3_patch.md` — **v1.2.3 patch, NOT merged into the body.** 7 changes; the two that bite most often are `child_logic` now required for *both* `composite_split` and `macro_aggregate` (change 1) and `text_span` being an **array of contiguous segments** rather than a string (change 6). Read both documents together.
- `pipeline/schema/annotation_guideline_v1_2_2_notion.md` — **frozen annotation guideline** (2026-08-26). The operational rules annotators and adjudicators apply, and the source of the `§1-1` / `§T2-3` / `§C1-1` **rule IDs** that every adjudication record's `rule_id` cites (appendix 3 is the index). v1.2.2 added the IDs only — no rule text changed from v1.2.1. Frozen for the duration of adjudication: revisions found mid-adjudication are recorded as `rule_status=conflict/gap`, not edited in.
- `pipeline/schema/annotation_guideline_v1_2_1.md` — the 2026-08-25 freeze, superseded by v1.2.2. Same rules, no IDs; cite v1.2.2.
- `pipeline/schema/stage1_iaa_review_and_guideline_v1_1.md` — Round 2 IAA review record (difference areas + examples). Not guideline text.

### Adjudication track (active work, AMIA 2027 abstract critical path)

- `iaa_pipeline_spec/streamlit_status_and_gaps_2026-08-25.md` — **start here.** Implementation status vs docs, the open gaps, verification log.
- `iaa_pipeline_spec/adjudication_guide_v2_over_v1.md` — adjudicator-facing guide **v2**, with the v1→v2 change table. §2-0 fixes the adjudication reference standard: **spec v1.2.2 + v1.2.3 patch + guideline v1.2.2**. `adjudication_guide_v2_notion.md` is the trimmed Notion copy of the same guide.
- `iaa_pipeline_spec/adjudication_handover.md` — technical design rationale (§3 task list A–D, §10 implementation record)
- `iaa_pipeline_spec/audit_streamlit_v1.md` — blinding architecture (leaks A1–A7). **Read before touching any UI code.**
- `docs/amia2027_gold_freeze_2026-09-03.md` — the **current gold freeze record** (74 items). Each freeze gets its own dated doc; read the newest.
- `docs/amia2027_work_summary.md` — research-status narrative for the abstract (sampling funnel, per-area status, verified numbers).
- `docs/amia_stage1_numbers.md` / `docs/amia_stage1_trajectories.md` — **generated, do not hand-edit.** Regenerate with the scripts below.

## Production annotation pipeline (`pipeline/`)

Scripts are numbered `01`–`08` for execution order. `_archive_*` files are inactive backups (orchestrator source-fixed; kept only as a safety net for old data imports). The 5-stage LLM flow lives in `orchestrator.py`:

```
Stage A (Python)   01_criteria_extraction   AACT XML → input_trials.json
Prompt 1 (LLM)     splitting decision + cohort_scope
Prompt 2 (LLM)     semantic_category + relation_type + target_subtype
Prompt 3 (LLM)     preferred_name normalization
Stage I/J          regex (regex_extractor.py) + Prompt 4 LLM fallback → HAS_VALUE / HAS_TEMPORAL
Prompt 5 (LLM)     alternative_constraint / exception_qualifier (frontier model)
Stage N (Python)   validation
```

After annotation, three **idempotent one-shot cleanup** scripts run (`03_recover_has_value`, `04_correct_relation_type`, `05_reextract_constraints`), then `06_validate_annotation` attaches `_validation: {passed, issues}` metadata, `07_neo4j_ingest` loads Neo4j, and `08_review_queries` runs 21 Cypher queries.

**Library modules** (not numbered): `config.py` (model presets, schema enums, gap-handling rules), `orchestrator.py`, `llm_client.py`, `regex_extractor.py`, `transforms.py`, `validators.py`.

### config.py is the schema source of truth

`pipeline/config.py` holds the canonical v1.2.2 enum definitions (`SEMANTIC_CATEGORIES`, `RELATION_TYPES`, `CONCEPT_SUBTYPES`, etc.), the `RELATION_PROPERTY_WHITELIST` (allowed properties per relation_type), and `LLM_OUTPUT_STRIP_FIELDS` (fields the LLM may emit that get dropped before storage). The `SCHEMA_PATH` JSON (`ontology_v1.2.1.json`) is a dead reference — do **not** treat it as authoritative. When changing the annotation schema, edit `config.py` enums and keep `iaa_pipeline/stage_schemas.py` docstrings in sync.

### LLM provider is auto-detected

`llm_client.py` picks the provider from the model name prefix: `gpt-*` / `o3*` / `o4*` → OpenAI, `claude-*` → Anthropic. Switch models by editing the active `MODELS` preset block in `config.py` (Presets A–D). `LLM_TEMPERATURE = 0.0` for reproducibility.

## IAA framework (`iaa_pipeline/`)

Evaluation track that imports `pipeline.config`, `pipeline.llm_client`, etc. Key modules: `stage_runner.py` (only `run_stage1_splitting()` is real; Stages 2–5 raise `NotImplementedError`), `aligners.py` (record alignment — Stage 1 by `criterion_id`, Stage 2 fuzzy span via `SequenceMatcher.ratio() ≥ 0.85`), `metrics.py` (self-contained Cohen's κ, no sklearn; `compute_stage{1,2,4}_iaa()` work, Stage 3/5 stub), `cache.py` (sha256-keyed disk LLM cache; key includes prompt content + model so changing either invalidates it).

**Blinding is a hard requirement** in the annotation UIs (Stage 1/2 = `from_scratch`, blind; Stage 3–5 = `llm_assisted`). The blind render function `render_criterion_form_blind` does **not** accept an `llm_record` parameter — blinding is enforced at the function signature level. See `iaa_pipeline_spec/audit_streamlit_v1.md` before touching any UI code. The same rule applies to adjudication: `render_adjudication_form_blind` does not accept `peer_records`, and during a blind pass peer envelopes are **not read at all** (not merely hidden). There are two UIs: `iaa_pipeline/streamlit_app.py` (local, filesystem-backed) and `streamlit_apps/stage1_app.py` (hosted on Streamlit Community Cloud, stateless/session-only, shared-password auth, download workflow).

The IAA experiment uses a **stratified trial subset** listed in `iaa_pipeline_spec/iaa_8trials.txt` — the filename says 8 but the file now holds **9 trials** (NCT03800134 / AEGEAN was added later, commit `e0da99c`); the hosted app filters its dropdown to this list. Bundled trial data lives in `streamlit_apps/data/{trial_id}/stage1/{input,llm_output}.json`.

## Adjudication → gold set (`iaa_pipeline/adjudication.py` + `scripts/`)

One adjudicator (actor `GOLD`), not annotator consensus, settles each item — two annotators can agree and still both be wrong, so the gold answer is decided against the frozen reference standard with a cited `rule_id` and an evidence `tier` (0 = spec/structure alone decides, up through clinical judgement). Unresolvable items become tier-3 **gap tickets** rather than forced labels; `record_type` keeps them distinguishable from gold on every exported line.

Data flows one way and never backwards:

```
iaa_workspace/{trial}/stage1/round2/   committed envelopes (git-ignored, the live source)
  → results/adjudication/adjudication_queue.json   stratified worklist (S1/S2/S3/S4 strata)
  → STAGE1_GOLD_{N}items_{date}/                   dated frozen export + MANIFEST.txt (sha256)
  → docs/amia_stage1_*.md                          numbers recomputed FROM the frozen export
```

Every freeze is a **new dated directory**, never an edit of an existing one, and the numbers docs are regenerated from the export rather than transcribed — so an abstract figure can always be traced back to a hashed file.

**The 2026-09-03 freeze is closed.** `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/` (74 gold, 0 open gap, 8 trials, S1 49 + S4 25 — S1 stratum complete) is committed and tagged `amia2027-stage1-gold-74items-20260903`, and the adjudication reference standard is frozen at **spec v1.2.2 + v1.2.3 patch + guideline v1.2.2**. Do not edit that directory, its freeze doc, or the guideline. Remaining adjudication (S2 35, S3 4, the S4 second tranche, and the 6 `needs_recursion=true` hierarchies) continues on a new branch and lands as a **new dated freeze**; guideline v1.3 is deliberately deferred until that evidence is in, so that an item resolved by an existing rule stays distinguishable from one resolved by a rule v1.3 just added.

`build_adjudication_queue.py` **redraws the S4 audit sample** every time it runs; the seed is fixed but the sampling frame is not, and that sample is reported in the paper's Methods. To change only the working order of an existing queue, use `reorder_adjudication_queue.py`, which rewrites the `priority` column and asserts the row set is unchanged.

`iaa_workspace/` is git-ignored (bundled UI data lives in `streamlit_apps/data/` instead), so the frozen export directories are the only committed record of an adjudication result — treat them as append-only.

**Frozen evidence lives under `evidence/`** (`evidence/README.md` for the convention). The current bundle is `evidence/stage1/adjudication_v1_2_2_2026-09-07/` — 113 gold / 0 gap / 8 trials, committed at `80f0f28` and tagged `stage1-adjudication-complete-2026-09-08`. It carries `SHA256SUMS`, the exact adjudication queue (unreproducible — `build_adjudication_queue.py` redraws S4), and immutable copies of the R1/R2/GOLD envelopes that `iaa_workspace/` alone could not preserve. The root `STAGE1_GOLD_113items_2026-09-07/` holds the same gold payload because `scripts/amia_stage1_*.py` glob the repo root for `*GOLD_*items_*`; deleting it silently regresses those scripts to the 74-item freeze.


## Common commands

```bash
# Install
pip install -e .              # core
pip install -e ".[dev]"       # + pytest, jupyter
pip install -e ".[iaa]"       # + streamlit, typing_extensions (IAA UIs)

# Production pipeline — run from project root.
# Scripts using relative imports (02) MUST run via -m; the numeric prefix is fine here.
python -m pipeline.02_llm_annotation --trial NCT03425643          # one trial
python -m pipeline.02_llm_annotation                              # full batch (resumes by default)
python pipeline/03_recover_has_value.py                          # cleanup scripts run as files
python pipeline/06_validate_annotation.py 2>&1 | tail -15        # validation summary (expect 30 trials / 40 issues)
python -m pipeline.07_neo4j_ingest --reset --trial NCT03425643   # Neo4j load
python pipeline/08_review_queries.py --trial NCT03425643         # run 21 Cypher review queries
python pipeline/review_session.py --trial NCT03425643            # reviewer walk-through (REVIEW.md Step 2-5) → xlsx

# IAA
python -m iaa_pipeline.cli stage1 streamlit_apps/data/NCT03425643/stage1/input.json \
    --output-dir iaa_workspace/ --cache-dir cache/               # Stage 1 LLM extraction
bash scripts/run_iaa_ui.sh                                       # local annotation UI
streamlit run streamlit_apps/stage1_app.py                       # hosted-style UI
python scripts/compute_iaa.py --include-llm                      # κ from committed envelopes
python scripts/compute_iaa.py --stage 1 --round 2                # round-subfolder envelopes
python scripts/compare_rounds.py                                 # round1→round2 Δ table (2-axis SD)
python scripts/convert_production_to_iaa.py                      # production output → IAA envelopes (0 LLM calls)

# Adjudication / gold set (iaa_pipeline_spec/adjudication_handover.md)
python scripts/build_adjudication_queue.py --out results/adjudication   # stratified worklist (113 items)
                                                                       # WARNING: redraws the S4 audit sample
python scripts/reorder_adjudication_queue.py                            # reorder an EXISTING queue (priority only, row set asserted identical)
python scripts/tier0_check.py --round 2 --out results/adjudication      # spec-violation hygiene check
python scripts/export_adjudicated_dataset.py --strict                   # freeze committed GOLD → dated export dir + MANIFEST (sha256)
python scripts/amia_stage1_numbers.py --out docs/amia_stage1_numbers.md # abstract numbers, recomputed from the frozen export
python scripts/amia_stage1_trajectories.py --strict \
    --out docs/amia_stage1_trajectories.md                              # Table 1 round1→round2 trajectories (read-only; cross-checks vs the frozen export)
streamlit run iaa_pipeline/streamlit_app.py    # sidebar: Role = Adjudicator, Round = 2

# Tests (no LLM / no streamlit runtime needed)
python tests/test_iaa_metrics.py        # 44 tests, script mode
python tests/test_adjudication.py       # 50 tests, adjudication logic
python -m pytest tests/test_iaa_metrics.py tests/test_adjudication.py -v
```

## Environment / gotchas

- **Two `.env` files, separate concerns**: `./.env` (project root) holds Neo4j creds (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`); `pipeline/.env` holds `OPENAI_API_KEY`. New scripts that need both must `load_dotenv` from both locations.
- **Numeric module-name caveat**: files like `02_llm_annotation.py` that use relative imports (`from .orchestrator import ...`) must be run with `python -m pipeline.02_llm_annotation`. Files using absolute imports (`from pipeline.xxx import ...`, e.g. `03`, `05`) are run as `python pipeline/03_*.py` from the project root. Match the existing pattern per file rather than assuming one form.
- **Neo4j**: only one local instance can run at a time (port 7687). Requires Neo4j 5.x / 2025.x / 2026.x.
- **`pipeline/output/` is git-untracked** (reproducible data, intentionally excluded). The 30-trial `_validation` JSONs live there.
- **Never commit secrets** into `.streamlit/secrets.toml` (gitignored; `.example` is a placeholder only) — a near-miss is documented in HANDOFF §13-3.

## Conventions

- Promote a review finding to a `validators.py` rule (R1–R4 relation / C1–C3 criterion) only when the same pattern appears in **≥3 trials**.
- Push to remote **only when explicitly asked**. Get user confirmation before large changes.
- The user prefers **Korean responses**, honest tradeoff assessments, and simple practical solutions over elaborate automation (see HANDOFF §9 "사용자 선호").
- `AGENTS.md` is a Codex-facing mirror of this file; when you change CLAUDE.md's shared content, update it too. Its current copy was produced by a find/replace that mangled some strings (e.g. it claims `Codex-*` model names route to Anthropic — the real rule is `claude-*`), so read `CLAUDE.md` as authoritative where the two disagree.
- Numbers that appear in the abstract are **generated, never transcribed** — regenerate `docs/amia_stage1_*.md` from the frozen export instead of editing a figure by hand.
