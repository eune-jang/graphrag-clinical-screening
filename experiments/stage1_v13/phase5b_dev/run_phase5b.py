#!/usr/bin/env python3
"""Phase 5B runner — P0 baseline and isolated prompt candidates.

Unlike the Phase 5A harness this one uses the runtime's `JsonlTracer`, so every
attempt is recorded including ones that failed and were retried (I-07). Retry
counts come from the trace, never from `calls - nodes`.

Runtime source is untouched: the model call is injected through the `llm=`
extension point, and the caller exposes `last_call_meta` so token usage reaches
the attempt record.

    python run_phase5b.py --stage 5B-0 --dry-run
    python run_phase5b.py --stage 5B-0 --live

Stages
    5B-0   P0    x all cases          shared baseline
    5B-1   P-X2  x X2 subset          candidate, isolated
    5B-2   P-PR  x provenance subset  candidate, isolated
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from pipeline.stage1_v13.context import root_context  # noqa: E402
from pipeline.stage1_v13.contracts import derive_tier  # noqa: E402
from pipeline.stage1_v13.runner import render_prompt, run_stage1_v13  # noqa: E402
from pipeline.stage1_v13.tracing import JsonlTracer, summarize_attempts  # noqa: E402
from pipeline.stage1_v13.validators import Stage1V13ValidationError  # noqa: E402

MODEL = "gpt-5.6-terra"
REQUESTED_REASONING_EFFORT = "medium"
MAX_COMPLETION_TOKENS = 8000

PROMPTS = {
    "5B-0": ("P0", REPO / "pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt"),
    "5B-1": ("P-X2", REPO / "pipeline/prompts/development/stage1/candidates/candidate_x2_from_v1_3_1.txt"),
    "5B-2": ("P-PR", REPO / "pipeline/prompts/development/stage1/candidates/candidate_pr_from_v1_3_1.txt"),
}
#: Prespecified in SCORING_PLAN.md §8. Ceilings, not targets.
CAPS = {"5B-0": 60, "5B-1": 25, "5B-2": 25}
SUBSETS = {
    "5B-0": None,  # every case
    "5B-1": ("x2_positive", "x2_negative_control", "x2_safety_control", "structural_control"),
    "5B-2": ("provenance_target", "structural_control"),
}
PROTECTED = ("iaa_workspace", "evidence", "STAGE1_GOLD_", "AMIA_2027_", "results")


class CallCapExceeded(RuntimeError):
    """The harness refused another paid call."""


def load_api_key() -> None:
    """Put pipeline/.env keys on the environment. Never printed or traced."""
    env = REPO / "pipeline" / ".env"
    if not env.exists():
        raise SystemExit("[stop] pipeline/.env 가 없습니다")
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        m = re.match(r"\s*([A-Z_0-9]+)\s*=\s*(.+)", line)
        if m:
            os.environ.setdefault(m.group(1), m.group(2).strip())
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("[stop] OPENAI_API_KEY 를 찾지 못했습니다")


class TerraClient:
    """gpt-5.6-terra caller with a hard cap.

    reasoning_effort travels through extra_body: the pinned SDK (1.6.1) has no
    named parameter for it. `last_call_meta` is read by the runtime tracer after
    each call, so usage lands on the attempt record rather than a side channel.
    """

    def __init__(self, cap: int):
        from openai import OpenAI

        self.client = OpenAI()
        self.cap = cap
        self.calls = 0
        self.last_call_meta: dict | None = None

    def __call__(self, prompt_text: str, model: str) -> str:
        if self.calls >= self.cap:
            raise CallCapExceeded(f"호출 상한 {self.cap} 도달 (실제 {self.calls}회)")
        self.calls += 1
        self.last_call_meta = None
        r = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            response_format={"type": "json_object"},
            extra_body={"reasoning_effort": REQUESTED_REASONING_EFFORT,
                        "max_completion_tokens": MAX_COMPLETION_TOKENS},
        )
        u = getattr(r, "usage", None)
        self.last_call_meta = {
            "usage": ({"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
                       "total_tokens": u.total_tokens} if u else None),
            "response_model": getattr(r, "model", None),
            "call_index": self.calls,
        }
        return r.choices[0].message.content or ""


def load_cases(stage: str) -> list[dict]:
    cases = [json.loads(l) for l in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    groups = SUBSETS[stage]
    return cases if groups is None else [c for c in cases if c["metric_group"] in groups]


def build_run_config(stage: str, prompt_path: Path) -> dict:
    """Everything the runtime cannot know, merged into every attempt record.

    `requested_reasoning_effort`, never `confirmed_` — the provider exposes no
    metadata that would confirm the setting was applied.
    """
    import openai

    return {
        "stage": stage,
        "prompt_label": PROMPTS[stage][0],
        "prompt_artifact": str(prompt_path.relative_to(REPO)),
        "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "model": MODEL,
        "requested_reasoning_effort": REQUESTED_REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "sdk_name": "openai",
        "sdk_version": openai.__version__,
        "python_version": platform.python_version(),
        "request_mechanism": "chat.completions + extra_body",
    }


def case_row(case: dict, node, calls: int, error: str | None) -> dict:
    if node is None:
        return {"case_id": case["case_id"], "metric_group": case["metric_group"],
                "status": "hard_failure", "api_calls": calls, "error": error}
    nodes = list(node.walk())
    return {
        "case_id": case["case_id"],
        "metric_group": case["metric_group"],
        "status": "ok",
        "root_decision": node.output.get("splitting_decision"),
        "child_logic": node.output.get("child_logic"),
        "cohort_scope": node.output.get("cohort_scope"),
        "primary_rule_id": node.output.get("primary_rule_id"),
        "supporting_rule_ids": node.output.get("supporting_rule_ids"),
        "derived_tier": derive_tier(node.output.get("primary_rule_id")),
        "n_children": len(node.output.get("sub_criteria") or []),
        "needs_recursion": node.output.get("needs_recursion"),
        "recursion_targets": node.output.get("recursion_targets"),
        "observed_max_depth": max(n.depth for n in nodes),
        "n_passes": len(nodes),
        "complete": node.is_complete,
        "incomplete": [{"node_id": n.node_id, "reason": n.incomplete_reason}
                       for n in node.incomplete_nodes()],
        "expected_structural": case["expected_structural"],
        "expected_recursion": case["expected_recursion"],
        "expected_max_depth": case["expected_max_depth"],
        "api_calls": calls,
        "error": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 1 v1.3 Phase 5B runner")
    ap.add_argument("--stage", required=True, choices=list(PROMPTS))
    ap.add_argument("--dry-run", action="store_true", help="렌더만 확인, API 호출 0")
    ap.add_argument("--live", action="store_true", help="실제 유료 호출")
    ap.add_argument("--cap", type=int, default=None)
    args = ap.parse_args()
    if not (args.dry_run or args.live):
        ap.error("--dry-run 또는 --live 중 하나가 필요합니다")

    stage = args.stage
    label, prompt_path = PROMPTS[stage]
    cap = args.cap or CAPS[stage]
    cases = load_cases(stage)
    template = prompt_path.read_text(encoding="utf-8")
    cfg = build_run_config(stage, prompt_path)
    out_dir = HERE / "runs" / f"{stage}_{label}"

    print(f"=== PRE-RUN CHECKS — {stage} ({label}) ===", file=sys.stderr)
    print(f"  prompt   : {cfg['prompt_artifact']}", file=sys.stderr)
    print(f"  sha256   : {cfg['prompt_sha256']}", file=sys.stderr)
    print(f"  model    : {MODEL} · requested_reasoning_effort={REQUESTED_REASONING_EFFORT}", file=sys.stderr)
    print(f"  sdk      : openai {cfg['sdk_version']} · python {cfg['python_version']}", file=sys.stderr)
    print(f"  cases    : {len(cases)}", file=sys.stderr)
    print(f"  cap      : {cap}", file=sys.stderr)
    print(f"  out      : {out_dir.relative_to(REPO)}", file=sys.stderr)

    problems = []
    unresolved = 0
    for c in cases:
        ctx = root_context(c["root_criterion_text"], criterion_type=c["criterion_type"],
                           trial_has_cohorts=c["trial_has_cohorts"], criterion_id=c["case_id"])
        unresolved += render_prompt(ctx, template).count("{{")
    if unresolved:
        problems.append(f"미치환 placeholder {unresolved}개")
    head = out_dir.relative_to(REPO).parts[0]
    if any(head == p or head.startswith(p) for p in PROTECTED):
        problems.append(f"보호 경로 출력: {out_dir}")
    print(f"  unresolved {{{{…}}}}: {unresolved}", file=sys.stderr)
    if problems:
        for p in problems:
            print(f"  [FAIL] {p}", file=sys.stderr)
        return 1
    print("  모든 사전 점검 통과", file=sys.stderr)

    if args.dry_run:
        print("\n[dry-run] API 호출 0. 종료합니다.", file=sys.stderr)
        return 0

    load_api_key()
    (out_dir / "outputs").mkdir(parents=True, exist_ok=True)
    tracer = JsonlTracer(out_dir / "attempts.jsonl", run_config=cfg)
    client = TerraClient(cap=cap)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []

    for case in cases:
        cid = case["case_id"]
        ctx = root_context(case["root_criterion_text"], criterion_type=case["criterion_type"],
                           trial_has_cohorts=case["trial_has_cohorts"], criterion_id=cid)
        before = client.calls
        node, error = None, None
        try:
            node = run_stage1_v13(ctx, llm=client, model=MODEL, template=template, tracer=tracer)
        except CallCapExceeded as exc:
            print(f"  [stop] {exc}", file=sys.stderr)
            rows.append(case_row(case, None, client.calls - before, str(exc)))
            break
        except Stage1V13ValidationError as exc:
            error = f"validation: {exc.errors[:3]}"
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"

        row = case_row(case, node, client.calls - before, error)
        rows.append(row)
        if node:
            (out_dir / "outputs" / f"{cid}.json").write_text(
                json.dumps(node.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"  {cid:4} {row['root_decision']:17} logic={str(row['child_logic']):4} "
                  f"rule={str(row['primary_rule_id']):5} depth={row['observed_max_depth']} "
                  f"passes={row['n_passes']} calls={row['api_calls']}", file=sys.stderr)
        else:
            print(f"  {cid:4} FAILED: {error}", file=sys.stderr)

    attempts = [json.loads(l) for l in (out_dir / "attempts.jsonl").read_text(encoding="utf-8").splitlines()]
    usages = [a["usage"] for a in attempts if a.get("usage")]
    summary = {
        "stage": stage, "prompt_label": label,
        "purpose": "shared baseline characterization" if stage == "5B-0" else "isolated candidate comparison",
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_config": cfg, "call_cap": cap,
        "root_cases": len(rows), "api_calls_total": client.calls,
        "attempt_summary": summarize_attempts(attempts),
        "token_usage": {
            "prompt": sum(u["prompt_tokens"] for u in usages),
            "completion": sum(u["completion_tokens"] for u in usages),
            "total": sum(u["total_tokens"] for u in usages),
        } if usages else None,
        "hard_failures": sum(1 for r in rows if r["status"] == "hard_failure"),
        "complete_hierarchies": sum(1 for r in rows if r.get("complete")),
        "cases": rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n=== {stage} 완료 · API 호출 {client.calls}/{cap} ===", file=sys.stderr)
    print(f"  → {out_dir.relative_to(REPO)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
