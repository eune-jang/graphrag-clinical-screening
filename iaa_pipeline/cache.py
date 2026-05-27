"""LLM response cache.

Keyed by sha256(prompt_template_content + input_text + model_name).
Stored as one JSON file per key in the cache directory.

This is critical for the IAA pipeline: re-running stages should not
re-pay for the same LLM call. With 8 trials × ~30 criteria × 5 stages,
a single re-run without cache costs ~5× the original.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _hash_key(prompt_template: str, input_payload: dict, model: str) -> str:
    """Compute a deterministic hash for cache key.

    `prompt_template` is the literal template text (with placeholders still
    in it). `input_payload` is the dict passed to call_llm. `model` is the
    resolved model name. Together these uniquely determine the LLM response
    (modulo temperature, which is 0 in this pipeline).
    """
    # Sort keys in input_payload for stable hashing
    payload_str = json.dumps(input_payload, sort_keys=True, ensure_ascii=False)
    blob = f"{model}\n||\n{prompt_template}\n||\n{payload_str}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class LLMCache:
    """Disk-backed cache for LLM responses."""

    def __init__(self, cache_dir: Path | None):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        # In-process counters for observability
        self.hits = 0
        self.misses = 0

    @property
    def enabled(self) -> bool:
        return self.cache_dir is not None

    def get(
        self,
        prompt_template: str,
        input_payload: dict,
        model: str,
    ) -> Any | None:
        """Return cached response or None."""
        if not self.enabled:
            return None
        key = _hash_key(prompt_template, input_payload, model)
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            self.misses += 1
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.hits += 1
            return data["response"]
        except (json.JSONDecodeError, KeyError):
            # Corrupted cache file — treat as miss
            self.misses += 1
            return None

    def put(
        self,
        prompt_template: str,
        input_payload: dict,
        model: str,
        response: Any,
    ) -> None:
        """Store a response in the cache."""
        if not self.enabled:
            return
        key = _hash_key(prompt_template, input_payload, model)
        path = self.cache_dir / f"{key}.json"
        record = {
            "prompt_hash": key,
            "model": model,
            "input_payload": input_payload,
            "response": response,
            "cached_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def stats(self) -> dict:
        return {
            "enabled": self.enabled,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (
                self.hits / (self.hits + self.misses)
                if (self.hits + self.misses) > 0 else None
            ),
        }
