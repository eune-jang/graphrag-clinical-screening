"""Attempt-level tracing for the Stage 1 v1.3 development runtime.

Phase 5A logged one record per *successful* pass, which meant a response that
failed parsing or validation and was then retried left no trace at all. That
run happened to have zero retries so nothing was lost, but the shape of the log
made retry evidence unrecoverable by construction. This module fixes that.

The model is three levels deep, and the distinction matters:

    ROOT CASE                       one criterion
      └─ PASS  (hierarchy node)     one level of the hierarchy
           └─ ATTEMPT               one call to the model

A pass may take several attempts. **Every attempt is written, including the
ones that failed**, in order, append-only. Retry counts are recorded, never
derived from `api_calls - successful_nodes`.

Everything here is experiment/runtime metadata. It adds no ontology property,
changes no prompt schema, and never touches a historical record.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

#: `disposition` values — what became of one attempt.
DISPOSITION_SUCCESS = "success"
DISPOSITION_PARSE_FAILURE = "parse_failure"
DISPOSITION_VALIDATION_FAILURE = "validation_failure"
DISPOSITION_API_ERROR = "api_error"
DISPOSITION_CACHE_HIT = "cache_hit"
DISPOSITION_CACHE_REJECTED = "cache_rejected"


class AttemptTracer(Protocol):
    """Anything that can persist one attempt record."""

    def record(self, attempt: dict[str, Any]) -> None: ...


@dataclass
class JsonlTracer:
    """Append-only JSONL tracer.

    `run_config` is merged into every record, which is where the fields the
    runtime cannot know belong — model family settings, the prompt artifact
    path, SDK and interpreter versions. Keep secrets out of it; nothing in this
    module filters them for you.
    """

    path: Path
    run_config: dict[str, Any] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    _n: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, attempt: dict[str, Any]) -> None:
        self._n += 1
        row = {"run_id": self.run_id, "record_index": self._n, **self.run_config, **attempt}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    @property
    def n_records(self) -> int:
        return self._n


@dataclass
class MemoryTracer:
    """In-memory tracer for tests and dry inspection."""

    run_config: dict[str, Any] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    records: list[dict[str, Any]] = field(default_factory=list)

    def record(self, attempt: dict[str, Any]) -> None:
        self.records.append(
            {"run_id": self.run_id, "record_index": len(self.records) + 1,
             **self.run_config, **attempt}
        )

    def for_pass(self, hierarchy_path: str) -> list[dict[str, Any]]:
        return [r for r in self.records if r.get("hierarchy_path") == hierarchy_path]


def prompt_sha256(template: str) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


def build_attempt(
    *,
    ctx,
    template: str,
    model: str,
    attempt_index: int,
    disposition: str,
    raw_response: str | None = None,
    parsed_json: Any = None,
    parse_error: str | None = None,
    validation_errors: list[str] | None = None,
    api_error: str | None = None,
    latency_s: float | None = None,
    llm_meta: dict[str, Any] | None = None,
    cache: str = "disabled",
) -> dict[str, Any]:
    """One attempt record.

    `parsed_json` is present only when parsing succeeded; `validation_errors`
    only when validation ran. Absence is meaningful, so neither is filled with
    a placeholder.
    """
    return {
        "case_id": getattr(ctx, "criterion_id", None),
        "hierarchy_path": ctx.node_id,
        "depth": ctx.depth,
        "pass_id": f"{ctx.node_id}",
        "attempt_id": f"{ctx.node_id}#{attempt_index}",
        "attempt_index": attempt_index,
        "is_retry": attempt_index > 0,
        "model": model,
        "prompt_sha256": prompt_sha256(template),
        "root_criterion_text": ctx.root_criterion_text,
        "target_segments": list(ctx.target_segments),
        "parent_context": ctx.parent_context,
        "criterion_type": ctx.criterion_type,
        "trial_has_cohorts": ctx.trial_has_cohorts,
        "raw_response": raw_response,
        "parse_status": (
            "ok" if parsed_json is not None
            else ("failed" if parse_error else "not_attempted")
        ),
        "parse_error": parse_error,
        "parsed_json": parsed_json,
        "validation_status": (
            "not_run" if validation_errors is None
            else ("pass" if not validation_errors else "fail")
        ),
        "validation_errors": validation_errors,
        "latency_s": latency_s,
        "usage": (llm_meta or {}).get("usage"),
        "llm_meta": {k: v for k, v in (llm_meta or {}).items() if k != "usage"} or None,
        "api_error": api_error,
        "cache": cache,
        "disposition": disposition,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def summarize_attempts(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Retry/format/validation counts taken from the records themselves.

    Deliberately does not infer anything from call totals: a retry is a record
    with `is_retry` true, not an arithmetic leftover.
    """
    passes = {r["hierarchy_path"] for r in records}
    return {
        "attempts": len(records),
        "passes": len(passes),
        "retry_attempts": sum(1 for r in records if r.get("is_retry")),
        "passes_needing_retry": len(
            {r["hierarchy_path"] for r in records if r.get("is_retry")}
        ),
        "first_attempt_parse_ok": sum(
            1 for r in records if r.get("attempt_index") == 0 and r.get("parse_status") == "ok"
        ),
        "first_attempt_validation_pass": sum(
            1 for r in records
            if r.get("attempt_index") == 0 and r.get("validation_status") == "pass"
        ),
        "dispositions": {
            d: sum(1 for r in records if r.get("disposition") == d)
            for d in sorted({r.get("disposition") for r in records if r.get("disposition")})
        },
        "cache": {
            c: sum(1 for r in records if r.get("cache") == c)
            for c in sorted({r.get("cache") for r in records if r.get("cache")})
        },
    }
