"""Stage 1 v1.3 output contract.

Deliberately **independent of `iaa_pipeline/stage_schemas.py`**. That module is
the historical v1.2.2 storage contract that the frozen 113-item evidence was
written against; extending it would change a contract the freeze depends on.
The two are reconciled only once the v1.3 prompt is frozen — until then this
file owns the v1.3 shape and `read_legacy_stage1_record` owns the bridge.

Field classification (canonical core H6 + "Provenance defaults"). This is the
boundary that keeps pipeline mechanics out of the ontology:

    pipeline-control   needs_recursion, recursion_targets, recursion_note
    provenance         primary_rule_id, supporting_rule_ids
    execution context  ROOT_CRITERION_TEXT, TARGET_SEGMENTS,
                       PARENT_CONTEXT, NEIGHBORING_CRITERIA
    ontology           splitting_decision, child_logic, cohort_scope,
                       sub_criteria[].{child_id,text_span,cohort_scope}

None of the first three groups is an ontology property. Nothing in this file
adds one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

# The enum source of truth stays `pipeline.config`; v1.3 does not change it.
from pipeline.config import CHILD_LOGIC as CHILD_LOGIC_VALUES
from pipeline.config import SPLITTING_DECISIONS

# Decisions that carry child Criterion objects and therefore require child_logic.
SPLIT_DECISIONS: tuple[str, ...] = ("composite_split", "macro_aggregate")
# Decisions for which child_logic must be null (canonical H5).
NO_LOGIC_DECISIONS: tuple[str, ...] = ("none", "nested_exception")

# Canonical rule identifiers, exactly as the v1.3.1 prompt enumerates them for
# `primary_rule_id`. H1/H2 are only ever cited through their refined branches.
RULE_IDS: frozenset[str] = frozenset({
    "H0", "H1-A", "H1-B", "H2-A", "H2-B", "H3", "H4", "H5", "H6",
    "X1", "X2", "X3", "X4", "X5", "X6", "X7",
})

# Canonical "Provenance defaults": tier follows the primary decisive rule.
# Kept separate from ontology semantics and never inferred from free text.
TIER_BY_PRIMARY_RULE: dict[str, int] = {
    "H2-A": 0,   # ontology / semantic-category validity
    "H2-B": 1,   # clinical authority (oncology axis)
}
DEFAULT_TIER = 2  # H0/H1/H3/H4/H5/H6 and X-rules, unless higher authority cited

PIPELINE_CONTROL_FIELDS: tuple[str, ...] = (
    "needs_recursion", "recursion_targets", "recursion_note",
)
PROVENANCE_FIELDS: tuple[str, ...] = ("primary_rule_id", "supporting_rule_ids")
EXECUTION_CONTEXT_FIELDS: tuple[str, ...] = (
    "ROOT_CRITERION_TEXT", "TARGET_SEGMENTS", "PARENT_CONTEXT", "NEIGHBORING_CRITERIA",
)

# The child_id the canonical core reserves for "recurse the main content of a
# nested exception". It is not a child object; it names the derived remainder.
MAIN_TARGET = "main"


# ──────────────────────────────────────────────────────────────────────
# Output shape
# ──────────────────────────────────────────────────────────────────────

class V13SubCriterion(TypedDict, total=False):
    """One child Criterion, or — under `nested_exception` — one exception span.

    The prompt deliberately gives both the same field name and `child_id`
    convention; they are told apart by the parent's `splitting_decision`, not
    by a different key.
    """
    child_id: str                    # required: "a", "b", ...
    text_span: list[str]             # required: >=1 verbatim source segments
    cohort_scope: list[str] | None   # optional
    rationale: str                   # optional


class V13Output(TypedDict, total=False):
    """One validated Stage-1 v1.3 pass — exactly one hierarchy level."""
    splitting_decision: Literal["none", "composite_split", "macro_aggregate", "nested_exception"]
    child_logic: str | None
    cohort_scope: list[str] | None
    sub_criteria: list[V13SubCriterion]
    needs_recursion: bool
    recursion_targets: list[str]
    recursion_note: str
    primary_rule_id: str
    supporting_rule_ids: list[str]
    notes: str


class ParentContext(TypedDict):
    """`PARENT_CONTEXT` as the v1.3.1 prompt defines it.

    Interpretation aid only. `sibling_spans` text must never reach an output
    `text_span` unless that text also occurs in the current TARGET_SEGMENTS —
    enforced in `validators.validate_v13_output`.
    """
    parent_decision: str
    parent_child_logic: str | None
    current_child_id: str
    sibling_spans: dict[str, list[str]]


#: Reasons a node asked for another pass that did not happen. Runtime metadata
#: only — never an ontology property, never part of the prompt output schema,
#: and never written into a historical record.
INCOMPLETE_MAX_DEPTH = "max_depth"      # development safety guard tripped
INCOMPLETE_EMPTY_MAIN = "empty_main"    # nothing substantive left after subtraction


@dataclass
class Stage1V13Node:
    """One pass plus the passes it spawned — the hierarchy this runtime returns.

    Mixed logic (`A AND (B1 OR B2)`) stays hierarchical: each level keeps its
    own `child_logic`, and children live under `children`, never flattened up.

    `output` holds the model's response **verbatim**. Anything the runner itself
    concludes lives in `incomplete_reason`, so a reader can always tell what the
    model said apart from what the pipeline decided.
    """
    node_id: str                      # "root", "root.a", "root.a.main", ...
    depth: int
    target_segments: list[str]
    output: V13Output
    children: dict[str, "Stage1V13Node"] = field(default_factory=dict)
    parent_context: ParentContext | None = None
    #: Set when this pass returned needs_recursion=true but the runner did not
    #: recurse. None means the level finished on its own terms.
    incomplete_reason: str | None = None

    @property
    def decision(self) -> str:
        return self.output.get("splitting_decision", "none")

    @property
    def is_incomplete(self) -> bool:
        """This level asked for another pass that never ran."""
        return self.incomplete_reason is not None

    def walk(self):
        """Depth-first over this node and every descendant."""
        yield self
        for child in self.children.values():
            yield from child.walk()

    def incomplete_nodes(self) -> list["Stage1V13Node"]:
        """Every node in this subtree whose recursion was cut short.

        Empty list == the hierarchy ran to completion. This is the programmatic
        check; do not infer completion from `recursion_note`, which belongs to
        the model.
        """
        return [n for n in self.walk() if n.is_incomplete]

    @property
    def is_complete(self) -> bool:
        return not self.incomplete_nodes()

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON for the development CLI. Not an ontology serialization."""
        return {
            "node_id": self.node_id,
            "depth": self.depth,
            "target_segments": self.target_segments,
            "parent_context": self.parent_context,
            "incomplete_reason": self.incomplete_reason,
            "output": self.output,
            "children": [c.to_dict() for c in self.children.values()],
        }


