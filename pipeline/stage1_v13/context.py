"""Stage 1 v1.3 execution context — the input side of canonical X1.

The v1.2.2-era production path sent one variable, `criterion_text`. v1.3 splits
that into read-only root context and the segments actually being annotated:

    ROOT_CRITERION_TEXT   full original criterion, read-only
    TARGET_SEGMENTS       exact source segments for THIS pass; the only place
                          an output text_span may come from
    PARENT_CONTEXT        recursive passes only; interpretation aid
    NEIGHBORING_CRITERIA  read-only interpretation context

Keeping the two apart is what stops a recursive pass from re-importing sibling
content, which is the whole point of X1 and X7.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .contracts import MAIN_TARGET, ParentContext


@dataclass
class Stage1Context:
    """Everything one v1.3 pass needs, and nothing it must not see."""

    root_criterion_text: str
    target_segments: list[str]
    criterion_type: str | None = None
    trial_has_cohorts: list[Any] | None = None
    parent_context: ParentContext | None = None
    neighboring_criteria: str | None = None
    criterion_id: str | None = None
    node_id: str = "root"
    depth: int = 0
    _warnings: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not (self.root_criterion_text or "").strip():
            raise ValueError("root_criterion_text는 비어 있을 수 없습니다")
        segs = [s for s in (self.target_segments or []) if isinstance(s, str) and s.strip()]
        if not segs:
            raise ValueError("target_segments에 최소 한 개의 비어 있지 않은 세그먼트가 필요합니다")
        self.target_segments = segs
        # A target segment that is not verbatim inside the root means the caller
        # already synthesized text — every downstream span check would inherit
        # that corruption, so fail at the boundary instead.
        for seg in self.target_segments:
            if seg not in self.root_criterion_text:
                raise ValueError(
                    f"target_segment가 ROOT_CRITERION_TEXT의 축자 부분문자열이 아닙니다: {seg!r}"
                )

    # ── prompt variables ───────────────────────────────────────────────
    def to_prompt_variables(self) -> dict[str, Any]:
        """Map onto the six placeholders in stage1_prompt_v1_3_1.txt.

        Every placeholder is supplied. The legacy production path passes only
        two of prompt_1's three, leaving `{{neighboring_criteria}}` literal in
        the request — a deferred legacy defect this runtime does not repeat.
        """
        return {
            "root_criterion_text": self.root_criterion_text,
            "target_segments_json_array": json.dumps(self.target_segments, ensure_ascii=False),
            "criterion_type": self.criterion_type or "null",
            "cohort_list_or_null": self.trial_has_cohorts,
            "parent_context_or_null": self.parent_context,
            "neighboring_criteria_or_null": self.neighboring_criteria,
        }

    def cache_payload(self) -> dict[str, Any]:
        """Cache identity for one pass.

        `LLMCache` hashes prompt template content + this payload + model. The
        payload must therefore distinguish every input that can change the
        answer — at a recursive pass two different children share the same root
        text and differ only in TARGET_SEGMENTS and PARENT_CONTEXT, so both are
        included. Node id and depth are excluded on purpose: identical inputs
        reached by different paths are the same call.
        """
        return {
            "root_criterion_text": self.root_criterion_text,
            "target_segments": self.target_segments,
            "criterion_type": self.criterion_type,
            "trial_has_cohorts": self.trial_has_cohorts,
            "parent_context": self.parent_context,
            "neighboring_criteria": self.neighboring_criteria,
        }


def root_context(
    root_criterion_text: str,
    *,
    criterion_type: str | None = None,
    trial_has_cohorts: list[Any] | None = None,
    neighboring_criteria: str | None = None,
    criterion_id: str | None = None,
    target_segments: list[str] | None = None,
) -> Stage1Context:
    """Root pass: TARGET_SEGMENTS = [ROOT_CRITERION_TEXT], PARENT_CONTEXT = null.

    A caller may pass explicit `target_segments` to resume mid-hierarchy; they
    are still checked against the root text.
    """
    return Stage1Context(
        root_criterion_text=root_criterion_text,
        target_segments=list(target_segments) if target_segments else [root_criterion_text],
        criterion_type=criterion_type,
        trial_has_cohorts=trial_has_cohorts,
        parent_context=None,
        neighboring_criteria=neighboring_criteria,
        criterion_id=criterion_id,
        node_id="root",
        depth=0,
    )


def build_parent_context(parent_output: dict, current_child_id: str) -> ParentContext:
    """`PARENT_CONTEXT` for a recursive pass.

    `sibling_spans` carries every *other* child's spans so the model can recover
    a shared subject or qualifier. It must never be copied into output; the
    validator enforces that by accepting spans only from TARGET_SEGMENTS.
    """
    siblings: dict[str, list[str]] = {}
    for sub in parent_output.get("sub_criteria") or []:
        cid = sub.get("child_id")
        if cid and cid != current_child_id:
            siblings[cid] = list(sub.get("text_span") or [])
    return {
        "parent_decision": parent_output.get("splitting_decision", ""),
        "parent_child_logic": parent_output.get("child_logic"),
        "current_child_id": current_child_id,
        "sibling_spans": siblings,
    }


def child_context(parent_ctx: Stage1Context, parent_output: dict, child_id: str) -> Stage1Context:
    """Next pass for one child of a `composite_split` / `macro_aggregate`.

    TARGET_SEGMENTS become exactly that child's spans — nothing is added, so the
    child cannot reach sibling or root-only text.
    """
    spans: list[str] = []
    for sub in parent_output.get("sub_criteria") or []:
        if sub.get("child_id") == child_id:
            spans = list(sub.get("text_span") or [])
            break
    if not spans:
        raise ValueError(f"child_id={child_id!r}의 text_span을 부모 출력에서 찾지 못했습니다")

    return Stage1Context(
        root_criterion_text=parent_ctx.root_criterion_text,
        target_segments=spans,
        criterion_type=parent_ctx.criterion_type,
        trial_has_cohorts=parent_ctx.trial_has_cohorts,
        parent_context=build_parent_context(parent_output, child_id),
        neighboring_criteria=parent_ctx.neighboring_criteria,
        criterion_id=parent_ctx.criterion_id,
        node_id=f"{parent_ctx.node_id}.{child_id}",
        depth=parent_ctx.depth + 1,
    )


# ──────────────────────────────────────────────────────────────────────
# nested_exception main-span derivation — safety critical
# ──────────────────────────────────────────────────────────────────────

def _has_content(fragment: str) -> bool:
    """A fragment worth annotating carries at least one alphanumeric character.

    Removing an exception can leave `"."` or `", "` behind. Those are verbatim
    substrings but not eligibility content, and feeding them back would spend a
    pass on punctuation.
    """
    return any(ch.isalnum() for ch in fragment)


def derive_main_segments(target_segments: list[str], exception_spans: list[str]) -> list[str]:
    """MAIN content = current TARGET_SEGMENTS minus the selected exception spans.

    The prompt does not emit a main span, so the pipeline derives it. This is
    the one place where a bug would silently corrupt provenance, so the rules
    are strict:

    - subtraction only; never paraphrase, normalize, or re-word;
    - never merge fragments that the removal separated — they stay separate
      segments, which is why a recursive pass may receive several;
    - each exception span consumes **one** occurrence, taken left to right and
      skipping any region already claimed. A span the model listed once does
      not remove a second, unrelated occurrence of the same wording;
    - fragments are whitespace-trimmed (still verbatim substrings) and dropped
      when they carry no alphanumeric content.

    Returns [] when nothing substantive remains — the caller must then stop
    rather than recurse into emptiness.
    """
    out: list[str] = []
    for segment in target_segments:
        claimed: list[tuple[int, int]] = []
        for span in exception_spans:
            if not span:
                continue
            start = 0
            while True:
                idx = segment.find(span, start)
                if idx < 0:
                    break  # this span does not occur (again) in this segment
                end = idx + len(span)
                if any(not (end <= cs or idx >= ce) for cs, ce in claimed):
                    start = idx + 1  # overlaps an earlier removal; look further
                    continue
                claimed.append((idx, end))
                break

        claimed.sort()
        cursor = 0
        pieces: list[str] = []
        for cs, ce in claimed:
            pieces.append(segment[cursor:cs])
            cursor = ce
        pieces.append(segment[cursor:])

        for piece in pieces:
            trimmed = piece.strip()
            if trimmed and _has_content(trimmed):
                out.append(trimmed)
    return out


def main_context(parent_ctx: Stage1Context, parent_output: dict) -> Stage1Context | None:
    """Next pass for the MAIN content of a `nested_exception`.

    Returns None when subtraction leaves nothing substantive, which is a normal
    stop condition rather than an error. Exception spans themselves never
    become a context — they are not child Criterion nodes and never recurse.
    """
    exception_spans: list[str] = []
    for sub in parent_output.get("sub_criteria") or []:
        exception_spans.extend(sub.get("text_span") or [])

    main_segments = derive_main_segments(parent_ctx.target_segments, exception_spans)
    if not main_segments:
        return None

    return Stage1Context(
        root_criterion_text=parent_ctx.root_criterion_text,
        target_segments=main_segments,
        criterion_type=parent_ctx.criterion_type,
        trial_has_cohorts=parent_ctx.trial_has_cohorts,
        parent_context=build_parent_context(parent_output, MAIN_TARGET),
        neighboring_criteria=parent_ctx.neighboring_criteria,
        criterion_id=parent_ctx.criterion_id,
        node_id=f"{parent_ctx.node_id}.{MAIN_TARGET}",
        depth=parent_ctx.depth + 1,
    )


def format_neighboring_criteria(
    current_criterion: dict,
    all_criteria: list[dict],
    window: int = 2,
) -> str:
    """Read-only NEIGHBORING_CRITERIA block, current criterion marked.

    Interpretation context only. Canonical X7 forbids using it to create spans,
    suppress a local requirement, or deduplicate across criteria; the span
    validator makes the first of those impossible by construction.
    """
    try:
        idx = next(
            i for i, c in enumerate(all_criteria)
            if c.get("criterion_id") == current_criterion.get("criterion_id")
        )
    except StopIteration:
        return ""
    lo, hi = max(0, idx - window), min(len(all_criteria), idx + window + 1)
    lines = []
    for i in range(lo, hi):
        c = all_criteria[i]
        marker = ">>> CURRENT >>>" if i == idx else "                "
        lines.append(f"{marker} {c.get('criterion_id')}: {c.get('text')}")
    return "\n".join(lines)
