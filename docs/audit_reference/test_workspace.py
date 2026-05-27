"""Tests for workspace.py — the phase-aware data access layer.

These tests are the core correctness guarantee of the IAA framework.
They verify that:

  1. Phase 1 annotators CANNOT read LLM output or other annotators' work
  2. Phase 1 transitions to Phase 2 only after ALL required annotators commit
  3. Phase 2 access requires the requesting annotator to have committed
  4. Gold is immutable once written
  5. Drafts can be modified before commit but not after

If any of these tests fail or are bypassed, the IAA measurement is
not valid.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iaa_pipeline.workspace import (
    Phase,
    PhaseAccessError,
    Workspace,
    STAGE_MODES,
)


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def ws(tmp_path):
    """Fresh workspace for each test."""
    return Workspace(tmp_path / "iaa_ws")


@pytest.fixture
def stage1(ws):
    """A Stage 1 workspace for a fictional trial."""
    sw = ws.stage("NCT99999999", 1)
    # Populate input.json
    sw._stage_dir.mkdir(parents=True, exist_ok=True)
    sw._input_path.write_text(json.dumps({
        "trial_id": "NCT99999999",
        "criteria": [
            {"criterion_id": "NCT99999999_I1", "type": "inclusion", "text": "Adult patients."},
            {"criterion_id": "NCT99999999_I2", "type": "inclusion", "text": "ECOG ≤ 1."},
        ],
    }), encoding="utf-8")
    # Populate llm_output.json
    sw._llm_path.write_text(json.dumps({
        "trial_id": "NCT99999999",
        "stage": 1,
        "source": "llm",
        "model": "test-model",
        "created_at": "2026-01-01T00:00:00Z",
        "records": [
            {"criterion_id": "NCT99999999_I1", "splitting_decision": "none", "sub_criteria": []},
            {"criterion_id": "NCT99999999_I2", "splitting_decision": "none", "sub_criteria": []},
        ],
    }), encoding="utf-8")
    return sw


def make_envelope(*, annotator: str, trial_id: str, stage: int, records: list[dict]) -> dict:
    return {
        "trial_id": trial_id,
        "stage": stage,
        "source": "annotator",
        "annotator": annotator,
        "created_at": "2026-01-02T00:00:00Z",
        "records": records,
    }


# ──────────────────────────────────────────────────────────────────────
# CRITICAL: Phase 1 blinding
# ──────────────────────────────────────────────────────────────────────

class TestPhase1Blinding:
    """The most important test class. If any of these fail, IAA is broken."""

    def test_phase1_blocks_llm_read(self, stage1):
        """Phase 1: annotator cannot read LLM output. Period."""
        with pytest.raises(PhaseAccessError) as exc_info:
            stage1.read_llm_output(
                requesting_annotator="EHJ",
                required_annotators=["EHJ", "DYK"],
            )
        assert "PHASE_1_BLIND" in str(exc_info.value)

    def test_phase1_blocks_other_annotator_read(self, stage1):
        """Phase 1: annotator cannot read another annotator's work."""
        # Setup: DYK has draft (but not committed)
        stage1.write_own_draft(
            "DYK",
            make_envelope(
                annotator="DYK",
                trial_id="NCT99999999",
                stage=1,
                records=[{"criterion_id": "NCT99999999_I1", "splitting_decision": "none",
                          "sub_criteria": []}],
            ),
        )

        # EHJ tries to read DYK's work
        with pytest.raises(PhaseAccessError):
            stage1.read_other_committed(
                requesting_annotator="EHJ",
                other_annotator="DYK",
                required_annotators=["EHJ", "DYK"],
            )

    def test_phase1_blocks_even_after_partial_commit(self, stage1):
        """Phase 1: EHJ committed, DYK hasn't. Neither can see LLM yet."""
        envelope_ehj = make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1,
            records=[{"criterion_id": "NCT99999999_I1",
                      "splitting_decision": "none", "sub_criteria": []}],
        )
        stage1.commit("EHJ", envelope_ehj)

        # EHJ committed, but DYK hasn't → still PHASE_1_BLIND
        assert stage1.current_phase(
            required_annotators=["EHJ", "DYK"]
        ) == Phase.PHASE_1_BLIND

        # Both EHJ and DYK should be blocked from LLM
        with pytest.raises(PhaseAccessError):
            stage1.read_llm_output(
                requesting_annotator="EHJ",
                required_annotators=["EHJ", "DYK"],
            )
        with pytest.raises(PhaseAccessError):
            stage1.read_llm_output(
                requesting_annotator="DYK",
                required_annotators=["EHJ", "DYK"],
            )

    def test_phase1_allows_own_draft_read_write(self, stage1):
        """Phase 1: annotator can freely read/write their own draft."""
        envelope = make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1,
            records=[{"criterion_id": "NCT99999999_I1",
                      "splitting_decision": "composite_split", "sub_criteria": [
                          {"child_id": "a", "text_span": "Adult"}
                      ]}],
        )
        stage1.write_own_draft("EHJ", envelope)
        loaded = stage1.read_own_draft("EHJ")
        assert loaded["records"][0]["splitting_decision"] == "composite_split"

    def test_phase1_allows_input_read(self, stage1):
        """Phase 1: annotator can read the input criteria (the question)."""
        data = stage1.read_input()
        assert data["trial_id"] == "NCT99999999"
        assert len(data["criteria"]) == 2


