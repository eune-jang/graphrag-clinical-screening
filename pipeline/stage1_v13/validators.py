"""Strict validation for Stage 1 v1.3 output.

Asymmetric by design, and the asymmetry is the compatibility boundary:

    reading historical v1.2.2 records   tolerant  (contracts.read_legacy_stage1_record)
    validating v1.3 output              strict    (this module)

Historical records are never rewritten to satisfy these rules. In particular
the legacy production rule "nested_exception requires >=2 sub_criteria"
(`pipeline/validators.py:59-61`) is **not** applied here: canonical H4 makes
sub_criteria one-or-more exception spans, and that legacy rule would reject 9
of the 10 nested_exception records in the frozen 113-item gold.
"""
from __future__ import annotations

from .contracts import (
    CHILD_LOGIC_VALUES,
    MAIN_TARGET,
    NO_LOGIC_DECISIONS,
    RULE_IDS,
    SPLITTING_DECISIONS,
    SPLIT_DECISIONS,
)
from .context import Stage1Context


class Stage1V13ValidationError(ValueError):
    """A v1.3 pass produced output that violates the canonical contract."""

    def __init__(self, errors: list[str], node_id: str = "root"):
        self.errors = errors
        self.node_id = node_id
        super().__init__(f"[{node_id}] v1.3 출력 검증 실패 ({len(errors)}건):\n  - " + "\n  - ".join(errors))


# ──────────────────────────────────────────────────────────────────────
# X1 — text-span fidelity (hard failure)
# ──────────────────────────────────────────────────────────────────────

def _validate_spans(output: dict, ctx: Stage1Context) -> list[str]:
    """Every segment must be a verbatim contiguous substring of ONE TARGET_SEGMENT.

    The error messages separate the three ways a span can be sourced wrongly,
    because "not in TARGET_SEGMENTS" alone does not tell a prompt developer
    whether the model paraphrased, reached into the root, or copied a sibling.
    """
    errors: list[str] = []
    targets = ctx.target_segments
    root = ctx.root_criterion_text
    sibling_text: list[str] = []
    if ctx.parent_context:
        for spans in (ctx.parent_context.get("sibling_spans") or {}).values():
            sibling_text.extend(spans)

    for sub in output.get("sub_criteria") or []:
        cid = sub.get("child_id", "?")
        spans = sub.get("text_span")

        if not isinstance(spans, list):
            errors.append(f"sub_criteria[{cid}].text_span은 배열이어야 합니다 (X1)")
            continue
        if not spans:
            errors.append(f"sub_criteria[{cid}].text_span이 비어 있습니다 (X1)")
            continue

        for seg in spans:
            if not isinstance(seg, str):
                errors.append(f"sub_criteria[{cid}].text_span 세그먼트가 문자열이 아닙니다: {seg!r} (X1)")
                continue
            if not seg.strip():
                errors.append(f"sub_criteria[{cid}].text_span에 빈 세그먼트가 있습니다 (X1)")
                continue
            if any(seg in t for t in targets):
                continue

            if any(seg in s for s in sibling_text):
                errors.append(
                    f"sub_criteria[{cid}]: sibling_spans에서 가져온 텍스트를 출력 span으로 사용했습니다 "
                    f"— PARENT_CONTEXT는 해석용이며 복사 대상이 아닙니다 (X1/X2): {seg!r}"
                )
            elif seg in root:
                errors.append(
                    f"sub_criteria[{cid}]: ROOT_CRITERION_TEXT에는 있으나 현재 TARGET_SEGMENTS 밖의 "
                    f"텍스트입니다 — 재귀 패스가 형제 내용을 다시 가져올 수 없습니다 (X1): {seg!r}"
                )
            else:
                errors.append(
                    f"sub_criteria[{cid}]: 원문에 없는 합성/정규화된 span입니다 (X1): {seg!r}"
                )
    return errors


# ──────────────────────────────────────────────────────────────────────
# H4 / H5 / H6 — structure, child logic, recursion
# ──────────────────────────────────────────────────────────────────────

