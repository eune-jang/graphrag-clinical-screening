# Stage 1 Annotation Guideline v1.3.0 — Canonical Core (FROZEN)

**Status:** FROZEN normative specification (v1.3.0)  
**Basis:** v1.2.2 frozen Stage 1 guideline + v1.2.3 alignment patch + 113-item post-AMIA adjudication evidence + external structural review  
**Design goal:** Preserve the v1.2.2 ontology and labels while simplifying rule precedence and resolving recurrent boundary ambiguities.

**Freeze declaration:** The H0–H6 hierarchy, X1–X7 cross-cutting rules, label semantics, split/merge boundaries, child-logic semantics, and criterion-locality rules are frozen in v1.3.0. Historical v1.2.2 evidence remains unchanged.

## 0. Canonical principle

> **Stage 1 represents independent eligibility logic, not the number of clinical concepts mentioned in the text.**
>
> First identify eligibility-determinative propositions. Then refine only when ontology or domain constraints require finer structural representation.

A Stage-1 leaf is the smallest criterion unit that can be evaluated as one eligibility proposition **and** is valid for downstream semantic annotation.

The default unit of analysis is the **current target criterion/segment(s)**. Stage 1 should remain criterion-local: neighboring criteria may provide read-only interpretation context, but cross-criterion duplication or consolidation is a separate protocol-level task.

---

## H0. ROLE / SCOPE GATE

Before splitting, determine the role of each phrase in the current target.

### Structural content
- mandatory eligibility requirement
- alternative eligibility pathway
- exception / waiver / carve-out

### Contextual or dependent content
- qualifier (temporal, numeric, severity, method, purpose, scope)
- definition of a population or term
- cohort/applicability scope
- permissive or optional statement
- assessment/confirmation method that only supports another requirement

**Rule:** Do not create an independent child solely because a contextual/dependent phrase names a distinct clinical concept.

### H0 operational test — context-restored standalone requirement
For a borderline phrase, mentally restore the shared subject/context and ask:

> **If this phrase were presented as a separate eligibility criterion, would it still preserve a meaningful independent requirement?**

- **Yes** → it may be an independent proposition; continue to H1.
- **No** → it is more likely a qualifier, method, scope, definition, or other dependent content.

This is a semantic test, **not a grammatical-completeness test**. A valid child span may be grammatically incomplete when the parent/root context is available.

Examples:
- `may also have received additional lines of treatment` → permissive; not a mandatory child.
- a definition of `women of childbearing potential` → context/applicability; not a separate child.
- `radiation pneumonitis requiring steroid treatment` → `requiring steroid treatment` functions as a severity/history qualifier unless steroid exposure is independently required.
- `ANC ≥1.5 ... without colony-stimulating-factor support for 7 days` → the ANC requirement and the no-support requirement can each remain meaningful requirements after shared context is restored; they are independent-proposition candidates.

---

## H1. DETERMINE PROPOSITION BOUNDARIES

H1 determines **how many eligibility propositions** are present before ontology/domain refinement.

Do not count propositions from:
- number of concepts,
- number of noun phrases,
- number of records/tests,
- surface `and/or`,
- ontology class membership alone.

### H1-A. Same screening-target test

First identify the **screening target**.

> **Screening target = the clinical object/state to which the eligibility predicate applies, not the predicate/action itself.**

Examples:
- in `recovered from major surgery`, the predicate is `recovered`; the screening target is `major surgery`.
- in `active IBD` and `history of IBD`, the screening target is IBD.
- in `prior anti-PD-1 or anti-PD-L1 therapy`, the operational screening target may be prior checkpoint-inhibitor exposure.

Candidate expressions may be treated as **one proposition by default** only when all of the following hold:

1. they refer to the same underlying screening target or one operationally unified target;
2. their differences are state/time/history, overlapping/subsumed wording, or **interchangeable members/targets of one operational exposure or screening class that answer the same screening question**; and
3. they do **not** carry materially different branch-specific operational constraints (e.g., different temporal windows, numeric thresholds, grades, mechanisms that require separate checks, or independently required evidence) that make the branches separately adjudicable.

If **any** merge condition fails, do not merge at H1-A; proceed to H1-B. Failure of a merge condition is not, by itself, proof that a split is required.

Important:
- sharing an ontology superclass does **not** by itself mean two expressions are the same screening target;
- sharing the same predicate does **not** mean two expressions are the same screening target.

