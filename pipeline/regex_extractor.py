"""
Regex-based extraction for HAS_VALUE and HAS_TEMPORAL standard patterns.
Covers ~94% of HAS_VALUE and ~72% of HAS_TEMPORAL (per automation_boundary_analysis.md).

When regex fails or detects non-standard keywords, the criterion is routed
to Prompt 4 (LLM fallback).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class RegexResult:
    has_value: list[dict] = field(default_factory=list)
    has_temporal: list[dict] = field(default_factory=list)
    is_complete: bool = False          # True = no LLM fallback needed
    fallback_reason: str | None = None # why regex was insufficient


# ── Operator symbols ───────────────────────────────────────────────────

_OP_MAP = {
    "≥": "≥", ">=": "≥", "⩾": "≥",
    "≤": "≤", "<=": "≤", "⩽": "≤",
    ">": ">", "<": "<", "=": "=",
    "</=": "≤", ">/=": "≥",   # extraction-artifact variants
}

# ── Input normalization ────────────────────────────────────────────────
# AACT / PDF / markdown ingestion mangles operators into:
#   \>=, \<=          (markdown-escaped >=, <=)
#   \x1e (RS)         (record separator emitted for `≥` by some converters)
#   \x7f (DEL)        (same idea for `≥` / `≤`)
#   \x03bc, µ    (μ — micro sign variants)
# Normalize before regex matching so we don't have to encode all variants
# into the value pattern.
_CHAR_NORMALIZE = [
    ("\\>=", "≥"), ("\\<=", "≤"),
    ("\\>", ">"),  ("\\<", "<"),
    ("\x1e=", "≥"), ("\x1e", "≥"),     # most common: \x1e standalone = "≥"
    ("\x7f=", "≥"), ("\x7f", "≥"),
    ("\x03bc", "μ"), ("µ", "μ"),
    ("⩾", "≥"), ("⩽", "≤"),
    ("</=", "≤"), (">/=", "≥"),
]

# Natural-language operator phrases (lowercase target text matching).
# Mapped to canonical operator AFTER substitution.
_NL_OPERATOR_SUBS = [
    (r"\bgreater\s+than\s+or\s+equal\s+to\b", "≥"),
    (r"\bgreater\s+to\s+or\s+equal\s+to\b",   "≥"),   # typo seen in real data
    (r"\bless\s+than\s+or\s+equal\s+to\b",    "≤"),
    (r"\bat\s+least\b",                       "≥"),
    (r"\bno\s+less\s+than\b",                 "≥"),
    (r"\bno\s+more\s+than\b",                 "≤"),
    (r"\bgreater\s+than\b",                   ">"),
    (r"\bless\s+than\b",                      "<"),
    (r"\bor\s+higher\b",                      "_OR_HIGHER_"),  # suffix form
    (r"\bor\s+older\b",                       "_OR_HIGHER_"),
    (r"\band\s+older\b",                      "_OR_HIGHER_"),
]


def _normalize_input(text: str) -> str:
    """Repair common encoding artifacts and natural-language operators."""
    for src, dst in _CHAR_NORMALIZE:
        text = text.replace(src, dst)
    lower_replaced = text
    for pat, op in _NL_OPERATOR_SUBS:
        lower_replaced = re.sub(pat, op, lower_replaced, flags=re.IGNORECASE)
    # Suffix form: "18 years and older" → "≥ 18 years"
    lower_replaced = re.sub(
        r"(\d+(?:\.\d+)?)\s*([a-zA-Z%/µμ]+(?:\s*/\s*[a-zA-Z]+)?)?\s*_OR_HIGHER_",
        r"≥ \1 \2",
        lower_replaced,
    )
    # Cleanup any residual sentinel
    lower_replaced = lower_replaced.replace("_OR_HIGHER_", "")
    return lower_replaced


# ── HAS_VALUE patterns ────────────────────────────────────────────────
# Pattern: "ANC ≥ 1500/µL", "Total bilirubin ≤ 1.5 × ULN"

_VALUE_RE = re.compile(
    r"""
    (?:(?P<test_name>[A-Za-z][A-Za-z0-9\s/\-()]+?)\s+)?   # optional test name
    (?P<operator>[≥≤><]=?|=)                        # operator
    \s*
    (?P<value>\d[\d,]*(?:\.\d+)?)                   # numeric value (commas ok)
    \s*
    (?P<unit>[×x]\s*ULN|%|[a-zA-Z/µμ\^0-9]+(?:\s*/\s*[a-zA-Z]+)?)  # unit
    """,
    re.VERBOSE | re.IGNORECASE,
)

# ── HAS_TEMPORAL patterns ─────────────────────────────────────────────
# Pattern: "within 28 days prior to randomization"
#          "at least 4 weeks before first dose"

_TEMPORAL_RE = re.compile(
    r"""
    (?:within|at\s+least|≥|≤|>|<)?\s*
    (?P<value>\d+(?:\.\d+)?)\s*
    (?P<unit>days?|weeks?|months?|years?)\s*
    (?:prior\s+to|before|after|following|of|from)\s*
    (?P<anchor>[A-Za-z][A-Za-z\s]+?)
    (?:\.|,|$)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Direction keywords
