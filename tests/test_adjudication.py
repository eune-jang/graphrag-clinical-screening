"""Tests for the Stage 1 adjudication logic (adjudication_handover.md §B/§C).

Run with:
    python -m pytest tests/test_adjudication.py -v

Or as a script (no pytest needed):
    python tests/test_adjudication.py
"""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iaa_pipeline.adjudication import (  # noqa: E402
    GAP_TIER,
    RULE_STATUSES,
    TIERS,
    build_gap_ticket,
    build_gold_envelope,
    build_gold_record,
    committed_envelope_name,
    envelope_dir,
    gap_tickets_path,
    load_queue,
    merge_gap_tickets,
    peer_summary,
    queue_index,
    span_violations,
    validate_adjudication,
)
from iaa_pipeline.metrics import compute_stage1_iaa  # noqa: E402
from iaa_pipeline.streamlit_app import (  # noqa: E402
    GOLD_ACTOR,
    build_adjudication_seed,
    build_adjudication_tab_spec,
    discover_peer_actors,
    find_actor_envelope,
    render_adjudication_form_blind,
    resolve_envelope_path,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_adjudication_queue import (  # noqa: E402
    S2_FILTERS,
    enumeration_signals,
    risk_signals,
    signal_families,
    sort_queue,
)
from tier0_check import check_record  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# Blinding guarantees (§B-2 — the adjudication analogue of audit A1/A3/A7)
# ──────────────────────────────────────────────────────────────────────

def test_blind_adjudication_form_rejects_peer_records():
    """Signature-level guarantee: no peer data can reach the blind form."""
    params = inspect.signature(render_adjudication_form_blind).parameters
    assert "peer_records" not in params
    assert "llm_record" not in params


def test_blind_tab_spec_hides_peer_tab():
    assert "👥 Peer labels" not in build_adjudication_tab_spec(blind=True)
    assert "👥 Peer labels" in build_adjudication_tab_spec(blind=False)


def test_blind_seed_ignores_existing_gold():
    """A revealed-pass gold edit must not leak back into a blind re-open."""
    gold = {"splitting_decision": "macro_aggregate",
            "sub_criteria": [{"child_id": "a", "text_span": "x"}]}
    blind = {"splitting_decision": "none", "sub_criteria": []}
    seed = build_adjudication_seed(blind=True, existing_gold=gold,
                                   blind_label=blind)
    assert seed["splitting_decision"] == "none"

    seed_open = build_adjudication_seed(blind=False, existing_gold=gold,
                                        blind_label=blind)
    assert seed_open["splitting_decision"] == "macro_aggregate"


def test_open_seed_falls_back_to_blind_label():
    blind = {"splitting_decision": "composite_split", "sub_criteria": []}
    seed = build_adjudication_seed(blind=False, existing_gold=None,
                                   blind_label=blind)
    assert seed["splitting_decision"] == "composite_split"


# ──────────────────────────────────────────────────────────────────────
# Span validation (§B-3)
# ──────────────────────────────────────────────────────────────────────

_TEXT = "Planned surgery must comprise lobectomy, sleeve resection, or bilobectomy"


def test_span_exact_substring_passes():
    subs = [{"child_id": "a", "text_span": "sleeve resection"}]
    assert span_violations(_TEXT, subs) == []


def test_span_not_substring_flagged_with_suggestion():
    subs = [{"child_id": "a", "text_span": "Planned surgery must comprise bilobectomy"}]
    problems = span_violations(_TEXT, subs)
    assert len(problems) == 1
    assert problems[0]["code"] == "NOT_SUBSTRING"
    assert problems[0]["suggestion"]  # a hint is offered


def test_span_whitespace_diff_reported_separately_and_not_normalized():
    """"hepatitis  C" vs "hepatitis C" — detected, but never auto-fixed."""
    text = "Active infection including tuberculosis hepatitis B and C"
    subs = [{"child_id": "a", "text_span": "hepatitis B  and C"}]
    problems = span_violations(text, subs)
    assert [p["code"] for p in problems] == ["WHITESPACE_ONLY_DIFF"]
    # the original span is returned untouched
    assert problems[0]["span"] == "hepatitis B  and C"


def test_span_empty_flagged():
    problems = span_violations(_TEXT, [{"child_id": "a", "text_span": "   "}])
    assert [p["code"] for p in problems] == ["EMPTY_SPAN"]


def test_span_violation_blocks_save_until_override():
    bad = [{"child_id": "a", "text_span": "not in the text at all",
            "rationale": "r"},
           {"child_id": "b", "text_span": "lobectomy", "rationale": "r"}]
    problems = span_violations(_TEXT, bad)
    errs = validate_adjudication(
        splitting_decision="composite_split", sub_criteria=bad, tier=2,
        rationale_short="ok", rule_status=None, span_override=None,
        span_problems=problems,
    )
    assert any("span_override" in e for e in errs)

    errs_override = validate_adjudication(
        splitting_decision="composite_split", sub_criteria=bad, tier=2,
        rationale_short="ok", rule_status=None,
        span_override="가이드라인 예외: 공통 전제 복제", span_problems=problems,
    )
    assert not any("span_override" in e for e in errs_override)


# ──────────────────────────────────────────────────────────────────────
# Required fields (§C-2)
# ──────────────────────────────────────────────────────────────────────

def test_tier_and_rationale_required():
    errs = validate_adjudication(
        splitting_decision="none", sub_criteria=[], tier=None,
        rationale_short="", rule_status=None, span_override=None,
        span_problems=[],
    )
    assert any("tier" in e for e in errs)
    assert any("rationale_short" in e for e in errs)


def test_child_rationale_required_when_split():
    subs = [{"child_id": "a", "text_span": "lobectomy"},
            {"child_id": "b", "text_span": "bilobectomy"}]
    errs = validate_adjudication(
        splitting_decision="composite_split", sub_criteria=subs, tier=1,
        rationale_short="ok", rule_status=None, span_override=None,
        span_problems=[],
    )
    assert sum(1 for e in errs if "rationale 필수" in e) == 2

    for s in subs:
        s["rationale"] = "왜 이렇게 잘랐는지"
    assert validate_adjudication(
        splitting_decision="composite_split", sub_criteria=subs, tier=1,
        rationale_short="ok", rule_status=None, span_override=None,
        span_problems=[],
    ) == []


def test_child_rationale_not_required_when_none():
    assert validate_adjudication(
        splitting_decision="none", sub_criteria=[], tier=2,
        rationale_short="단일 조회 단위", rule_status=None, span_override=None,
        span_problems=[],
    ) == []


def test_composite_split_needs_two_children():
    subs = [{"child_id": "a", "text_span": "lobectomy", "rationale": "r"}]
    errs = validate_adjudication(
        splitting_decision="composite_split", sub_criteria=subs, tier=0,
        rationale_short="ok", rule_status=None, span_override=None,
        span_problems=[],
    )
    assert any("sub_criteria < 2" in e for e in errs)


def test_invalid_rule_status_rejected():
    errs = validate_adjudication(
        splitting_decision="none", sub_criteria=[], tier=2,
        rationale_short="ok", rule_status="bogus", span_override=None,
        span_problems=[],
    )
    assert any("rule_status" in e for e in errs)
    assert set(RULE_STATUSES) == {"existing", "new", "conflict", "gap"}


# ──────────────────────────────────────────────────────────────────────
# Record shape (§7.4-① gold at top level, 🔴2 tier 3 excluded)
# ──────────────────────────────────────────────────────────────────────

def _gold_record(**over):
    base = dict(
        criterion_id="NCT05756153_E6",
        gold={"splitting_decision": "macro_aggregate", "child_logic": None,
              "sub_criteria": [{"child_id": "a", "text_span": "hypertension",
                                "rationale": "별도 조회"}],
              "confidence": "high"},
        blind_label={"splitting_decision": "macro_aggregate", "sub_criteria": []},
        tier=2, rationale_short="각각 별도 조회", rule_id="v1.1_§4_macro",
        rule_status="conflict", conflicting_rule="v1.1_§4_참고",
        escalate_pi=False, span_override=None,
        adjudicated_at="2026-07-30T00:00:00Z", queue_stratum="S1",
        compared={"EHJ": "none", "DYK": "macro_aggregate"},
    )
    base.update(over)
    return build_gold_record(**base)


def test_gold_label_sits_at_record_top_level():
    """§7.4-①: compute_stage1_iaa reads the TOP level, not a nested block."""
    rec = _gold_record()
    assert rec["splitting_decision"] == "macro_aggregate"
    assert rec["sub_criteria"][0]["text_span"] == "hypertension"
    assert "gold_label" not in rec  # the v2 draft's mistake


def test_gold_record_is_readable_by_compute_stage1_iaa():
    """End-to-end: a GOLD envelope must produce real κ inputs, not None."""
    gold = build_gold_envelope(
        trial_id="NCT05756153", stage=1, annotator=GOLD_ACTOR,
        records=[_gold_record(),
                 _gold_record(criterion_id="NCT05756153_E7",
                              gold={"splitting_decision": "none",
                                    "sub_criteria": []})],
        created_at="2026-07-30T00:00:00Z", committed=True,
    )
    peer = {"records": [
        {"criterion_id": "NCT05756153_E6", "splitting_decision": "none",
         "sub_criteria": []},
        {"criterion_id": "NCT05756153_E7", "splitting_decision": "none",
         "sub_criteria": []},
    ]}
    iaa = compute_stage1_iaa(gold, peer)
    assert iaa["alignment"]["n_matched"] == 2
    assert iaa["splitting_decision"]["n"] == 2
    # 1 of 2 agree; the label was actually read (not silently None)
    assert iaa["splitting_decision"]["n_agree"] == 1
    assert "__NONE__" not in iaa["splitting_decision"]["classes"]


def test_child_rationale_and_cohort_scope_survive_into_gold():
    """§7.4: writing gold KEEPS child rationale/cohort_scope for D-4 few-shot."""
    rec = _gold_record(gold={
        "splitting_decision": "composite_split", "child_logic": "AND",
        "cohort_scope": ["Arm 1"],
        "sub_criteria": [{"child_id": "a", "text_span": "x", "rationale": "r",
                          "cohort_scope": ["Arm 1"]}],
    })
    assert rec["child_logic"] == "AND"
    assert rec["cohort_scope"] == ["Arm 1"]
    assert rec["sub_criteria"][0]["rationale"] == "r"
    assert rec["sub_criteria"][0]["cohort_scope"] == ["Arm 1"]


def test_adjudication_meta_kept_out_of_gold_fields():
    rec = _gold_record()
    adj = rec["adjudication"]
    assert adj["tier"] == 2 and adj["rule_status"] == "conflict"
    assert adj["conflicting_rule"] == "v1.1_§4_참고"
    assert rec["blind_label"]["splitting_decision"] == "macro_aggregate"
    # meta must not pollute the label namespace
    for k in ("tier", "rule_id", "rule_status", "rationale_short"):
        assert k not in rec


def test_gap_ticket_carries_tier_and_blind_label():
    """§0.4-⚪5: tier-3 items keep the adjudicator's blind opinion."""
    t = build_gap_ticket(
        criterion_id="NCT_E9", reason="NCCN·CRC 어느 근거로도 미결정",
        blind_label={"splitting_decision": "none", "sub_criteria": []},
        compared={"EHJ": "none", "DYK": "composite_split"},
        escalate_pi=True, note="PI 확인 필요", queue_stratum="S1",
        adjudicated_at="2026-07-30T00:00:00Z",
    )
    assert t["tier"] == GAP_TIER == 3
    assert t["blind_label"]["splitting_decision"] == "none"
    assert t["EHJ"] == "none" and t["DYK"] == "composite_split"
    assert "splitting_decision" not in t  # NOT a gold record


def test_gap_tickets_upsert_by_criterion_id():
    a = build_gap_ticket(criterion_id="X", reason="r1", blind_label=None,
                         compared=None, escalate_pi=False, note=None,
                         queue_stratum=None, adjudicated_at="t1")
    b = build_gap_ticket(criterion_id="X", reason="r2", blind_label=None,
                         compared=None, escalate_pi=False, note=None,
                         queue_stratum=None, adjudicated_at="t2")
    c = build_gap_ticket(criterion_id="Y", reason="r3", blind_label=None,
                         compared=None, escalate_pi=False, note=None,
                         queue_stratum=None, adjudicated_at="t3")
    merged = merge_gap_tickets([a], [b, c])
    assert len(merged) == 2
    assert merged[0]["reason"] == "r2"  # replaced, not duplicated
    assert merged[1]["criterion_id"] == "Y"


def test_tier3_only_needs_rationale():
    """A gap ticket must stay reachable — gold-label rules can't block it."""
    errs = validate_adjudication(
        splitting_decision=None, sub_criteria=[], tier=3,
        rationale_short="미결정 사유", rule_status="gap", span_override=None,
        span_problems=[],
    )
    assert errs == []
    assert 3 in TIERS


# ──────────────────────────────────────────────────────────────────────
# Paths / discovery (§7.4-🔴1, 🟡3)
# ──────────────────────────────────────────────────────────────────────

def test_gold_lives_in_round_dir_next_to_peers():
    stage_dir = Path("/ws/NCT1/stage1")
    assert envelope_dir(stage_dir, 2) == stage_dir / "round2"
    assert envelope_dir(stage_dir, None) == stage_dir
    assert gap_tickets_path(stage_dir, 2) == stage_dir / "round2" / "gap_tickets.json"
    assert committed_envelope_name("GOLD", "NCT1", 1) == "GOLD_NCT1_stage1_committed.json"


def test_discovery_finds_gold_beside_peers_and_ignores_gap_tickets():
    """The whole point of §7.4-🔴1: one directory must yield all three actors."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for actor in ("EHJ", "DYK", GOLD_ACTOR):
            (d / f"{actor}_NCT1_stage1_committed.json").write_text(json.dumps({
                "trial_id": "NCT1", "source": "annotator", "annotator": actor,
                "committed": True, "records": [],
            }), encoding="utf-8")
        # a gap-ticket file (JSON array) must not be mistaken for an envelope
        (d / "gap_tickets.json").write_text(json.dumps([{"criterion_id": "X"}]),
                                            encoding="utf-8")

        peers = discover_peer_actors(d, exclude=GOLD_ACTOR)
        assert peers == ["DYK", "EHJ"]

        # compute_iaa's own discovery sees all three -> 3 pairs
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from compute_iaa import discover_sources
        annotators, llm = discover_sources(d, d)
        assert set(annotators) == {"EHJ", "DYK", GOLD_ACTOR}
        assert llm is None
        import itertools
        assert len(list(itertools.combinations(sorted(annotators), 2))) == 3


def test_resolve_envelope_path_reuses_existing_file():
    """A second save must not create a duplicate actor file in one directory."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        odd = d / "hand_named.json"
        odd.write_text(json.dumps({
            "trial_id": "NCT1", "source": "annotator", "annotator": GOLD_ACTOR,
            "committed": True, "records": [],
        }), encoding="utf-8")
        assert find_actor_envelope(d, GOLD_ACTOR) == odd
        assert resolve_envelope_path(d, GOLD_ACTOR, trial_id="NCT1", stage=1) == odd
        # a fresh actor gets the canonical name
        assert resolve_envelope_path(d, "EHJ", trial_id="NCT1", stage=1).name == \
            "EHJ_NCT1_stage1_committed.json"


# ──────────────────────────────────────────────────────────────────────
# Queue (§A-3)
# ──────────────────────────────────────────────────────────────────────

def test_load_queue_filters_trial_and_sorts_by_priority():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "q.csv"
        p.write_text(
            "priority,stratum,trial,criterion_id\n"
            "3,S2,NCT1,NCT1_E3\n"
            "1,S1,NCT1,NCT1_E1\n"
            "2,S1,NCT2,NCT2_E1\n",
            encoding="utf-8",
        )
        rows = load_queue(p, trial_id="NCT1")
        assert [r["criterion_id"] for r in rows] == ["NCT1_E1", "NCT1_E3"]
        assert set(queue_index(rows)) == {"NCT1_E1", "NCT1_E3"}
        assert load_queue(Path(td) / "missing.csv") == []


def test_queue_sort_puts_72_conflicts_first_then_binary_axis():
    rows = [
        {"stratum": "S1", "is_72_conflict": 0, "binary_mismatch": 0,
         "trial": "T", "criterion_id": "c2"},
        {"stratum": "S3", "is_72_conflict": 1, "binary_mismatch": 0,
         "trial": "T", "criterion_id": "c3"},
        {"stratum": "S1", "is_72_conflict": 0, "binary_mismatch": 1,
         "trial": "T", "criterion_id": "c1"},
    ]
    out = sort_queue(rows)
    assert [r["criterion_id"] for r in out] == ["c3", "c1", "c2"]
    assert [r["priority"] for r in out] == [1, 2, 3]


# ──────────────────────────────────────────────────────────────────────
# S2 risk filter (§0.3-🟠3 + the measured semicolon finding)
# ──────────────────────────────────────────────────────────────────────

_REQUIRED_S2_TEXTS = {
    # the 6 items the handover requires the filter to catch by RULE
    "NCT02474355_E8": "Any clinically important abnormalities in rhythm, conduction or "
                      "morphology of resting ECG (e.g., complete left bundle branch block)",
    "NCT02474355_I6": "Adequate bone marrow reserve and organ function as demonstrated "
                      "by complete blood count",
    "NCT02474355_E9": "Any factors that increase the risk of QTc prolongation",
    "NCT01295827_E6": "Risk factors for bowel obstruction (including a history of acute "
                      "diverticulitis)",
    "NCT05756153_E6": "With uncontrolled systemic diseases, such as hypertension or diabetes.",
    "NCT03728556_E6": "Any prior treatment that targets immune checkpoints, including "
                      "PD-1, PD-L1, CTLA4, OX-40, CD137",
}


def test_recommended_filters_catch_all_required_items():
    for name in ("spec", "strong", "umbrella"):
        for cid, text in _REQUIRED_S2_TEXTS.items():
            assert S2_FILTERS[name](signal_families(text)), f"{name} missed {cid}"


def test_keyword_only_filter_misses_required_items():
    """Why the handover's pre-v2.2 "~15건" scope is not usable.

    Measured on the real corpus, `keyword` misses 4 of the 6 required items;
    on these condensed texts it misses more, so the assertion is a lower bound
    plus the canonical case by name.
    """
    missed = [cid for cid, text in _REQUIRED_S2_TEXTS.items()
              if not S2_FILTERS["keyword"](signal_families(text))]
    assert "NCT05756153_E6" in missed  # the canonical §1.3 case
    assert len(missed) >= 4


def test_trailing_semicolon_alone_is_not_a_risk_signal():
    """Measured: a trailing ';' is source formatting, not an enumeration.

    All 12 items the `spec` variant adds over `strong` look like this — label
    agreement in both rounds, `enum:semicolon` as their only signal, and one
    semicolon at the very end. 11 of them come from a single trial.
    """
    text = "Performance status of ECOG 0 - 2;"
    fams = signal_families(text)
    assert fams["enum"] == ["enum:semicolon"]
    assert not fams["umb"] and not fams["dx"] and not fams["bm"]
    assert S2_FILTERS["spec"](fams) is True       # the doc's literal filter fires
    assert S2_FILTERS["strong"](fams) is False    # the default does not


def test_real_in_sentence_enumeration_caught_without_semicolon_branch():
    """The enumeration risk itself is carried by commas/`or`, not the semicolon.

    Text shape taken from NCT02075840_E12, one of only 5 criteria in the corpus
    with a true in-sentence semicolon. Dropping the semicolon branch loses no
    coverage: every such item is either an SD disagreement (S1 already) or
    matches on commas / `or` / umbrella, as here.
    """
    text = ("Any psychological, familial, sociological, or geographical condition "
            "potentially hampering compliance with the study protocol requirements "
            "and/or follow-up procedures; these conditions should be discussed")
    fams = signal_families(text)
    assert "enum:semicolon" in fams["enum"]
    non_semicolon = [s for s in fams["enum"] if s != "enum:semicolon"]
    assert non_semicolon  # commas / or carry the signal on their own
    assert S2_FILTERS["strong"](fams) is True


def test_enumeration_signals_thresholds():
    assert enumeration_signals("a, b, c, d") == ["commas=3"]
    assert enumeration_signals("a or b or c") == ["or=2"]
    assert enumeration_signals("a; b") == ["semicolon"]
    assert enumeration_signals("plain text") == []


def test_risk_signals_returns_flat_list():
    sigs = risk_signals("Adequate organ function in metastatic NSCLC")
    assert any(s.startswith("umb:") for s in sigs)
    assert any(s.startswith("dx:") for s in sigs)


# ──────────────────────────────────────────────────────────────────────
# Tier 0 check (§A-2)
# ──────────────────────────────────────────────────────────────────────

def test_tier0_flags_composite_with_one_child():
    rec = {"criterion_id": "X", "splitting_decision": "composite_split",
           "sub_criteria": [{"child_id": "a", "text_span": "x"}],
           "child_logic": "AND"}
    assert [c for c, _ in check_record(rec)] == ["T0_COMPOSITE_LT2_CHILDREN"]


def test_tier0_flags_null_child_logic():
    rec = {"criterion_id": "X", "splitting_decision": "composite_split",
           "sub_criteria": [{"child_id": "a"}, {"child_id": "b"}],
           "child_logic": None}
    assert [c for c, _ in check_record(rec)] == ["T0_COMPOSITE_NULL_CHILD_LOGIC"]


def test_tier0_ignores_non_composite_decisions():
    for d in ("none", "macro_aggregate", "nested_exception"):
        rec = {"criterion_id": "X", "splitting_decision": d,
               "sub_criteria": [], "child_logic": None}
        assert check_record(rec) == []


def test_peer_summary_shape():
    assert peer_summary(None) == {}
    s = peer_summary({"splitting_decision": "none", "notes": "메모",
                      "sub_criteria": [{"child_id": "a"}]})
    assert s["splitting_decision"] == "none"
    assert s["n_children"] == 1
    assert s["notes"] == "메모"


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