Examples:
- `history of IBD or active IBD` → same disease target, no branch-specific operational constraint → one proposition by default.
- `HIV and/or AIDS` → same disease spectrum / overlapping target for this screening purpose → one proposition by default.
- `allergy or hypersensitivity to X` → overlapping target → one proposition by default.
- `prior anti-PD-1 or anti-PD-L1 therapy` → interchangeable targets within one operational checkpoint-inhibitor exposure question, with no branch-specific constraint → one proposition by default.
- `CYP3A4 inhibitor or CYP3A4 inducer use` → same enzyme system but pharmacologically distinct exposure checks; do not merge merely because both belong to the CYP3A4 domain → continue to H1-B.
- `systemic corticosteroid treatment within 7 days` vs `other immunosuppressive treatment` → related exposure class, but the first branch has its own temporal constraint → continue to H1-B.
- `recovery from major surgery` vs `recovery from other complication` → the shared predicate is recovery, but the clinical targets differ; do not merge merely because the predicate is shared.

### H1-B. Independent assertion test

For candidates not merged by H1-A, ask:

> **After restoring shared context, does each candidate remain a distinct eligibility requirement that can be satisfied/violated separately in a way that changes whether the criterion as written holds?**

Use the truth-value contrast as **supporting evidence**, not as the sole proposition-counting rule.

Separate proposition candidates are supported when:
- each candidate has an independent eligibility role;
- each can be evaluated separately after shared context is restored;
- branch-specific constraints/evidence make the candidates operationally distinct;
- the protocol explicitly presents alternative or conjunctive requirements.

Keep one proposition when:
- multiple concepts jointly define one integrated regimen, measurement, status, or judgment;
- separating them would destroy a relation that is itself part of the requirement (e.g., `chemotherapy concurrent with radiation`);
- one expression is only a qualifier/method/scope for the other under H0.

Examples:
- `pregnant or lactating` → separate propositions.
- `active CNS metastases and/or carcinomatous meningitis` → separate clinical targets and separately evaluable exclusion states.
- `platinum-based chemotherapy concurrent with radiation therapy` → one integrated treatment-history proposition when concurrency defines the regimen.
- `recovered from major surgery or significant traumatic injury` → separate targets; proceed as separate proposition candidates, with H2 checking downstream leaf validity.

---

## H2. LEAF VALIDITY CHECK

After H1, test each prospective leaf for downstream representational validity.

### H2-A. Semantic-category mixing

A leaf must not contain **multiple independently asserted eligibility requirements** that require different Stage-2 `semantic_category` values.

- `NSCLC` + independently required `PD-L1 expression` → split.
- condition + independently required medication exposure → split.

Do **not** trigger this rule merely because a phrase contains a different target subtype or a concept used as:
- qualifier,
- purpose,
- assessment/confirmation method,
- scope,
- component of one integrated regimen/judgment.

H2-A validates the H1 proposition boundary; it should not turn Stage 1 into concept extraction.

### H2-B. Oncology/domain refinement

Diagnosis, stage, resectability, and biomarker **are separate Stage-1 units when they are independently asserted as coordinate eligibility predicates of the current criterion/target**.

Default local rule:

> **If an axis term is used only as the clinical object/population to which another eligibility predicate applies, treat it as scope by default. Split the axis only when the current criterion itself independently requires that axis as a coordinate eligibility assertion.**

Examples:
- `NSCLC + Stage III + unresectable`, where diagnosis, stage, and resectability are each asserted as population-defining requirements → separate units.
- `deemed unresectable NSCLC by multidisciplinary evaluation` → `by multidisciplinary evaluation` is an assessment method; `NSCLC` is not split solely because it names a diagnosis if, in the current target, it functions only as the disease scope of the unresectability judgment.
- stage subgrades that jointly define one stage category remain one stage unit.
- an independently required biomarker is separate from diagnosis.

### Confirmation rule — v1.3 normative change

> **Histologic, cytologic, pathologic, or documented confirmation normally belongs to the diagnosis proposition. Split confirmation only when the confirmation method/evidence itself is independently eligibility-determinative.**

This intentionally supersedes the v1.2.2 canonical example that could separate confirmation from diagnosis.

### Criterion-locality

Whether the same diagnosis/stage/resectability requirement appears in a neighboring criterion does **not** determine the local Stage-1 split. Cross-criterion duplication/deduplication belongs to a separate protocol-level consolidation step.

---

## H3. LIST / COVERAGE CHECK

