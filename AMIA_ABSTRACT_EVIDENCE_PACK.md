# AMIA 2027 Abstract Evidence Pack — Stage 1 IAA & Adjudication

> Audit date: 2026-08-24 (Asia/Seoul)  
> **Re-audit: 2026-09-03** — adjudication outcomes are now available. Sections 1, 2.1–2.3, 3.6, 3.7, 3.9, and 4–7 were updated against the frozen 74-item gold export; sections 3.1–3.5 and 3.8 concern Round 1/2 annotator envelopes only and are **unchanged**, having been re-verified as still reproducing.  
> Scope: Stage 1 splitting IAA, Round 1→2 changes, adjudication preparation, and (new) adjudication outcomes  
> Evidence priority: committed raw envelopes → executable calculation code → generated result files. Existing narrative summaries were not treated as sources of truth. Adjudication outcomes were read from the frozen export and the GOLD envelopes, **not** from `docs/amia_stage1_numbers.md` or the freeze narratives, which were treated as claims to be checked rather than sources.  
> Mutation policy: the original audit created this file only. The 2026-09-03 re-audit likewise modified no other repository file; it re-ran read-only commands and read the already-frozen export.

## 1. Executive evidence status

- **Defensible study sample:** 8 trials, 172 criterion pairs, two annotators, with complete committed envelopes in both rounds. The current selection list contains 9 trial IDs, but one listed trial (`NCT03425643`) has no Round 1/2 committed envelopes and therefore is not part of the measured IAA.
- **Primary Stage 1 result:** 4-class splitting-decision Cohen's κ increased from **0.6081 to 0.6500**. Observed agreement increased from **136/172 (79.07%) to 138/172 (80.23%)**, an absolute increase of **2/172 = 1.16 percentage points**.
- **Round transition:** among 172 criterion pairs, 123 stayed agreed, 21 stayed disagreed, 15 changed disagreement→agreement, and 13 changed agreement→disagreement. Thus net agreement gain was 2, while Round 2 still had 34 disagreements.
- **Child logic:** κ increased from **0.7626 (30/33 agreements)** to **0.8671 (38/40 agreements)**, but denominators changed because the metric is restricted to pairs where both annotators selected `composite_split`. It is not a fixed-cohort pre/post comparison.
- **Adjudication status (updated 2026-09-03):** the generated queue contains **113 items across the same 8 measured trials**: S1 49, S2 35, S3 4, and a fixed-seed S4 sample of 25 from a frame of 84. **74 of the 113 are now adjudicated and frozen** — all 49 S1 items and all 25 S4 items; **S2 (35) and S3 (4) are not adjudicated**. Every adjudicated criterion is one of the 172 measured pairs. Frozen at `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/` with a sha256 manifest.
- **Adjudication outcome:** on the 74 adjudicated criteria the gold label matched EHJ on **54/74 (73.0%)** and DYK on **51/74 (68.9%)**. These pooled figures mix two deliberately unequal strata and must not be reported without them: on **S4** (fixed-seed random sample of criteria where both annotators already agreed) gold confirmed the shared answer in **24/25**, whereas on **S1** (the disagreement stratum) gold matched EHJ in **30/49** and DYK in **27/49**. In **6 of 74** criteria the settled label is one a 2-of-3 majority vote could not have produced: 3 where both annotators agreed and gold overrode both, and 3 where gold adopted neither annotator's label.
- **⚠ Adjudicator is not independent of the annotators:** the adjudicator is **EHJ**, one of the two annotators and the author of the annotation guideline; this is stated in `iaa_pipeline_spec/adjudication_guide_v2_notion.md` but is **not recoverable from any data artifact** (GOLD envelopes carry only `annotator: "GOLD"`, with no adjudicator identity field). EHJ-vs-gold agreement is therefore **not an independent comparison** and is closer to intra-annotator test–retest than to accuracy against an external reference. DYK-vs-gold is the only cross-person gold comparison. Documented mitigations: mandatory blind first pass, PI escalation for undecidable items, and self-reported `rule_status=conflict`.
- **Adjudication procedure:** all 74 records carry `pass="blind"` and none carry `pass="revealed"`, so the blind→revealed revision analysis (D-3) has **zero sample**; `blind_label` equals the gold label on all 74 by construction. `rationale_short` is present on 74/74.
- **Tier-0 status:** Round 2 has **3 violation rows affecting 2 criterion–annotator records** among 344 annotator records (16 envelopes): one `<2 children` violation and two null-child-logic violations. “3 Tier-0 cases” is ambiguous and should be avoided.
- **Few-shot overlap:** `examples.json` contains a Stage 1 example sourced from `NCT01295827`, which is also an IAA trial. However, the example text (`KEYNOTE-001 I1_F`) is not an exact criterion in the IAA input file. This is same-trial provenance overlap, not record-level overlap. Whether annotators saw that example or derived guidance cannot be established from the envelopes because they contain no prompt/guideline version metadata.

## 2. Audited data lineage

### 2.1 Raw observations

The measured observations are the 32 committed annotator envelopes under:

```text
iaa_workspace/{trial_id}/stage1/round{1,2}/{EHJ,DYK}_*_committed.json
```

There are 8 trials × 2 annotators × 2 rounds = 32 envelopes. Each round contains 16 envelopes and 344 records; pairing EHJ and DYK by `criterion_id` gives 172 matched criterion pairs with no unmatched records.

Adjudication outcomes (re-audit) add a second raw source, 8 GOLD envelopes containing 74 records:

```text
iaa_workspace/{trial_id}/stage1/round2/GOLD_{trial_id}_stage1_committed.json
iaa_workspace/{trial_id}/stage1/round2/gap_tickets.json      (1 trial only, empty)
```

