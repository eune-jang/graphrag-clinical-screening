# Claude Code Handoff v2 — Post-Adjudication Freeze, v1.3 Alignment, and Repository Stabilization

**Target repository:** `graphrag-clinical-screening`  
**Suggested destination:** `docs/CLAUDE_CODE_HANDOFF_POST_ADJUDICATION.md`  
**Handoff date:** 2026-09-08  
**Project state:** Stage 1 adjudication is complete; the full 113-item adjudication evidence set has been exported and validated. The next immediate task is repository audit/freeze, followed by controlled v1.3 prompt implementation work.

---

## 0. Read this first

This repository belongs to a broader **GraphRAG-based clinical-trial eligibility screening program**, but the currently mature and methodologically validated workstream is narrower:

> **Protocol KG annotation → Stage 1 structural decomposition → IAA → adjudication → gold evidence set → guideline/prompt refinement → held-out re-evaluation**

Do **not** treat the repository as a fully validated patient-level GraphRAG screening agent.

This handoff has two equally important purposes:

1. preserve the exact post-adjudication research state and its provenance;
2. keep future code changes aligned with the already-developed **v1.3 Stage 1 decision framework** rather than redesigning Stage 1 from scratch.

For the first pass, **perform a read-only repository audit only**. Do not refactor, rename, delete, migrate schemas, or rewrite prompts until the audit report is reviewed.

---

# PART A. RESEARCH STATE

## 1. Long-term project context

The long-term goal is an explainable clinical-trial eligibility screening system that combines:

- clinical-trial eligibility criteria,
- structured/unstructured EMR data,
- a multi-layer clinical knowledge graph,
- ontology-guided retrieval/reasoning,
- open/small LLMs where appropriate,
- traceable reasoning paths for screening decisions.

The broader trajectory includes synthetic/open-data development, hospital validation, and later external/cross-site validation. However, the current repository evidence base is strongest for the **Protocol KG / Stage 1 annotation methodology**.

---

## 2. Formal Stage 1 IAA state

The formal Stage 1 inter-annotator analysis set is:

- **8 trials**
- **172 aligned criteria**
- two annotators: EHJ and DYK
- two annotation rounds

Key full-corpus result:

- Round 2 splitting-decision Cohen's κ = **0.650** (`n=172`)

Interpretation constraint:

- full-corpus EHJ–DYK κ measures inter-annotator agreement;
- gold-comparison metrics computed on adjudication-enriched subsets measure correctness against an adjudicated reference;
- these must **not** be presented as directly comparable quantities.

The Stage 1 research contribution is not merely “κ improved.” The stronger methodological finding is that a single aggregate κ can mask heterogeneous structural disagreement, particularly split-vs-none behavior and systematic granularity differences.

---

## 3. Adjudication lineage — do not collapse 61, 74, and 113

There are multiple valid frozen exports from different milestones. They are **lineage snapshots, not competing current truths**.

### 3.1 61-item AMIA snapshot

The first AMIA-focused adjudication freeze contained:

- 61 confirmed gold
- 0 gap
- 8 trials
- queue composition: 36 S1 + 25 S4
- rule status: 51 existing / 9 new / 1 conflict

This was a deliberate AMIA analysis subset, not the final full adjudication evidence set.

### 3.2 74-item AMIA-expanded snapshot

The AMIA freeze was later expanded to include all 49 S1 items:

- 74 confirmed gold
- 0 gap
- 8 trials
- queue composition: S1 49 + S4 25
- tier 0/1/2 = 6 / 2 / 66
- decisions = none 39 / composite_split 28 / nested_exception 5 / macro_aggregate 2
- rule status = existing 64 / new 9 / conflict 1
- `escalate_pi=true`: 3
- conflict item: `NCT05756153_E6`

This remains an important publication/AMIA lineage artifact, but it is no longer the latest complete adjudication scope.

### 3.3 Full 113-item adjudication evidence set — CURRENT LATEST

The full adjudication queue has now been completed.

Canonical exported evidence set:

```text
STAGE1_ADJUDICATED_113items_2026-09-07.jsonl
STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl
```