For lists introduced by `including`, `such as`, `e.g.`, bullets, numbering, or similar structures, determine whether the named items **exhaust the parent eligibility meaning**.

### Open / non-exhaustive list

Examples: `e.g.`, `such as`, `including ... etc.`, or wording that clearly leaves other unnamed members possible.

If named items do not exhaust the parent meaning, do **not** split the named examples solely because they are individually recognizable concepts.

Reason: doing so would lose residual scope such as `other active infections` or `other uncontrolled systemic diseases`.

### Closed / operationally exhaustive list

Examples: `any of the following`, explicitly numbered complete alternatives, or a local list that fully operationalizes the parent requirement in the current target.

If the items are independently eligibility-determinative, they may become children.

### Operational-content tiebreaker

Item-specific numeric, temporal, grade, treatment, or evidence constraints are **strong evidence** that a named item carries independent operational content.

However:

> **Item-specific constraints do not by themselves prove that the surrounding list is closed/exhaustive.**

If, after applying the tiebreaker, the list remains open/non-exhaustive, **keep the broad parent meaning as one Stage-1 unit at the current level** rather than forcing overlapping named-item children.

Do not create a redundant residual-umbrella child solely to preserve residual scope.

**Representation note:** downstream relation-level constraints (e.g., value/temporal/status constraints attached to Criterion→Concept relations) can preserve item-specific operational detail inside a broader Stage-1 leaf. This is the explicit representational basis for keeping an open parent as one Stage-1 unit when named items carry local thresholds.

### Macro gate

Use `macro_aggregate` only when:
1. there are multiple independent child judgments,
2. the parent contains a true umbrella/wrapper,
3. the children collectively operationalize the parent without leaving hidden residual pass/fail content.

If there is no umbrella → `composite_split`.

---

## H4. ASSIGN STRUCTURE TYPE

Apply one hierarchy level at a time.

### `none`
One valid eligibility proposition remains at the current level.

### `composite_split`
Two or more independent eligibility propositions exist and no pure umbrella header organizes them.

### `macro_aggregate`
Two or more independent eligibility propositions are organized under a true umbrella/wrapper whose eligibility meaning is fully operationalized by the children.

### `nested_exception`
The current target contains a true carve-out, waiver, or exception to the main rule.

Exception test:
- if removing the exception phrase restores a broader main rule and the exception relaxes/waives part of that rule → `nested_exception`;
- a negative requirement such as `without X` is **not** automatically an exception; if absence of X must independently be satisfied, treat it as an ordinary requirement.

### Conditional permissive language

`allowed/permitted if Y` is an exception/waiver when `Y` changes the eligibility of an otherwise restricted state `X`.

Distinguish this from ordinary permissive language that does not alter eligibility requirements, such as `may also have received additional treatment`.

### Branch-specific exception

If an exception modifies only one branch of a larger composite structure:
1. split the top-level branches first,
2. keep the root `composite_split`/`macro_aggregate`,
3. preserve the dependent exception text with the affected branch so it remains available in the branch's `TARGET_SEGMENTS`,
4. recursively annotate the affected branch as `nested_exception`.

Exception spans are not child Criterion nodes and are not recursively split.

---

## H5. ASSIGN CHILD LOGIC

For `composite_split` and `macro_aggregate`, `child_logic` is mandatory.

**Interpretation of "holds":** evaluate whether each child condition **holds as written in the criterion**, not whether the patient is ultimately eligible.

- `AND`: all child conditions must hold for the parent criterion as written to hold.
- `OR`: any one child/path is sufficient for the parent criterion as written to hold.

### Applicable-branch semantics

Some criteria contain conditional requirements whose branch applies only when the corresponding prior event/state exists.

For such criteria:

> **`AND` means that every applicable branch must satisfy its requirement. A branch whose antecedent does not apply imposes no requirement; it is not treated as a failed child.**

This defines the logical representation of the criterion; Stage 1 does not perform patient-level eligibility evaluation.

Examples:
- exclusion: `pregnant or lactating` → `child_logic = OR`, because either child condition being true is sufficient for the exclusion criterion to hold.
- inclusion: `recovered from prior major surgery or significant traumatic injury` → separate recovery branches with `child_logic = AND` over applicable branches. The surface `or` names alternative antecedent events; it does not mean that recovery from only one applicable event is sufficient.

Determine logic from eligibility semantics, not from surface `and/or`, criterion type, or punctuation.