All 8 GOLD envelopes have `committed: true`; their record counts sum to 74 and match the frozen export line-for-line. All 74 criterion IDs are inside the 172 matched pairs, and all 74 are inside the 113-item queue.

Measured trials and per-round matched denominators:

| Trial | Criterion pairs |
|---|---:|
| NCT01295827 | 25 |
| NCT02075840 | 22 |
| NCT02125461 | 11 |
| NCT02474355 | 20 |
| NCT02912949 | 25 |
| NCT03728556 | 28 |
| NCT03800134 | 22 |
| NCT05756153 | 19 |
| **Total** | **172** |

### 2.2 Calculation path

- Envelope discovery: `scripts/compute_iaa.py::discover_sources`
- Record alignment: `iaa_pipeline/aligners.py::align_stage1`, keyed by `criterion_id`
- Categorical κ: `iaa_pipeline/metrics.py::cohens_kappa`
- Stage 1 metrics: `iaa_pipeline/metrics.py::compute_stage1_iaa`
- Binary/type decomposition: `iaa_pipeline/metrics.py::compute_sd_axes`
- Child-count and span metrics: `iaa_pipeline/metrics.py::compute_split_degree_agreement`
- Round comparison: `scripts/compare_rounds.py`
- Queue construction: `scripts/build_adjudication_queue.py::build_rows`, `sample_s4`, and `sort_queue`
- Tier-0 scan: `scripts/tier0_check.py::check_record` and `scan`
- Gold freeze/export and its structural validation: `scripts/export_adjudicated_dataset.py::collect_lines`, `validate`
- Abstract-number regeneration from the frozen export: `scripts/amia_stage1_numbers.py`
- Round-transition trajectories and stratum cross-checks: `scripts/amia_stage1_trajectories.py`

### 2.3 Verification procedure

Each reported number below was checked in three ways where applicable:

1. read from the committed Round 1/2 envelopes;
2. regenerated by executing the current repository scripts without output-writing options;
3. compared with `results/iaa/round{1,2}/iaa_stage1.json` or adjudication result files.

An additional independent aggregation directly counted labels and transitions from the 32 envelopes and recomputed κ from `κ=(p_o-p_e)/(1-p_e)`. It reproduced the primary and child-logic results to floating-point precision.

For the 2026-09-03 re-audit, every adjudication number in §3.6 and §3.9 was recomputed the same way: labels were read from the frozen export and the round-2 annotator envelopes, and κ was recomputed from `κ=(p_o-p_e)/(1-p_e)` **without importing `iaa_pipeline.metrics`**. The independent values reproduce `scripts/compute_iaa.py --include-llm` and `scripts/amia_stage1_numbers.py` to 4 decimal places (EHJ-gold κ 0.5241, DYK-gold κ 0.4941, EHJ-DYK on the same 74 κ 0.2860). Stratum membership was cross-checked against `results/adjudication/adjudication_queue.json` rather than against narrative documents.

## 3. Claim registry

### 3.1 Sample and completeness claims

| Claim | Value | Denominator | Trial count | Raw/result source | Generating code | Definition | Unresolved inconsistency / abstract wording |
|---|---:|---:|---:|---|---|---|---|
| Trials with complete Round 1 and Round 2 dual annotations | 8 | 9 IDs in current selection list | 8 measured | `iaa_workspace/*/stage1/round{1,2}/*committed.json`; `iaa_pipeline_spec/iaa_8trials.txt` | `discover_sources` in `scripts/compute_iaa.py` | Trial must contain committed EHJ and DYK envelopes for the specified round | File name says 8 but contains 9. `NCT03425643` is listed but has no committed round envelopes. Say “8 trials with complete paired annotations,” not “9 trials.” |
| Matched criterion pairs per round | 172 | 172 aligned IDs | 8 | 32 raw envelopes; `results/iaa/round1/iaa_stage1.json`; `round2/...` | `align_stage1`; pooled `compute_stage1_iaa` | Intersection of EHJ and DYK `criterion_id` values pooled across included trials | No unresolved numerical inconsistency; all 172 are matched in both rounds. |
| Annotator records scanned per round | 344 | 16 envelopes | 8 | raw envelopes; live `tier0_check.py --round 1/2` | `tier0_check.scan` | All records across both annotators, not paired units | Do not use 344 as the IAA denominator; the paired denominator is 172. |
| Annotators | 2 | — | 8 | envelope `annotator` fields | `discover_sources` | EHJ and DYK | Envelopes lack role/training metadata; describe expertise only from external study records, not this repository. |

### 3.2 Primary splitting-decision claims