The `WITH_TEXT` export is the preferred review/publication-facing artifact because it adds original criterion text and criterion type while preserving provenance.

Validated profile:

- **113 total records**
- **113 confirmed gold**
- **0 Tier-3 gap tickets**
- **8 trials**
- **113 unique criterion IDs**
- **0 duplicate IDs**
- **0 missing IDs**
- criterion type: 62 exclusion / 51 inclusion
- every text-span segment matched verbatim to source criterion text
- span violations: **0**

Adjudication profile:

- adjudication pass: blind 113
- tier 0 / 1 / 2 = **10 / 2 / 101**
- splitting decision:
  - none = **59**
  - composite_split = **42**
  - nested_exception = **10**
  - macro_aggregate = **2**
- rule status:
  - existing = **99**
  - new = **12**
  - conflict = **2**
- queue stratum:
  - S1 = **49**
  - S2 = **35**
  - S3 = **4**
  - S4 = **25**
- `escalate_pi=true` = **7**
- conflict records = **2**

Conflict criterion IDs:

```text
NCT03800134_E6
NCT05756153_E6
```

Escalation criterion IDs:

```text
NCT02075840_E12
NCT02125461_I2
NCT02912949_E7
NCT03728556_I3
NCT03800134_E5
NCT03800134_E6
NCT05756153_E6
```

### 3.4 Blind-pass provenance

This point is important and must not be rewritten inaccurately in documentation.

The 113-item dataset was produced as a **single blind-pass adjudication workflow**:

- no record has `adjudication.pass == "revealed"`;
- no gold label was revised after peer labels were unblinded;
- `blind_label` equals top-level gold for all 113 records;
- records where `blind_label != gold`: **0**.

Therefore there is no empirical D-3 “blind-to-revealed label change” sample in this dataset.

Do not retrospectively describe the final 113-item adjudication as a two-pass revealed adjudication if repository artifacts do not support that claim.

---

## 4. Adjudication method that must be preserved

Adjudication is **not majority voting** and not annotator consensus.

It is a correctness determination based on an evidence hierarchy:

- Tier 0: ontology/spec structural constraint
- Tier 1: external clinical authority
- Tier 2: CRC / operational screening logic
- Tier 3: unresolved → gap ticket

Important principles:

- annotator agreement does not imply correctness;
- both annotators may be wrong;
- agreement cases were deliberately audited;
- unresolved items should be represented as gap tickets rather than forced into gold;
- in the final 113-item set, no Tier-3 gaps remained.

The frozen adjudication reference set was:

- ontology base: **v1.2.2**
- ontology alignment patch: **v1.2.3**
- Stage 1 annotation guideline: **v1.2.2 frozen adjudication version**

Do not mutate historical adjudication records to conform to v1.3.

---

# PART B. v1.3 METHOD STATE — THIS HAS ALREADY BEEN DESIGNED

## 5. Do not redesign Stage 1 from scratch

After adjudication, the Stage 1 rules were reorganized from a relatively flat rule list into a more explicit decision hierarchy.

The **Canonical Core v1.3.0 is frozen**.

The current development prompt is a **v1.3.1 non-normative development patch** of that v1.3.0 baseline. It may improve wording, synthetic examples, validation details, or pipeline-context mechanics, but it must not silently change the meaning or precedence of the canonical H/X rules.

Any semantic change to rule meaning, precedence, split/merge boundary, exception boundary, or child-logic behavior should be treated as a **new normative guideline version** rather than a silent prompt patch.

---

## 6. Canonical Stage 1 decision hierarchy

Apply the hierarchy in this exact order:

```text
H0  Role / Scope Gate
 ↓
H1  Proposition Boundary
 ↓
H2  Leaf Validity
 ↓
H3  List / Coverage Check
 ↓
H4  Assign Structure Type
 ↓
H5  Child Logic
 ↓
H6  Recursion
```

Cross-cutting output rules are separated from the H0–H6 decision hierarchy.

This separation is deliberate: `text_span`, shared qualifiers, exception-span boundaries, cohort scope, external delegation, queryability, and criterion-locality are output/representation constraints rather than additional structure-type decision levels.

