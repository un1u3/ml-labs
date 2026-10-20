"""Sensitive-information detection on model output.

Two checks:
  * PII / secrets: reuses the PII detectors. Contact details that appear in
    the retrieved public documents (e.g. the bank's support hotline) are
    allow-listed; anything else is redacted.
  * Confidential-context leakage: the system prompt carries a canary token and
    internal notes. If the output contains the canary, or a long verbatim run
    of the system prompt, the response is blocked and replaced with a fallback.
"""
import re
from typing import Iterable, List

from . import pii
from .types import Action, GuardrailResult

NGRAM = 8  # this many consecutive words copied from the system prompt counts as a leak


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _leaks_prompt(output: str, system_prompt: str) -> bool:
    sp = _words(system_prompt)
    grams = {tuple(sp[i:i + NGRAM]) for i in range(len(sp) - NGRAM + 1)}
    out = _words(output)
    return any(tuple(out[i:i + NGRAM]) in grams for i in range(len(out) - NGRAM + 1))


def check(output: str, system_prompt: str, canary: str, public_sources: Iterable[str]) -> GuardrailResult:
    if canary.lower() in output.lower() or _leaks_prompt(output, system_prompt):
        return GuardrailResult(
            "output_sensitive", True, Action.BLOCK,
            reason="Response discloses confidential system instructions",
            details={"leak": "system_prompt"})

    public_text = " ".join(public_sources)
    findings = [f for f in pii.find_pii(output) if f.value not in public_text]
    if not findings:
        return GuardrailResult("output_sensitive", False, Action.ALLOW, reason="No sensitive data", sanitized_text=output)
    redacted, _ = pii.redact(output, findings)
    return GuardrailResult(
        "output_sensitive", True, Action.REDACT,
        reason=f"Redacted {', '.join(sorted({f.kind for f in findings}))} from response",
        details={"findings": [{"type": f.kind, "masked": f.masked} for f in findings]},
        sanitized_text=redacted,
    )
