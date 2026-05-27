"""Smoke tests for iaa_pipeline aligners + metrics.

Run with:
    python -m pytest tests/test_iaa_metrics.py -v

Or as a script (no pytest needed):
    python tests/test_iaa_metrics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iaa_pipeline.aligners import (
    align_stage1,
    align_stage2,
    align_relations_by_span,
    align_error_types,
)
from iaa_pipeline.metrics import (
    cohens_kappa,
    set_agreement,
    compute_stage1_iaa,
    compute_stage2_iaa,
    compute_stage4_iaa,
    compute_error_type_iaa,
)
from iaa_pipeline.streamlit_app import (
    build_form_seed,
    build_tab_spec,
    envelope_is_committed,
    render_criterion_form_blind,
    render_criterion_form_assisted,
    STAGE_MODE,
)

# Hosted app helpers (filtering bundled trials to IAA subset)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "streamlit_apps"))
import stage1_app as hosted  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# Cohen's kappa unit tests
# ──────────────────────────────────────────────────────────────────────

def test_kappa_perfect_agreement_multi_class():
    """Two annotators agree on every label across multiple classes."""
    a = ["composite_split", "none", "macro_aggregate", "none"]
    b = ["composite_split", "none", "macro_aggregate", "none"]
    result = cohens_kappa(a, b)
    assert result.observed == 1.0
    assert result.kappa == 1.0
    assert result.n == 4


def test_kappa_undefined_single_class():
    """Both annotators always pick the same single label — κ undefined."""
    a = ["none"] * 5
    b = ["none"] * 5
    result = cohens_kappa(a, b)
    assert result.observed == 1.0
    assert result.kappa is None  # 1 - p_e == 0


def test_kappa_random_agreement():
    """Two annotators on a balanced binary with low real agreement."""
    a = ["A", "B", "A", "B", "A", "B"]
    b = ["B", "A", "A", "B", "B", "A"]
    result = cohens_kappa(a, b)
    # observed = 2/6, p_e = 0.5 → κ negative
    assert result.observed < 0.5
    assert result.kappa < 0
    assert result.n == 6


def test_kappa_handles_none_labels():
    """None values should be treated as their own class, not crash."""
    a = ["AND", None, "OR", None]
    b = ["AND", None, "AND", None]
    result = cohens_kappa(a, b)
    assert result.n == 4
    assert result.n_agree == 3  # 3 of 4 match


def test_kappa_length_mismatch_raises():
    try:
        cohens_kappa(["a", "b"], ["a"])
    except ValueError:
        return
    raise AssertionError("expected ValueError on length mismatch")


# ──────────────────────────────────────────────────────────────────────
# Set agreement
# ──────────────────────────────────────────────────────────────────────

def test_set_agreement_exact():
    s = set_agreement(["cohort_a", "cohort_b"], ["cohort_b", "cohort_a"])
    assert s["exact_match"] is True
    assert s["jaccard"] == 1.0


def test_set_agreement_partial():
    s = set_agreement(["a", "b"], ["b", "c"])
    assert s["exact_match"] is False
    assert abs(s["jaccard"] - 1 / 3) < 1e-3  # metric rounds to 4 decimals


def test_set_agreement_both_none():
    s = set_agreement(None, None)
    assert s["exact_match"] is True
    assert s["jaccard"] == 1.0


# ──────────────────────────────────────────────────────────────────────
# Stage 1 alignment + IAA
# ──────────────────────────────────────────────────────────────────────

def _make_stage1_envelope(annotator: str, decisions: dict[str, str]) -> dict:
    """Build a minimal Stage 1 envelope from {criterion_id: splitting_decision}."""
    return {
        "trial_id": "NCT_TEST",
        "stage": 1,
        "source": "annotator",
        "annotator": annotator,
        "created_at": "2026-05-27T00:00:00Z",
        "records": [
            {
                "criterion_id": cid,
                "splitting_decision": d,
                "sub_criteria": [],
            }
            for cid, d in decisions.items()
        ],
    }


def test_stage1_alignment_perfect():
    env_a = _make_stage1_envelope("A", {
        "I1": "composite_split", "I2": "none", "I3": "macro_aggregate"
    })
    env_b = _make_stage1_envelope("B", {
        "I1": "composite_split", "I2": "none", "I3": "macro_aggregate"
    })
    alignment = align_stage1(env_a, env_b)
    assert alignment.n_matched == 3
    assert alignment.only_a == []
    assert alignment.only_b == []


def test_stage1_iaa_partial():
    """Realistic case: 4 of 5 agree."""
    env_a = _make_stage1_envelope("A", {
        "I1": "composite_split", "I2": "none", "I3": "none",
        "I4": "nested_exception", "I5": "macro_aggregate",
    })
    env_b = _make_stage1_envelope("B", {
        "I1": "composite_split", "I2": "none", "I3": "composite_split",
        "I4": "nested_exception", "I5": "macro_aggregate",
    })
    iaa = compute_stage1_iaa(env_a, env_b)
    assert iaa["alignment"]["n_matched"] == 5
    assert iaa["splitting_decision"]["n_agree"] == 4
    assert iaa["splitting_decision"]["observed_agreement"] == 0.8


def test_stage1_iaa_missing_criterion_one_side():
    """If A has 3 criteria and B has 2, only_a/only_b populated."""
    env_a = _make_stage1_envelope("A", {"I1": "none", "I2": "none", "I3": "none"})
    env_b = _make_stage1_envelope("B", {"I1": "none", "I2": "none"})
    iaa = compute_stage1_iaa(env_a, env_b)
    assert iaa["alignment"]["n_matched"] == 2
    assert iaa["alignment"]["n_only_a"] == 1
    assert iaa["alignment"]["n_only_b"] == 0


# ──────────────────────────────────────────────────────────────────────
# Stage 2 alignment (fuzzy span)
# ──────────────────────────────────────────────────────────────────────

def test_relation_alignment_exact_span_match():
    rels_a = [
        {"relation_id": "r1", "target_text_span": "ECOG performance status",
         "relation_type": "HAS_VALUE", "target_subtype": "Observation"},
        {"relation_id": "r2", "target_text_span": "within 10 days",
         "relation_type": "HAS_TEMPORAL", "target_subtype": "Observation"},
    ]
    rels_b = [
        {"relation_id": "x1", "target_text_span": "within 10 days",
         "relation_type": "HAS_TEMPORAL", "target_subtype": "Observation"},
        {"relation_id": "x2", "target_text_span": "ECOG performance status",
         "relation_type": "HAS_VALUE", "target_subtype": "Observation"},
    ]
    result = align_relations_by_span(rels_a, rels_b)
    assert result.n_matched == 2
    assert result.only_a == []
    assert result.only_b == []


def test_relation_alignment_fuzzy_span():
    """Slightly different wording should fuzzy-match."""
    rels_a = [{"relation_id": "r1", "target_text_span": "ECOG performance status of 0 or 1",
               "relation_type": "HAS_VALUE", "target_subtype": "Observation"}]
    rels_b = [{"relation_id": "x1", "target_text_span": "ECOG performance status of 0-1",
               "relation_type": "HAS_VALUE", "target_subtype": "Observation"}]
    result = align_relations_by_span(rels_a, rels_b, threshold=0.85)
    assert result.n_matched == 1


def test_relation_alignment_no_match():
    rels_a = [{"relation_id": "r1", "target_text_span": "EGFR mutation",
               "relation_type": "REQUIRES_BIOMARKER", "target_subtype": "Biomarker"}]
    rels_b = [{"relation_id": "x1", "target_text_span": "ALK rearrangement",
               "relation_type": "REQUIRES_BIOMARKER", "target_subtype": "Biomarker"}]
    result = align_relations_by_span(rels_a, rels_b, threshold=0.85)
    assert result.n_matched == 0
    assert len(result.only_a) == 1
    assert len(result.only_b) == 1


def test_stage2_iaa_end_to_end():
    """Two annotators on a single sub_criterion with two relations each."""
    env_a = {
        "trial_id": "NCT_TEST", "stage": 2, "source": "annotator",
        "annotator": "A", "created_at": "2026-05-27T00:00:00Z",
        "records": [{
            "sub_criterion_id": "NCT_TEST_I4",
            "semantic_category": "performance_status",
            "relations": [
                {"relation_id": "r1", "relation_type": "HAS_VALUE",
                 "target_subtype": "Observation", "target_text_span": "ECOG"},
                {"relation_id": "r2", "relation_type": "HAS_TEMPORAL",
                 "target_subtype": "Observation", "target_text_span": "within 10 days"},
            ],
        }],
    }
    env_b = {
        "trial_id": "NCT_TEST", "stage": 2, "source": "annotator",
        "annotator": "B", "created_at": "2026-05-27T00:00:00Z",
        "records": [{
            "sub_criterion_id": "NCT_TEST_I4",
            "semantic_category": "performance_status",
            "relations": [
                {"relation_id": "x1", "relation_type": "HAS_VALUE",
                 "target_subtype": "Observation", "target_text_span": "ECOG"},
                # B missed the HAS_TEMPORAL
            ],
        }],
    }
    iaa = compute_stage2_iaa(env_a, env_b)
    assert iaa["sub_criteria_alignment"]["n_matched"] == 1
    assert iaa["semantic_category"]["n_agree"] == 1
    assert iaa["relations"]["n_matched"] == 1
    assert iaa["relations"]["n_only_a"] == 1
    assert iaa["relations"]["n_only_b"] == 0


# ──────────────────────────────────────────────────────────────────────
# Stage 4 IAA
# ──────────────────────────────────────────────────────────────────────

def test_stage4_iaa_perfect_value_partial_temporal():
    env_a = {
        "trial_id": "T", "stage": 4, "source": "annotator", "annotator": "A",
        "created_at": "2026-05-27T00:00:00Z",
        "records": [
            {"sub_criterion_id": "X_I1", "relation_id": "r1",
             "relation_type": "HAS_VALUE", "operator": "≥", "value": 18,
             "unit": "years", "extraction_source": "regex"},
            {"sub_criterion_id": "X_I2", "relation_id": "r1",
             "relation_type": "HAS_TEMPORAL", "operator": "within", "value": 14,
             "unit": "days", "anchor": "randomization", "direction": "before",
             "anchor_type": "trial_event", "extraction_source": "llm"},
        ],
    }
    env_b = {
        "trial_id": "T", "stage": 4, "source": "annotator", "annotator": "B",
        "created_at": "2026-05-27T00:00:00Z",
        "records": [
            {"sub_criterion_id": "X_I1", "relation_id": "r1",
             "relation_type": "HAS_VALUE", "operator": "≥", "value": 18,
             "unit": "years", "extraction_source": "regex"},
            {"sub_criterion_id": "X_I2", "relation_id": "r1",
             "relation_type": "HAS_TEMPORAL", "operator": "within", "value": 14,
             "unit": "days", "anchor": "informed consent", "direction": "before",
             "anchor_type": "trial_event", "extraction_source": "llm"},
        ],
    }
    iaa = compute_stage4_iaa(env_a, env_b)
    assert iaa["has_value"]["n_pairs"] == 1
    assert iaa["has_value"]["macro_match_rate"] == 1.0
    assert iaa["has_temporal"]["n_pairs"] == 1
    # anchor disagreement: 5/6 fields match
    assert iaa["has_temporal"]["fields"]["anchor"]["match_rate"] == 0.0
    assert iaa["has_temporal"]["fields"]["operator"]["match_rate"] == 1.0


# ──────────────────────────────────────────────────────────────────────
# Error type IAA
# ──────────────────────────────────────────────────────────────────────

def test_error_type_iaa_basic():
    entries_a = [
        {"stage": 2, "record_locator": {"sub_criterion_id": "X_I1"},
         "error_type": "R-MISSING", "annotator": "A", "created_at": "..."},
        {"stage": 2, "record_locator": {"sub_criterion_id": "X_I2"},
         "error_type": "PASS", "annotator": "A", "created_at": "..."},
    ]
    entries_b = [
        {"stage": 2, "record_locator": {"sub_criterion_id": "X_I1"},
         "error_type": "R-MISSING", "annotator": "B", "created_at": "..."},
        {"stage": 2, "record_locator": {"sub_criterion_id": "X_I2"},
         "error_type": "R-WRONG", "annotator": "B", "created_at": "..."},
    ]
    iaa = compute_error_type_iaa(entries_a, entries_b)
    assert iaa["alignment"]["n_matched"] == 2
    assert iaa["error_type"]["n_agree"] == 1
    assert iaa["error_type"]["observed_agreement"] == 0.5


def test_error_type_multi_label_normalized():
    entries_a = [{"stage": 2, "record_locator": {"id": "x"},
                  "error_type": "R-MISSING, M-CATEGORY",
                  "annotator": "A", "created_at": "..."}]
    entries_b = [{"stage": 2, "record_locator": {"id": "x"},
                  "error_type": "M-CATEGORY,R-MISSING",  # same set, different order/spacing
                  "annotator": "B", "created_at": "..."}]
    iaa = compute_error_type_iaa(entries_a, entries_b)
    assert iaa["error_type"]["n_agree"] == 1


# ──────────────────────────────────────────────────────────────────────
# Blinding guarantee tests (audit_streamlit_v1.md fixes)
# ──────────────────────────────────────────────────────────────────────

LLM_RECORD_SAMPLE = {
    "criterion_id": "X_I1",
    "splitting_decision": "composite_split",
    "child_logic": "AND",
    "sub_criteria": [
        {"child_id": "a", "text_span": "first part"},
        {"child_id": "b", "text_span": "second part"},
        {"child_id": "c", "text_span": "third part"},
    ],
    "confidence": "high",
    "notes": "LLM-generated notes",
}

ANNOTATOR_RECORD_SAMPLE = {
    "criterion_id": "X_I1",
    "splitting_decision": "none",
    "sub_criteria": [],
    "confidence": "medium",
}


def test_blind_seed_ignores_llm_record():
    """A1 resolution: from_scratch mode never seeds defaults from LLM."""
    seed = build_form_seed(
        mode="from_scratch",
        existing_record=None,
        llm_record=LLM_RECORD_SAMPLE,
    )
    assert seed == {}, f"BLINDING VIOLATION: LLM data leaked into from_scratch seed: {seed}"


def test_blind_seed_preserves_annotator_own_work():
    """A1 resolution: annotator can still resume their own draft."""
    seed = build_form_seed(
        mode="from_scratch",
        existing_record=ANNOTATOR_RECORD_SAMPLE,
        llm_record=LLM_RECORD_SAMPLE,  # provided but must be ignored
    )
    assert seed["splitting_decision"] == "none"  # from annotator, NOT from LLM
    assert seed["confidence"] == "medium"
    assert "notes" not in seed  # annotator didn't have notes; must NOT pick LLM's


def test_assisted_seed_falls_back_to_llm():
    """llm_assisted mode (Stages 3-5) correctly uses LLM as fallback."""
    seed = build_form_seed(
        mode="llm_assisted",
        existing_record=None,
        llm_record=LLM_RECORD_SAMPLE,
    )
    assert seed["splitting_decision"] == "composite_split"
    assert len(seed["sub_criteria"]) == 3


def test_assisted_seed_prefers_annotator_over_llm():
    """llm_assisted: annotator's own draft beats LLM (so they can resume)."""
    seed = build_form_seed(
        mode="llm_assisted",
        existing_record=ANNOTATOR_RECORD_SAMPLE,
        llm_record=LLM_RECORD_SAMPLE,
    )
    assert seed["splitting_decision"] == "none"