---

## 7. H0 — Role / Scope Gate

First decide whether a phrase actually carries eligibility logic.

Potentially independent structural content:

- mandatory eligibility requirement
- alternative eligibility pathway
- exception / waiver / carve-out

Usually dependent/contextual:

- temporal, numeric, grade, severity, method, or purpose qualifier
- population/term definition
- cohort/applicability scope
- permissive/optional statement
- assessment/confirmation method that merely supports another requirement

Operational rule:

> A borderline phrase becomes an independent Stage 1 requirement only if, after shared subject/context is restored, it still creates a separate patient-level eligibility condition rather than merely describing another condition.

Important consequence:

- do not split just because a phrase names a disease, drug, test, or procedure;
- do not split scope-only/definition-only material;
- confirmation methods normally remain attached to the requirement they support.

---

## 8. H1 — Proposition Boundary

### H1-A. Same screening-target test

The screening target is the clinical object/state being judged, not merely the shared predicate/action.

Merge by default only when **all** merge conditions hold:

1. expressions refer to the same underlying screening target or an operationally unified target;
2. differences are only status/time/history, overlapping/subsumed wording, or interchangeable members of one operational class that answer the same screening question;
3. branches do not have materially different operational constraints such as different time windows, thresholds, grades, mechanisms, or independently required evidence.

Failure of the merge test does **not** automatically prove a split; continue to H1-B.

### H1-B. Independent assertion test

Treat candidates as separate eligibility propositions when:

1. each expresses a distinct eligibility requirement after shared context is restored;
2. each can be evaluated independently;
3. changing one while holding the other fixed can change whether the criterion condition **as written** holds.

Truth-value contrast is supporting evidence, not a stand-alone concept-counting rule.

Keep content together when multiple concepts jointly define one integrated regimen, measurement, status, or clinical judgment.

---

## 9. H2 — Leaf Validity

### H2-A. Semantic-category constraint

A prospective leaf must not contain **multiple independently asserted eligibility requirements** that require different Stage 2 semantic categories.

This is a downstream-validity constraint, not a rule to split every multi-concept phrase.

Do not apply it to content already classified under H0 as qualifier, method, purpose, scope, or part of one integrated regimen/judgment.

Default provenance mapping:

- H2-A → Tier 0

### H2-B. Oncology/domain-axis refinement

Diagnosis, stage, resectability, and biomarker become separate Stage 1 units **when the current target independently asserts them as coordinate eligibility requirements**.

Important refinements:

- if an axis term merely identifies the disease/population to which another predicate applies, treat it as scope by default;
- histologic/cytologic/pathologic/documented confirmation normally belongs to the diagnosis proposition;
- split confirmation only when confirmation evidence/method is independently required as an eligibility condition;
- stage subgrades that jointly define one stage category remain one stage unit;
- keep the decision criterion-local; neighboring criteria are not used to deduplicate or suppress a local requirement.

Default provenance mapping:

- H2-B → Tier 1

---

## 10. H3 — List / Coverage Check

A key post-adjudication refinement is to distinguish **open/non-exhaustive** from **closed/operationally exhaustive** lists.

### Open / non-exhaustive list

If named examples do not exhaust the parent meaning:

- do not split examples solely because they are recognizable concepts;
- preserve the broad parent meaning as the Stage 1 unit;
- preserve item-specific detail downstream where appropriate;
- do not invent a redundant residual-umbrella child.

Typical signals include `e.g.`, `such as`, non-exhaustive `including`, `etc.`.

### Closed / operationally exhaustive list

If the list fully defines the alternatives in the current target, items may become children when independently eligibility-determinative.

Typical signals include `any of the following` or explicitly complete numbered alternatives.

Item-specific time/grade/value/treatment/evidence constraints are strong evidence of independent operational content, but do not alone prove that a list is closed.

---

## 11. H4 — Structure Type

Only after H0–H3, choose exactly one current-level label:

- `none`
- `composite_split`
- `macro_aggregate`
- `nested_exception`

Definitions:

### `none`