def derive_tier(primary_rule_id: str | None) -> int:
    """Canonical provenance default. Deterministic, never inferred from prose.

    Tier is *not* required output for the development runtime; it is exposed so
    a caller can derive it consistently instead of hand-assigning one.
    Historical gold tiers are never recomputed from this.
    """
    return TIER_BY_PRIMARY_RULE.get(primary_rule_id or "", DEFAULT_TIER)


# ──────────────────────────────────────────────────────────────────────
# Backward compatibility with historical v1.2.2 records
# ──────────────────────────────────────────────────────────────────────
#
# The compatibility boundary lives here and nowhere else:
#
#   read   historical v1.2.2 records → tolerant (this function)
#   write  v1.3 output               → strict   (validators.py)
#
# Historical records are never rewritten to carry v1.3 fields. A v1.2.2 record
# that lacks `recursion_targets` is correct as it stands; the canonical core
# says so explicitly.

LEGACY_ONLY_DEFAULTS: dict[str, Any] = {
    "needs_recursion": False,
    "recursion_targets": [],
    "recursion_note": "",
    "primary_rule_id": None,
    "supporting_rule_ids": [],
}


def normalize_text_span(value: Any) -> list[str]:
    """`text_span` as a list, accepting both storage forms.

    v1.1/R1/R2 envelopes stored a single string; spec v1.2.3 change 6 made it an
    array. Mirrors `iaa_pipeline.adjudication.normalize_text_span` deliberately
    — this package must not import the historical adjudication module, whose
    behaviour is anchored to tag `stage1-adjudication-complete-2026-09-08`.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        out = []
        for seg in value:
            if isinstance(seg, str) and seg.strip():
                out.append(seg.strip())
        return out
    return []


def read_legacy_stage1_record(record: dict) -> V13Output:
    """Project a historical v1.2.2 Stage-1 record into the v1.3 output shape.

    Read-only: the argument is not mutated and nothing is written back. Missing
    v1.3-only fields take the defaults above, which is what "this record predates
    v1.3" means — not an error.

    `nested_exception` is left exactly as stored. Historical gold holds one
    exception span in 9 of 10 such records, which the v1.3 contract accepts and
    the legacy production validator (`pipeline/validators.py`, `>=2`) does not.
    That legacy rule is not used here.
    """
    out: V13Output = {
        "splitting_decision": record.get("splitting_decision", "none"),
        "child_logic": record.get("child_logic"),
        "cohort_scope": record.get("cohort_scope"),
        "sub_criteria": [
            {
                "child_id": sub.get("child_id", ""),
                "text_span": normalize_text_span(sub.get("text_span")),
                "cohort_scope": sub.get("cohort_scope"),
                "rationale": sub.get("rationale", ""),
            }
            for sub in (record.get("sub_criteria") or [])
            if isinstance(sub, dict)
        ],
        "notes": record.get("notes", ""),
    }
    for key, default in LEGACY_ONLY_DEFAULTS.items():
        value = record.get(key, default)
        out[key] = default if value is None and key != "primary_rule_id" else value
    return out