def test_seed_returns_copy_not_reference():
    """Mutating the seed must not corrupt the source record."""
    src = dict(ANNOTATOR_RECORD_SAMPLE)
    seed = build_form_seed(mode="from_scratch", existing_record=src, llm_record=None)
    seed["splitting_decision"] = "MUTATED"
    assert src["splitting_decision"] == "none"


def test_seed_unknown_mode_raises():
    try:
        build_form_seed(mode="other", existing_record=None, llm_record=None)
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown mode")


def test_tab_spec_from_scratch_excludes_llm_tab():
    """A3 resolution: 🤖 LLM Output tab not rendered in from_scratch."""
    tabs = build_tab_spec(mode="from_scratch", phase="phase_1_annotate",
                           annotator_committed=False)
    assert "🤖 LLM Output" not in tabs
    # Even after commit, from_scratch never shows the LLM tab
    tabs2 = build_tab_spec(mode="from_scratch", phase="phase_2_review",
                            annotator_committed=True)
    assert "🤖 LLM Output" not in tabs2


def test_tab_spec_llm_assisted_includes_llm_tab():
    tabs = build_tab_spec(mode="llm_assisted", phase="phase_1_annotate",
                           annotator_committed=False)
    assert "🤖 LLM Output" in tabs


def test_tab_spec_phase1_excludes_iaa_tab():
    """A5 resolution: IAA tab is hidden during annotation phase."""
    tabs = build_tab_spec(mode="from_scratch", phase="phase_1_annotate",
                           annotator_committed=False)
    assert "📊 IAA" not in tabs
    # Even if committed, Phase 1 hides IAA — you must move to Phase 2
    tabs2 = build_tab_spec(mode="from_scratch", phase="phase_1_annotate",
                            annotator_committed=True)
    assert "📊 IAA" not in tabs2