# ──────────────────────────────────────────────────────────────────────
# Phase transition
# ──────────────────────────────────────────────────────────────────────

class TestPhaseTransition:

    def test_transitions_to_phase2_after_all_commit(self, stage1):
        for ann in ["EHJ", "DYK"]:
            stage1.commit(ann, make_envelope(
                annotator=ann, trial_id="NCT99999999", stage=1,
                records=[{"criterion_id": "NCT99999999_I1",
                          "splitting_decision": "none", "sub_criteria": []}],
            ))
        assert stage1.current_phase(
            required_annotators=["EHJ", "DYK"]
        ) == Phase.PHASE_2_ADJUDICATION

    def test_transitions_to_complete_after_gold(self, stage1):
        for ann in ["EHJ", "DYK"]:
            stage1.commit(ann, make_envelope(
                annotator=ann, trial_id="NCT99999999", stage=1,
                records=[{"criterion_id": "NCT99999999_I1",
                          "splitting_decision": "none", "sub_criteria": []}],
            ))
        stage1.write_gold({
            "trial_id": "NCT99999999",
            "stage": 1,
            "source": "gold",
            "created_at": "2026-01-03T00:00:00Z",
            "records": [{"criterion_id": "NCT99999999_I1", "splitting_decision": "none"}],
        }, adjudicators=["EHJ"])
        assert stage1.current_phase(
            required_annotators=["EHJ", "DYK"]
        ) == Phase.PHASE_COMPLETE


# ──────────────────────────────────────────────────────────────────────
# Phase 2 access
# ──────────────────────────────────────────────────────────────────────

class TestPhase2Access:

    def _commit_both(self, stage1):
        for ann in ["EHJ", "DYK"]:
            stage1.commit(ann, make_envelope(
                annotator=ann, trial_id="NCT99999999", stage=1,
                records=[{"criterion_id": "NCT99999999_I1",
                          "splitting_decision": "none", "sub_criteria": []}],
            ))

    def test_phase2_allows_llm_read_for_committed(self, stage1):
        self._commit_both(stage1)
        llm = stage1.read_llm_output(
            requesting_annotator="EHJ",
            required_annotators=["EHJ", "DYK"],
        )
        assert llm is not None
        assert llm["source"] == "llm"

    def test_phase2_allows_other_annotator_read(self, stage1):
        self._commit_both(stage1)
        other = stage1.read_other_committed(
            requesting_annotator="EHJ",
            other_annotator="DYK",
            required_annotators=["EHJ", "DYK"],
        )
        assert other is not None
        assert other["annotator"] == "DYK"

    def test_phase2_blocks_third_party_who_didnt_commit(self, stage1):
        """Edge case: third annotator (CKW) who didn't commit can't see anything."""
        self._commit_both(stage1)
        # CKW didn't commit but tries to access
        with pytest.raises(PhaseAccessError):
            stage1.read_llm_output(
                requesting_annotator="CKW",
                required_annotators=["EHJ", "DYK"],
            )


# ──────────────────────────────────────────────────────────────────────
# Commit immutability
# ──────────────────────────────────────────────────────────────────────

class TestCommitImmutability:

    def test_cannot_commit_twice(self, stage1):
        env = make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1,
            records=[{"criterion_id": "NCT99999999_I1",
                      "splitting_decision": "none", "sub_criteria": []}],
        )
        stage1.commit("EHJ", env)
        with pytest.raises(PhaseAccessError, match="already committed"):
            stage1.commit("EHJ", env)

    def test_cannot_modify_draft_after_commit(self, stage1):
        env = make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1,
            records=[{"criterion_id": "NCT99999999_I1",
                      "splitting_decision": "none", "sub_criteria": []}],
        )
        stage1.commit("EHJ", env)
        with pytest.raises(PhaseAccessError, match="already committed"):
            stage1.write_own_draft("EHJ", env)

    def test_commit_validates_annotator_match(self, stage1):
        """Cannot commit envelope claiming to be from different annotator."""
        env_dyk = make_envelope(
            annotator="DYK", trial_id="NCT99999999", stage=1,
            records=[],
        )
        with pytest.raises(ValueError, match="does not match"):
            stage1.commit("EHJ", env_dyk)


# ──────────────────────────────────────────────────────────────────────
# Gold immutability
# ──────────────────────────────────────────────────────────────────────

