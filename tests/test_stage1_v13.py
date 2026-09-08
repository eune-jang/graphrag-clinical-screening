"""Tests for the Stage 1 v1.3 development runtime (`pipeline/stage1_v13/`).

These test **runtime mechanics** — contract, validation, recursion, main-span
derivation — not model quality. Every LLM call is a scripted mock, so the suite
costs nothing and is deterministic. Model behaviour is a separate concern and
belongs to a later phase.

Historical expectations are never relaxed to make something pass: the legacy
`nested_exception >= 2 sub_criteria` rule is asserted to be *absent* here,
because canonical H4 allows one exception span and the frozen 113-item gold
holds exactly that in 9 of its 10 nested_exception records.

Run with:
    python -m pytest tests/test_stage1_v13.py -v

Or as a script (no pytest needed):
    python tests/test_stage1_v13.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage1_v13.contracts import (  # noqa: E402
    MAIN_TARGET,
    RULE_IDS,
    derive_tier,
    normalize_text_span,
    read_legacy_stage1_record,
)
from pipeline.stage1_v13.context import (  # noqa: E402
    Stage1Context,
    build_parent_context,
    child_context,
    derive_main_segments,
    format_neighboring_criteria,
    main_context,
    root_context,
)
from pipeline.stage1_v13.runner import (  # noqa: E402
    DEV_PROMPT_PATH,
    Stage1V13Error,
    load_dev_prompt,
    render_prompt,
    run_pass,
    run_stage1_v13,
    summarize,
)
from pipeline.stage1_v13.validators import (  # noqa: E402
    Stage1V13ValidationError,
    assert_valid_v13_output,
    validate_v13_output,
)

ROOT = "Histologically confirmed NSCLC with EGFR mutation, except patients with prior TKI therapy."


# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────

def ctx_for(root: str = ROOT, targets=None, **kw) -> Stage1Context:
    return Stage1Context(root_criterion_text=root, target_segments=targets or [root], **kw)


def out(**kw) -> dict:
    """A valid `none` output, overridable per test."""
    base = {
        "splitting_decision": "none",
        "child_logic": None,
        "cohort_scope": None,
        "sub_criteria": [],
        "needs_recursion": False,
        "recursion_targets": [],
        "recursion_note": "",
        "primary_rule_id": "H0",
        "supporting_rule_ids": [],
        "notes": "",
    }
    base.update(kw)
    return base


def scripted_llm(*responses):
    """Mock LLM returning the given payloads in order, one per pass."""
    queue = list(responses)
    calls: list[str] = []

    def _llm(prompt_text: str, model: str) -> str:
        calls.append(prompt_text)
        if not queue:
            raise AssertionError("mock LLM에 예정된 응답보다 많은 호출이 들어왔습니다")
        return json.dumps(queue.pop(0), ensure_ascii=False)

    _llm.calls = calls  # type: ignore[attr-defined]
    return _llm


# ──────────────────────────────────────────────────────────────────────
# CONTRACT — the four decisions
# ──────────────────────────────────────────────────────────────────────

def test_contract_none_valid():
    assert validate_v13_output(out(), ctx_for()) == []


def test_contract_composite_split_valid():
    o = out(
        splitting_decision="composite_split", child_logic="AND",
        sub_criteria=[
            {"child_id": "a", "text_span": ["Histologically confirmed NSCLC"], "cohort_scope": None},
            {"child_id": "b", "text_span": ["EGFR mutation"], "cohort_scope": None},
        ],
        primary_rule_id="H1-B",
    )
    assert validate_v13_output(o, ctx_for()) == []


def test_contract_macro_aggregate_valid():
    o = out(
        splitting_decision="macro_aggregate", child_logic="AND",
        sub_criteria=[
            {"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
            {"child_id": "b", "text_span": ["EGFR mutation"]},
        ],
        primary_rule_id="H3",
    )
    assert validate_v13_output(o, ctx_for()) == []


def test_contract_nested_exception_single_span_valid():
    """canonical H4: one exception span is enough. The legacy >=2 rule is gone."""
    o = out(
        splitting_decision="nested_exception",
        sub_criteria=[{"child_id": "a", "text_span": ["except patients with prior TKI therapy"]}],
        primary_rule_id="H4",
    )
    assert validate_v13_output(o, ctx_for()) == []


def test_contract_rejects_unknown_decision():
    errs = validate_v13_output(out(splitting_decision="split"), ctx_for())
    assert any("splitting_decision" in e for e in errs)


def test_contract_composite_requires_two_children():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["EGFR mutation"]}])
    assert any("2개 이상" in e for e in validate_v13_output(o, ctx_for()))


def test_contract_duplicate_child_id_rejected():
    o = out(splitting_decision="composite_split", child_logic="OR",
            sub_criteria=[{"child_id": "a", "text_span": ["EGFR mutation"]},
                          {"child_id": "a", "text_span": ["NSCLC"]}])
    assert any("중복" in e for e in validate_v13_output(o, ctx_for()))


# ──────────────────────────────────────────────────────────────────────
# H5 — child logic
# ──────────────────────────────────────────────────────────────────────

def test_h5_explicit_and():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert validate_v13_output(o, ctx_for()) == []


def test_h5_explicit_or():
    o = out(splitting_decision="composite_split", child_logic="OR",
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert validate_v13_output(o, ctx_for()) == []


def test_h5_child_logic_mandatory_for_split():
    o = out(splitting_decision="composite_split", child_logic=None,
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert any("child_logic이 필수" in e for e in validate_v13_output(o, ctx_for()))


def test_h5_child_logic_mandatory_for_macro_too():
    """v1.2.2 let macro_aggregate omit child_logic; v1.3 does not."""
    o = out(splitting_decision="macro_aggregate", child_logic=None,
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert any("child_logic이 필수" in e for e in validate_v13_output(o, ctx_for()))


def test_h5_no_child_logic_for_none():
    assert any("none에는 child_logic" in e
               for e in validate_v13_output(out(child_logic="AND"), ctx_for()))


def test_h5_no_child_logic_for_nested_exception():
    o = out(splitting_decision="nested_exception", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["except patients with prior TKI therapy"]}])
    assert any("nested_exception에는 child_logic" in e for e in validate_v13_output(o, ctx_for()))


def test_h5_invalid_child_logic_value():
    o = out(splitting_decision="composite_split", child_logic="XOR",
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert any("child_logic" in e for e in validate_v13_output(o, ctx_for()))


# ──────────────────────────────────────────────────────────────────────
# X1 — text-span fidelity
# ──────────────────────────────────────────────────────────────────────

def test_x1_single_segment_ok():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert validate_v13_output(o, ctx_for()) == []


def test_x1_multiple_segments_ok():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed", "NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert validate_v13_output(o, ctx_for()) == []


def test_x1_segments_from_different_target_segments_ok():
    c = ctx_for(targets=["Histologically confirmed NSCLC", "EGFR mutation"])
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC", "EGFR mutation"]},
                          {"child_id": "b", "text_span": ["NSCLC"]}])
    assert validate_v13_output(o, c) == []


def test_x1_synthesized_span_rejected():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["non-small cell lung cancer"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    errs = validate_v13_output(o, ctx_for())
    assert any("합성/정규화된 span" in e for e in errs)


def test_x1_span_in_root_but_outside_target_segments_rejected():
    c = ctx_for(targets=["Histologically confirmed NSCLC"])
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])  # root only
    errs = validate_v13_output(o, c)
    assert any("TARGET_SEGMENTS 밖" in e for e in errs)


def test_x1_sibling_only_span_rejected():
    parent = {
        "splitting_decision": "composite_split", "child_logic": "AND",
        "sub_criteria": [
            {"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
            {"child_id": "b", "text_span": ["EGFR mutation"]},
        ],
    }
    c = Stage1Context(
        root_criterion_text=ROOT,
        target_segments=["Histologically confirmed NSCLC"],
        parent_context=build_parent_context(parent, "a"),
    )
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])  # sibling's span
    errs = validate_v13_output(o, c)
    assert any("sibling_spans" in e for e in errs), errs


def test_x1_sibling_text_allowed_when_also_in_target_segments():
    """§7: sibling text is only forbidden when it is *not* in TARGET_SEGMENTS."""
    parent = {
        "splitting_decision": "composite_split", "child_logic": "AND",
        "sub_criteria": [{"child_id": "a", "text_span": ["NSCLC"]},
                         {"child_id": "b", "text_span": ["EGFR mutation"]}],
    }
    c = Stage1Context(
        root_criterion_text=ROOT,
        target_segments=["Histologically confirmed NSCLC with EGFR mutation"],
        parent_context=build_parent_context(parent, "a"),
    )
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert validate_v13_output(o, c) == []


def test_x1_empty_and_non_string_segments_rejected():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["  "]},
                          {"child_id": "b", "text_span": [123]}])
    errs = validate_v13_output(o, ctx_for())
    assert any("빈 세그먼트" in e for e in errs)
    assert any("문자열이 아닙니다" in e for e in errs)


def test_x1_text_span_must_be_array():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": "NSCLC"},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert any("배열이어야" in e for e in validate_v13_output(o, ctx_for()))


def test_x1_context_rejects_target_segment_not_in_root():
    try:
        Stage1Context(root_criterion_text=ROOT, target_segments=["not in the root at all"])
    except ValueError as e:
        assert "축자 부분문자열" in str(e)
    else:
        raise AssertionError("합성된 target_segment가 통과했습니다")


# ──────────────────────────────────────────────────────────────────────
# X3 — exception spans and MAIN derivation
# ──────────────────────────────────────────────────────────────────────

def test_x3_main_derivation_exception_at_end():
    segs = derive_main_segments([ROOT], ["except patients with prior TKI therapy"])
    assert segs == ["Histologically confirmed NSCLC with EGFR mutation,"]


def test_x3_main_derivation_exception_in_middle():
    text = "Patients with, except for those on dialysis, adequate renal function."
    segs = derive_main_segments([text], ["except for those on dialysis"])
    assert segs == ["Patients with,", ", adequate renal function."]


def test_x3_main_derivation_multiple_exception_spans():
    text = "No other malignancy, other than basal cell carcinoma, or unless treated curatively."
    segs = derive_main_segments([text], ["other than basal cell carcinoma", "unless treated curatively"])
    assert segs == ["No other malignancy,", ", or"]  # 마지막 "." 은 내용 없는 조각이라 제거


def test_x3_main_derivation_preserves_punctuation_inside_main():
    text = "Adequate function (ANC, platelets), except transfusion-dependent patients."
    segs = derive_main_segments([text], ["except transfusion-dependent patients"])
    assert segs == ["Adequate function (ANC, platelets),"]


def test_x3_main_derivation_drops_punctuation_only_fragments():
    text = "Stage III NSCLC, unless resectable."
    segs = derive_main_segments([text], ["unless resectable"])
    assert segs == ["Stage III NSCLC,"]  # trailing "." dropped: no alphanumeric content


def test_x3_main_derivation_yields_multiple_segments():
    text = "A and B, except when C applies, and D."
    segs = derive_main_segments([text], ["except when C applies"])
    assert len(segs) == 2 and all(s in text for s in segs)


def test_x3_main_derivation_never_synthesizes():
    """Every derived fragment must still be a verbatim substring of the source."""
    text = "Recovered from surgery, other than minor procedures, within 4 weeks."
    segs = derive_main_segments([text], ["other than minor procedures"])
    for s in segs:
        assert s in text, s


def test_x3_main_derivation_repeated_wording_consumes_one_occurrence():
    text = "No X except Y and no Z except Y."
    segs = derive_main_segments([text], ["except Y"])
    joined = " ".join(segs)
    assert "except Y" in joined  # the second occurrence survives


def test_x3_main_derivation_empty_when_all_consumed():
    assert derive_main_segments(["except Y"], ["except Y"]) == []


def test_x3_main_context_none_when_nothing_remains():
    c = ctx_for(root="except Y", targets=["except Y"])
    parent = out(splitting_decision="nested_exception",
                 sub_criteria=[{"child_id": "a", "text_span": ["except Y"]}],
                 needs_recursion=True, recursion_targets=[MAIN_TARGET], primary_rule_id="H4")
    assert main_context(c, parent) is None


def test_x3_exception_spans_never_become_recursion_targets():
    o = out(splitting_decision="nested_exception",
            sub_criteria=[{"child_id": "a", "text_span": ["except patients with prior TKI therapy"]}],
            needs_recursion=True, recursion_targets=["a"], primary_rule_id="H4")
    assert any("main" in e for e in validate_v13_output(o, ctx_for()))


# ──────────────────────────────────────────────────────────────────────
# X4 — cohort scope
# ──────────────────────────────────────────────────────────────────────

def test_x4_top_level_scope_allowed_for_none():
    c = ctx_for(trial_has_cohorts=["Cohort A", "Cohort B"])
    assert validate_v13_output(out(cohort_scope=["Cohort A"]), c) == []


def test_x4_top_level_scope_allowed_for_nested_exception():
    c = ctx_for(trial_has_cohorts=["Cohort A"])
    o = out(splitting_decision="nested_exception", cohort_scope=["Cohort A"],
            sub_criteria=[{"child_id": "a", "text_span": ["except patients with prior TKI therapy"]}],
            primary_rule_id="H4")
    assert validate_v13_output(o, c) == []


def test_x4_top_level_scope_forbidden_for_split():
    c = ctx_for(trial_has_cohorts=["Cohort A"])
    o = out(splitting_decision="composite_split", child_logic="AND", cohort_scope=["Cohort A"],
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}])
    assert any("top-level cohort_scope는 null" in e for e in validate_v13_output(o, c))


def test_x4_child_level_scope_ok():
    c = ctx_for(trial_has_cohorts=["Cohort A", "Cohort B"])
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"], "cohort_scope": ["Cohort A"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"], "cohort_scope": None}])
    assert validate_v13_output(o, c) == []


def test_x4_unknown_cohort_label_rejected():
    c = ctx_for(trial_has_cohorts=["Cohort A"])
    assert any("TRIAL_HAS_COHORTS에 없는" in e
               for e in validate_v13_output(out(cohort_scope=["Cohort Z"]), c))


def test_x4_scope_must_be_list():
    assert any("배열 또는 null" in e
               for e in validate_v13_output(out(cohort_scope="Cohort A"), ctx_for()))


# ──────────────────────────────────────────────────────────────────────
# H6 — recursion
# ──────────────────────────────────────────────────────────────────────

TEMPLATE = "ROOT={{root_criterion_text}} TARGETS={{target_segments_json_array}} PARENT={{parent_context_or_null}}"


def run_mock(root: str, *responses, **kw):
    return run_stage1_v13(
        root_context(root, **kw), llm=scripted_llm(*responses),
        model="mock-model", template=TEMPLATE,
    )


def test_h6_no_recursion():
    node = run_mock(ROOT, out())
    assert node.children == {} and node.depth == 0


def test_h6_single_child_recursion():
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    node = run_mock(ROOT, parent, out(primary_rule_id="H2-B"))
    assert list(node.children) == ["a"]
    assert node.children["a"].node_id == "root.a"
    assert node.children["a"].target_segments == ["Histologically confirmed NSCLC"]


def test_h6_several_recursion_targets():
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a", "b"], primary_rule_id="H1-B")
    node = run_mock(ROOT, parent, out(), out())
    assert sorted(node.children) == ["a", "b"]


def test_h6_nested_exception_main_recursion():
    parent = out(splitting_decision="nested_exception",
                 sub_criteria=[{"child_id": "a", "text_span": ["except patients with prior TKI therapy"]}],
                 needs_recursion=True, recursion_targets=[MAIN_TARGET], primary_rule_id="H4")
    node = run_mock(ROOT, parent, out())
    assert list(node.children) == [MAIN_TARGET]
    assert node.children[MAIN_TARGET].target_segments == [
        "Histologically confirmed NSCLC with EGFR mutation,"
    ]


def test_h6_multi_level_mixed_logic_not_flattened():
    """A AND (B1 OR B2) keeps its own child_logic at each level."""
    root_text = "Histologically confirmed NSCLC with EGFR mutation, except patients with prior TKI therapy."
    lvl0 = out(splitting_decision="composite_split", child_logic="AND",
               sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                             {"child_id": "b", "text_span": ["EGFR mutation, except patients with prior TKI therapy"]}],
               needs_recursion=True, recursion_targets=["b"], primary_rule_id="H1-B")
    lvl1 = out(splitting_decision="composite_split", child_logic="OR",
               sub_criteria=[{"child_id": "a", "text_span": ["EGFR mutation"]},
                             {"child_id": "b", "text_span": ["prior TKI therapy"]}],
               primary_rule_id="H1-A")
    node = run_stage1_v13(root_context(root_text), llm=scripted_llm(lvl0, lvl1),
                          model="m", template=TEMPLATE)
    assert node.output["child_logic"] == "AND"
    assert node.children["b"].output["child_logic"] == "OR"
    assert list(node.children) == ["b"]          # 자식 a는 재귀 대상이 아니다
    assert len(list(node.walk())) == 2


def test_h6_max_depth_guard_stops_recursion():
    text = "alpha beta gamma delta"
    lvl0 = out(splitting_decision="composite_split", child_logic="AND",
               sub_criteria=[{"child_id": "a", "text_span": ["alpha beta gamma"]},
                             {"child_id": "b", "text_span": ["delta"]}],
               needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    lvl1 = out(splitting_decision="composite_split", child_logic="AND",
               sub_criteria=[{"child_id": "a", "text_span": ["alpha beta"]},
                             {"child_id": "b", "text_span": ["gamma"]}],
               needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    node = run_stage1_v13(root_context(text), llm=scripted_llm(lvl0, lvl1),
                          model="m", template=TEMPLATE, max_depth=1)
    # depth 1에서 재귀를 더 요구하지만 max_depth가 막고, 그 사실을 노트에 남긴다
    assert node.children["a"].children == {}
    assert "max_depth" in node.children["a"].output["recursion_note"]


def test_h6_recursion_targets_must_be_known_child_ids():
    o = out(splitting_decision="composite_split", child_logic="AND",
            sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                          {"child_id": "b", "text_span": ["EGFR mutation"]}],
            needs_recursion=True, recursion_targets=["c"], primary_rule_id="H1-B")
    assert any("존재하지 않는 child_id" in e for e in validate_v13_output(o, ctx_for()))


def test_h6_needs_recursion_consistency():
    o1 = out(needs_recursion=True, recursion_targets=[])
    assert any("recursion_targets가 비어" in e for e in validate_v13_output(o1, ctx_for()))
    o2 = out(splitting_decision="composite_split", child_logic="AND",
             sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                           {"child_id": "b", "text_span": ["EGFR mutation"]}],
             needs_recursion=False, recursion_targets=["a"], primary_rule_id="H1-B")
    assert any("needs_recursion=false인데" in e for e in validate_v13_output(o2, ctx_for()))


def test_h6_child_context_isolates_target_segments():
    parent = {"splitting_decision": "composite_split", "child_logic": "AND",
              "sub_criteria": [{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}]}
    child = child_context(ctx_for(), parent, "a")
    assert child.target_segments == ["Histologically confirmed NSCLC"]
    assert child.parent_context["current_child_id"] == "a"
    assert "b" in child.parent_context["sibling_spans"]
    assert "a" not in child.parent_context["sibling_spans"]


# ──────────────────────────────────────────────────────────────────────
# PROVENANCE
# ──────────────────────────────────────────────────────────────────────

def test_provenance_valid_primary_rule_id():
    assert validate_v13_output(out(primary_rule_id="X7"), ctx_for()) == []


def test_provenance_invalid_rule_id_rejected():
    assert any("canonical 규칙 ID가 아닙니다" in e
               for e in validate_v13_output(out(primary_rule_id="H9"), ctx_for()))


def test_provenance_missing_primary_rule_id_rejected():
    assert any("primary_rule_id는 필수" in e
               for e in validate_v13_output(out(primary_rule_id=""), ctx_for()))


def test_provenance_supporting_rules_validated():
    assert any("유효하지 않은 규칙 ID" in e
               for e in validate_v13_output(out(supporting_rule_ids=["X9"]), ctx_for()))


def test_provenance_primary_not_repeated_in_supporting():
    o = out(primary_rule_id="H0", supporting_rule_ids=["H0", "X2"])
    assert any("정확히 하나" in e for e in validate_v13_output(o, ctx_for()))


def test_provenance_supporting_must_be_list():
    assert any("배열이어야" in e
               for e in validate_v13_output(out(supporting_rule_ids="X2"), ctx_for()))


def test_provenance_tier_derivation_is_deterministic():
    assert derive_tier("H2-A") == 0
    assert derive_tier("H2-B") == 1
    assert derive_tier("H0") == 2 and derive_tier("X7") == 2
    assert derive_tier(None) == 2


def test_provenance_all_prompt_rule_ids_recognized():
    for rid in ["H0", "H1-A", "H1-B", "H2-A", "H2-B", "H3", "H4", "H5", "H6",
                "X1", "X2", "X3", "X4", "X5", "X6", "X7"]:
        assert rid in RULE_IDS


# ──────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY with historical v1.2.2 records
# ──────────────────────────────────────────────────────────────────────

def test_legacy_record_readable_without_v13_fields():
    legacy = {
        "criterion_id": "NCT01_I1",
        "splitting_decision": "composite_split",
        "child_logic": "AND",
        "sub_criteria": [{"child_id": "a", "text_span": ["NSCLC"], "rationale": "r"}],
    }
    projected = read_legacy_stage1_record(legacy)
    assert projected["recursion_targets"] == []
    assert projected["needs_recursion"] is False
    assert projected["primary_rule_id"] is None
    assert legacy.get("recursion_targets") is None  # source untouched


def test_legacy_string_text_span_normalized_on_read():
    projected = read_legacy_stage1_record(
        {"splitting_decision": "composite_split", "sub_criteria": [{"child_id": "a", "text_span": "NSCLC"}]}
    )
    assert projected["sub_criteria"][0]["text_span"] == ["NSCLC"]


def test_legacy_nested_exception_single_span_accepted():
    """9 of the 10 historical nested_exception gold records look exactly like this."""
    projected = read_legacy_stage1_record(
        {"splitting_decision": "nested_exception",
         "sub_criteria": [{"child_id": "a", "text_span": ["except X"]}]}
    )
    assert len(projected["sub_criteria"]) == 1


def test_normalize_text_span_forms():
    assert normalize_text_span(None) == []
    assert normalize_text_span("  a  ") == ["a"]
    assert normalize_text_span(["a", "", "  ", "b"]) == ["a", "b"]
    assert normalize_text_span(123) == []


def test_legacy_read_is_tolerant_but_v13_validation_is_strict():
    """The compatibility boundary: tolerant read, strict write."""
    legacy = {"splitting_decision": "composite_split", "child_logic": None,
              "sub_criteria": [{"child_id": "a", "text_span": "NSCLC"},
                               {"child_id": "b", "text_span": "EGFR mutation"}]}
    projected = read_legacy_stage1_record(legacy)          # no exception
    errs = validate_v13_output(projected, ctx_for())       # but not v1.3-valid
    assert any("child_logic이 필수" in e for e in errs)


def test_real_historical_gold_records_are_readable():
    """Every record in the frozen 113-item export projects without error."""
    path = Path(__file__).resolve().parent.parent / (
        "evidence/stage1/adjudication_v1_2_2_2026-09-07/gold/"
        "STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl"
    )
    if not path.exists():
        return  # frozen export not present in this checkout
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)["record"]
        projected = read_legacy_stage1_record(record)
        assert projected["splitting_decision"] in {
            "none", "composite_split", "macro_aggregate", "nested_exception"}
        for sub in projected["sub_criteria"]:
            assert isinstance(sub["text_span"], list)
        n += 1
    assert n == 113


# ──────────────────────────────────────────────────────────────────────
# RUNNER mechanics
# ──────────────────────────────────────────────────────────────────────

def test_runner_hard_fails_on_invalid_output():
    bad = out(splitting_decision="composite_split", child_logic=None,
              sub_criteria=[{"child_id": "a", "text_span": ["NSCLC"]},
                            {"child_id": "b", "text_span": ["EGFR mutation"]}])
    try:
        run_stage1_v13(root_context(ROOT), llm=scripted_llm(bad, bad, bad),
                       model="m", template=TEMPLATE)
    except Stage1V13ValidationError as e:
        assert "child_logic" in str(e)
    else:
        raise AssertionError("잘못된 출력이 통과했습니다")


def test_runner_retries_then_succeeds():
    bad = out(primary_rule_id="NOPE")
    node = run_stage1_v13(root_context(ROOT), llm=scripted_llm(bad, out()),
                          model="m", template=TEMPLATE)
    assert node.output["primary_rule_id"] == "H0"


def test_runner_rejects_unparseable_json():
    def broken(prompt_text, model):
        return "not json at all"
    try:
        run_stage1_v13(root_context(ROOT), llm=broken, model="m", template=TEMPLATE)
    except Stage1V13ValidationError as e:
        assert "JSON 파싱 실패" in str(e)
    else:
        raise AssertionError("파싱 불가 응답이 통과했습니다")


def test_root_context_defaults():
    c = root_context(ROOT, criterion_type="inclusion")
    assert c.target_segments == [ROOT]
    assert c.parent_context is None
    assert c.depth == 0 and c.node_id == "root"


def test_prompt_variables_cover_every_placeholder():
    """All six v1.3.1 placeholders are supplied — no literal {{...}} survives."""
    template = load_dev_prompt()
    rendered = render_prompt(root_context(ROOT, criterion_type="inclusion"), template)
    assert "{{" not in rendered, rendered[rendered.index("{{"): rendered.index("{{") + 60]


def test_dev_prompt_file_exists_and_is_the_imported_one():
    assert DEV_PROMPT_PATH.exists()
    text = DEV_PROMPT_PATH.read_text(encoding="utf-8")
    assert "v1.3.1 DEVELOPMENT" in text
    assert "Canonical Core v1.3.0" in text


def test_cache_payload_distinguishes_recursive_passes():
    """Two children share a root but must not share a cache entry."""
    parent = {"splitting_decision": "composite_split", "child_logic": "AND",
              "sub_criteria": [{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}]}
    a = child_context(ctx_for(), parent, "a").cache_payload()
    b = child_context(ctx_for(), parent, "b").cache_payload()
    assert a != b
    assert a["target_segments"] != b["target_segments"]
    assert a["parent_context"] != b["parent_context"]


def test_cache_payload_ignores_node_path():
    """Identical inputs reached by different paths are the same call."""
    c1 = ctx_for()
    c2 = ctx_for()
    c2.node_id, c2.depth = "root.a.b", 2
    assert c1.cache_payload() == c2.cache_payload()


def test_summarize_renders_tree():
    parent = out(splitting_decision="composite_split", child_logic="AND",
                 sub_criteria=[{"child_id": "a", "text_span": ["Histologically confirmed NSCLC"]},
                               {"child_id": "b", "text_span": ["EGFR mutation"]}],
                 needs_recursion=True, recursion_targets=["a"], primary_rule_id="H1-B")
    text = summarize(run_mock(ROOT, parent, out()))
    assert "root: composite_split" in text and "root.a: none" in text


def test_neighboring_criteria_marks_current():
    crits = [{"criterion_id": "I1", "text": "a"}, {"criterion_id": "I2", "text": "b"},
             {"criterion_id": "I3", "text": "c"}]
    block = format_neighboring_criteria(crits[1], crits)
    assert ">>> CURRENT >>> I2" in block and "I1" in block and "I3" in block


def test_dev_output_refuses_protected_paths():
    """A development run must never write into historical or frozen areas."""
    from pipeline.stage1_v13.runner import _reject_protected
    for bad in ["evidence/x.json", "iaa_workspace/x.json",
                "STAGE1_GOLD_113items_2026-09-07/x.json", "AMIA_2027_anything/x.json"]:
        try:
            _reject_protected(Path(bad))
        except Stage1V13Error:
            continue
        raise AssertionError(f"보호 경로가 허용되었습니다: {bad}")


def test_dev_output_allows_ordinary_paths():
    from pipeline.stage1_v13.runner import _reject_protected
    _reject_protected(Path("/tmp/stage1_v13_dev.json"))
    _reject_protected(Path("pipeline/output_dev/x.json"))


def test_v13_runner_loads_only_the_development_prompt():
    """Layer 4 stays legacy: this path resolves to the dev prompt, never prompt_1."""
    assert DEV_PROMPT_PATH.parts[-3:] == ("development", "stage1", "stage1_prompt_v1_3_1.txt")
    assert "prompt_1_splitting" not in str(DEV_PROMPT_PATH)


def test_production_filename_map_unchanged_by_importing_v13():
    """Importing the v1.3 package must not repoint production prompt resolution."""
    import inspect

    from pipeline import llm_client
    src = inspect.getsource(llm_client._load_prompt)
    assert '"prompt_1": "prompt_1_splitting.txt"' in src
    assert "stage1_prompt_v1_3_1" not in src
    assert "development" not in src


def test_v13_render_does_not_inject_examples_json():
    """examples.json is v1.2.2-era few-shot; the v1.3 path must not pull it in."""
    rendered = render_prompt(root_context(ROOT, criterion_type="inclusion"), load_dev_prompt())
    assert "## Inline Examples" not in rendered
    assert "KEYNOTE-671" not in rendered


def test_assert_valid_raises_with_node_id():
    try:
        assert_valid_v13_output(out(primary_rule_id="ZZ"), ctx_for())
    except Stage1V13ValidationError as e:
        assert e.node_id == "root" and e.errors
    else:
        raise AssertionError("검증 실패가 발생하지 않았습니다")


# ──────────────────────────────────────────────────────────────────────
# Script-mode runner
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [(name, fn) for name, fn in globals().items()
             if name.startswith("test_") and callable(fn)]
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