def test_tab_spec_phase2_requires_commit_for_iaa():
    """A5 resolution: Phase 2 still requires the current annotator's commit."""
    tabs_no_commit = build_tab_spec(mode="from_scratch", phase="phase_2_review",
                                     annotator_committed=False)
    assert "📊 IAA" not in tabs_no_commit
    tabs_committed = build_tab_spec(mode="from_scratch", phase="phase_2_review",
                                     annotator_committed=True)
    assert "📊 IAA" in tabs_committed


def test_blind_render_signature_rejects_llm_record():
    """A1/A2 resolution at signature level: blind render does not accept llm_record."""
    import inspect
    params = inspect.signature(render_criterion_form_blind).parameters
    assert "llm_record" not in params, (
        f"BLINDING VIOLATION: render_criterion_form_blind accepts llm_record: {list(params)}"
    )
    # Sanity: the assisted variant DOES accept it
    assisted_params = inspect.signature(render_criterion_form_assisted).parameters
    assert "llm_record" in assisted_params


def test_stage_mode_mapping_matches_spec():
    """Spec §246-254: Stage 3 is 'the first LLM-assisted stage'."""
    assert STAGE_MODE[1] == "from_scratch"
    assert STAGE_MODE[2] == "from_scratch"
    assert STAGE_MODE[3] == "llm_assisted"
    assert STAGE_MODE[4] == "llm_assisted"
    assert STAGE_MODE[5] == "llm_assisted"