For `none` and `nested_exception`, do not assign `child_logic`.

Mixed logic such as `A AND (B1 OR B2)` must be represented hierarchically, not flattened into one parent.

---

## H6. RECURSION

One annotation pass handles one hierarchy level only.

- Every generated child is conceptually re-evaluated using H0–H6 with the **full root criterion available as read-only context**.
- Stop when the current target is `none`.
- For `nested_exception`, only the main portion can recurse; the exception span does not.

Operational definition:

> `needs_recursion=true` means an explicit next-level annotation remains because at least one generated child (or the main part of a nested exception) would itself receive a non-`none` Stage-1 decision.

A child that has been conceptually checked and is already a leaf has `needs_recursion=false`.

### Pipeline-control metadata

These fields are **execution metadata**, not ontology semantics:

- `needs_recursion: true|false`
- `recursion_targets: []`
  - for `composite_split` / `macro_aggregate`: child IDs requiring another Stage-1 pass
  - for `nested_exception`: use `["main"]` if the main content requires another pass
- `recursion_note`: brief reason for recursion, if `needs_recursion=true`

`recursion_targets` is a **new v1.3 pipeline-control field**. It is not an ontology property and was not present in the historical 113-item v1.2.2 adjudication records.

If `needs_recursion=false`, `recursion_targets` should be empty.

---

# Cross-cutting output rules

## X1. Current-target and text-span fidelity

LLM/annotation input should explicitly distinguish:

- `ROOT_CRITERION_TEXT`: full original criterion, read-only context
- `TARGET_SEGMENTS`: one or more exact source segments currently being annotated

At the root pass, `TARGET_SEGMENTS` normally contains the full criterion as one segment.

At recursive passes, `TARGET_SEGMENTS` contains only the child/main material intentionally propagated from the parent level, including any dependent branch-specific qualifier/exception text that must remain available.

Output rules:
- `text_span` is an array of one or more strings.
- Every output segment must be a verbatim contiguous substring of **one of the current `TARGET_SEGMENTS`**.
- A single child may contain multiple `text_span` segments.
- Those segments may come from **different `TARGET_SEGMENTS`**.
- Do not synthesize or normalize wording inside `text_span`.
- Do not pull new text from elsewhere in `ROOT_CRITERION_TEXT` if it is outside the current `TARGET_SEGMENTS`.

This prevents recursive annotation from re-importing sibling content.

## X2. Shared expressions and qualifier scope

- Do not duplicate a shared clinical entity solely to make a child grammatical.
- Copy a shared dependent qualifier (temporal/numeric/conditional/severity) into every child it semantically modifies.
- A child may be grammatically incomplete if root/parent context is available downstream.

Syntactic placement is a **default cue**, not a hard rule:
- a qualifier outside a coordination is evidence that it may modify all conjuncts;
- a qualifier located within one conjunct is evidence that it may modify only that branch;
- clinical/eligibility meaning overrides the default cue.

## X3. Exception-span boundaries

- When an explicit trigger exists, include the full trigger phrase from its first word, e.g. `with the exception of ...`, `other than ...`, `not required if ...`.
- For a triggerless parenthetical exception, annotate the exception content itself; do not add surrounding opening/closing parentheses merely because they enclose the exception.
- Preserve punctuation that belongs inside the selected exception content.
- Multiple sibling exception spans may attach to one main rule.

## X4. Cohort scope
- Cohort difference alone does not trigger splitting.
- Split only when cohort-specific **eligibility content** differs.
- Record `cohort_scope` only when the criterion text itself restricts applicability.
- Copy cohort labels verbatim from the provided trial cohort list.
- For `none` or `nested_exception`, scope may be attached to the current Criterion.
- For `composite_split` or `macro_aggregate`, record applicable scope on the relevant **child** Criterion(s), not as a parent-level shortcut.
- If a criterion/child applies to all cohorts, omit the ontology property. A fixed pipeline JSON transport may use `null`, but null values should be omitted during ontology serialization.

## X5. Broad adequacy / assessment / delegation
- Broad adequacy statement with no concrete subrequirements → `none`.
- Named test or assessment method without a separate pass/fail requirement → do not split the method.
- Thresholds delegated only to IB/Table/appendix → `none` at the current text + note delegation.
- Explicit local thresholds → evaluate normally under H0–H4.

## X6. Conceptual queryability / evidence source

Stage-1 units are based on conceptual eligibility decisions, not on whether a specific institution has a convenient structured EMR field.

