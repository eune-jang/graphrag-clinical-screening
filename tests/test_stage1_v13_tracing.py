"""Tests for Stage 1 v1.3 attempt-level tracing (I-07).

Phase 5A's trace kept one record per *successful* pass, so a response that
failed and was retried vanished. These tests pin the fix: every attempt is
recorded, in order, failures included, and retry counts come from the records
rather than from `calls - successful_nodes`.

No real API calls — every model response is a scripted mock.

Run with:
    python -m pytest tests/test_stage1_v13_tracing.py -v

Or as a script (no pytest needed):
    python tests/test_stage1_v13_tracing.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage1_v13.context import root_context  # noqa: E402
from pipeline.stage1_v13.contracts import MAIN_TARGET  # noqa: E402
from pipeline.stage1_v13.runner import run_pass, run_stage1_v13  # noqa: E402
from pipeline.stage1_v13.tracing import (  # noqa: E402
    DISPOSITION_API_ERROR,
    DISPOSITION_CACHE_HIT,
    DISPOSITION_CACHE_REJECTED,
    DISPOSITION_PARSE_FAILURE,
    DISPOSITION_SUCCESS,
    DISPOSITION_VALIDATION_FAILURE,
    JsonlTracer,
    MemoryTracer,
    summarize_attempts,
)
from pipeline.stage1_v13.validators import Stage1V13ValidationError  # noqa: E402

ROOT = "Histologically confirmed NSCLC with EGFR mutation, except patients with prior TKI therapy."
TEMPLATE = "ROOT={{root_criterion_text}} TARGETS={{target_segments_json_array}} PARENT={{parent_context_or_null}}"


def out(**kw) -> dict:
    base = {
        "splitting_decision": "none", "child_logic": None, "cohort_scope": None,
        "sub_criteria": [], "needs_recursion": False, "recursion_targets": [],
        "recursion_note": "", "primary_rule_id": "H0", "supporting_rule_ids": [], "notes": "",
    }
    base.update(kw)
    return base


def scripted(*responses, meta=None):
    """Mock LLM. A response may be a raw string (to force a parse failure)."""
    queue = list(responses)

    def _llm(prompt_text: str, model: str) -> str:
        if not queue:
            raise AssertionError("mock LLM에 예정된 응답보다 많은 호출")
        r = queue.pop(0)
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)

    if meta is not None:
        _llm.last_call_meta = meta  # type: ignore[attr-defined]
    return _llm


def ctx():
    return root_context(ROOT, criterion_type="inclusion", criterion_id="T01")


SPLIT = out(
    splitting_decision="composite_split", child_logic="AND",
    sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                  {"child_id": "b", "text_span": ["EGFR mutation"]}],
    primary_rule_id="H1-B",
)


# ──────────────────────────────────────────────────────────────────────
# attempt recording
# ──────────────────────────────────────────────────────────────────────

def test_first_attempt_success_records_one_attempt():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted(out()), model="m", template=TEMPLATE, tracer=t)
    assert len(t.records) == 1
    r = t.records[0]
    assert r["attempt_index"] == 0 and r["is_retry"] is False
    assert r["disposition"] == DISPOSITION_SUCCESS
    assert r["parse_status"] == "ok" and r["validation_status"] == "pass"


def test_parse_failure_then_retry_success_keeps_both():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted("not json at all", out()), model="m", template=TEMPLATE, tracer=t)
    assert len(t.records) == 2
    bad, good = t.records
    assert bad["disposition"] == DISPOSITION_PARSE_FAILURE
    assert bad["attempt_index"] == 0 and bad["is_retry"] is False
    assert good["disposition"] == DISPOSITION_SUCCESS
    assert good["attempt_index"] == 1 and good["is_retry"] is True


def test_validation_failure_then_retry_success_keeps_both():
    t = MemoryTracer()
    bad = out(primary_rule_id="NOPE")
    run_pass(ctx(), llm=scripted(bad, out()), model="m", template=TEMPLATE, tracer=t)
    assert len(t.records) == 2
    assert t.records[0]["disposition"] == DISPOSITION_VALIDATION_FAILURE
    assert t.records[1]["disposition"] == DISPOSITION_SUCCESS


def test_failed_raw_response_is_retained():
    """The rejected response itself must survive, not just the fact of failure."""
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted("<<<garbage>>>", out()), model="m", template=TEMPLATE, tracer=t)
    assert t.records[0]["raw_response"] == "<<<garbage>>>"


def test_parsed_json_absent_on_parse_failure():
    """Absence is meaningful — no placeholder is written."""
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted("nope", out()), model="m", template=TEMPLATE, tracer=t)
    assert t.records[0]["parsed_json"] is None
    assert t.records[0]["parse_status"] == "failed"
    assert t.records[0]["parse_error"]
    assert t.records[0]["validation_status"] == "not_run"


def test_validation_errors_retained_on_validation_failure():
    t = MemoryTracer()
    bad = out(splitting_decision="composite_split", child_logic=None,
              sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                            {"child_id": "b", "text_span": ["EGFR mutation"]}])
    try:
        run_pass(ctx(), llm=scripted(bad, bad, bad), model="m", template=TEMPLATE, tracer=t)
    except Stage1V13ValidationError:
        pass
    assert len(t.records) == 3  # 1 + MAX_RETRIES, every one kept
    for r in t.records:
        assert r["disposition"] == DISPOSITION_VALIDATION_FAILURE
        assert any("child_logic" in e for e in r["validation_errors"])
        assert r["parsed_json"] is not None  # parsed fine, failed validation


def test_api_error_is_recorded_then_propagates():
    """The runner does not retry API errors — but the attempt is still traced."""
    t = MemoryTracer()
    try:
        run_pass(ctx(), llm=scripted(RuntimeError("boom")), model="m", template=TEMPLATE, tracer=t)
    except RuntimeError as e:
        assert "boom" in str(e)
    else:
        raise AssertionError("API 오류가 전파되지 않았습니다")
    assert len(t.records) == 1
    assert t.records[0]["disposition"] == DISPOSITION_API_ERROR
    assert "boom" in t.records[0]["api_error"]
    assert t.records[0]["raw_response"] is None


def test_attempt_order_preserved():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted("bad", out(primary_rule_id="ZZ"), out()),
             model="m", template=TEMPLATE, tracer=t)
    assert [r["attempt_index"] for r in t.records] == [0, 1, 2]
    assert [r["disposition"] for r in t.records] == [
        DISPOSITION_PARSE_FAILURE, DISPOSITION_VALIDATION_FAILURE, DISPOSITION_SUCCESS]
    assert [r["record_index"] for r in t.records] == [1, 2, 3]


# ──────────────────────────────────────────────────────────────────────
# recursion
# ──────────────────────────────────────────────────────────────────────

def test_recursive_child_attempts_are_logged_with_path_and_depth():
    t = MemoryTracer()
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    run_stage1_v13(ctx(), llm=scripted(parent, out()), model="m", template=TEMPLATE, tracer=t)
    assert [r["hierarchy_path"] for r in t.records] == ["root", "root.a"]
    assert [r["depth"] for r in t.records] == [0, 1]
    assert t.records[1]["target_segments"] == ["Histologically confirmed NSCLC"]
    assert t.records[1]["parent_context"]["current_child_id"] == "a"


def test_two_sibling_recursive_branches_are_logged_separately():
    t = MemoryTracer()
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a", "b"], primary_rule_id="H1-B")
    run_stage1_v13(ctx(), llm=scripted(parent, out(), out()), model="m", template=TEMPLATE, tracer=t)
    paths = [r["hierarchy_path"] for r in t.records]
    assert paths == ["root", "root.a", "root.b"]
    assert len({r["pass_id"] for r in t.records}) == 3
    assert t.records[1]["target_segments"] != t.records[2]["target_segments"]


def test_nested_exception_main_pass_is_logged():
    t = MemoryTracer()
    parent = out(splitting_decision="nested_exception",
                 sub_criteria=[{"child_id": "a",
                                "text_span": ["except patients with prior TKI therapy"]}],
                 needs_recursion=True, recursion_targets=[MAIN_TARGET], primary_rule_id="H4")
    run_stage1_v13(ctx(), llm=scripted(parent, out()), model="m", template=TEMPLATE, tracer=t)
    assert [r["hierarchy_path"] for r in t.records] == ["root", f"root.{MAIN_TARGET}"]
    assert t.records[1]["target_segments"] == [
        "Histologically confirmed NSCLC with EGFR mutation,"]


def test_retry_inside_a_recursive_child_is_attributed_to_that_child():
    t = MemoryTracer()
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    run_stage1_v13(ctx(), llm=scripted(parent, "bad", out()), model="m", template=TEMPLATE, tracer=t)
    assert [(r["hierarchy_path"], r["attempt_index"]) for r in t.records] == [
        ("root", 0), ("root.a", 0), ("root.a", 1)]


# ──────────────────────────────────────────────────────────────────────
# cache
# ──────────────────────────────────────────────────────────────────────

class _FakeCache:
    def __init__(self, stored=None):
        self.stored = stored
        self.puts = 0

    def get(self, prompt_template, input_payload, model):
        return self.stored

    def put(self, prompt_template, input_payload, model, response):
        self.puts += 1


def test_cache_hit_is_recorded():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted(), model="m", template=TEMPLATE,
             cache=_FakeCache(stored=out()), tracer=t)
    assert len(t.records) == 1
    assert t.records[0]["disposition"] == DISPOSITION_CACHE_HIT
    assert t.records[0]["cache"] == "hit"


def test_cache_miss_is_recorded_on_the_live_attempt():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted(out()), model="m", template=TEMPLATE,
             cache=_FakeCache(stored=None), tracer=t)
    assert t.records[0]["cache"] == "miss"


def test_invalid_cache_entry_is_recorded_as_rejected_then_recalled():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted(out()), model="m", template=TEMPLATE,
             cache=_FakeCache(stored=out(primary_rule_id="BAD")), tracer=t)
    assert [r["disposition"] for r in t.records] == [
        DISPOSITION_CACHE_REJECTED, DISPOSITION_SUCCESS]


def test_cache_disabled_is_marked():
    t = MemoryTracer()
    run_pass(ctx(), llm=scripted(out()), model="m", template=TEMPLATE, tracer=t)
    assert t.records[0]["cache"] == "disabled"


# ──────────────────────────────────────────────────────────────────────
# record content, persistence, summaries
# ──────────────────────────────────────────────────────────────────────

def test_record_carries_every_required_context_field():
    t = MemoryTracer(run_config={"reasoning_effort": "medium", "max_completion_tokens": 8000,
                                 "prompt_artifact": "x.txt", "sdk_version": "1.6.1"})
    run_pass(ctx(), llm=scripted(out()), model="m", template=TEMPLATE, tracer=t)
    r = t.records[0]
    for f in ["run_id", "case_id", "hierarchy_path", "depth", "pass_id", "attempt_id",
              "attempt_index", "is_retry", "model", "prompt_sha256", "root_criterion_text",
              "target_segments", "parent_context", "criterion_type", "trial_has_cohorts",
              "raw_response", "parse_status", "parsed_json", "validation_status",
              "validation_errors", "latency_s", "usage", "api_error", "cache",
              "disposition", "recorded_at",
              "reasoning_effort", "max_completion_tokens", "prompt_artifact", "sdk_version"]:
        assert f in r, f
    assert r["case_id"] == "T01"


def test_llm_meta_is_captured_when_the_callable_exposes_it():
    t = MemoryTracer()
    llm = scripted(out(), meta={"usage": {"total_tokens": 42}, "provider": "openai"})
    run_pass(ctx(), llm=llm, model="m", template=TEMPLATE, tracer=t)
    assert t.records[0]["usage"] == {"total_tokens": 42}
    assert t.records[0]["llm_meta"] == {"provider": "openai"}


def test_jsonl_tracer_is_append_only():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "sub" / "attempts.jsonl"
        tr = JsonlTracer(path, run_config={"model": "m"})
        run_pass(ctx(), llm=scripted("bad", out()), model="m", template=TEMPLATE, tracer=tr)
        run_pass(ctx(), llm=scripted(out()), model="m", template=TEMPLATE, tracer=tr)
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 3 and tr.n_records == 3
        assert [r["record_index"] for r in rows] == [1, 2, 3]
        assert len({r["run_id"] for r in rows}) == 1


def test_summary_counts_retries_from_records_not_arithmetic():
    t = MemoryTracer()
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    run_stage1_v13(ctx(), llm=scripted(parent, "bad", out()), model="m", template=TEMPLATE, tracer=t)
    s = summarize_attempts(t.records)
    assert s["attempts"] == 3
    assert s["passes"] == 2
    assert s["retry_attempts"] == 1
    assert s["passes_needing_retry"] == 1
    assert s["first_attempt_parse_ok"] == 1        # root ok, root.a first attempt failed
    assert s["first_attempt_validation_pass"] == 1
    assert s["dispositions"] == {DISPOSITION_PARSE_FAILURE: 1, DISPOSITION_SUCCESS: 2}


def test_tracer_is_optional_and_changes_nothing():
    node_a = run_stage1_v13(ctx(), llm=scripted(out()), model="m", template=TEMPLATE)
    node_b = run_stage1_v13(ctx(), llm=scripted(out()), model="m", template=TEMPLATE,
                            tracer=MemoryTracer())
    assert node_a.to_dict() == node_b.to_dict()


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            failed.append((name, e))
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