One valid eligibility proposition remains.

### `composite_split`

Two or more independent propositions with no true umbrella.

### `macro_aggregate`

Two or more independent propositions under a true wrapper/umbrella, where children collectively operationalize the umbrella and no hidden residual pass/fail meaning remains.

### `nested_exception`

A true carve-out, waiver, or exception to a broader main rule.

Important exception semantics:

- negative requirement `without X` is not automatically an exception;
- a phrase that merely clarifies scope outside the main rule is not an exception;
- the excepted/waived case must be one the main rule, read alone, would have prohibited or required;
- a branch-specific exception should be preserved with the affected branch and resolved on recursion rather than flattening the root structure.

Exception spans are **not child Criterion nodes** and are never recursively split.

---

## 12. H5 — Child Logic

`child_logic` is required for:

- `composite_split`
- `macro_aggregate`

Allowed values:

- `AND`
- `OR`

For `none` and `nested_exception`:

- `child_logic = null`

Interpretation rule:

> Child logic describes whether the child conditions, **as written in the criterion**, jointly make the parent criterion hold. It is not a patient-level final eligibility verdict.

Do not infer child logic from:

- inclusion vs exclusion type
- surface `and/or`
- punctuation

Do not flatten mixed logic such as `A AND (B1 OR B2)` into one level.

---

## 13. H6 — Recursion

Each Stage 1 call handles **one hierarchy level only**.

Every generated child is conceptually re-evaluated under H0–H6.

Pipeline-control metadata:

```text
needs_recursion
recursion_targets
recursion_note
```

Rules:

- `needs_recursion=true` only when an explicit lower-level non-none structure remains;
- `recursion_targets` identifies exactly which child IDs require another Stage 1 pass;
- for nested exception, only main content may recurse (`["main"]` when needed);
- exception spans never recurse;
- if no lower-level structure remains, `needs_recursion=false` and `recursion_targets=[]`.

`recursion_targets` is **new pipeline-control metadata**. It is not an ontology property and was not present in the historical v1.2.2 113-item adjudication records.

---

## 14. Cross-cutting canonical output rules (X1–X7)

These are not additional H-level decision stages.

### X1. Current-target / text-span fidelity

- `ROOT_CRITERION_TEXT` is read-only context.
- output spans must come only from current `TARGET_SEGMENTS`.
- each `text_span` is an array of one or more verbatim contiguous source substrings.
- never synthesize, normalize, paraphrase, or concatenate non-contiguous wording into one span.
- at recursive passes, do not import text from outside propagated target segments.

### X2. Shared expressions / qualifier scope

- do not duplicate shared entities merely to make children grammatical;
- repeat a dependent qualifier in every child it semantically modifies;
- grammatical incompleteness is acceptable when parent/root context supplies shared meaning.

### X3. Exception-span boundaries

- include the complete explicit trigger phrase from its first word when a trigger exists;
- parenthetical triggerless exception: select the exception content itself;
- multiple sibling exception spans may attach to one main rule.

### X4. Cohort scope

- cohort difference alone is not a split trigger;
- record cohort scope only when criterion text itself limits applicability;
- for split structures, child-level scope is used rather than a top-level split-parent scope;
- null may be used in fixed JSON transport, while ontology serialization omits universal/null scope.

### X5. Broad adequacy / assessment / external delegation

- broad adequacy statement without concrete local subrequirements → `none`;
- assessment method without independent pass/fail content remains attached;
- thresholds delegated only to IB/Table/appendix → `none` at that text level, with delegation note;
- explicit local thresholds are evaluated normally.

### X6. Conceptual queryability / evidence source

- Stage 1 units are conceptual eligibility decisions;
- different standard evidence sources support a split but do not alone define it;
- site-specific EMR field availability is not a normative structural rule.

### X7. Criterion-local decomposition

- annotate only the current criterion/target;
- do not import neighboring criterion text as child spans;
- do not suppress local requirements because similar content appears elsewhere;
- cross-criterion grouping/deduplication is outside Stage 1.

---

## 15. v1.3 provenance model

The new design separates one decisive rule from supporting rules.