Independent documentation in standard clinical sources (e.g., medication history, pathology, imaging, laboratory results, treatment records) can be **supporting evidence** that two assertions are separately adjudicable, but:
- site-specific field availability is not a structural rule;
- a different source document alone is not sufficient to force a split.

## X7. Criterion-local decomposition

Stage 1 decomposes the **current target only**.

- Do not import a neighboring criterion's text as a child span.
- Do not suppress a local requirement merely because the same requirement appears elsewhere in the protocol.
- Cross-criterion grouping, deduplication, and protocol-level macro construction are separate preprocessing/consolidation tasks.

---

# Provenance defaults

Evidence tier should be derived from the **primary decisive canonical rule**, not manually guessed from the whole criterion.

Proposed defaults:
- H2-A semantic-category / ontology validity rule → Tier 0
- H2-B oncology/domain clinical-authority rule → Tier 1
- H0 / H1 / H3 / H4 / H5 / H6 and X-rules → Tier 2 by default unless a rule explicitly cites a higher authority

Recommended provenance fields:
- `primary_rule_id`
- optional `supporting_rule_ids`
- `tier` derived from `primary_rule_id`

This provenance convention is separate from the H0–H6 structural decision hierarchy.

---

# Compatibility with v1.2.2

v1.3.0 preserves the four labels, explicit child-logic semantics, text-span array convention, cohort-scope convention, and recursive one-level-at-a-time representation. It reorganizes precedence rather than changing the ontology wholesale.

## Legacy rule ID → v1.3 canonical-family mapping

This table is intended for **analysis/provenance recoding**, not for rewriting the historical 113-item records. Preserve each original `rule_id`; add a derived `canonical_rule_family` when comparing v1.2.2 evidence with v1.3 LLM outputs.

`mapping_type`:
- `direct` — same core behavior, reorganized wording
- `conditional` — old rule maps to more than one H/X step or its scope has been narrowed
- `superseded` — old behavior is intentionally replaced in v1.3

| v1.2.2 rule | v1.3 family | mapping_type | v1.3.0 interpretation |
|---|---|---|---|
| §1-1 | H4 | direct | composite_split definition |
| §1-2 | H3/H4 | conditional | macro requires closed/fully operationalized umbrella |
| §1-3, §1-4 | H4 | direct | nested_exception / trigger semantics |
| §1-5 | H4, X3 | direct | exception span is not a child Criterion |
| §2-1 | H0–H6 | conditional | old decision order replaced by explicit H0→H6 precedence |
| §2-2 | H1, H3, H4, H6 | conditional | top-level structure first; internal list/exception handled at proper level |
| §2-3 | H4, H6 | direct | branch-specific exception handled by top-level split + recursion |
| §2-4 | H6 | direct | one hierarchy level per pass |
| §2-5 | H6 | conditional | all children conceptually rechecked; explicit recursion only for non-none lower structure |
| §2-6 | H6 | direct | nested exception: recurse main only |
| §2-7 | H6, X1 | conditional | full root remains read-only context; output restricted to TARGET_SEGMENTS |
| §3-1 | H0, H1 | conditional | query-unit principle decomposed into role/scope + proposition boundary |
| §3-2, §3-3 | H2-A | conditional | semantic-category split only for independently asserted requirements |
| §3-4 | X5 | direct | external-document delegation → none at current text level |
| §3-5 | X7 | superseded | neighboring-criterion macro construction moved outside Stage 1 |
| §4-1, §4-2 | H4 | direct | umbrella distinguishes macro from composite after units are identified |
| §4-3 | H1, H3 | conditional | one operational class / open examples may remain one unit |
| §4-4 | H3, H4 | conditional | residual-scope issue resolved by coverage test; do not force redundant residual child |
| §5-1, §5-2 | H1, H4 | direct | one child per independent proposition |
| §5-3 | H4 | direct | macro umbrella remains parent wrapper |
| §5-4 | H6 | direct | children are re-evaluated recursively |
| §6-1 | H2-B | conditional | fixed 3-way rule narrowed to criterion-local independent coordinate axes |
| §6-2 | H2-B | direct | stage subgrades remain one stage unit |
| §6-3 | H2-A/H2-B | direct | independently required biomarker remains separate from diagnosis |
| §6-4, §6-5 | downstream note | conditional | downstream re-linking behavior; not a primary Stage-1 decision rule |
| §7-1, §7-2 | H5 | direct | child_logic explicit for composite/macro only |
| §7-3 | H5 | direct | logic from eligibility semantics, not surface connector |
| §7-4 | H5, H6 | direct | mixed logic represented hierarchically |
| §T0-1 | X1 | direct | exact verbatim substring |
| §T0-2 | X1 | conditional | array preserved; recursive output now restricted to current TARGET_SEGMENTS |
| §T1-1 | X2 | direct | do not duplicate shared clinical entity for grammar |
| §T1-2 | X2, H5 | conditional | shared independent requirement represented structurally; dependent qualifier handled separately |
| §T2-1 | X1 | direct | discontinuous judgment uses multiple segments |
| §T3-1–§T3-5 | X2 | direct | dependent qualifier follows semantic scope; syntax only a cue |
| §T4-1, §T4-2 | X1 | conditional | incomplete spans allowed with ROOT/PARENT context; TARGET_SEGMENTS controls provenance |
| §T5-1, §T5-2 | X3 | direct | exception span boundary / no recursive split |
| §T6-1–§T6-3 | X1, X3 | direct | exact span-boundary rules |
| §C1-1–§C1-4 | X4 | direct | record explicit applicability only |
| §C2-1, §C2-2 | X4 | direct | cohort difference is not a split trigger |
| §C3-1–§C3-4 | X4 | conditional | child-level scope preserved; pipeline null may be omitted at ontology serialization |

