#!/usr/bin/env python3
"""Recursive Stage 1 v1.3 **development** runner.

One LLM call annotates exactly one hierarchy level (canonical H6). The runner
owns everything around that call: building the next level's TARGET_SEGMENTS,
deriving the main content of a nested exception, validating hard, and stopping.

    root
      └─ pass ── validate ── needs_recursion? ── for each recursion target:
                                                   build child context
                                                   pass again

Explicitly NOT production:

- the prompt is loaded by absolute path from
  `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt`;
- `pipeline/prompts/prompt_1_splitting.txt` and the production filename map in
  `llm_client` are untouched, so nothing reaches this path by default;
- `examples.json` is never injected — the v1.3.1 prompt carries its own
  synthetic examples, and the historical 113 items must stay out of few-shot.

Usage
    python -m pipeline.stage1_v13.runner --text "..." --type inclusion --dry-run
    python -m pipeline.stage1_v13.runner --input dev_input.json --out out.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Protocol

from pipeline.config import MAX_RETRIES, MODELS, PIPELINE_DIR
from pipeline.llm_client import _call_provider, _parse_json_response, _substitute_template

from .contracts import MAIN_TARGET, Stage1V13Node, V13Output, derive_tier
from .context import Stage1Context, child_context, main_context, root_context
from .validators import Stage1V13ValidationError, validate_v13_output

logger = logging.getLogger(__name__)

DEV_PROMPT_PATH = PIPELINE_DIR / "prompts" / "development" / "stage1" / "stage1_prompt_v1_3_1.txt"

#: Depth ceiling. Canonical recursion terminates when a level is `none`, but a
#: malformed response could keep asking for another pass, so the runner refuses
#: to recurse forever regardless of what the model says.
DEFAULT_MAX_DEPTH = 5

#: Paths a development run must never write into.
_PROTECTED_PREFIXES = ("iaa_workspace", "evidence", "STAGE1_GOLD_", "AMIA_2027_")


class Stage1V13Error(RuntimeError):
    """The v1.3 development runner could not produce a valid hierarchy."""


class _Cache(Protocol):
    """Duck-typed subset of `iaa_pipeline.cache.LLMCache`.

    Typed structurally rather than imported so `pipeline/` keeps not depending
    on `iaa_pipeline/`; the CLI wires the real cache in when asked.
    """

    def get(self, prompt_template: str, input_payload: dict, model: str) -> Any | None: ...
    def put(self, prompt_template: str, input_payload: dict, model: str, response: Any) -> None: ...


#: (prompt_text, model) -> raw response text. Injected in tests so the whole
#: recursion, validation and main-derivation path runs with zero API spend.
LLMFn = Callable[[str, str], str]


def load_dev_prompt(path: Path | None = None) -> str:
    """Read the v1.3.1 development prompt by explicit path."""
    p = path or DEV_PROMPT_PATH
    if not p.exists():
        raise Stage1V13Error(f"v1.3 개발 프롬프트를 찾지 못했습니다: {p}")
    return p.read_text(encoding="utf-8")


def render_prompt(ctx: Stage1Context, template: str) -> str:
    """Substitute the six v1.3 placeholders. No examples.json injection."""
    return _substitute_template(template, ctx.to_prompt_variables())


# ──────────────────────────────────────────────────────────────────────
# One pass
# ──────────────────────────────────────────────────────────────────────

def run_pass(
    ctx: Stage1Context,
    *,
    llm: LLMFn,
    model: str,
    template: str,
    cache: _Cache | None = None,
    max_retries: int = MAX_RETRIES,
) -> V13Output:
    """One hierarchy level: render → call → parse → validate (hard).

    Retries on validation failure because a malformed pass is usually a
    formatting slip, but the loop never relaxes a rule to make output pass.
    """
    prompt_text = render_prompt(ctx, template)
    payload = ctx.cache_payload()

    if cache is not None:
        cached = cache.get(template, payload, model)
        if cached is not None:
            errors = validate_v13_output(cached, ctx)
            if not errors:
                logger.debug("[%s] cache hit", ctx.node_id)
                return cached
            logger.warning("[%s] 캐시된 응답이 검증에 실패해 무시합니다: %s", ctx.node_id, errors[:2])

    last_errors: list[str] = []
    for attempt in range(1 + max_retries):
        raw = llm(prompt_text, model)
        try:
            parsed = _parse_json_response(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            last_errors = [f"JSON 파싱 실패: {exc}"]
            logger.warning("[%s] attempt %d: %s", ctx.node_id, attempt + 1, last_errors[0])
            continue

        errors = validate_v13_output(parsed, ctx)
        if not errors:
            if cache is not None:
                cache.put(template, payload, model, parsed)
            return parsed

        last_errors = errors
        logger.warning(
            "[%s] attempt %d: 검증 실패 %d건 — %s",
            ctx.node_id, attempt + 1, len(errors), errors[0],
        )

    raise Stage1V13ValidationError(last_errors, node_id=ctx.node_id)


# ──────────────────────────────────────────────────────────────────────
# Recursion
# ──────────────────────────────────────────────────────────────────────

def run_stage1_v13(
    ctx: Stage1Context,
    *,
    llm: LLMFn | None = None,
    model: str | None = None,
    template: str | None = None,
    cache: _Cache | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Stage1V13Node:
    """Run one pass and every pass it legitimately asks for.

    Recursion rules, all from canonical H6:

    - `composite_split` / `macro_aggregate` → recurse the child IDs named in
      `recursion_targets`, each seeing only its own spans as TARGET_SEGMENTS;
    - `nested_exception` with `["main"]` → recurse the derived remainder;
      **exception spans never recurse**, and there is no code path that would;
    - `none`, or `needs_recursion=false` → stop.

    A depth-limited stop is recorded in the node's `recursion_note` rather than
    raised, so a development run still returns the hierarchy it did build.
    """
    llm = llm or _default_llm
    model = model or MODELS["prompt_1"]
    template = template if template is not None else load_dev_prompt()

    output = run_pass(ctx, llm=llm, model=model, template=template, cache=cache)
    node = Stage1V13Node(
        node_id=ctx.node_id,
        depth=ctx.depth,
        target_segments=list(ctx.target_segments),
        output=output,
        parent_context=ctx.parent_context,
    )

    if not output.get("needs_recursion"):
        return node

    targets = output.get("recursion_targets") or []
    if ctx.depth + 1 > max_depth:
        node.output = {
            **output,
            "recursion_note": (
                f"{output.get('recursion_note', '')} "
                f"[runner: max_depth={max_depth} 도달, 재귀 중단]"
            ).strip(),
        }
        logger.warning("[%s] max_depth=%d 도달 — 재귀 중단", ctx.node_id, max_depth)
        return node

    decision = output.get("splitting_decision")

    if decision == "nested_exception":
        if MAIN_TARGET not in targets:
            return node
        sub_ctx = main_context(ctx, output)
        if sub_ctx is None:
            node.output = {
                **output,
                "recursion_note": (
                    f"{output.get('recursion_note', '')} "
                    "[runner: exception span 제거 후 남은 main 내용이 없어 재귀 중단]"
                ).strip(),
            }
            logger.info("[%s] main 내용이 비어 재귀하지 않습니다", ctx.node_id)
            return node
        node.children[MAIN_TARGET] = run_stage1_v13(
            sub_ctx, llm=llm, model=model, template=template, cache=cache, max_depth=max_depth,
        )
        return node

    for child_id in targets:
        sub_ctx = child_context(ctx, output, child_id)
        node.children[child_id] = run_stage1_v13(
            sub_ctx, llm=llm, model=model, template=template, cache=cache, max_depth=max_depth,
        )
    return node


def _default_llm(prompt_text: str, model: str) -> str:
    """Real provider call, routed by model name in `pipeline.llm_client`."""
    return _call_provider(model, prompt_text)


# ──────────────────────────────────────────────────────────────────────
# Development CLI
# ──────────────────────────────────────────────────────────────────────

def summarize(node: Stage1V13Node) -> str:
    """Indented decision tree — the quickest way to eyeball a dev run."""
    lines = []
    for n in node.walk():
        out = n.output
        logic = f" logic={out.get('child_logic')}" if out.get("child_logic") else ""
        rec = " ↻" + str(out.get("recursion_targets")) if out.get("needs_recursion") else ""
        lines.append(
            f"{'  ' * n.depth}{n.node_id}: {out.get('splitting_decision')}{logic}"
            f" [{out.get('primary_rule_id')} → tier {derive_tier(out.get('primary_rule_id'))}]{rec}"
        )
    return "\n".join(lines)


def _reject_protected(out_path: Path) -> None:
    """A development run must not write into historical or frozen areas."""
    try:
        rel = out_path.resolve().relative_to(PIPELINE_DIR.parent)
    except ValueError:
        return  # outside the repository entirely
    head = rel.parts[0] if rel.parts else ""
    if any(head == p or head.startswith(p) for p in _PROTECTED_PREFIXES):
        raise Stage1V13Error(
            f"개발 실행 결과를 보호된 경로에 쓸 수 없습니다: {rel}\n"
            f"  (historical/frozen: {', '.join(_PROTECTED_PREFIXES)})"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m pipeline.stage1_v13.runner",
        description=(
            "Stage 1 v1.3 DEVELOPMENT runner — canonical core v1.3.0 + "
            "development prompt v1.3.1. Not a production path."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="ROOT_CRITERION_TEXT")
    src.add_argument("--input", type=Path,
                     help='JSON: {"root_criterion_text":..., "criterion_type":..., "trial_has_cohorts":[...]}')
    ap.add_argument("--type", dest="criterion_type", choices=["inclusion", "exclusion"])
    ap.add_argument("--cohorts", nargs="*", default=None, help="TRIAL_HAS_COHORTS 라벨")
    ap.add_argument("--model", default=None, help=f"기본값: config.MODELS['prompt_1'] = {MODELS['prompt_1']}")
    ap.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    ap.add_argument("--cache-dir", type=Path, default=None, help="LLM 응답 캐시 (선택)")
    ap.add_argument("--out", type=Path, default=None, help="결과 JSON 경로 (기본: stdout)")
    ap.add_argument("--dry-run", action="store_true",
                    help="LLM을 호출하지 않고 루트 패스의 렌더된 프롬프트만 출력 (API 비용 0)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    print("Stage 1 v1.3 DEVELOPMENT — not a production run", file=sys.stderr)

    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        text = data["root_criterion_text"]
        criterion_type = data.get("criterion_type") or args.criterion_type
        cohorts = data.get("trial_has_cohorts", args.cohorts)
        criterion_id = data.get("criterion_id")
    else:
        text, criterion_type, cohorts, criterion_id = args.text, args.criterion_type, args.cohorts, None

    ctx = root_context(
        text,
        criterion_type=criterion_type,
        trial_has_cohorts=cohorts,
        criterion_id=criterion_id,
    )
    template = load_dev_prompt()

    if args.dry_run:
        print(f"--- rendered prompt: {ctx.node_id} "
              f"({len(ctx.target_segments)} TARGET_SEGMENTS) ---", file=sys.stderr)
        print(render_prompt(ctx, template))
        print("\n[dry-run] LLM을 호출하지 않았습니다.", file=sys.stderr)
        return 0

    cache = None
    if args.cache_dir:
        from iaa_pipeline.cache import LLMCache  # optional; keeps pipeline/ import-light
        cache = LLMCache(args.cache_dir)

    try:
        node = run_stage1_v13(
            ctx, model=args.model, template=template, cache=cache, max_depth=args.max_depth,
        )
    except (Stage1V13Error, Stage1V13ValidationError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    print(summarize(node), file=sys.stderr)
    payload = json.dumps(node.to_dict(), ensure_ascii=False, indent=2)
    if args.out:
        _reject_protected(args.out)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"→ {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