| Claim | Round 1 | Round 2 | Change | Denominator | Source | Generating function / definition | Unresolved inconsistency / abstract wording |
|---|---:|---:|---:|---:|---|---|---|
| 4-class splitting-decision κ | 0.6081 | 0.6500 | +0.0420 | 172 pairs each | raw envelopes; `results/iaa/round{1,2}/iaa_stage1.json`; live `compute_iaa.py` | `cohens_kappa` over `composite_split`, `macro_aggregate`, `nested_exception`, `none` | Rounded 3-decimal wording: 0.608→0.650. |
| Exact label agreements | 136 | 138 | +2 | 172 | same | exact equality of 4-class labels | This is the count underlying observed agreement. |
| Observed agreement | 79.07% | 80.23% | **+1.16 percentage points** | 172 | same; independent count | `n_agree / n` | `compare_rounds.py` displays `+0.012` after rounding. Do not call this a 1.2% relative increase; it is 1.16 percentage points. |
| Expected chance agreement | 46.60% | 43.52% | −3.08 percentage points | 172 | live current code; independent marginals | sum of the products of annotator class marginals | Saved June result JSONs do not include this field because current expected-agreement reporting was added later/uncommitted. Reproducible from raw labels. |
| 4-class disagreements | 36 | 34 | −2 | 172 | raw labels; queue counters | unequal splitting-decision labels | Net reduction hides substantial churn; report transition counts if interpreting improvement. |
| Binary split-vs-none κ | 0.642 | 0.683 | +0.041 | 172 | live `compute_iaa.py`; `compare_rounds.py` | `composite`, `macro`, and `nested` collapsed to `split`; compared against `none` | Derived by current uncommitted analysis code and absent from the stored June JSON. Label as post hoc/secondary unless prespecified elsewhere. |
| Type κ among pairs where both split | 0.683 | 0.718 | +0.034 | 50 (R1), 59 (R2) | live scripts; raw labels | 3-class κ only where both labels are in the split set | Changing denominator; not a fixed-pair pre/post comparison. |

Round-specific label marginals, which explain the expected-agreement shift:

| Round | Annotator | none | composite | macro | nested | Total |
|---|---|---:|---:|---:|---:|---:|
| 1 | EHJ | 113 | 42 | 6 | 11 | 172 |
| 1 | DYK | 102 | 50 | 12 | 8 | 172 |
| 2 | EHJ | 110 | 45 | 7 | 10 | 172 |
| 2 | DYK | 89 | 65 | 7 | 11 | 172 |

The κ gain (+0.0420) accompanied only two additional exact agreements, while expected agreement fell by approximately 3.08 percentage points because the marginal label distributions changed. The repository supports describing this as a **marginal-distribution-sensitive κ increase**. Calling it an “artifact” or claiming a causal mechanism is a stronger interpretation and should be qualified.

### 3.3 Round 1→2 transition claims

| Transition | Value | Denominator | Trial count | Raw/result source | Generating code / definition | Unresolved inconsistency |
|---|---:|---:|---:|---|---|---|
| Agreed in both rounds | 123 | 172 | 8 | direct raw-envelope comparison | equality in R1 and equality in R2 for same trial/criterion | Not directly emitted by `compare_rounds.py`; independently counted from raw. |
| Disagreed in both rounds (“persistent”) | 21 | 172 | 8 | raw; queue JSON counters | R1 unequal and R2 unequal | `build_adjudication_queue.py` calls this `s1_persist`. |
| Disagreement→agreement (“resolved”) | 15 | 172 | 8 | raw; queue JSON counters | R1 unequal, R2 equal | “Resolved” means inter-annotator agreement only, not adjudicated correctness. |
| Agreement→disagreement (“new”) | 13 | 172 | 8 | raw; queue JSON counters | R1 equal, R2 unequal | “New” means new disagreement, not new criterion. |
| S1 union | 49 | 172 | 8 | queue JSON/CSV | any R1 or R2 SD disagreement = 21+15+13 | S1 is a queue stratum, not Round 2 disagreement count. |
| EHJ-only split | 9→3 | binary-disagreement subset | 8 | raw; live scripts | EHJ split and DYK `none` | Actor direction depends on argument order; current report’s DYK-vs-EHJ line reverses display order. Values here are explicitly EHJ-only. |
| DYK-only split | 20→24 | binary-disagreement subset | 8 | raw; live scripts | DYK split and EHJ `none` | Same argument-order caveat. |
| Split-type mismatch | 7→7 | both-split subset | 8 | raw; live scripts | both split but 3-class types differ | Denominator of both-split pairs changed 50→59. |

Conservation check: Round 1 disagreements = 21 persistent + 15 resolved = 36; Round 2 disagreements = 21 persistent + 13 new = 34; Round 2 agreements = 123 stable + 15 resolved = 138.

### 3.4 Child-logic claims and specification versioning

| Claim | Round 1 | Round 2 | Denominator | Source | Generating function / definition | Unresolved inconsistency / safe wording |
|---|---:|---:|---:|---|---|---|
| Child-logic κ | 0.7626 | 0.8671 | 33, 40 | raw; result JSON; live scripts | `compute_stage1_iaa`: only criterion pairs where **both** chose `composite_split`; missing values would become a `null` class | Use “among co-composite pairs.” Do not imply all 172 criteria were assessed. |
| Child-logic agreements | 30/33 (90.91%) | 38/40 (95.00%) | changing subset | raw; result JSON | exact AND/OR equality | κ change is +0.1045 unrounded (+0.105 at 3 decimals); older narrative may show +0.104 due subtracting rounded values. |
| Observed child-logic classes | AND, OR | AND, OR | 33, 40 | raw envelopes | direct class count | No XOR and no null values occurred in the scored co-composite subsets. |
| Schema enum | AND/OR | AND/OR | schema-level | `pipeline/config.py`; `iaa_pipeline/stage_schemas.py`; ontology v1.2.2 | v1.2.2 removed XOR | Current `iaa_pipeline_spec/03_json_schemas.md` is internally stale: line-level record definition still mentions XOR and table says “3-class + null.” |

Version findings:

1. The ontology and executable schema define `CHILD_LOGIC = {AND, OR}` for v1.2.2; XOR was removed after zero occurrences in the 30-trial stress test.
2. Git history contains commit `126b97c` intended to remove XOR from `03_json_schemas.md`, but the current checked-out file still contains XOR and “3-class + null.” This repository state should be treated as an unresolved documentation/version inconsistency.
3. The raw envelopes do not store `schema_version`, `prompt_version`, or guideline version. Therefore the exact instructional version used by each annotator/round cannot be proven from the data artifacts alone.
4. The Round 1 and Round 2 child-logic denominators differ (33 vs 40). The increase should not be framed as improvement on an identical set of records without a fixed-subset sensitivity analysis.