Desired output provenance:

```text
primary_rule_id
supporting_rule_ids
```

Rules:

- output exactly one **primary decisive rule**;
- put secondary/supporting rules into `supporting_rule_ids`;
- evidence tier may be derived from primary-rule provenance.

Suggested default tier mapping:

- H2-A → Tier 0
- H2-B → Tier 1
- H0/H1/H3/H4/H5/H6/X → Tier 2 unless higher authority is explicitly invoked

This replaces the tendency to attach several flat v1.2.2 rule IDs without clearly identifying which rule actually decided the label.

---

## 16. v1.3 version/freeze policy

Current state:

- **Canonical Core v1.3.0: frozen**
- **Stage 1 prompt v1.3.1: development / non-normative patch**

A v1.3.x development prompt may change:

- wording
- synthetic examples
- redundant DO/DO-NOT guidance
- JSON validation details
- input context mechanics such as `PARENT_CONTEXT`

without a normative version bump **only if behavior does not change**.

The following require a new normative guideline version (e.g. v1.4), not a silent v1.3.x patch:

- H/X rule meaning
- H-rule precedence
- split/merge boundary
- exception boundary
- child-logic semantics

Before comparative model evaluation across model families, the final prompt must be frozen.

---

# PART C. HISTORICAL vs CURRENT SOURCE-OF-TRUTH

## 17. Historical ontology/schema drift risks

Older artifacts remain useful for lineage, but they must not be mistaken for current implementation truth.

Known historical differences include:

- old v1.2.1 JSON using `lab_value` where later implementation may use a different current category naming;
- old `child_logic` enum including `XOR`;
- historical implicit inclusion=AND / exclusion=OR defaults;
- older text-span formats;
- older ontology-layer numbering in non-canonical project documents.

The v1.2.3 alignment patch already established important corrections such as:

- explicit `child_logic` for composite/macro parents;
- no default omission;
- nested exception represented graph-wise through `INCLUDES_EXCEPTION`, not ordinary child Criterion nodes;
- Stage 1 `text_span` as an array of contiguous source segments;
- universal `cohort_scope` omitted at ontology serialization;
- `REQUIRES_STATUS` allowed to target Stage under the alignment patch.

Do not “upgrade” historical raw outputs in place. Preserve lineage.

---

## 18. Audit-time authority precedence

Use this ordering when classifying current files, but report mismatches rather than silently rewriting them:

1. current executable implementation contract
   - `pipeline/config.py`
   - validators/transforms actually used by the pipeline
2. Stage-specific implementation contract
   - `iaa_pipeline/stage_schemas.py`
   - Stage 1 runner/adjudication code
3. accepted current ontology design
   - unified v1.2.2 spec
   - v1.2.3 alignment patch
4. frozen v1.2.2 Stage 1 guideline used for historical adjudication
5. frozen adjudication evidence artifacts and manifests
6. frozen v1.3.0 canonical decision core / current v1.3.1 development prompt
7. historical/superseded ontology, guideline, prompt, and export artifacts

Important nuance:

- the v1.3 core is the **next-method normative design**;
- it must not retroactively alter the frozen 113-item historical adjudication records.

---

# PART D. FIRST REPOSITORY TASK — READ-ONLY AUDIT

## 19. Do this before refactoring

Start with:

```bash
pwd
git status --short
git branch --show-current
git log -1 --oneline
git remote -v
```

Then inspect repository structure without modifying it.

A useful first inventory is:

```bash
find . -maxdepth 3 -type f | sort
```

If too large, summarize while excluding caches/build/generated directories.

Do **not** run `git add .` yet.

---

## 20. Classify changed/untracked files

Classify every changed/untracked file into one of:

- source code
- prompt
- ontology/spec
- annotation guideline
- v1.3 design/canonical-core artifact
- adjudication source input
- adjudication result
- gold/evidence export
- gap ticket
- IAA/report output
- manuscript/AMIA artifact
- generated UI/cache/log
- local-only/secret
- historical/superseded
- unknown/research review needed

---

## 21. Locate and verify canonical adjudication artifacts

Find the repository paths for:

```text
STAGE1_ADJUDICATED_113items_2026-09-07.jsonl
STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl
MANIFEST.txt
```

Verify the exported manifest against repository source files.

Expected hashes from the known freeze:

```text
STAGE1_ADJUDICATED_113items_2026-09-07.jsonl
bb0960577ce876b108cd04485ff60353d1e3f6aa8cf44e338c9884db29062865

STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl
c3e498bee0ef5ba5479c51005a80d375731fd4b1f6272ce68a34bed0a6be9a7f
```

If repository files disagree with these hashes, **report the mismatch and stop before “repairing” anything**.

Also locate:

- Round 1 source annotations
- Round 2 source annotations
- adjudication queue source
- per-trial GOLD committed records
- `gap_tickets.json`
- final IAA/adjudication metrics
- any `needs_recursion` historical fields
- all 61-item and 74-item intermediate freezes

---

## 22. Preserve the 61 → 74 → 113 lineage

Do not delete intermediate snapshots merely because 113 is latest.

Preferred interpretation:

```text
61 = initial AMIA adjudication freeze
74 = AMIA expanded freeze (all S1 + S4)
113 = full adjudication evidence set (S1 + S2 + S3 + S4)
```

During repository cleanup, mark 61/74 as historical/publication-lineage snapshots and 113 as the latest full Stage 1 adjudication evidence set.

Do not let a future `CURRENT_STATUS.md` imply that 61 or 74 is the final full adjudication scope.

---

## 23. Verify frozen-input integrity

Round 1 and Round 2 annotations are research source data and should be treated as read-only historical inputs.

Check whether they changed after their freeze using:

- Git history
- hashes/manifests
- file timestamps only as secondary evidence

If changed, report exact diffs. Do not normalize them to v1.3.

---

# PART E. FIRST AUDIT DELIVERABLE

## 24. Return this report before making structural changes

```text
A. Git state
B. repository structure summary
C. changed/untracked file classification
D. exact canonical 113-item artifact paths + hash verification
E. 61/74 historical snapshot locations
F. frozen R1/R2 integrity check
G. current ontology/guideline/prompt/version map
H. v1.3.0 canonical-core and v1.3.1 development-prompt locations
I. source-of-truth mismatch list
J. files recommended for adjudication-complete commit
K. files to ignore/archive/review later
L. proposed checkpoint/tag (do not create without approval)
```

Do not proceed to broad refactoring until this report is reviewed.

---

# PART F. GIT CHECKPOINT STRATEGY

## 25. Suggested checkpoint sequence

### Checkpoint 1 — completed adjudication state

Suggested tag concept:

```text
stage1-adjudication-complete-2026-09-08
```

This should preserve the exact state containing the complete 113-item adjudication evidence and its provenance.

### Checkpoint 2 — repository-stabilized gold/evidence state

After:

- hash verification
- canonical path confirmation
- source-of-truth audit
- metrics verification
- docs pointer cleanup

suggested tag concept:

```text
stage1-gold-v1
```

Do not create or push tags without explicit user approval.

---

# PART G. REPOSITORY ORGANIZATION POLICY

## 26. Minimal-change stabilization, not dramatic rewrite

Preserve working directories where possible:

```text
graphrag-clinical-screening/
├── pipeline/                 # production annotation implementation
├── iaa_pipeline/             # IAA + adjudication implementation
├── scripts/
├── tests/
├── docs/
│   ├── CURRENT_STATUS.md
│   ├── methods/
│   ├── decisions/
│   └── papers/
├── experiments/              # frozen experiment snapshots/manifests
├── outputs/                  # generated outputs, selectively tracked
├── archive/                  # superseded historical artifacts if useful
├── context/                  # LLM-context recipe/registry
└── gpt_context_package/      # generated snapshot, not source of truth
```

Do not force this exact layout when current imports/scripts depend strongly on existing paths. Prefer safe incremental changes.

---

## 27. Stable active filenames

For active code/prompts, avoid filename proliferation such as:

```text
prompt_v2.txt
prompt_v3_final.txt
prompt_final_final2.txt
```