class TestGoldImmutability:

    def test_gold_cannot_be_overwritten(self, stage1):
        gold = {
            "trial_id": "NCT99999999", "stage": 1, "source": "gold",
            "created_at": "2026-01-03T00:00:00Z", "records": [],
        }
        stage1.write_gold(gold, adjudicators=["EHJ"])
        with pytest.raises(PhaseAccessError, match="immutable"):
            stage1.write_gold(gold, adjudicators=["EHJ"])


# ──────────────────────────────────────────────────────────────────────
# File isolation
# ──────────────────────────────────────────────────────────────────────

class TestFileIsolation:
    """Verify that annotators' files are physically isolated in subdirectories.

    This is defense-in-depth: even if the access-control code were
    bypassed, an annotator's file system tools (find, grep, ls) would
    not show them another annotator's work without specifically asking.
    """

    def test_annotator_dirs_are_separate(self, stage1):
        stage1.write_own_draft("EHJ", make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1, records=[],
        ))
        stage1.write_own_draft("DYK", make_envelope(
            annotator="DYK", trial_id="NCT99999999", stage=1, records=[],
        ))
        ehj_dir = stage1._annotator_dir("EHJ")
        dyk_dir = stage1._annotator_dir("DYK")
        assert ehj_dir != dyk_dir
        assert ehj_dir.exists()
        assert dyk_dir.exists()
        # EHJ's draft should not be in DYK's dir, and vice versa
        assert (ehj_dir / "draft.json").exists()
        assert not (ehj_dir / "DYK.json").exists()


# ──────────────────────────────────────────────────────────────────────
# Stage modes
# ──────────────────────────────────────────────────────────────────────

class TestStageModes:

    def test_stage_modes_match_spec(self):
        """Stages 1, 2 are from_scratch; 3, 4, 5 are llm_assisted."""
        assert STAGE_MODES[1] == "from_scratch"
        assert STAGE_MODES[2] == "from_scratch"
        assert STAGE_MODES[3] == "llm_assisted"
        assert STAGE_MODES[4] == "llm_assisted"
        assert STAGE_MODES[5] == "llm_assisted"


# ──────────────────────────────────────────────────────────────────────
# Reproduction tests for the original streamlit_app.py bugs
# ──────────────────────────────────────────────────────────────────────

class TestOriginalBugsAreFixed:
    """These tests document the original bugs that motivated this refactor.

    Each test corresponds to a 'reproducibility test' from the audit:
    they describe a concrete annotator action that would have leaked
    LLM data in the original code, and verify it no longer succeeds.
    """

    def test_bug1_llm_cannot_seed_form_defaults(self, stage1):
        """Original bug: LLM output was used as form default values.

        Reproduction: An annotator opens the Stage 1 form. The original
        code looked up LLM output via `seed = existing_record or llm_record`.
        With this design, asking the workspace for LLM output raises.
        """
        with pytest.raises(PhaseAccessError):
            stage1.read_llm_output(
                requesting_annotator="EHJ",
                required_annotators=["EHJ", "DYK"],
            )

    def test_bug2_other_annotator_files_are_not_listable_in_open_dir(self, stage1):
        """Original bug: sidebar listed all annotator_*.json files.

        With per-annotator subdirectories, a `glob('annotator_*.json')`
        in the stage dir returns nothing — the files are at
        annotator/{id}/draft.json instead.
        """
        stage1.write_own_draft("EHJ", make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1, records=[],
        ))
        stage1.write_own_draft("DYK", make_envelope(
            annotator="DYK", trial_id="NCT99999999", stage=1, records=[],
        ))
        # Old code did: stage_dir.glob('annotator_*.json')
        # New layout: files are inside annotator/{id}/, not at stage_dir top level
        top_level_matches = list(stage1._stage_dir.glob("annotator_*.json"))
        assert top_level_matches == []

    def test_bug3_phase_does_not_advance_on_identity_switch(self, stage1):
        """Original bug: changing the annotator ID text field exposed
        another annotator's work.

        New design: phase is determined by commit markers, not by who's
        currently typing in the UI. Switching IDs doesn't change phase.
        """
        stage1.commit("EHJ", make_envelope(
            annotator="EHJ", trial_id="NCT99999999", stage=1,
            records=[{"criterion_id": "NCT99999999_I1",
                      "splitting_decision": "none", "sub_criteria": []}],
        ))
        # Even if "DYK" is typed in the UI, current_phase is still PHASE_1
        # because DYK has not committed.
        assert stage1.current_phase(
            required_annotators=["EHJ", "DYK"]
        ) == Phase.PHASE_1_BLIND
        # And LLM is still blocked for "DYK"
        with pytest.raises(PhaseAccessError):
            stage1.read_llm_output(
                requesting_annotator="DYK",
                required_annotators=["EHJ", "DYK"],
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
