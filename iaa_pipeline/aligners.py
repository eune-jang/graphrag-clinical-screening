"""Record alignment between two annotators (or LLM vs annotator).

Two annotators can produce different numbers of records for the same input
(e.g., annotator A finds 3 relations in a sub-criterion, B finds 2). Before
any per-record agreement metric can be computed, records must be paired up.

Alignment keys per stage (see iaa_pipeline_spec/03_json_schemas.md):

  Stage 1   criterion_id                              (1:1, never missing)
  Stage 2   sub_criterion_id  → relations by target_text_span (fuzzy)
  Stage 3   (sub_criterion_id, relation_id)           (depends on Stage 2 gold)
  Stage 4   (sub_criterion_id, relation_id)
  Stage 5   (sub_criterion_id, relation_id)
  ErrorType record_locator (tuple of sorted key=value pairs)

The output of every aligner is an `AlignmentResult` containing:
  - matched   : pairs where both A and B have a record
  - only_a    : records in A but not in B  (B "missing")
  - only_b    : records in B but not in A  (A "missing")

Metrics computed over `matched` use the categorical fields. Metrics computed
over presence (e.g., "annotator A found N relations, B found M") use the
counts of `matched + only_a` vs `matched + only_b`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Hashable


# ──────────────────────────────────────────────────────────────────────
# Generic alignment result
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AlignmentResult:
    """Result of aligning records from two annotators.

    matched : list of (record_a, record_b) pairs, both non-None
    only_a  : records present only in annotator A
    only_b  : records present only in annotator B
    """
    matched: list[tuple[dict, dict]] = field(default_factory=list)
    only_a: list[dict] = field(default_factory=list)
    only_b: list[dict] = field(default_factory=list)

    @property
    def n_matched(self) -> int:
        return len(self.matched)

    @property
    def n_a_total(self) -> int:
        return len(self.matched) + len(self.only_a)

    @property
    def n_b_total(self) -> int:
        return len(self.matched) + len(self.only_b)

    @property
    def presence_agreement(self) -> float:
        """Fraction of records that aligned (Jaccard-like).

        |matched| / (|matched| + |only_a| + |only_b|)
        """
        denom = len(self.matched) + len(self.only_a) + len(self.only_b)
        return len(self.matched) / denom if denom else 1.0


# ──────────────────────────────────────────────────────────────────────
# Key-based alignment (the common case)
# ──────────────────────────────────────────────────────────────────────

def align_by_key(
    records_a: list[dict],
    records_b: list[dict],
    key: str | tuple[str, ...],
) -> AlignmentResult:
    """Align two lists of records by an exact key.

    `key` may be a single field name or a tuple of field names (composite key).
    Records missing any key field are silently dropped (caller's responsibility
    to validate beforehand if strictness is desired).
    """
    keys = (key,) if isinstance(key, str) else tuple(key)

    def make_key(rec: dict) -> Hashable | None:
        try:
            return tuple(rec[k] for k in keys)
        except KeyError:
            return None

    map_a: dict[Hashable, dict] = {}
    map_b: dict[Hashable, dict] = {}
    for r in records_a:
        k = make_key(r)
        if k is not None:
            map_a[k] = r
    for r in records_b:
        k = make_key(r)
        if k is not None:
            map_b[k] = r

    result = AlignmentResult()
    for k, ra in map_a.items():
        if k in map_b:
            result.matched.append((ra, map_b[k]))
        else:
            result.only_a.append(ra)
    for k, rb in map_b.items():
        if k not in map_a:
            result.only_b.append(rb)
    return result


# ──────────────────────────────────────────────────────────────────────
# Stage 1 — by criterion_id (exact)
# ──────────────────────────────────────────────────────────────────────

def align_stage1(envelope_a: dict, envelope_b: dict) -> AlignmentResult:
    """Align Stage 1 records by criterion_id.

    Stage 1 has exactly one record per input criterion, so the only
    failure mode is one side missing a criterion entirely (rare; usually
    means a record had an _error placeholder).
    """
    records_a = _live_records(envelope_a)
    records_b = _live_records(envelope_b)
    return align_by_key(records_a, records_b, "criterion_id")


# ──────────────────────────────────────────────────────────────────────
# Stage 2 — sub_criterion + relation alignment (fuzzy on text_span)
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Stage2Alignment:
    """Two-level alignment for Stage 2.

    sub_criteria : Stage-1-like alignment by sub_criterion_id
    relations    : list of (sub_criterion_id, AlignmentResult-on-relations)
                   only computed for sub_criteria that matched on both sides
    """
    sub_criteria: AlignmentResult
    relations: list[tuple[str, AlignmentResult]] = field(default_factory=list)


def align_stage2(
    envelope_a: dict,
    envelope_b: dict,
    *,
    span_similarity_threshold: float = 0.85,
) -> Stage2Alignment:
    """Align Stage 2 envelopes: first by sub_criterion_id, then relations.

    Relations within a sub_criterion are aligned by `target_text_span`:
      1. Exact text match (case-insensitive after whitespace normalization)
      2. Fuzzy match using SequenceMatcher.ratio() ≥ threshold
         (only used when no exact match found)

    Spec reference: 03_json_schemas.md §183-193 "Relation alignment problem".
    """
    records_a = _live_records(envelope_a)
    records_b = _live_records(envelope_b)
    sub_alignment = align_by_key(records_a, records_b, "sub_criterion_id")

    relation_alignments: list[tuple[str, AlignmentResult]] = []
    for rec_a, rec_b in sub_alignment.matched:
        rels_a = rec_a.get("relations", []) or []
        rels_b = rec_b.get("relations", []) or []
        rel_align = align_relations_by_span(
            rels_a, rels_b, threshold=span_similarity_threshold
        )
        relation_alignments.append((rec_a["sub_criterion_id"], rel_align))

    return Stage2Alignment(
        sub_criteria=sub_alignment,
        relations=relation_alignments,
    )


def align_relations_by_span(
    relations_a: list[dict],
    relations_b: list[dict],
    *,
    threshold: float = 0.85,
) -> AlignmentResult:
    """Align two relation lists by target_text_span.

    First pass: exact match (normalized). Second pass: best fuzzy match
    above threshold. A record can only be matched once.
    """
    norm_a = [_normalize_span(r.get("target_text_span", "")) for r in relations_a]
    norm_b = [_normalize_span(r.get("target_text_span", "")) for r in relations_b]
    matched_b: set[int] = set()
    result = AlignmentResult()

    # Pass 1: exact normalized match
    used_a: set[int] = set()
    for i, na in enumerate(norm_a):
        if not na:
            continue
        for j, nb in enumerate(norm_b):
            if j in matched_b or not nb:
                continue
            if na == nb:
                result.matched.append((relations_a[i], relations_b[j]))
                matched_b.add(j)
                used_a.add(i)
                break

    # Pass 2: fuzzy match for the leftover ones
    for i, na in enumerate(norm_a):
        if i in used_a or not na:
            continue
        best_j: int | None = None
        best_score = threshold
        for j, nb in enumerate(norm_b):
            if j in matched_b or not nb:
                continue
            score = SequenceMatcher(None, na, nb).ratio()
            if score >= best_score:
                best_score = score
                best_j = j
        if best_j is not None:
            result.matched.append((relations_a[i], relations_b[best_j]))
            matched_b.add(best_j)
            used_a.add(i)

    # Leftovers
    for i, ra in enumerate(relations_a):
        if i not in used_a:
            result.only_a.append(ra)
    for j, rb in enumerate(relations_b):
        if j not in matched_b:
            result.only_b.append(rb)
    return result


# ──────────────────────────────────────────────────────────────────────
# Stage 3, 4, 5 — by (sub_criterion_id, relation_id) composite key
# ──────────────────────────────────────────────────────────────────────

def align_stage3(envelope_a: dict, envelope_b: dict) -> AlignmentResult:
    return align_by_key(
        _live_records(envelope_a),
        _live_records(envelope_b),
        ("sub_criterion_id", "relation_id"),
    )


def align_stage4(envelope_a: dict, envelope_b: dict) -> AlignmentResult:
    return align_by_key(
        _live_records(envelope_a),
        _live_records(envelope_b),
        ("sub_criterion_id", "relation_id"),
    )


def align_stage5(envelope_a: dict, envelope_b: dict) -> AlignmentResult:
    return align_by_key(
        _live_records(envelope_a),
        _live_records(envelope_b),
        ("sub_criterion_id", "relation_id"),
    )


# ──────────────────────────────────────────────────────────────────────
# Error type annotations — by record_locator (dict)
# ──────────────────────────────────────────────────────────────────────

def align_error_types(
    entries_a: list[dict],
    entries_b: list[dict],
) -> AlignmentResult:
    """Align ErrorTypeAnnotation entries by record_locator.

    record_locator is a dict like {"sub_criterion_id": "X", "relation_id": "r1"}.
    We hash it deterministically by sorting items.
    """
    def loc_key(entry: dict) -> Hashable | None:
        loc = entry.get("record_locator")
        if not isinstance(loc, dict):
            return None
        return tuple(sorted(loc.items()))

    map_a: dict[Hashable, dict] = {}
    map_b: dict[Hashable, dict] = {}
    for e in entries_a:
        k = loc_key(e)
        if k is not None:
            map_a[k] = e
    for e in entries_b:
        k = loc_key(e)
        if k is not None:
            map_b[k] = e

    result = AlignmentResult()
    for k, ea in map_a.items():
        if k in map_b:
            result.matched.append((ea, map_b[k]))
        else:
            result.only_a.append(ea)
    for k, eb in map_b.items():
        if k not in map_a:
            result.only_b.append(eb)
    return result


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _live_records(envelope: dict) -> list[dict]:
    """Extract the records list, filtering out _error placeholders."""
    records = envelope.get("records", [])
    return [r for r in records if "_error" not in r]


def _normalize_span(span: Any) -> str:
    """Normalize a text span for alignment comparison."""
    if not isinstance(span, str):
        return ""
    return " ".join(span.lower().split())