### 3.5 Structural decomposition claims

| Claim | Round 1 | Round 2 | Denominator | Source | Function / definition | Unresolved inconsistency / status |
|---|---:|---:|---:|---|---|---|
| Exact child-count agreement among criteria split by either annotator | 0.4304 | 0.5930 | 79, 86 | raw; result JSON; live scripts | equal number of `sub_criteria`, restricted to pairs with at least one nonzero child count | Auxiliary metric added after the base framework; changing denominator. |
| Span alignment F1 | 0.5560 | 0.6766 | micro totals across 172 pairs | raw; result JSON; current metrics | token-set Jaccard ≥0.5, greedy one-to-one span matching; `2M/(|A|+|B|)` | Algorithmic auxiliary metric, not direct human-label κ. Threshold and greedy matching must be disclosed if used. |
| Cohort exact match | 0.9826 | 0.9826 | 172 each | result JSON; current metrics | union of record/child cohort sets, ignoring child IDs | This implementation intentionally decouples cohort assignment from split structure. |
| Cohort mean Jaccard | 0.9884 | 0.9903 | 172 each | result JSON; current metrics | mean set Jaccard; empty/empty = 1 | Difference is small and not a primary claim. |

### 3.6 Adjudication queue claims

| Claim | Value | Denominator | Trial count | Raw/result source | Generating code / definition | Unresolved inconsistency / abstract wording |
|---|---:|---:|---:|---|---|---|
| Queue total | 113 | 172 matched criteria | 8 | `results/adjudication/adjudication_queue.{json,csv}`; live builder | S1 + S2 + S3 + sampled S4, mutually exclusive priority order | Planned workload. **74/113 adjudicated as of 2026-09-03** (see §3.9); the remaining 39 are S2+S3. |
| S1 | 49 | 172 | 8 | queue result | any SD disagreement in either round | 21 persistent + 15 resolved + 13 new. |
| S2 | 35 | remaining non-S1 | 8 | queue result | strong text-risk signal or hard-coded conflict after S1 exclusion | Pattern-based risk stratum; not a validated error count. |
| S3 | 4 | remaining non-S1/S2 | 8 | queue result | child-count or span mismatch despite SD agreement | Depends on token-Jaccard/greedy span algorithm. |
| S4 sampled | 25 | frame 84 | 8 | queue JSON metadata | `random.Random(20260730).sample` over criterion-ID-sorted S4 frame | Coverage is 25/84; not a census of agreements. |
| Current GOLD records *(2026-09-03)* | **74** | 113 queued | 8 | 8 `GOLD_*_stage1_committed.json`, all `committed: true`; frozen export | `iaa_pipeline/adjudication.py` / UI writer; `export_adjudicated_dataset.py` | Gold-set size and gold-axis agreement are now reportable **with stratum denominators** (§3.9). Do not report a single pooled accuracy figure alone. |
| Adjudicated per stratum *(2026-09-03)* | S1 49/49, S4 25/25, S2 0/35, S3 0/4 | 113 | 8 | export `adjudication.queue_stratum` × queue JSON | set intersection of gold IDs with each queue stratum | Coverage is **complete for S1 and S4 and zero for S2 and S3**. The gold set is therefore not a sample of the queue; it is two whole strata. |
| Current gap tickets *(2026-09-03)* | 0 tickets, 1 file | 74 adjudicated | 8 | `NCT03728556/.../gap_tickets.json` = `[]`; no file in the other 7 trials | `gap_tickets_path` / adjudication save flow | The one file that exists is empty, so among the 74 adjudicated criteria no item was recorded as undecidable. The 7 absent files still mean "not written," not "zero." Do not report "0 gap tickets" for the full 113. |

The queue builder’s current estimate is 9.4–15.1 hours at 5–8 minutes per item. That estimate is a planning assumption, not an observed study result.

### 3.7 Tier-0 claims

| Claim | Round 1 | Round 2 | Denominator | Source | Generating function / definition | Unresolved inconsistency / safe wording |
|---|---:|---:|---:|---|---|---|
| Violation rows | 2 | 3 | 344 records / 16 envelopes per round | live `tier0_check.py`; Round 2 CSV | each triggered rule emits one row | One record may trigger multiple rules. |
| Affected criterion–annotator records | 1 | 2 | 344 | raw + CSV | unique `(trial, criterion_id, actor)` | Prefer this as the number of affected annotations. |
| `composite_split` records scanned | 92 | 110 | 344 records | live scanner | count of records labeled composite | Useful denominator for rule applicability. |
| `<2 children` flags | 1 | 1 | 92 / 110 composite records | raw + scanner | composite with fewer than 2 children | Same EHJ `NCT02474355_E10` persists. |
| Null/blank child-logic flags | 1 | 2 | 92 / 110 composite records | raw + scanner | composite with null/blank `child_logic` | Round 2 adds DYK `NCT02125461_E3`; EHJ `NCT02474355_E10` also triggers this rule. |

Round 2 exact affected records:

- EHJ, `NCT02474355_E10`: two violations (`sub_criteria=1`, `child_logic=null`).
- DYK, `NCT02125461_E3`: one violation (`child_logic=null`).

Tier-0 only identifies labels that violate two executable structural rules. It does not adjudicate the correct replacement label, and the scanner deliberately does not implement semantic checks requiring Stage 2 fields.