_DIR_MAP = {
    "prior to": "before", "before": "before",
    "after": "after", "following": "after",
    "within": "within", "of": "within",
    "since": "since", "from": "before",
}

# ── Non-standard pattern detector ─────────────────────────────────────

_NONSTANDARD_KEYWORDS = re.compile(
    r"whichever|half[- ]?life|approximately|±|encouraged|optional|"
    r"if\s+(?:available|technically|liver)|or\s+baseline|investigator",
    re.IGNORECASE,
)

# ── Trial-event anchor vocabulary ─────────────────────────────────────

_TRIAL_EVENT_ANCHORS = {
    "randomization", "first dose", "first dose of study treatment",
    "informed consent", "study treatment start", "study entry",
    "day 1", "cycle 1 day 1", "registration",
}


def _normalize_anchor(raw: str) -> tuple[str, str]:
    """Return (normalized_anchor, anchor_type)."""
    lower = raw.strip().lower()
    for ta in _TRIAL_EVENT_ANCHORS:
        if ta in lower:
            slug = ta.replace(" ", "_")
            return slug, "trial_event"
    return raw.strip().replace(" ", "_").lower(), "unspecified"


def _detect_direction(context: str) -> str:
    """Infer temporal direction from surrounding text."""
    lower = context.lower()
    for kw, direction in _DIR_MAP.items():
        if kw in lower:
            return direction
    return "before"  # default per guideline 4.6.2


def _normalize_operator(raw: str) -> str:
    return _OP_MAP.get(raw, raw)


# ── Main extraction ───────────────────────────────────────────────────

def extract_constraints(criterion_text: str) -> RegexResult:
    """
    Extract HAS_VALUE and HAS_TEMPORAL from criterion text using regex.
    Returns RegexResult with is_complete=True if all patterns are standard.
    """
    result = RegexResult()

    # Repair encoding artifacts and rewrite natural-language operators
    # into canonical symbolic form. After this step the regex sees clean
    # patterns like "ANC ≥ 1500/µL".
    criterion_text = _normalize_input(criterion_text)

    # Check for non-standard patterns first
    if _NONSTANDARD_KEYWORDS.search(criterion_text):
        result.is_complete = False
        result.fallback_reason = "non-standard keyword detected"
        # Still attempt partial extraction below; Prompt 4 will fill gaps

    # HAS_VALUE extraction
    for m in _VALUE_RE.finditer(criterion_text):
        unit_raw = m.group("unit").strip()
        # Normalize × ULN
        unit_raw = re.sub(r"[×x]\s*ULN", "× ULN", unit_raw, flags=re.IGNORECASE)
        # Strip commas from numeric value before float()
        value_raw = m.group("value").replace(",", "")

        test_name = m.group("test_name")
        result.has_value.append({
            "operator": _normalize_operator(m.group("operator")),
            "value": float(value_raw),
            "unit": unit_raw,
            "_test_name_hint": test_name.strip() if test_name else "",
        })

    # HAS_TEMPORAL extraction
    for m in _TEMPORAL_RE.finditer(criterion_text):
        anchor_raw = m.group("anchor")
        anchor_norm, anchor_type = _normalize_anchor(anchor_raw)

        # Find direction from context preceding match
        start = max(0, m.start() - 30)
        context = criterion_text[start:m.end()]
        direction = _detect_direction(context)

        # Infer operator from direction keywords
        pre_text = criterion_text[max(0, m.start() - 20):m.start()].lower()
        if "at least" in pre_text or "≥" in pre_text:
            op = "≥"
        elif "within" in pre_text:
            op = "≤"
        else:
            op = "≤"

        unit_raw = m.group("unit").rstrip("s")  # normalize "days" → "day"
        # Actually keep plural for readability
        unit_norm = m.group("unit").strip()
        if not unit_norm.endswith("s"):
            unit_norm += "s"

        result.has_temporal.append({
            "operator": op,
            "value": float(m.group("value")),
            "unit": unit_norm,
            "anchor": anchor_norm,
            "direction": direction,
            "anchor_type": anchor_type,
        })

    # Decide completeness
    if result.fallback_reason is None:
        # If we found at least something and no non-standard keyword, mark complete
        result.is_complete = True

    return result
