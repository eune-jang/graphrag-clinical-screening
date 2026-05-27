"""Workspace data access layer with phase-aware access control.

This module is the ONLY place that reads or writes annotation files. Any
UI code must go through these functions. The functions are deliberately
designed so that you CANNOT accidentally load LLM output during Phase 1
or another annotator's work at any phase — the access is blocked at the
data layer, not at the UI layer.

Workspace layout:

  {workspace_root}/
    {trial_id}/
      stage{N}/
        input.json                       (criterion text — always readable)
        llm_output.json                  (LLM annotation — locked in Phase 1)
        annotator/{annotator_id}/
          draft.json                     (annotator's in-progress work)
          committed.json                 (after annotator clicks "commit")
          .committed_at                  (timestamp marker file)
        gold.json                        (Phase 2 output)
        phase_log.jsonl                  (state transitions, append-only)

Phase invariants:

  - PHASE_1_BLIND: annotator works alone. CANNOT read llm_output.json or
    any other annotator's files. CAN read/write their own draft.
  - PHASE_2_ADJUDICATION: only enters AFTER all required annotators have
    committed. CAN read everyone's committed.json + llm_output.json.
  - PHASE_COMPLETE: gold.json exists. Everything is read-only.

The phase is determined by file-system state, not by a user-selected
toggle. This is intentional: you can't accidentally drop into Phase 2.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal


# ──────────────────────────────────────────────────────────────────────
# Phase enum — the state machine
# ──────────────────────────────────────────────────────────────────────

class Phase(str, Enum):
    """The phase of a single (trial, stage) workspace.

    Phase transitions are one-way:
        PHASE_1_BLIND → PHASE_2_ADJUDICATION → PHASE_COMPLETE

    PHASE_1_BLIND ends when ALL required annotators have committed.
    PHASE_2_ADJUDICATION ends when gold.json is written.
    """
    PHASE_1_BLIND = "phase_1_blind"
    PHASE_2_ADJUDICATION = "phase_2_adjudication"
    PHASE_COMPLETE = "phase_complete"


# Mode names match Phase names but are the responsibility of the calling
# context. We use them to choose UI rendering paths.
AnnotationMode = Literal["from_scratch", "llm_assisted"]


STAGE_MODES: dict[int, AnnotationMode] = {
    1: "from_scratch",
    2: "from_scratch",
    3: "llm_assisted",
    4: "llm_assisted",
    5: "llm_assisted",
}


# ──────────────────────────────────────────────────────────────────────
# Workspace handle
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StageWorkspace:
    """A handle to one (trial_id, stage_number) workspace.

    Construct via Workspace.stage(trial_id, stage). Do not call the
    private methods directly — use the public methods that enforce
    phase invariants.
    """
    root: Path
    trial_id: str
    stage: int

    # ── Path helpers (private) ───────────────────────────────────────

    @property
    def _stage_dir(self) -> Path:
        return self.root / self.trial_id / f"stage{self.stage}"

    @property
    def _input_path(self) -> Path:
        return self._stage_dir / "input.json"

    @property
    def _llm_path(self) -> Path:
        return self._stage_dir / "llm_output.json"

    @property
    def _gold_path(self) -> Path:
        return self._stage_dir / "gold.json"

    @property
    def _phase_log_path(self) -> Path:
        return self._stage_dir / "phase_log.jsonl"

    def _annotator_dir(self, annotator: str) -> Path:
        safe = _safe_id(annotator)
        return self._stage_dir / "annotator" / safe

    def _draft_path(self, annotator: str) -> Path:
        return self._annotator_dir(annotator) / "draft.json"

    def _committed_path(self, annotator: str) -> Path:
        return self._annotator_dir(annotator) / "committed.json"

    def _commit_marker_path(self, annotator: str) -> Path:
        return self._annotator_dir(annotator) / ".committed_at"

    # ── Phase detection ──────────────────────────────────────────────

    def current_phase(self, *, required_annotators: list[str]) -> Phase:
        """Determine the current phase from filesystem state.

        - PHASE_COMPLETE if gold.json exists
        - PHASE_2_ADJUDICATION if all required annotators have committed
          AND gold.json does not yet exist
        - PHASE_1_BLIND otherwise
        """
        if self._gold_path.exists():
            return Phase.PHASE_COMPLETE
        if all(self._commit_marker_path(a).exists() for a in required_annotators):
            return Phase.PHASE_2_ADJUDICATION
        return Phase.PHASE_1_BLIND

    def has_annotator_committed(self, annotator: str) -> bool:
        return self._commit_marker_path(annotator).exists()

    # ── Public reads — Phase-aware access control ────────────────────

    def read_input(self) -> dict:
        """Read criterion text input. Always allowed at every phase."""
        if not self._input_path.exists():
            raise FileNotFoundError(
                f"No input.json for {self.trial_id} stage {self.stage}. "
                "Pipeline must run criterion extraction first."
            )
        return json.loads(self._input_path.read_text(encoding="utf-8"))

    def read_own_draft(self, annotator: str) -> dict | None:
        """Read this annotator's in-progress draft. Always allowed for self."""
        p = self._draft_path(annotator)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def read_own_committed(self, annotator: str) -> dict | None:
        """Read this annotator's committed envelope. Always allowed for self."""
        p = self._committed_path(annotator)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def read_llm_output(
        self,
        *,
        requesting_annotator: str,
        required_annotators: list[str],
    ) -> dict | None:
        """Read LLM output. BLOCKED during Phase 1.

        This is the critical access-control function. In Phase 1, no
        annotator can read LLM output, regardless of UI requests.

        Phase 2 access is allowed for any annotator who has committed.
        Phase Complete: anyone can read (read-only mode).

        Raises:
            PhaseAccessError if called during Phase 1.
        """
        phase = self.current_phase(required_annotators=required_annotators)

        if phase == Phase.PHASE_1_BLIND:
            raise PhaseAccessError(
                f"LLM output is not accessible during PHASE_1_BLIND. "
                f"Annotator '{requesting_annotator}' attempted access. "
                f"Phase 2 begins when all required annotators "
                f"({required_annotators}) have committed."
            )

        if phase == Phase.PHASE_2_ADJUDICATION:
            if not self.has_annotator_committed(requesting_annotator):
                raise PhaseAccessError(
                    f"Annotator '{requesting_annotator}' has not committed yet. "
                    "LLM output reveals only after own commit."
                )

        if not self._llm_path.exists():
            return None
        return json.loads(self._llm_path.read_text(encoding="utf-8"))

    def read_other_committed(
        self,
        *,
        requesting_annotator: str,
        other_annotator: str,
        required_annotators: list[str],
    ) -> dict | None:
        """Read another annotator's committed work. BLOCKED in Phase 1.

        Same access-control logic as read_llm_output. The requesting
        annotator must have committed before they can see anyone else's.
        """
        if requesting_annotator == other_annotator:
            # This is a misuse — read your own committed via read_own_committed
            return self.read_own_committed(requesting_annotator)

        phase = self.current_phase(required_annotators=required_annotators)
        if phase == Phase.PHASE_1_BLIND:
            raise PhaseAccessError(
                f"Other annotators' work is not accessible during PHASE_1_BLIND. "
                f"'{requesting_annotator}' attempted to read '{other_annotator}'."
            )
        if not self.has_annotator_committed(requesting_annotator):
            raise PhaseAccessError(
                f"'{requesting_annotator}' has not committed yet. "
                "Other annotators' work reveals only after own commit."
            )

        p = self._committed_path(other_annotator)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def read_gold(self) -> dict | None:
        """Read gold envelope. Available in PHASE_COMPLETE only."""
        if not self._gold_path.exists():
            return None
        return json.loads(self._gold_path.read_text(encoding="utf-8"))

    # ── Public writes ────────────────────────────────────────────────

    def write_own_draft(self, annotator: str, envelope: dict) -> None:
        """Save draft progress. Only allowed during Phase 1."""
        # We allow drafts during Phase 1; once committed, no more drafts.
        if self.has_annotator_committed(annotator):
            raise PhaseAccessError(
                f"'{annotator}' has already committed. Cannot modify draft."
            )
        self._annotator_dir(annotator).mkdir(parents=True, exist_ok=True)
        self._draft_path(annotator).write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._append_log({
            "event": "draft_saved",
            "annotator": annotator,
            "n_records": len(envelope.get("records", [])),
        })

    def commit(self, annotator: str, envelope: dict) -> None:
        """Commit annotator's work. Locks the envelope. One-way operation.

        After commit:
          - draft.json is left for posterity
          - committed.json is written
          - .committed_at marker file is created
          - annotator can NO LONGER modify their work
          - annotator still cannot see LLM or other annotators until
            all required annotators have committed (auto-transitions
            to PHASE_2_ADJUDICATION)
        """
        if self.has_annotator_committed(annotator):
            raise PhaseAccessError(f"'{annotator}' has already committed.")

        # Sanity: envelope should look like a real annotation
        if envelope.get("source") != "annotator":
            raise ValueError("Envelope must have source='annotator' to commit.")
        if envelope.get("annotator") != annotator:
            raise ValueError(
                f"Envelope annotator field ({envelope.get('annotator')!r}) "
                f"does not match committing annotator ({annotator!r})."
            )

        self._annotator_dir(annotator).mkdir(parents=True, exist_ok=True)
        committed_envelope = {
            **envelope,
            "_committed_at": _utc_now_iso(),
        }
        self._committed_path(annotator).write_text(
            json.dumps(committed_envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._commit_marker_path(annotator).write_text(
            _utc_now_iso(), encoding="utf-8"
        )
        self._append_log({
            "event": "annotator_committed",
            "annotator": annotator,
            "n_records": len(envelope.get("records", [])),
        })

    def write_gold(self, envelope: dict, *, adjudicators: list[str]) -> None:
        """Write gold envelope. Only allowed during PHASE_2_ADJUDICATION."""
        if self._gold_path.exists():
            raise PhaseAccessError("Gold already written. Gold is immutable.")
        if envelope.get("source") != "gold":
            raise ValueError("Gold envelope must have source='gold'.")
        self._gold_path.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._append_log({
            "event": "gold_written",
            "adjudicators": adjudicators,
            "n_records": len(envelope.get("records", [])),
        })

    # ── Append-only audit log ────────────────────────────────────────

    def _append_log(self, entry: dict) -> None:
        self._stage_dir.mkdir(parents=True, exist_ok=True)
        entry = {**entry, "ts": _utc_now_iso()}
        with self._phase_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_phase_log(self) -> list[dict]:
        if not self._phase_log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._phase_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


# ──────────────────────────────────────────────────────────────────────
# Top-level Workspace
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Workspace:
    """A workspace root directory containing multiple trials.

    Usage:
        ws = Workspace(Path("/path/to/iaa_workspace"))
        stage1 = ws.stage("NCT03425643", 1)
        criteria = stage1.read_input()
    """
    root: Path

    def stage(self, trial_id: str, stage: int) -> StageWorkspace:
        if stage not in (1, 2, 3, 4, 5):
            raise ValueError(f"stage must be 1-5, got {stage}")
        return StageWorkspace(root=self.root, trial_id=trial_id, stage=stage)

    def list_trials(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            d.name for d in self.root.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )


# ──────────────────────────────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────────────────────────────

class PhaseAccessError(Exception):
    """Raised when code attempts to access data outside its allowed phase."""


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _safe_id(s: str) -> str:
    """Sanitize an identifier for use as a directory name."""
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
    return cleaned.strip("_") or "unknown"


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
