"""Inter-annotator agreement (IAA) metrics.

Self-contained — no sklearn / numpy dependency.

Primary metrics:
  - Cohen's κ        for categorical (splitting_decision, semantic_category, ...)
  - Exact-match rate for categorical when κ is undefined (single-class case)
  - Per-field F1     for partially-overlapping field sets (Stage 4)
  - Set agreement    for unordered lists (cohort_scope)

Top-level entry points:
  - compute_stage1_iaa(envelope_a, envelope_b)
  - compute_stage2_iaa(envelope_a, envelope_b)
  - compute_stage4_iaa(envelope_a, envelope_b)
  - compute_error_type_iaa(entries_a, entries_b)

Each returns a dict of metric_name -> value (or sub-dict).

See iaa_pipeline_spec/03_json_schemas.md §107-114, §174-181, §306-316 for
which fields go into IAA computation per stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .aligners import (
    AlignmentResult,
    Stage2Alignment,
    align_stage1,
    align_stage2,
    align_stage4,
    align_error_types,
)


# ──────────────────────────────────────────────────────────────────────
# Core categorical metrics
# ──────────────────────────────────────────────────────────────────────

@dataclass
class CategoricalAgreement:
    """Agreement on a categorical field for a set of aligned pairs."""
    n: int                      # number of pairs compared
    n_agree: int                # exact-match count
    observed: float             # n_agree / n
    kappa: float | None         # Cohen's κ; None when undefined (e.g. only one class)
    classes: list[str]          # observed classes (sorted, for reporting)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "n_agree": self.n_agree,
            "observed_agreement": round(self.observed, 4),
            "cohens_kappa": round(self.kappa, 4) if self.kappa is not None else None,
            "classes": self.classes,
        }


def cohens_kappa(labels_a: list[Any], labels_b: list[Any]) -> CategoricalAgreement:
    """Compute Cohen's κ between two lists of categorical labels.

    Formula:
        κ = (p_o - p_e) / (1 - p_e)
    where p_o is observed agreement and p_e is chance agreement.

    Returns κ=None when 1 - p_e == 0 (i.e., both annotators always pick
    the same single class — observed agreement is 1.0 but κ is undefined).
    Always returns the observed agreement regardless.
    """
    if len(labels_a) != len(labels_b):
        raise ValueError(
            f"labels_a and labels_b must be the same length "
            f"({len(labels_a)} vs {len(labels_b)})"
        )
    n = len(labels_a)
    if n == 0:
        return CategoricalAgreement(n=0, n_agree=0, observed=1.0, kappa=None, classes=[])

    # Normalize None to a sentinel so it counts as its own class
    def norm(x: Any) -> Any:
        return "__NONE__" if x is None else x

    a_norm = [norm(x) for x in labels_a]
    b_norm = [norm(x) for x in labels_b]
    classes = sorted({*a_norm, *b_norm}, key=lambda x: str(x))

    n_agree = sum(1 for x, y in zip(a_norm, b_norm) if x == y)
    p_o = n_agree / n

    # Marginal probabilities
    p_e = 0.0
    for c in classes:
        p_a = sum(1 for x in a_norm if x == c) / n
        p_b = sum(1 for y in b_norm if y == c) / n
        p_e += p_a * p_b

    if abs(1.0 - p_e) < 1e-12:
        kappa: float | None = None
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return CategoricalAgreement(
        n=n,
        n_agree=n_agree,
        observed=p_o,
        kappa=kappa,
        classes=[c for c in classes if c != "__NONE__"] + (["null"] if "__NONE__" in classes else []),
    )


def _cohort_scope_repr(record: dict) -> frozenset:
    """Normalized, comparable representation of a record's cohort_scope.

    cohort_scope can appear in two places:
      - record level (non-split criteria, and legacy drafts)
      - per sub-criterion (split criteria — the current model)

    Each element is a ``(child_id, cohort)`` tuple so that the same cohort
    assigned to different children does not spuriously "match". Record-level
    scope is tagged with the sentinel child id ``"*"``. This keeps exact-set
    and Jaccard comparison meaningful across both placements.
    """
    pairs: set[tuple[str, Any]] = set()
    for cohort in record.get("cohort_scope") or []:
        pairs.add(("*", cohort))
    for sub in record.get("sub_criteria") or []:
        if not isinstance(sub, dict):
            continue
        child_id = sub.get("child_id", "?")
        for cohort in sub.get("cohort_scope") or []:
            pairs.add((child_id, cohort))
    return frozenset(pairs)


def set_agreement(set_a: Iterable[Any] | None, set_b: Iterable[Any] | None) -> dict[str, Any]:
    """Compare two unordered sets (e.g., cohort_scope lists).

    Returns exact match + Jaccard similarity. Treats None and [] as equal.
    """
    sa = frozenset(set_a) if set_a else frozenset()
    sb = frozenset(set_b) if set_b else frozenset()
    exact = sa == sb
    union = sa | sb
    jaccard = len(sa & sb) / len(union) if union else 1.0
    return {"exact_match": exact, "jaccard": round(jaccard, 4)}


# ──────────────────────────────────────────────────────────────────────
# Per-field exact match (Stage 4 style)
# ──────────────────────────────────────────────────────────────────────

def per_field_match_rate(
    pairs: list[tuple[dict, dict]],
    fields: list[str],
) -> dict[str, dict[str, Any]]:
    """For each field name, compute the exact-match rate across pairs.

    Pairs where a field is absent in both sides are counted as matching
    (both annotators implicitly agreed the field doesn't apply). Pairs
    where it's present in one but not the other count as disagreement.
    """
    out: dict[str, dict[str, Any]] = {}
    for f in fields:
        n = 0
        n_agree = 0
        for a, b in pairs:
            has_a = f in a
            has_b = f in b
            if not has_a and not has_b:
                continue  # neither side mentions this field; skip
            n += 1
            if has_a and has_b and a[f] == b[f]:
                n_agree += 1
        out[f] = {
            "n": n,
            "n_agree": n_agree,
            "match_rate": round(n_agree / n, 4) if n else None,
        }
    return out


# ──────────────────────────────────────────────────────────────────────
# Stage 1 — splitting IAA
# ──────────────────────────────────────────────────────────────────────

def compute_stage1_iaa(envelope_a: dict, envelope_b: dict) -> dict[str, Any]:
    """Compute Stage 1 IAA between two annotator envelopes.

    Returns a dict with:
      - alignment       : presence stats
      - splitting_decision : Cohen's κ (primary)
      - child_logic        : Cohen's κ on the subset where BOTH annotators
                             marked the parent as composite_split
                             (per spec §111 "only for composite_split")
      - cohort_scope       : set agreement stats over pairs
    """
    alignment = align_stage1(envelope_a, envelope_b)

    sd_a = [a.get("splitting_decision") for a, _ in alignment.matched]
    sd_b = [b.get("splitting_decision") for _, b in alignment.matched]
    sd_agree = cohens_kappa(sd_a, sd_b)

    # child_logic only on pairs where both said composite_split
    cl_a, cl_b = [], []
    for a, b in alignment.matched:
        if a.get("splitting_decision") == "composite_split" \
                and b.get("splitting_decision") == "composite_split":
            cl_a.append(a.get("child_logic"))
            cl_b.append(b.get("child_logic"))
    cl_agree = cohens_kappa(cl_a, cl_b)

    # cohort_scope per pair (set-level agreement). cohort_scope lives at the
    # record level for non-split criteria and per sub-criterion for split
    # criteria, so we compare a normalized (child_id, cohort) representation
    # that accounts for both placements (and legacy record-level data).
    cs_stats = [
        set_agreement(_cohort_scope_repr(a), _cohort_scope_repr(b))
        for a, b in alignment.matched
    ]
    n_cs = len(cs_stats)
    cs_exact = sum(1 for s in cs_stats if s["exact_match"]) / n_cs if n_cs else 1.0
    cs_jaccard = sum(s["jaccard"] for s in cs_stats) / n_cs if n_cs else 1.0

    return {
        "stage": 1,
        "alignment": _alignment_summary(alignment),
        "splitting_decision": sd_agree.as_dict(),
        "child_logic": cl_agree.as_dict() | {
            "scope": "pairs where both = composite_split",
        },
        "cohort_scope": {
            "n_pairs": n_cs,
            "exact_match_rate": round(cs_exact, 4),
            "mean_jaccard": round(cs_jaccard, 4),
        },
    }


# ──────────────────────────────────────────────────────────────────────
# Stage 2 — semantic category + relation IAA
# ──────────────────────────────────────────────────────────────────────

def compute_stage2_iaa(
    envelope_a: dict,
    envelope_b: dict,
    *,
    span_similarity_threshold: float = 0.85,
) -> dict[str, Any]:
    """Compute Stage 2 IAA.

    Two layers of comparison:
      1. semantic_category κ at the sub_criterion level
      2. relation_type κ + target_subtype κ at the aligned-relation level
         (relations aligned by target_text_span; presence agreement reported)
    """
    s2 = align_stage2(envelope_a, envelope_b,
                       span_similarity_threshold=span_similarity_threshold)

    # semantic_category on matched sub_criteria
    sc_a = [a.get("semantic_category") for a, _ in s2.sub_criteria.matched]
    sc_b = [b.get("semantic_category") for _, b in s2.sub_criteria.matched]
    sc_agree = cohens_kappa(sc_a, sc_b)

    # Aggregate relation-level alignments across all sub_criteria
    all_relation_pairs: list[tuple[dict, dict]] = []
    n_only_a = 0
    n_only_b = 0
    for _sub_id, rel_align in s2.relations:
        all_relation_pairs.extend(rel_align.matched)
        n_only_a += len(rel_align.only_a)
        n_only_b += len(rel_align.only_b)

    rt_a = [a.get("relation_type") for a, _ in all_relation_pairs]
    rt_b = [b.get("relation_type") for _, b in all_relation_pairs]
    ts_a = [a.get("target_subtype") for a, _ in all_relation_pairs]
    ts_b = [b.get("target_subtype") for _, b in all_relation_pairs]

    rel_total = len(all_relation_pairs) + n_only_a + n_only_b
    rel_presence = len(all_relation_pairs) / rel_total if rel_total else 1.0

    return {
        "stage": 2,
        "sub_criteria_alignment": _alignment_summary(s2.sub_criteria),
        "semantic_category": sc_agree.as_dict(),
        "relations": {
            "n_matched": len(all_relation_pairs),
            "n_only_a": n_only_a,
            "n_only_b": n_only_b,
            "presence_agreement": round(rel_presence, 4),
            "relation_type": cohens_kappa(rt_a, rt_b).as_dict(),
            "target_subtype": cohens_kappa(ts_a, ts_b).as_dict(),
        },
    }


# ──────────────────────────────────────────────────────────────────────
# Stage 4 — constraint IAA (per-field exact match + macro)
# ──────────────────────────────────────────────────────────────────────

# Fields to compare per relation_type. See spec §306-316.
STAGE4_VALUE_FIELDS = ["operator", "value", "unit", "scale"]
STAGE4_TEMPORAL_FIELDS = ["operator", "value", "unit", "anchor", "direction", "anchor_type"]


def compute_stage4_iaa(envelope_a: dict, envelope_b: dict) -> dict[str, Any]:
    """Compute Stage 4 IAA.

    Records are aligned by (sub_criterion_id, relation_id). Per-field
    exact match rate is computed separately for HAS_VALUE and HAS_TEMPORAL
    records. Macro = mean of per-field rates.

    Also splits agreement by extraction_source (regex vs llm) per spec §319
    — regex records should hit ~100% (deterministic), so the LLM subset is
    where real disagreement lives.
    """
    alignment = align_stage4(envelope_a, envelope_b)

    value_pairs: list[tuple[dict, dict]] = []
    temporal_pairs: list[tuple[dict, dict]] = []
    regex_pairs: list[tuple[dict, dict]] = []
    llm_pairs: list[tuple[dict, dict]] = []
    for a, b in alignment.matched:
        rt_a = a.get("relation_type")
        rt_b = b.get("relation_type")
        if rt_a == "HAS_VALUE" and rt_b == "HAS_VALUE":
            value_pairs.append((a, b))
        elif rt_a == "HAS_TEMPORAL" and rt_b == "HAS_TEMPORAL":
            temporal_pairs.append((a, b))
        # If they disagree on relation_type, skip — Stage 2 should've caught it
        if a.get("extraction_source") == "regex" and b.get("extraction_source") == "regex":
            regex_pairs.append((a, b))
        else:
            llm_pairs.append((a, b))

    value_fields = per_field_match_rate(value_pairs, STAGE4_VALUE_FIELDS)
    temporal_fields = per_field_match_rate(temporal_pairs, STAGE4_TEMPORAL_FIELDS)

    def macro(field_dict: dict[str, dict]) -> float | None:
        rates = [v["match_rate"] for v in field_dict.values() if v["match_rate"] is not None]
        return round(sum(rates) / len(rates), 4) if rates else None

    return {
        "stage": 4,
        "alignment": _alignment_summary(alignment),
        "has_value": {
            "n_pairs": len(value_pairs),
            "fields": value_fields,
            "macro_match_rate": macro(value_fields),
        },
        "has_temporal": {
            "n_pairs": len(temporal_pairs),
            "fields": temporal_fields,
            "macro_match_rate": macro(temporal_fields),
        },
        "by_extraction_source": {
            "regex": {"n_pairs": len(regex_pairs)},
            "llm": {"n_pairs": len(llm_pairs)},
        },
    }


# ──────────────────────────────────────────────────────────────────────
# Error-type IAA (cross-stage)
# ──────────────────────────────────────────────────────────────────────

def compute_error_type_iaa(
    entries_a: list[dict],
    entries_b: list[dict],
) -> dict[str, Any]:
    """Compute Cohen's κ on error_type entries aligned by record_locator.

    For multi-label error_type values (comma-separated per spec §403), the
    comparison treats them as sets — two annotators agree iff their sets
    are exactly equal. (Macro/jaccard could be added later.)
    """
    alignment = align_error_types(entries_a, entries_b)

    def normalize_label(x: Any) -> str:
        if x is None:
            return "__NONE__"
        if isinstance(x, str) and "," in x:
            return ",".join(sorted(s.strip() for s in x.split(",") if s.strip()))
        return str(x)

    labels_a = [normalize_label(a.get("error_type")) for a, _ in alignment.matched]
    labels_b = [normalize_label(b.get("error_type")) for _, b in alignment.matched]
    agreement = cohens_kappa(labels_a, labels_b)

    return {
        "alignment": _alignment_summary(alignment),
        "error_type": agreement.as_dict(),
    }


# ──────────────────────────────────────────────────────────────────────
# Stages 3 & 5 — stubs (require gold + adjudication structure)
# ──────────────────────────────────────────────────────────────────────

def compute_stage3_iaa(*_args, **_kwargs) -> dict[str, Any]:
    """Stage 3 LLM-assisted α/β/γ/δ — not yet implemented.

    Requires four parallel envelopes (LLM, A, B, consensus). See spec §246-254.
    """
    raise NotImplementedError(
        "Stage 3 LLM-assisted IAA (α/β/γ/δ) not yet implemented. "
        "Requires four-way comparison (LLM, annotator_a, annotator_b, consensus). "
        "See iaa_pipeline_spec/03_json_schemas.md §246-254."
    )


def compute_stage5_iaa(*_args, **_kwargs) -> dict[str, Any]:
    """Stage 5 adjudication-based metrics — not yet implemented.

    Requires adjudication file format which is not yet defined. See spec §355-365.
    """
    raise NotImplementedError(
        "Stage 5 adjudication metrics not yet implemented. "
        "Requires adjudication file format. "
        "See iaa_pipeline_spec/03_json_schemas.md §355-365."
    )


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _alignment_summary(alignment: AlignmentResult) -> dict[str, Any]:
    return {
        "n_matched": alignment.n_matched,
        "n_only_a": len(alignment.only_a),
        "n_only_b": len(alignment.only_b),
        "presence_agreement": round(alignment.presence_agreement, 4),
    }