def _validate_structure(output: dict) -> list[str]:
    errors: list[str] = []

    decision = output.get("splitting_decision")
    if decision not in SPLITTING_DECISIONS:
        errors.append(
            f"splitting_decision이 유효하지 않습니다: {decision!r} "
            f"({sorted(SPLITTING_DECISIONS)} 중 하나) (H4)"
        )
        return errors  # 나머지 규칙은 결정에 의존하므로 여기서 중단

    subs = output.get("sub_criteria")
    if not isinstance(subs, list):
        errors.append("sub_criteria는 배열이어야 합니다 (H4)")
        subs = []

    child_logic = output.get("child_logic")
    needs_recursion = output.get("needs_recursion")
    targets = output.get("recursion_targets")

    if not isinstance(needs_recursion, bool):
        errors.append(f"needs_recursion은 boolean이어야 합니다: {needs_recursion!r} (H6)")
    if not isinstance(targets, list):
        errors.append(f"recursion_targets는 배열이어야 합니다: {targets!r} (H6)")
        targets = []

    child_ids = [s.get("child_id") for s in subs if isinstance(s, dict)]
    dupes = sorted({c for c in child_ids if child_ids.count(c) > 1})
    if dupes:
        errors.append(f"child_id가 중복되었습니다: {', '.join(map(str, dupes))} (H4)")
    if any(not c for c in child_ids):
        errors.append("child_id가 비어 있는 sub_criteria가 있습니다 (H4)")

    if decision == "none":
        if child_logic is not None:
            errors.append(f"none에는 child_logic을 부여하지 않습니다: {child_logic!r} (H5)")
        if subs:
            errors.append(f"none에는 sub_criteria가 없어야 합니다 ({len(subs)}건) (H4)")
        if needs_recursion is True:
            errors.append("none은 needs_recursion=false여야 합니다 (H6)")
        if targets:
            errors.append(f"none은 recursion_targets가 비어야 합니다: {targets} (H6)")

    elif decision in SPLIT_DECISIONS:
        if child_logic not in CHILD_LOGIC_VALUES:
            errors.append(
                f"{decision}에는 child_logic이 필수입니다 "
                f"({sorted(CHILD_LOGIC_VALUES)} 중 하나, 현재 {child_logic!r}) (H5)"
            )
        if len(subs) < 2:
            errors.append(f"{decision}에는 자식이 2개 이상 필요합니다 ({len(subs)}건) (H4)")
        unknown = [t for t in targets if t not in child_ids]
        if unknown:
            errors.append(
                f"recursion_targets에 존재하지 않는 child_id가 있습니다: {unknown} (H6)"
            )
        if MAIN_TARGET in targets:
            errors.append(f'{decision}에는 recursion_targets="{MAIN_TARGET}"을 쓰지 않습니다 (H6)')

    elif decision == "nested_exception":
        if child_logic is not None:
            errors.append(f"nested_exception에는 child_logic을 부여하지 않습니다: {child_logic!r} (H5)")
        # canonical H4: exception span 1개도 유효. legacy의 >=2 규칙은 쓰지 않는다.
        if len(subs) < 1:
            errors.append("nested_exception에는 exception span이 최소 1개 필요합니다 (H4/X3)")
        if not set(targets) <= {MAIN_TARGET}:
            errors.append(
                f'nested_exception의 recursion_targets는 [] 또는 ["{MAIN_TARGET}"]만 허용됩니다: '
                f"{targets} — exception span은 재귀하지 않습니다 (H6/X3)"
            )

    if isinstance(needs_recursion, bool):
        if needs_recursion and not targets:
            errors.append("needs_recursion=true인데 recursion_targets가 비어 있습니다 (H6)")
        if not needs_recursion and targets:
            errors.append(f"needs_recursion=false인데 recursion_targets가 있습니다: {targets} (H6)")

    return errors


# ──────────────────────────────────────────────────────────────────────
# X4 — cohort scope
# ──────────────────────────────────────────────────────────────────────

def _validate_cohort_scope(output: dict, ctx: Stage1Context) -> list[str]:
    errors: list[str] = []
    decision = output.get("splitting_decision")

    allowed: set[str] | None = None
    if ctx.trial_has_cohorts:
        allowed = set()
        for c in ctx.trial_has_cohorts:
            allowed.add(c if isinstance(c, str) else str(c.get("label") or c.get("name") or c))

    def check(scope, where: str) -> None:
        if scope is None:
            return
        if not isinstance(scope, list):
            errors.append(f"{where}.cohort_scope는 배열 또는 null이어야 합니다: {type(scope).__name__} (X4)")
            return
        if allowed is not None:
            unknown = [s for s in scope if s not in allowed]
            if unknown:
                errors.append(
                    f"{where}.cohort_scope에 TRIAL_HAS_COHORTS에 없는 라벨이 있습니다: {unknown} "
                    f"— 라벨은 축자 복사해야 합니다 (X4)"
                )

    top = output.get("cohort_scope")
    check(top, "top-level")
    if decision in SPLIT_DECISIONS and top is not None:
        errors.append(
            f"{decision}의 top-level cohort_scope는 null이어야 합니다 — "
            f"scope는 해당 자식에 부여합니다: {top} (X4)"
        )
    for sub in output.get("sub_criteria") or []:
        check(sub.get("cohort_scope"), f"sub_criteria[{sub.get('child_id', '?')}]")
    return errors


# ──────────────────────────────────────────────────────────────────────
# Provenance
# ──────────────────────────────────────────────────────────────────────

def _validate_provenance(output: dict) -> list[str]:
    errors: list[str] = []

    primary = output.get("primary_rule_id")
    if not isinstance(primary, str) or not primary.strip():
        errors.append(f"primary_rule_id는 필수입니다: {primary!r}")
    elif primary not in RULE_IDS:
        errors.append(f"primary_rule_id가 canonical 규칙 ID가 아닙니다: {primary!r} ({sorted(RULE_IDS)})")

    supporting = output.get("supporting_rule_ids", [])
    if supporting is None:
        supporting = []
    if not isinstance(supporting, list):
        errors.append(f"supporting_rule_ids는 배열이어야 합니다: {supporting!r}")
    else:
        bad = [s for s in supporting if not isinstance(s, str) or s not in RULE_IDS]
        if bad:
            errors.append(f"supporting_rule_ids에 유효하지 않은 규칙 ID가 있습니다: {bad}")
        if isinstance(primary, str) and primary in supporting:
            errors.append(
                f"primary_rule_id({primary})가 supporting_rule_ids에도 있습니다 — "
                f"결정 규칙은 정확히 하나입니다"
            )
    return errors


# ──────────────────────────────────────────────────────────────────────

def validate_v13_output(output: dict, ctx: Stage1Context) -> list[str]:
    """Every canonical check for one pass. Returns the error list (empty = valid)."""
    if not isinstance(output, dict):
        return [f"출력이 JSON 객체가 아닙니다: {type(output).__name__}"]
    return (
        _validate_structure(output)
        + _validate_spans(output, ctx)
        + _validate_cohort_scope(output, ctx)
        + _validate_provenance(output)
    )


def assert_valid_v13_output(output: dict, ctx: Stage1Context) -> None:
    """Hard failure form. v1.3 execution must not proceed on invalid output."""
    errors = validate_v13_output(output, ctx)
    if errors:
        raise Stage1V13ValidationError(errors, node_id=ctx.node_id)
