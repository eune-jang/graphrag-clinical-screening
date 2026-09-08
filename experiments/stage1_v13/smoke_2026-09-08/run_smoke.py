#!/usr/bin/env python3
"""PHASE 5A — Stage 1 v1.3 real-LLM integration smoke test.

Confirms the v1.3 development runtime can call a real model, render the prompt,
parse, validate, recurse, and keep execution provenance. **Not** prompt tuning,
accuracy evaluation, or model comparison.

Development artifact. Writes only under this directory; never into
iaa_workspace/, evidence/, STAGE1_GOLD_*/ or results/adjudication/.

The runtime source is untouched: the model call is injected through the
`llm=` extension point `run_stage1_v13` already exposes, so nothing in
`pipeline/stage1_v13/` or the legacy production path had to change.

Usage
    python experiments/stage1_v13/smoke_2026-09-08/run_smoke.py --dry-run
    python experiments/stage1_v13/smoke_2026-09-08/run_smoke.py --live
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from pipeline.stage1_v13.context import root_context  # noqa: E402
from pipeline.stage1_v13.runner import (  # noqa: E402
    DEV_PROMPT_PATH,
    load_dev_prompt,
    render_prompt,
    run_stage1_v13,
)
from pipeline.stage1_v13.validators import Stage1V13ValidationError, validate_v13_output  # noqa: E402

MODEL = "gpt-5.6-terra"
REASONING_EFFORT = "medium"
MAX_COMPLETION_TOKENS = 8000
#: Hard safety cap for this phase. The pre-run probe already consumed one call
#: of the 50 authorised, so the harness budget is deliberately lower.
CALL_CAP = 45

PROTECTED = ("iaa_workspace", "evidence", "STAGE1_GOLD_", "AMIA_2027_", "results")


class CallCapExceeded(RuntimeError):
    """The harness refused to make another paid call."""


def load_api_key() -> None:
    """Put pipeline/.env keys on the environment. Never printed or logged."""
    env = REPO / "pipeline" / ".env"
    if not env.exists():
        raise SystemExit("[stop] pipeline/.env 가 없습니다")
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        m = re.match(r"\s*([A-Z_]+)\s*=\s*(.+)", line)
        if m:
            os.environ.setdefault(m.group(1), m.group(2).strip())
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("[stop] OPENAI_API_KEY 를 찾지 못했습니다")


class TerraClient:
    """gpt-5.6-terra caller with per-pass tracing and a hard call cap.

    reasoning_effort goes through `extra_body`: the installed openai SDK (1.6.1)
    has no named parameter for it, and routing it this way avoids both a source
    change to the shared llm_client and an SDK upgrade that would also affect
    the legacy production path.
    """

    def __init__(self, *, cap: int = CALL_CAP):
        from openai import OpenAI

        self.client = OpenAI()
        self.cap = cap
        self.calls = 0
        self.traces: list[dict] = []
        self.prompt_sha = hashlib.sha256(
            DEV_PROMPT_PATH.read_bytes()
        ).hexdigest()
        self._ctx: dict = {}

    def bind(self, **ctx) -> None:
        """Context recorded with the next call (case id, node path, depth …)."""
        self._ctx = ctx

    def __call__(self, prompt_text: str, model: str) -> str:
        if self.calls >= self.cap:
            raise CallCapExceeded(
                f"호출 상한 {self.cap} 도달 — 중단합니다 (실제 호출 {self.calls}회)"
            )
        self.calls += 1
        t0 = time.time()
        err = None
        content = ""
        usage = None
        try:
            r = self.client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"},
                extra_body={
                    "reasoning_effort": REASONING_EFFORT,
                    "max_completion_tokens": MAX_COMPLETION_TOKENS,
                },
            )
            content = r.choices[0].message.content or ""
            u = getattr(r, "usage", None)
            if u:
                usage = {
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                }
        except Exception as exc:  # noqa: BLE001 — recorded, then re-raised
            err = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self.traces.append({
                "call_index": self.calls,
                **self._ctx,
                "model": MODEL,
                "reasoning_effort": REASONING_EFFORT,
                "prompt_artifact": str(DEV_PROMPT_PATH.relative_to(REPO)),
                "prompt_sha256": self.prompt_sha,
                "latency_s": round(time.time() - t0, 3),
                "usage": usage,
                "api_error": err,
                "raw_response": content,
            })
        return content


def summarize_case(case: dict, node, retries: int, error: str | None) -> dict:
    """Per-root-case row for the review table."""
    if node is None:
        return {
            "case_id": case["case_id"], "status": "hard_failure",
            "root_decision": None, "child_logic": None, "max_depth": None,
            "n_passes": 0, "complete": False, "incomplete": [],
            "retries": retries, "error": error,
        }
    nodes = list(node.walk())
    return {
        "case_id": case["case_id"],
        "status": "ok",
        "root_decision": node.output.get("splitting_decision"),
        "child_logic": node.output.get("child_logic"),
        "primary_rule_id": node.output.get("primary_rule_id"),
        "max_depth": max(n.depth for n in nodes),
        "n_passes": len(nodes),
        "complete": node.is_complete,
        "incomplete": [
            {"node_id": n.node_id, "reason": n.incomplete_reason}
            for n in node.incomplete_nodes()
        ],
        "retries": retries,
        "error": None,
    }


def classify_validation_errors(traces: list[dict]) -> dict[str, int]:
    """Bucket validator messages by the canonical family they cite."""
    buckets: dict[str, int] = {}
    for t in traces:
        for e in t.get("validation_errors") or []:
            if "sibling_spans" in e:
                key = "span:sibling_only"
            elif "TARGET_SEGMENTS 밖" in e:
                key = "span:root_outside_target"
            elif "합성/정규화된 span" in e:
                key = "span:synthesized"
            elif "primary_rule_id" in e or "supporting_rule_ids" in e:
                key = "provenance"
            elif "child_logic" in e:
                key = "H5:child_logic"
            elif "cohort_scope" in e:
                key = "X4:cohort_scope"
            elif "recursion" in e or "needs_recursion" in e:
                key = "H6:recursion"
            elif "JSON 파싱" in e:
                key = "format:json_parse"
            else:
                key = "other"
            buckets[key] = buckets.get(key, 0) + 1
    return buckets


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 1 v1.3 PHASE 5A smoke test")
    ap.add_argument("--dry-run", action="store_true", help="렌더만 확인, API 호출 0")
    ap.add_argument("--live", action="store_true", help="실제 유료 호출 수행")
    ap.add_argument("--cap", type=int, default=CALL_CAP)
    ap.add_argument("--only", nargs="*", help="특정 case_id만")
    args = ap.parse_args()
    if not (args.dry_run or args.live):
        ap.error("--dry-run 또는 --live 중 하나가 필요합니다")

    cases = [json.loads(l) for l in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.only:
        cases = [c for c in cases if c["case_id"] in args.only]

    template = load_dev_prompt()
    prompt_sha = hashlib.sha256(DEV_PROMPT_PATH.read_bytes()).hexdigest()

    # ── pre-run checks (§5) ────────────────────────────────────────────
    print("=== PRE-RUN CHECKS ===", file=sys.stderr)
    problems: list[str] = []
    if "prompt_1_splitting" in str(DEV_PROMPT_PATH):
        problems.append("프로덕션 프롬프트 경로가 사용되고 있습니다")
    print(f"  prompt artifact : {DEV_PROMPT_PATH.relative_to(REPO)}", file=sys.stderr)
    print(f"  prompt sha256   : {prompt_sha}", file=sys.stderr)
    unresolved = 0
    for case in cases:
        ctx = root_context(
            case["root_criterion_text"],
            criterion_type=case.get("criterion_type"),
            trial_has_cohorts=case.get("trial_has_cohorts"),
            criterion_id=case["case_id"],
        )
        rendered = render_prompt(ctx, template)
        n = rendered.count("{{")
        unresolved += n
        if n:
            problems.append(f"{case['case_id']}: 미치환 placeholder {n}개")
    print(f"  cases           : {len(cases)}", file=sys.stderr)
    print(f"  unresolved {{{{…}}}}: {unresolved}", file=sys.stderr)
    out_rel = HERE.relative_to(REPO)
    if any(str(out_rel).startswith(p) for p in PROTECTED):
        problems.append(f"출력 경로가 보호 영역입니다: {out_rel}")
    print(f"  output dir      : {out_rel}", file=sys.stderr)
    print(f"  call cap        : {args.cap}", file=sys.stderr)
    if problems:
        for p in problems:
            print(f"  [FAIL] {p}", file=sys.stderr)
        print("[stop] 사전 점검 실패 — API 호출하지 않습니다", file=sys.stderr)
        return 1
    print("  모든 사전 점검 통과", file=sys.stderr)

    if args.dry_run:
        print("\n[dry-run] API 호출 0. 종료합니다.", file=sys.stderr)
        return 0

    # ── live run ───────────────────────────────────────────────────────
    load_api_key()
    client = TerraClient(cap=args.cap)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []

    for case in cases:
        cid = case["case_id"]
        print(f"\n--- {cid} ---", file=sys.stderr)
        ctx = root_context(
            case["root_criterion_text"],
            criterion_type=case.get("criterion_type"),
            trial_has_cohorts=case.get("trial_has_cohorts"),
            criterion_id=cid,
        )
        before = client.calls
        node, error = None, None

        # The runner does not expose per-pass context to the llm callable, so
        # bind what we know per case; node path is recovered from the trace order.
        client.bind(case_id=cid, criterion_type=case.get("criterion_type"),
                    trial_has_cohorts=case.get("trial_has_cohorts"))
        try:
            node = run_stage1_v13(ctx, llm=client, model=MODEL, template=template)
        except Stage1V13ValidationError as exc:
            error = f"validation: {exc.errors}"
            for t in client.traces[before:]:
                t.setdefault("validation_errors", exc.errors)
        except CallCapExceeded as exc:
            print(f"  [stop] {exc}", file=sys.stderr)
            error = str(exc)
            rows.append(summarize_case(case, None, client.calls - before, error))
            break
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"

        used = client.calls - before
        row = summarize_case(case, node, max(0, used - (len(list(node.walk())) if node else 0)), error)
        row["api_calls"] = used
        rows.append(row)
        if node:
            (HERE / "outputs" / f"{cid}.json").write_text(
                json.dumps(node.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"  {row['root_decision']} logic={row['child_logic']} "
                  f"passes={row['n_passes']} depth={row['max_depth']} "
                  f"complete={row['complete']} calls={used}", file=sys.stderr)
        else:
            print(f"  FAILED: {error}", file=sys.stderr)

    # ── artefacts ──────────────────────────────────────────────────────
    (HERE / "traces" / "passes.jsonl").write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in client.traces), encoding="utf-8")

    usages = [t["usage"] for t in client.traces if t.get("usage")]
    summary = {
        "phase": "5A",
        "purpose": "real-LLM integration smoke test (not accuracy evaluation)",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "prompt_artifact": str(DEV_PROMPT_PATH.relative_to(REPO)),
        "prompt_sha256": prompt_sha,
        "call_cap": args.cap,
        "root_cases": len(rows),
        "api_calls_total": client.calls,
        "recursive_calls": sum(max(0, r.get("n_passes", 1) - 1) for r in rows),
        "hard_failures": sum(1 for r in rows if r["status"] == "hard_failure"),
        "complete_hierarchies": sum(1 for r in rows if r.get("complete")),
        "incomplete_hierarchies": sum(1 for r in rows if r["status"] == "ok" and not r["complete"]),
        "max_depth_truncations": sum(
            1 for r in rows for i in r.get("incomplete") or [] if i["reason"] == "max_depth"),
        "empty_main": sum(
            1 for r in rows for i in r.get("incomplete") or [] if i["reason"] == "empty_main"),
        "observed_max_depth": max((r.get("max_depth") or 0) for r in rows) if rows else 0,
        "depth_distribution": {},
        "validation_error_categories": classify_validation_errors(client.traces),
        "token_usage": {
            "prompt": sum(u["prompt_tokens"] for u in usages),
            "completion": sum(u["completion_tokens"] for u in usages),
            "total": sum(u["total_tokens"] for u in usages),
        } if usages else None,
        "cases": rows,
    }
    dist: dict[str, int] = {}
    for r in rows:
        if r.get("max_depth") is not None:
            dist[str(r["max_depth"])] = dist.get(str(r["max_depth"]), 0) + 1
    summary["depth_distribution"] = dist

    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "run_config.json").write_text(json.dumps({
        "model": MODEL, "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "sdk_param_channel": "extra_body (openai SDK 1.6.1 has no named reasoning_effort)",
        "call_cap": args.cap,
        "prompt_artifact": str(DEV_PROMPT_PATH.relative_to(REPO)),
        "prompt_sha256": prompt_sha,
        "runtime": "pipeline/stage1_v13 (llm injected; no runtime source change)",
        "secrets": "read from pipeline/.env at runtime; never logged",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== 총 API 호출 {client.calls}/{args.cap} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
