"""
LLM client: prompt loading, template substitution, API call, parse, validate.

Supports both OpenAI and Anthropic APIs.
Provider is auto-detected from model name:
  "gpt-*", "o3*", "o4*"  → OpenAI   (pip install openai)
  "claude-*"              → Anthropic (pip install anthropic)
"""
from __future__ import annotations
import json
import re
import time
import logging
from pathlib import Path
from typing import Any

from .config import (
    PROMPTS_DIR, EXAMPLES_PATH, MODELS,
    MAX_RETRIES, LLM_TEMPERATURE, LLM_MAX_TOKENS,
)
from .validators import VALIDATORS

logger = logging.getLogger(__name__)

# ── Lazy imports for SDK flexibility ───────────────────────────────────

try:
    import openai as _openai_mod
except ImportError:
    _openai_mod = None  # type: ignore

try:
    import anthropic as _anthropic_mod
except ImportError:
    _anthropic_mod = None  # type: ignore


# ── Provider detection ─────────────────────────────────────────────────

def _detect_provider(model: str) -> str:
    """Detect API provider from model name."""
    m = model.lower()
    if m.startswith(("gpt-", "o3", "o4", "ft:gpt")):
        return "openai"
    if m.startswith("claude-"):
        return "anthropic"
    raise ValueError(
        f"Cannot detect provider for model '{model}'. "
        f"Expected 'gpt-*' (OpenAI) or 'claude-*' (Anthropic)."
    )


# ── Client singletons ─────────────────────────────────────────────────

_openai_client = None
_anthropic_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        if _openai_mod is None:
            raise RuntimeError("openai SDK not installed. Run: pip install openai")
        _openai_client = _openai_mod.OpenAI()  # uses OPENAI_API_KEY env
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        if _anthropic_mod is None:
            raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")
        _anthropic_client = _anthropic_mod.Anthropic()  # uses ANTHROPIC_API_KEY env
    return _anthropic_client


# ── Prompt loading & caching ───────────────────────────────────────────

_prompt_cache: dict[str, str] = {}
_examples_cache: dict[str, list] = {}


def _load_prompt(prompt_id: str) -> str:
    """Load prompt template from file. Cached."""
    if prompt_id not in _prompt_cache:
        filename_map = {
            "prompt_1": "prompt_1_splitting.txt",
            "prompt_2": "prompt_2_category_relation_target.txt",
            "prompt_3": "prompt_3_preferred_name.txt",
            "prompt_4": "prompt_4_constraint_fallback.txt",
            "prompt_5": "prompt_5_alternative_constraint.txt",
        }
        path = PROMPTS_DIR / filename_map[prompt_id]
        _prompt_cache[prompt_id] = path.read_text(encoding="utf-8")
    return _prompt_cache[prompt_id]


def _load_examples(prompt_id: str) -> list[dict]:
    """Load examples for a given prompt from examples.json. Cached."""
    if not _examples_cache:
        data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
        key_map = {
            "prompt_1": "prompt_1_splitting",
            "prompt_2": "prompt_2_category_relation_target",
            "prompt_3": "prompt_3_preferred_name",
            "prompt_4": "prompt_4_constraint_fallback",
            "prompt_5": "prompt_5_alternative_constraint",
        }
        for pid, key in key_map.items():
            _examples_cache[pid] = data.get(key, [])
    return _examples_cache.get(prompt_id, [])


def _substitute_template(template: str, variables: dict[str, Any]) -> str:
    """Replace {{placeholder}} in prompt template with actual values."""
    result = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        if placeholder in result:
            if value is None:
                replacement = "null"
            elif isinstance(value, (dict, list)):
                replacement = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                replacement = str(value)
            result = result.replace(placeholder, replacement)
    return result


