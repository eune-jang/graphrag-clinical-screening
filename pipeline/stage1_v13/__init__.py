"""Stage 1 v1.3 **development** execution path.

This package is a parallel, versioned runtime for the frozen Canonical Core
v1.3.0 (`docs/guidelines/stage1/canonical_core_v1_3_0.md`) and the
non-normative development prompt
`pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt`.

It is deliberately **separate from the legacy production path**:

    pipeline/orchestrator.py + pipeline/prompts/prompt_1_splitting.txt
        legacy production, v1.2.2-era, untouched by this package
    pipeline/stage1_v13/
        v1.3 development runtime, opt-in only

Nothing here is wired into the production prompt loader. `llm_client` resolves
production prompts through an explicit filename map, so the v1.3.1 prompt is
reachable only by calling into this package on purpose.

Layer model (see docs/guidelines/stage1/CURRENT.md):

    LAYER 2    canonical core v1.3.0            normative
    LAYER 3    stage1_prompt_v1_3_1.txt         non-normative dev prompt
    LAYER 3.5  this package                     dev execution path  ← here
    LAYER 4    legacy production runtime        still not v1.3 conformant

What this package does NOT do: freeze a final prompt, replace production,
evaluate models, or touch historical evidence.

Development CLI:

    python -m pipeline.stage1_v13 --text "..." --type inclusion --dry-run
"""
from typing import Any

from .contracts import (
    CHILD_LOGIC_VALUES,
    INCOMPLETE_EMPTY_MAIN,
    INCOMPLETE_MAX_DEPTH,
    EXECUTION_CONTEXT_FIELDS,
    MAIN_TARGET,
    PIPELINE_CONTROL_FIELDS,
    PROVENANCE_FIELDS,
    RULE_IDS,
    SPLIT_DECISIONS,
    SPLITTING_DECISIONS,
    Stage1V13Node,
    derive_tier,
    read_legacy_stage1_record,
)
from .context import Stage1Context, derive_main_segments, root_context
from .validators import Stage1V13ValidationError, validate_v13_output

# `runner` is imported lazily: eagerly importing it here would put the module in
# sys.modules before `python -m pipeline.stage1_v13.runner` executes it, which
# makes runpy warn about a double import.
_LAZY = {"run_stage1_v13": "runner", "Stage1V13Error": "runner", "run_pass": "runner"}


def __getattr__(name: str) -> Any:  # PEP 562
    if name in _LAZY:
        from importlib import import_module
        return getattr(import_module(f".{_LAZY[name]}", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CHILD_LOGIC_VALUES",
    "INCOMPLETE_EMPTY_MAIN",
    "INCOMPLETE_MAX_DEPTH",
    "EXECUTION_CONTEXT_FIELDS",
    "MAIN_TARGET",
    "PIPELINE_CONTROL_FIELDS",
    "PROVENANCE_FIELDS",
    "RULE_IDS",
    "SPLIT_DECISIONS",
    "SPLITTING_DECISIONS",
    "Stage1Context",
    "Stage1V13Error",
    "Stage1V13Node",
    "Stage1V13ValidationError",
    "derive_main_segments",
    "derive_tier",
    "read_legacy_stage1_record",
    "root_context",
    "run_pass",
    "run_stage1_v13",
    "validate_v13_output",
]