def test_envelope_is_committed():
    """Commit flag must be explicit boolean True, not truthy strings."""
    assert envelope_is_committed({"committed": True}) is True
    assert envelope_is_committed({"committed": False}) is False
    assert envelope_is_committed({"committed": "yes"}) is False  # not boolean
    assert envelope_is_committed({}) is False
    assert envelope_is_committed(None) is False


# ──────────────────────────────────────────────────────────────────────
# Hosted app — IAA trial filtering
# ──────────────────────────────────────────────────────────────────────

def test_iaa_filter_file_exists_and_parses():
    """iaa_8trials.txt should exist and contain exactly 8 NCT IDs."""
    iaa_ids = hosted._load_iaa_trial_filter()
    assert iaa_ids is not None, "iaa_pipeline_spec/iaa_8trials.txt is missing"
    assert len(iaa_ids) == 8, f"expected 8 trials, got {len(iaa_ids)}: {iaa_ids}"
    # spec doc names KEYNOTE-671 explicitly as the pilot
    assert "NCT03425643" in iaa_ids


def test_hosted_app_lists_only_iaa_trials():
    """When the filter file is present, list_bundled_trials returns only the 8."""
    trials = hosted.list_bundled_trials()
    iaa_ids = hosted._load_iaa_trial_filter()
    assert iaa_ids is not None
    assert set(trials) == iaa_ids, (
        f"hosted app dropdown leaked non-IAA trials: "
        f"{set(trials) - iaa_ids}"
    )
    assert len(trials) == 8


def test_iaa_filter_skips_comments_and_blanks():
    """The parser ignores blank lines and comment lines (starting with #)."""
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("# comment line\nNCT00001\n\n# another\nNCT00002\n")
        tmp_path = f.name
    try:
        # Monkey-patch the constant to point at the temp file
        original = hosted.IAA_TRIAL_LIST
        hosted.IAA_TRIAL_LIST = Path(tmp_path)
        ids = hosted._load_iaa_trial_filter()
        assert ids == {"NCT00001", "NCT00002"}
    finally:
        hosted.IAA_TRIAL_LIST = original
        os.unlink(tmp_path)


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
