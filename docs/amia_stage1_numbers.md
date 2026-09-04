# AMIA 2027 — Stage 1 adjudicated gold: abstract numbers

Recomputed from the frozen export. Annotator inputs: `iaa_workspace/*/stage1/round2/`.

## 1. Dataset

- adjudicated items: **74 gold**, 0 open tier-3 gap
- trials: 8
- queue stratum: S1 49, S4 25
- tier: 0 6, 1 2, 2 66
- gold splitting_decision: none 39, composite_split 28, nested_exception 5, macro_aggregate 2

## 2. Annotator agreement (EHJ vs DYK), splitting_decision

| corpus | n | agreed | κ | observed |
|---|--:|--:|--:|--:|
| full round-2 | 172 | 138 | 0.650 | 0.802 |
| adjudicated subset | 74 | 40 | 0.286 | 0.540 |

> The adjudicated subset was intentionally enriched for disagreement and is
> therefore **not representative** of the full round-2 corpus. Its κ is
> descriptive only and should not be read as a second estimate of
> corpus-level agreement. Note that κ depends on the marginal distribution
> as well as on raw agreement, so disagreement-enriched sampling does not
> bound the corpus value in either direction — the two rows simply measure
> different samples.

## 3. Gold-axis agreement (adjudicated subset only)

| pair | n | agreed | observed | κ |
|---|--:|--:|--:|--:|
| EHJ vs GOLD | 74 | 54 | 0.730 | 0.524 |
| DYK vs GOLD | 74 | 51 | 0.689 | 0.494 |
| EHJ vs DYK | 74 | 40 | 0.540 | 0.286 |

> Same caveat: all three are measured on the disagreement-enriched subset,
> so they compare to each other but not to the corpus figures above.
>
> These are **agreement against a reference**, not accuracy. κ is
> chance-corrected, so it is not the proportion of criteria an annotator
> got right; the accuracy-shaped figure is the raw `agreed` column. In
> prose, prefer:
>
> *Against adjudicated gold, EHJ and DYK agreed on 54/74 (73.0%) and 51/74 (68.9%) of criteria, respectively (κ = 0.524 and 0.494).*

## 4. What adjudication actually changed

| outcome | n |
|---|--:|
| annotators agreed, gold confirmed | 37 |
| annotators split, gold sided with EHJ | 17 |
| annotators split, gold sided with DYK | 14 |
| annotators agreed, gold OVERRODE both | 3 |
| annotators split, gold chose a third answer | 3 |

Gold overrode a **unanimous** annotator pair on 3 item(s): NCT01295827_I2, NCT03728556_E17, NCT03728556_E5.
This is the case a 2-of-3 majority vote cannot produce, and the reason
the adjudicator's label is not treated as a third vote.

## 5. Guideline outcomes

- rule_status: existing 64, new 9, conflict 1
- escalate_pi=true: 3 (NCT02125461_I2, NCT03728556_I3, NCT05756153_E6)
- rule_status=conflict: NCT05756153_E6
- adjudication pass: blind 74

Adjudication ran as a single blind pass, so there is no revealed-pass
revision to report: `blind_label` equals the gold label on every record
and the D-3 (blind ≠ gold) analysis has no sample in this dataset.
