"""Output schema validation.

The model must return a single JSON object:

    {"answer": str, "citations": [doc_id, ...], "confidence": float 0-1, "needs_human": bool}

Validation checks JSON syntax, required fields, no extra fields, field types,
value ranges, and that every citation refers to a document that was actually
retrieved for this request (a model cannot cite a source it was not given).
"""
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .types import Action, GuardrailResult

SCHEMA: Dict[str, Dict[str, Any]] = {
    "answer": {"type": str, "min_len": 1, "max_len": 1500},
    "citations": {"type": list, "item_type": str, "max_items": 5},
    "confidence": {"type": (int, float), "min": 0.0, "max": 1.0},
    "needs_human": {"type": bool},
}

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


def parse(raw: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse raw model text into a dict. Accepts a ```json fenced block."""
    m = _FENCE.match(raw)
    text = m.group(1) if m else raw.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e.msg} at position {e.pos}"
    if not isinstance(obj, dict):
        return None, f"top-level value must be an object, got {type(obj).__name__}"
    return obj, None


def validate(raw: str, allowed_citations: Iterable[str]) -> GuardrailResult:
    obj, err = parse(raw)
    errors: List[str] = [err] if err else []
    if obj is not None:
        errors += _field_errors(obj, set(allowed_citations))
    flagged = bool(errors)
    return GuardrailResult(
        "schema", flagged, Action.REGENERATE if flagged else Action.ALLOW,
        reason="; ".join(errors) if flagged else "Valid response structure",
        details={"errors": errors, "parsed": obj if not flagged else None},
    )


def _field_errors(obj: Dict[str, Any], allowed: set) -> List[str]:
    errors = []
    for extra in sorted(set(obj) - set(SCHEMA)):
        errors.append(f"unexpected field '{extra}'")
    for name, rule in SCHEMA.items():
        if name not in obj:
            errors.append(f"missing required field '{name}'")
            continue
        v = obj[name]
        expected = rule["type"]
        # bool is a subclass of int in Python; don't accept True as a confidence.
        if not isinstance(v, expected) or (expected != bool and isinstance(v, bool)):
            errors.append(f"field '{name}' has type {type(v).__name__}")
            continue
        if isinstance(v, str):
            if len(v.strip()) < rule.get("min_len", 0):
                errors.append(f"field '{name}' is empty")
            if len(v) > rule.get("max_len", 10**9):
                errors.append(f"field '{name}' exceeds {rule['max_len']} characters")
        if isinstance(v, list):
            if len(v) > rule.get("max_items", 10**9):
                errors.append(f"field '{name}' has more than {rule['max_items']} items")
            for item in v:
                if not isinstance(item, rule["item_type"]):
                    errors.append(f"field '{name}' contains a non-string item")
                elif item not in allowed:
                    errors.append(f"citation '{item}' was not among the retrieved documents")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and "min" in rule:
            if not rule["min"] <= v <= rule["max"]:
                errors.append(f"field '{name}'={v} outside [{rule['min']}, {rule['max']}]")
    return errors