Keep stable active filenames and recover history from Git commits/tags.

Semantic-versioned research documents are different: ontology/guideline versions may retain explicit versioned filenames because the version has methodological meaning.

---

## 28. Create clear current-state pointers

Recommended after audit:

### `docs/CURRENT_STATUS.md`

Should summarize rapidly changing research state:

- Stage 1 R1/R2 complete
- full adjudication complete
- latest evidence set = 113 items
- v1.3.0 canonical core frozen
- v1.3.1 prompt development ongoing
- next actions

### `pipeline/schema/CURRENT.md`

Should identify:

- effective ontology base/patch
- implementation source of truth
- Stage 1 schema source
- historical/superseded schema artifacts
- whether v1.3 changes are ontology changes or Stage 1 decision-method changes

---

## 29. Keep methodological decisions in explicit decision records

Recommended directory:

```text
docs/decisions/
```

Useful ADR-style topics include:

- explicit child logic
- segmented text spans
- nested-exception graph representation
- gold vs gap policy
- Stage 1 decision hierarchy H0–H6
- same-screening-target merge boundary
- independent-assertion test
- confirmation-method handling
- open vs closed list coverage
- recursive decomposition / `recursion_targets`
- provenance `primary_rule_id` + `supporting_rule_ids`

Each decision record should contain:

- problem
- decision
- rationale/evidence
- date/status
- affected files
- whether normative or implementation-only

---

# PART H. GPT / LLM CONTEXT MANAGEMENT

## 30. `gpt_context_package` is downstream, not a source of truth

The package exists so an LLM can understand the project quickly without scanning the whole repository.

Treat it as:

> generated / disposable context snapshot

Desired flow:

```text
canonical repository sources
        ↓
context manifest / build recipe
        ↓
gpt_context_package
```

Not:

```text
repo ↔ manually synchronized context package
```

Long-term, preserve the **recipe** rather than manually maintaining duplicate context files.

Possible components:

```text
context/context_registry.yaml
scripts/build_gpt_context.py
```

Rebuild at meaningful milestones only, such as:

- post-adjudication/gold freeze
- final Stage 1 v1.3 prompt freeze
- held-out Stage 1 evaluation
- later Stage 2–5 milestones

Do not rebuild the context package until repository source-of-truth stabilization is complete.

---

# PART I. ROLE SPLIT — CHATGPT vs CLAUDE CODE

## 31. ChatGPT — research/context layer

Primary responsibilities:

- research design
- ontology semantics
- Stage 1 rule semantics
- adjudication interpretation
- IAA interpretation
- guideline architecture
- prompt-behavior design
- paper framing / Methods / Discussion
- deciding whether a discrepancy is methodological or implementation-only

## 32. Claude Code — repository/execution layer

Primary responsibilities:

- repository inspection
- Git state/checkpoint preparation
- file classification/reorganization
- implementation after semantic decisions are approved
- tests
- reproducibility checks
- manifest/hash verification
- schema/prompt/validator synchronization
- context build automation

### Boundary

If cleanup or implementation would change any of the following, stop and request methodological review rather than silently changing behavior:

- H0–H6 meaning or precedence
- same-target merge boundary
- independent-proposition boundary
- semantic-category leaf validity
- oncology-axis split rules
- confirmation-method handling
- open/closed list behavior
- macro/composite/nested boundary
- child-logic semantics
- recursion semantics
- text-span provenance rules
- cohort-scope semantics
- gold/gap inclusion policy
- adjudication evidence hierarchy
- IAA denominator/sample definition

---

# PART J. NEXT WORK AFTER REPOSITORY STABILIZATION

## 33. Expected sequence

Do not skip directly to broad comparative evaluation.

Recommended sequence:

```text
1. repository audit
2. adjudication-complete checkpoint
3. canonical source/path cleanup
4. verify v1.3.0 core + v1.3.1 development prompt placement
5. implement/validate v1.3 pipeline mechanics without changing frozen H/X semantics
6. test with prespecified development models
7. freeze FINAL Stage 1 prompt
8. run comparative model evaluation
9. later perform held-out human reproducibility evaluation on new trials
```