def _build_prompt_with_examples(prompt_id: str, variables: dict[str, Any]) -> str:
    """Build complete prompt: template + inline examples + variable substitution."""
    template = _load_prompt(prompt_id)
    examples = _load_examples(prompt_id)

    if examples:
        examples_block = "\n\n## Inline Examples\n\n"
        for i, ex in enumerate(examples, 1):
            examples_block += f"### Example {i}: {ex.get('label', '')}\n"
            examples_block += f"Source: {ex.get('source', '')}\n"
            examples_block += f"INPUT:\n```json\n{json.dumps(ex.get('input', {}), indent=2)}\n```\n"
            examples_block += f"OUTPUT:\n```json\n{json.dumps(ex.get('output', {}), indent=2)}\n```\n\n"

        marker = "# Now process"
        if marker in template:
            idx = template.index(marker)
            template = template[:idx] + examples_block + "\n" + template[idx:]

    return _substitute_template(template, variables)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()
    return json.loads(text)


# ── Provider-specific API calls ────────────────────────────────────────

def _call_openai(model: str, prompt_text: str) -> str:
    """Call OpenAI Chat Completions API. Returns raw text."""
    client = _get_openai_client()

    response = client.chat.completions.create(
        model=model,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a clinical trial annotation assistant. "
                    "Always respond with valid JSON only. "
                    "No preamble, no markdown fences."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
    )
    return response.choices[0].message.content


def _call_anthropic(model: str, prompt_text: str) -> str:
    """Call Anthropic Messages API. Returns raw text."""
    client = _get_anthropic_client()

    response = client.messages.create(
        model=model,
        max_tokens=LLM_MAX_TOKENS,
        temperature=LLM_TEMPERATURE,
        messages=[{"role": "user", "content": prompt_text}],
    )
    return response.content[0].text


def _call_provider(model: str, prompt_text: str) -> str:
    """Route to the correct provider based on model name."""
    provider = _detect_provider(model)
    if provider == "openai":
        return _call_openai(model, prompt_text)
    else:
        return _call_anthropic(model, prompt_text)


def _get_api_error_class(provider: str):
    """Get the appropriate API error class for exception handling."""
    if provider == "openai" and _openai_mod:
        return _openai_mod.APIError
    if provider == "anthropic" and _anthropic_mod:
        return _anthropic_mod.APIError
    return Exception


# ── Main call function ─────────────────────────────────────────────────

def call_llm(
    prompt_id: str,
    variables: dict[str, Any],
    model_override: str | None = None,
) -> dict:
    """
    Call LLM with prompt template + examples + variables.
    Auto-detects provider (OpenAI/Anthropic) from model name.
    Validates output, retries on failure up to MAX_RETRIES.

    Returns parsed JSON dict.
    Raises RuntimeError if all retries exhausted.
    """
    model = model_override or MODELS[prompt_id]
    provider = _detect_provider(model)
    prompt_text = _build_prompt_with_examples(prompt_id, variables)
    validator = VALIDATORS.get(prompt_id)
    api_error_cls = _get_api_error_class(provider)

    last_errors: list[str] = []

    for attempt in range(1 + MAX_RETRIES):
        try:
            logger.info(
                f"[{prompt_id}] attempt {attempt + 1}/{1 + MAX_RETRIES}, "
                f"model={model} ({provider})"
            )

            raw_text = _call_provider(model, prompt_text)
            parsed = _parse_json_response(raw_text)

            # Validate
            if validator:
                errors = validator(parsed)
                if errors:
                    last_errors = errors
                    logger.warning(
                        f"[{prompt_id}] validation failed (attempt {attempt + 1}): "
                        f"{errors}"
                    )
                    if attempt < MAX_RETRIES:
                        prompt_text += (
                            f"\n\n# RETRY — previous output had validation errors:\n"
                            f"{json.dumps(errors)}\n"
                            f"Please fix and output valid JSON only."
                        )
                    continue

            logger.info(f"[{prompt_id}] success on attempt {attempt + 1}")
            return parsed

        except json.JSONDecodeError as e:
            last_errors = [f"JSON parse error: {e}"]
            logger.warning(f"[{prompt_id}] JSON parse failed: {e}")
            if attempt < MAX_RETRIES:
                prompt_text += (
                    "\n\n# RETRY — your previous response was not valid JSON. "
                    "Output ONLY a JSON object, no preamble, no markdown."
                )

        except api_error_cls as e:
            last_errors = [f"API error ({provider}): {e}"]
            logger.error(f"[{prompt_id}] {provider} API error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"[{prompt_id}] exhausted {1 + MAX_RETRIES} attempts. "
        f"Last errors: {last_errors}"
    )