⚠ **Naming collision — two unrelated "Tier 0"s.** `tier0_check.py` "Tier-0 violations" are *annotator labels breaking a structural rule* (2 affected records in Round 2). The gold records' `adjudication.tier` is a different scale entirely: the *authority level the adjudicator used to settle the item* (0 = spec structural constraint, 1 = clinical evidence, 2 = guideline rule), and 6 of the 74 gold records carry `tier: 0` (§3.9). These numbers must never be combined or cross-referenced. Both Round-2 Tier-0 violation records were subsequently adjudicated: `NCT02474355_E10` (EHJ, `composite_split` with 1 child and null `child_logic`) settled to `none` under guideline §3-1, and `NCT02125461_E3` (DYK, `composite_split` with null `child_logic`) settled to `none` under §4-3 — a case where neither annotator's label was adopted.

### 3.8 NCT01295827 few-shot overlap audit

| Question | Finding | Evidence | Consequence |
|---|---|---|---|
| Is NCT01295827 in measured IAA? | Yes; 25 paired criteria in both rounds | raw Round 1/2 envelopes | It contributes 25/172 pairs. |
| Is NCT01295827 represented in Stage 1 few-shot examples? | Yes | `pipeline/prompts/examples.json`, source `KEYNOTE-001 I1_F (NCT01295827)` | Trial-level provenance overlap exists. |
| Is the few-shot text an exact IAA input criterion? | No exact text match; no IAA criterion ID `I1_F` exists | `iaa_workspace/NCT01295827/stage1/input.json` contains I1–I9 and E1–E16 | Do not call this direct criterion leakage based on current files. |
| Were annotators exposed to LLM output? | UI design is blind, but envelopes alone cannot prove the full operational exposure history | blinding code/audit docs; envelopes have no exposure metadata | Phrase as “blind UI design,” not as a fully auditable exposure guarantee. |
| Were annotators exposed to the same-trial few-shot example through a guideline or prompt? | Unresolved | no prompt/guideline version fields in envelopes; no session log establishing materials viewed | This should be disclosed as a possible same-trial familiarity/contamination risk if the example was available during training or guideline review. |
| Does same-trial overlap invalidate all NCT01295827 IAA records? | Not established | example is a distinct fragment not present in the IAA criterion list | Consider a sensitivity analysis excluding NCT01295827 before making strong generalization claims. |

Recommended pre-submission sensitivity analysis: recompute pooled primary metrics after excluding all 25 NCT01295827 pairs and report whether conclusions change. This audit did not add such a result to the claim registry because no repository-generating script currently emits it and the request was evidence auditing rather than code modification.

### 3.9 Adjudication outcome claims (added 2026-09-03)

Source: `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/AMIA_2027_STAGE1_ADJUDICATED_74items_2026-09-03.jsonl` (74 lines, all `record_type="gold"`, 0 gap tickets, 8 trials, 0 duplicate IDs, 0 span violations under `export_adjudicated_dataset.py --strict`).

#### 3.9.1 Composition

| Claim | Value | Denominator | Source | Definition | Unresolved inconsistency / abstract wording |
|---|---:|---:|---|---|---|
| Adjudicated criteria | 74 | 113 queued / 172 matched | 8 GOLD envelopes; frozen export | records in committed GOLD envelopes | Two complete strata, **not** a sample of the queue. Never describe as "74 of 113 sampled." |
| Trials represented | 8 | 8 measured | export `trial_id` | same 8 trials as the IAA | No trial is unrepresented. |
| Queue stratum | S1 49, S4 25 | 74 | export `adjudication.queue_stratum` × queue JSON | assigned at queue build | S2 (35) and S3 (4) are **entirely unadjudicated**. |
| Gold `splitting_decision` | none 39, composite_split 28, nested_exception 5, macro_aggregate 2 | 74 | export | 4-class label | — |
| Criterion type | exclusion 42, inclusion 32 | 74 | `stage1/input.json` join | source `type` field | — |
| `adjudication.tier` | 0 → 6, 1 → 2, 2 → 66 | 74 | export | authority level used to settle | **Not** `tier0_check.py` violations; see §3.7 warning. |
| `rule_status` | existing 64, new 9, conflict 1 | 74 | export | adjudicator's classification of the rule applied | `conflict` = `NCT05756153_E6`, the guideline author flagging their own rule. |
| `escalate_pi=true` | 3 | 74 | export | referred to PI | `NCT02125461_I2`, `NCT03728556_I3`, `NCT05756153_E6`. |
| `pass` | blind 74, revealed 0 | 74 | export | single blind pass | D-3 (blind ≠ gold) has **zero sample**; 0/74 records differ from their `blind_label`. |
| `rationale_short` present | 74/74 | 74 | export | non-empty rationale | The handover's C-2 requirement is met on every record. |

#### 3.9.2 Agreement against the adjudicated label

κ recomputed independently from `κ=(p_o-p_e)/(1-p_e)` on the 4-class `splitting_decision`.

| Pair | n | agreed | observed | expected | κ |
|---|---:|---:|---:|---:|---:|
| EHJ vs GOLD | 74 | 54 | 0.7297 | 0.4321 | 0.5241 |
| DYK vs GOLD | 74 | 51 | 0.6892 | 0.3857 | 0.4941 |
| EHJ vs DYK, same 74 | 74 | 40 | 0.5405 | 0.3565 | 0.2860 |
| EHJ vs DYK, full Round 2 | 172 | 138 | 0.8023 | 0.4352 | 0.6500 |

**Stratified breakdown — required whenever these figures are reported.** The pooled row is a mixture of two strata that were sampled on opposite criteria, so the pooled value is an artifact of the queue design, not an estimate of anything:

| Stratum | n | EHJ = GOLD | DYK = GOLD | EHJ = DYK | EHJ-GOLD κ | DYK-GOLD κ |
|---|---:|---:|---:|---:|---:|---:|
| S1 (disagreement stratum, census) | 49 | 30 | 27 | 15 | 0.3847 | 0.2560 |
| S4 (fixed-seed sample of agreements) | 25 | 24 | 24 | 25 | 0.8918 | 0.8918 |
| Pooled | 74 | 54 | 51 | 40 | 0.5241 | 0.4941 |

S4 is the only stratum with a defined sampling frame (25 drawn by `random.Random(20260730).sample` from 84 criteria on which both annotators agreed), so it is the only one that supports an inferential statement, and only about criteria where the annotators already agreed. S1 is a census of disagreements, not a sample.

Label marginals on the 74-item subset, which explain the low expected-agreement values:

| Actor | none | composite | macro | nested |
|---|---:|---:|---:|---:|
| EHJ | 49 | 15 | 5 | 5 |
| DYK | 28 | 35 | 5 | 6 |
| GOLD | 39 | 28 | 2 | 5 |

The gold marginal sits between the two annotators on the `none`/`composite` axis. This is consistent with the split-direction bias reported in §3.3 but does **not** establish that gold is a midpoint or a compromise; it is a description of one stratified subset.

#### 3.9.3 What adjudication changed

| Outcome | n | Definition |
|---|---:|---|
| Annotators agreed, gold confirmed | 37 | `EHJ == DYK == GOLD` |
| Annotators split, gold sided with EHJ | 17 | `EHJ != DYK`, `GOLD == EHJ` |
| Annotators split, gold sided with DYK | 14 | `EHJ != DYK`, `GOLD == DYK` |
| **Annotators agreed, gold overrode both** | **3** | `EHJ == DYK`, `GOLD != EHJ` |
| **Annotators split, gold chose a third answer** | **3** | `EHJ != DYK`, `GOLD` equals neither |

Per stratum: S1 (n=49) sided-EHJ 17, sided-DYK 14, confirmed 13, third answer 3, overrode both 2. S4 (n=25) confirmed 24, overrode both 1.

The **6** bottom rows are the load-bearing claim: with two annotators and an adjudicator as a third vote, a 2-of-3 majority can never override a unanimous pair and can never return a label neither annotator gave. These 6 criteria are exactly the cases majority voting could not produce.

- Unanimous overrides (3): `NCT01295827_I2`, `NCT03728556_E5`, `NCT03728556_E17`.
- Third answers (3): `NCT02125461_E3`, `NCT03800134_I9`, `NCT05756153_I8`.

Caveat: 1 of the 3 unanimous overrides falls in S4 and 2 in S1, so the rate cannot be projected onto the full corpus from this design.

#### 3.9.4 Adjudicator independence — unresolved

| Question | Finding | Evidence | Consequence |
|---|---|---|---|
| Who adjudicated? | EHJ — one of the two annotators, and the author of the annotation guideline | `iaa_pipeline_spec/adjudication_guide_v2_notion.md` §"내가 라벨러였다는 점" | EHJ-vs-gold is **not** an independent comparison. |
| Is this recoverable from the data? | No | GOLD envelopes carry `annotator: "GOLD"` only; `adjudication` has no adjudicator identity field | Must be disclosed in prose; it cannot be audited from the artifacts. |
| Was there a second adjudicator? | No | one GOLD actor across all 8 envelopes | No adjudicator reliability (κ between adjudicators) can be reported. |
| Documented mitigations | Mandatory blind first pass; PI escalation; self-reported `rule_status=conflict` | guide §1; `pass="blind"` on 74/74; 1 conflict recorded | Mitigations are real and were exercised, but they do not restore independence. |
| Time separation | EHJ's Round 2 envelopes were committed **2026-06-12 to 06-26**; adjudication was drafted **2026-08-26 to 08-31** and committed **2026-09-02 to 09-03** — a gap of roughly **9 to 12 weeks** | `created_at` / `committed_at` on the 8 EHJ and 8 GOLD round-2 envelopes | Supports a test–retest reading of EHJ-vs-gold, not an accuracy reading. The guide's own estimate ("6주 넘게", over 6 weeks) understates the measured gap; cite the envelope timestamps rather than the guide. |

Safe framing: report **DYK vs gold** as the cross-person comparison, report EHJ vs gold explicitly labeled as the adjudicator's own prior labels, and do not average the two into a single "annotator accuracy."

## 4. Reproducibility commands used

These commands are read-only when run without `--out`:

```bash
python scripts/compute_iaa.py --stage 1 --round 1
python scripts/compute_iaa.py --stage 1 --round 2
python scripts/compare_rounds.py
python scripts/build_adjudication_queue.py
python scripts/tier0_check.py --round 1
python scripts/tier0_check.py --round 2
```

Added for the 2026-09-03 re-audit. The first is read-only; the second and third rewrite only the named output paths and were run against the already-frozen export:

```bash
python scripts/amia_stage1_trajectories.py --strict          # 12/12 cross-checks pass
python scripts/compute_iaa.py --stage 1 --round 2 --include-llm --out results/iaa/round2_gold
python scripts/export_adjudicated_dataset.py --strict --date 2026-09-03   # idempotent; hashes below reproduced
```

Result-file hashes at 2026-08-24 audit time:

```text
14c0d1cb83b4859487dff3e7d1c31e389c3799eba77635912d2b36bdcb71fc4e  results/iaa/round1/iaa_stage1.json
77cf54eef38f43387a8a92ef913f7e80c9c9931ac08514ffe0a5b3fe0ee6c276  results/iaa/round2/iaa_stage1.json
fa09dfa76698141cc36f54dab8ede428d9c5fdec80c80acb689440082faa4309  results/adjudication/adjudication_queue.json
c6d44931e2be67421a8ff09ed5dde474044af5a9b38cfd2ba2793c326c8fce90  results/adjudication/tier0_violations.csv
```

Hashes at 2026-09-03 re-audit time:

```text
14c0d1cb83b4859487dff3e7d1c31e389c3799eba77635912d2b36bdcb71fc4e  results/iaa/round1/iaa_stage1.json          (unchanged)
77cf54eef38f43387a8a92ef913f7e80c9c9931ac08514ffe0a5b3fe0ee6c276  results/iaa/round2/iaa_stage1.json          (unchanged)
c6d44931e2be67421a8ff09ed5dde474044af5a9b38cfd2ba2793c326c8fce90  results/adjudication/tier0_violations.csv   (unchanged)
a42b471c36c5f155d28e64b65b8e768c3e74c71e43edba03d61e1a27a2f427c8  results/adjudication/adjudication_queue.json  (CHANGED — see caveat)
80ecebb5700d0443f628f4beb08a22c4106b4f6d65091a5136985783e89ed6c8  results/iaa/round2_gold/iaa_stage1.json
cc018fbc4f45a91c2d21a489c8ea798648ead25c5ac4c2a08fd895ed1745750f  AMIA_2027_STAGE1_GOLD_74items_2026-09-03/AMIA_2027_STAGE1_ADJUDICATED_74items_2026-09-03.jsonl
97ec0277c8279ef76d273023641b2b2d6f672e1b8786d3e57bf212516b45c57d  AMIA_2027_STAGE1_GOLD_74items_2026-09-03/AMIA_2027_STAGE1_ADJUDICATED_74items_WITH_TEXT_2026-09-03.jsonl
```

Important reproducibility caveats:

1. The working tree already contained uncommitted changes to `iaa_pipeline/metrics.py` and `scripts/compute_iaa.py` before the original audit. The stored IAA result JSONs were generated on 2026-06-26, while the current analysis code includes later/uncommitted additions such as expected agreement and binary/type decomposition. The original primary κ, observed agreement, child-logic κ, cohort metrics, child-count agreement, and span F1 are present in the stored JSONs and were reproduced by the current code. Post hoc axes should be version-pinned before publication.
2. **`scripts/compute_iaa.py` has since been committed; `iaa_pipeline/metrics.py` has not** (17 insertions still uncommitted as of 2026-09-03). The uncommitted delta now includes a *correctness fix*, not only added axes: `_span_tokens` assumed `text_span` was a string, which raised `AttributeError` on any pair involving a GOLD envelope, because spec v1.2.3 change 6 stores `text_span` as an array of contiguous segments. **Every gold-axis number in §3.9 depends on this uncommitted fix.** Pin the commit before submission.
3. `results/` is git-ignored, so none of the result files above are version-controlled. `adjudication_queue.json` was regenerated at some point after the original audit and its hash differs; all queue quantities cited here were re-verified against the current file and still reproduce exactly (113 items = S1 49 + S2 35 + S3 4 + S4 25; S4 seed 20260730, frame 84). The stratum assignments recorded in the gold records match the current queue with zero set difference.
4. The frozen export is content-addressed by its own `MANIFEST.txt`; re-running the export command reproduced both sha256 values byte-for-byte, so the freeze is idempotent with respect to the current workspace.

## 5. Claims safe for the abstract now

The following wording is directly supported:

> Across 8 NSCLC trials and 172 paired eligibility criteria, two annotators completed two rounds of Stage 1 structural splitting annotation. Four-class splitting-decision Cohen's κ increased from 0.608 to 0.650, while observed agreement increased from 136/172 (79.1%) to 138/172 (80.2%). Of 172 criteria, 21 remained discordant, 15 transitioned to agreement, and 13 developed new disagreement. Among pairs jointly labeled as composite splits, child-logic κ increased from 0.763 (n=33) to 0.867 (n=40). From a stratified adjudication queue of 113 items, 74 criteria were adjudicated in a single blind pass against a documented authority hierarchy: all 49 items in the disagreement stratum and a fixed-seed random sample of 25 criteria on which both annotators had agreed. On that agreement sample the adjudicated label confirmed the annotators' shared answer in 24 of 25 cases; within the disagreement stratum it matched one annotator in 30 of 49 and the other in 27 of 49. In 6 of the 74 adjudicated criteria the settled label could not have been produced by majority vote — 3 where both annotators agreed but were overridden, and 3 where neither annotator's label was adopted.

Wording constraints that must accompany the above:

- name the adjudicator's prior role as one of the annotators and guideline author (§3.9.4), or omit the EHJ-vs-gold figure entirely;
- give stratum denominators whenever a gold-agreement figure appears — never a single pooled percentage;
- call the gold-axis figures agreement against a reference, not accuracy; κ is chance-corrected and is not a proportion correct.

The following are **not yet supported**:

- ~~adjudicated gold-set size, adjudicator agreement, or annotator-vs-gold accuracy~~ → gold-set size and annotator-vs-gold **agreement** are now supported with stratum denominators (§3.9); **adjudicator agreement remains unsupported** — there is a single adjudicator and no second-adjudicator reliability;
- any corpus-level accuracy estimate from the 74-item gold set: it is two complete strata sampled on opposite criteria, and only S4 (25 from a frame of 84) has a defined sampling frame;
- EHJ-vs-gold read as accuracy against an independent reference — the adjudicator is EHJ (§3.9.4);
- adjudication outcomes for S2 (35) or S3 (4), which are entirely unadjudicated;
- any blind→revealed revision (D-3) analysis: all 74 records are `pass="blind"` and `blind_label` equals gold on 74/74, so the sample is zero, not small;
- "0 undecidable items" across the queue — the empty gap-ticket evidence covers only the 74 adjudicated criteria;
- claims that adjudication improved IAA;
- claims based on 9 measured trials;
- “3 Tier-0 cases” without clarifying whether this means violations (3) or affected annotations (2) — and note the separate `adjudication.tier` scale, where 6 gold records are tier 0 in a different sense (§3.7);
- fixed-cohort improvement in child logic;
- claims that the few-shot overlap was absent, or that it definitely contaminated annotators;
- causal wording that guideline revision produced or failed to produce the observed changes without documenting round-specific instructions and exposure.

## 6. Unresolved issues requiring resolution or disclosure

1. **8 vs 9 trials:** rename/update the selection documentation or explicitly define 9 selected versus 8 analyzed.
2. **Missing intervention metadata:** raw envelopes do not identify prompt, schema, or guideline version. The exact Round 1→2 intervention is therefore not recoverable from these artifacts alone.
3. **Child-logic documentation drift:** executable v1.2.2 schema is AND/OR, while `03_json_schemas.md` still says XOR / 3-class + null.
4. **Changing child-logic denominator:** n=33 to n=40; consider fixed-pair sensitivity analysis.
5. **Post hoc metric code:** expected agreement, binary split/type axes, and direction-bias reporting are in uncommitted working-tree code. Pin a commit before submission.
6. **Tier-0 counting unit:** distinguish violation rows, affected criterion–annotator records, and unique criteria.
7. **NCT01295827 provenance overlap:** disclose same-trial few-shot provenance and consider leave-one-trial-out sensitivity analysis.
8. ~~**Adjudication incomplete:** queue creation is evidenced; gold outcomes are not.~~ → **Resolved 2026-09-03** for S1 and S4 (74 records, frozen with sha256 manifest). Still open for S2 (35) and S3 (4), which remain unadjudicated and must be described as out of scope rather than as producing no findings.
9. **Adjudicator independence (new, highest priority):** the adjudicator is EHJ, one of the two annotators and the guideline author. No data artifact records this, and there is no second adjudicator. Disclose in the methods; do not present EHJ-vs-gold as independent (§3.9.4).
10. **Uncommitted correctness fix (new):** the gold-axis numbers depend on an uncommitted `iaa_pipeline/metrics.py` change that fixes an `AttributeError` on array-valued `text_span` (v1.2.3 change 6). Before submission this must be committed and the numbers regenerated from the pinned commit.
11. **Gold set is not a sample of the queue (new):** S1 and S4 are complete, S2 and S3 are empty. Any sentence of the form "74 of 113 items were adjudicated" invites the reader to treat the 74 as a sample. State the two strata explicitly.
12. **Ungoverned results directory (new):** `results/` is git-ignored, so `adjudication_queue.json`, the IAA JSONs, and the tier-0 CSV are not version-controlled; the queue file's hash already changed since the original audit. The frozen export directory is the only content-addressed artifact.

## 7. Evidence source index

| Purpose | Authoritative file(s) |
|---|---|
| Raw paired labels | `iaa_workspace/{8 measured trials}/stage1/round{1,2}/*committed.json` |
| Raw adjudicated labels | `iaa_workspace/{8 trials}/stage1/round2/GOLD_*_stage1_committed.json` |
| Frozen gold dataset (content-addressed) | `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/` (2 jsonl + 2 txt copies + `MANIFEST.txt`) |
| Gold freeze / export + structural validation | `scripts/export_adjudicated_dataset.py` |
| Gold-axis κ panel | `results/iaa/round2_gold/iaa_stage1.json`; `.md` |
| Abstract numbers from the frozen export | `scripts/amia_stage1_numbers.py`; `docs/amia_stage1_numbers.md` |
| Round-transition trajectories | `scripts/amia_stage1_trajectories.py`; `docs/amia_stage1_trajectories.md` |
| Adjudicator role disclosure | `iaa_pipeline_spec/adjudication_guide_v2_notion.md` |
| Adjudication design rationale | `iaa_pipeline_spec/adjudication_handover.md` |
| Freeze change records | `docs/amia2027_gold_freeze_2026-09-02.md`; `docs/amia2027_gold_freeze_2026-09-03.md` |
| Stored pooled/per-trial metrics | `results/iaa/round1/iaa_stage1.json`; `results/iaa/round2/iaa_stage1.json` |
| Alignment and metrics definitions | `iaa_pipeline/aligners.py`; `iaa_pipeline/metrics.py` |
| Discovery/report generation | `scripts/compute_iaa.py` |
| Round transition reporting | `scripts/compare_rounds.py` |
| Trial selection list | `iaa_pipeline_spec/iaa_8trials.txt` |
| Queue result and metadata | `results/adjudication/adjudication_queue.json`; `.csv` |
| Queue definitions | `scripts/build_adjudication_queue.py` |
| Tier-0 result | `results/adjudication/tier0_violations.csv` |
| Tier-0 rule definitions | `scripts/tier0_check.py` |
| Child-logic executable enum | `pipeline/config.py`; `iaa_pipeline/stage_schemas.py` |
| Child-logic narrative schema | `iaa_pipeline_spec/03_json_schemas.md` |
| Few-shot provenance | `pipeline/prompts/examples.json` |
| NCT01295827 analyzed input | `iaa_workspace/NCT01295827/stage1/input.json` |