## Explicit v1.3 normative changes / clarifications

1. H1 is split into `same screening-target` and `independent assertion` tests.
2. The H1 truth-value test is supporting evidence, not the sole proposition-counting rule.
3. Same-target merging requires matching operational constraints; any failed merge condition sends the case to H1-B.
4. `screening target` means the clinical object/state, not the shared predicate.
5. “target-class alternatives” is narrowed to interchangeable members/targets that answer the same screening question and carry no branch-specific constraint.
6. confirmation normally remains with diagnosis.
7. no MDT-specific exception is used; oncology-axis decomposition uses criterion-local predicate-vs-scope semantics.
8. open-list item-specific thresholds are strong operational cues but do not prove closure.
9. if a list remains open, retain the broad parent as one Stage-1 unit; downstream relation-level constraints preserve item-specific details.
10. redundant residual-umbrella children are not created solely to preserve open-list scope.
11. conditional `allowed/permitted if` may encode a waiver/exception.
12. H5 explicitly supports AND over applicable conditional branches.
13. recursion control uses `needs_recursion`, new `recursion_targets`, and `recursion_note`.
14. recursive span generation is restricted to `TARGET_SEGMENTS`, while full root text remains read-only context.
15. cross-criterion aggregation/deduplication is moved outside Stage 1.
16. cohort scope is represented at the child level after split; all-cohort scope is omitted at ontology serialization.

The frozen 113-item v1.2.2 evidence set should remain unchanged; any later v1.3-harmonized reference set should be versioned separately.

---

# Version and freeze policy

This canonical specification is frozen as:

`Stage 1 Canonical Guideline v1.3.0`

Any subsequent behavioral change requires a new normative version according to the policy below.

Version decisions are based on **behavioral semantics**, not the number of edited words.

## v1.3.x — non-normative implementation patch

Allowed after the canonical v1.3.0 freeze when behavior does not change:
- wording/formatting clarification
- synthetic example replacement/addition that illustrates an existing rule
- redundant `DO` / `DO NOT` instruction
- JSON validation or transport detail
- implementation note that does not alter a split/merge/logic boundary

## v1.4 — normative change

Required when any change alters:
- H0–H6 or X-rule meaning
- rule precedence
- structure-label semantics
- split/merge boundary
- exception boundary
- child-logic behavior
- criterion-local vs cross-criterion scope
- downstream representational assumption used to justify a Stage-1 decision

A `DO NOT` line counts as normative if it changes behavior rather than merely restating an already-frozen rule.

## Prompt freeze

Recommended sequence:

```text
Canonical v1.3.0 freeze
        ↓
Prompt development with 1 frontier + 1 open-weight model
        ↓
Non-normative prompt patches (v1.3.x) only
        ↓
FINAL PROMPT FREEZE
        ↓
Comparative evaluation across the prespecified 3 frontier + 2 open-weight model families
```

After the final prompt freeze, do not alter rule wording, examples, or output behavior between model families. Any later normative discovery is logged for v1.4 rather than retroactively modifying v1.3.0.