The historical 8 formal IAA trials should not be treated as a fresh human held-out Round 3 set because annotators were exposed during adjudication and method refinement.

---

## 34. v1.3 prompt-development guardrail

The v1.3.1 development prompt already includes mechanics such as:

- `ROOT_CRITERION_TEXT`
- `TARGET_SEGMENTS`
- `PARENT_CONTEXT`
- `NEIGHBORING_CRITERIA` as read-only interpretation context
- `needs_recursion`
- `recursion_targets`
- `primary_rule_id`
- `supporting_rule_ids`

When implementing or revising these mechanics:

- preserve H0→H6 precedence;
- keep recursion one level per call;
- keep exception spans non-recursive;
- keep all output spans restricted to current `TARGET_SEGMENTS`;
- never use neighboring criteria to create spans or perform cross-criterion deduplication;
- distinguish fixed JSON transport nulls from ontology serialization omission rules.

---

# PART K. CLAUDE CODE COMPLETION PROTOCOL

## 35. At the end of each substantial repository task, report

1. files changed
2. files moved/renamed
3. files added/removed
4. semantic behavior changed? `yes/no`
5. if yes, exact semantic change and approval basis
6. tests run and results
7. hashes/manifests checked
8. source-of-truth inconsistencies remaining
9. whether `CURRENT_STATUS.md` needs updating
10. whether a decision record/ADR is needed
11. whether the GPT context package should be rebuilt
12. recommended next Git checkpoint

Do not edit a generated GPT context snapshot just to make it look current. Fix the source, then rebuild.

---

# PART L. DO NOT DO THESE THINGS DURING INITIAL CLEANUP

## 36. Hard prohibitions

- Do not rewrite frozen Round 1 / Round 2 annotation files.
- Do not normalize historical 61/74/113 adjudication exports into v1.3 in place.
- Do not delete 61/74 snapshots before classifying them as historical publication lineage.
- Do not reinterpret the 113 set as two-pass revealed adjudication; artifact provenance says single blind pass.
- Do not silently replace the frozen v1.2.2 adjudication guideline with v1.3 in historical records.
- Do not modify Canonical Core v1.3.0 semantics through a “prompt cleanup.”
- Do not treat v1.3.1 development wording/example changes as permission to change H/X behavior.
- Do not infer current truth from the highest-looking filename alone.
- Do not place `.env`, API keys, Neo4j credentials, PHI, or hospital raw data in tracked context packages.
- Do not directly compare adjudication-enriched gold accuracy with full-corpus annotator κ as if they measure the same construct.

---

# 37. First concrete task to execute now

**Perform a read-only post-adjudication repository audit. Do not refactor yet.**

Return exactly these sections:

```text
A. Git state
B. repository structure summary
C. changed/untracked file classification
D. canonical 113-item export paths + SHA-256 verification
E. 61/74 historical snapshot paths
F. frozen Round 1/Round 2 integrity check
G. ontology/spec/guideline/prompt version map
H. v1.3.0 canonical core + v1.3.1 development prompt locations
I. source-of-truth mismatch list
J. files recommended for adjudication-complete commit
K. files to ignore/archive/review later
L. proposed next checkpoint/tag — do not create without approval
```

After the user reviews this audit, proceed to repository stabilization. Do not make methodological changes without explicit research review.

---

# 38. Current handoff interpretation

At the time of this handoff:

- Stage 1 Round 1 and Round 2 are complete.
- Full Stage 1 adjudication is complete.
- The latest full adjudication evidence set is **113/113 confirmed gold, 0 gap** across 8 trials.
- The 61-item and 74-item exports are valid historical AMIA lineage snapshots and must not be confused with the latest full adjudication scope.
- Adjudication provenance is **single blind pass**, with `blind_label == gold` for all 113 records.
- Canonical Stage 1 decision core **v1.3.0 is frozen**.
- The current **v1.3.1 prompt is a development, non-normative patch** of v1.3.0.
- The immediate priority is **preservation, audit, and source-of-truth stabilization**, followed by controlled v1.3 implementation/testing.

