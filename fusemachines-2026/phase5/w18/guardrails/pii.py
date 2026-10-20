"""PII detection and redaction (used on both input and output).

Approach: regular expressions for structured identifiers, with validators
(Luhn checksum for cards, octet range for IPs, digit count for phones) and
context keywords for free-form IDs (passport, account number, date of birth).
Overlapping matches are resolved by detector priority so a card number is not
also reported as a phone number.
"""
import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .types import Action, GuardrailResult


def _luhn_ok(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _ip_ok(value: str) -> bool:
    return all(0 <= int(p) <= 255 for p in value.split("."))


def _phone_ok(value: str) -> bool:
    n = sum(c.isdigit() for c in value)
    return 9 <= n <= 15


@dataclass(frozen=True)
class Detector:
    kind: str
    pattern: "re.Pattern[str]"
    validator: Optional[Callable[[str], bool]] = None
    group: int = 0  # capture group holding the sensitive value


# Order = priority when spans overlap (earlier wins).
DETECTORS: List[Detector] = [
    Detector("API_KEY", re.compile(r"\b(?:sk|pk|rk)[-_](?:live|test)?[-_]?[A-Za-z0-9]{16,}\b|\bAKIA[0-9A-Z]{16}\b")),
    Detector("PASSWORD", re.compile(r"(?i)\b(?:password|passcode|pin)\s*(?:is|=|:)\s*(\S{4,})"), group=1),
    Detector("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    Detector("CREDIT_CARD", re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), _luhn_ok),
    Detector("SSN", re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")),
    Detector("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b")),
    Detector("NATIONAL_ID", re.compile(
        r"(?i)\b(?:passport|citizenship|national\s+id|driver'?s?\s+licen[cs]e|licen[cs]e)"
        r"(?:\s+(?:no\.?|number|#))?\s*(?:is|:|-)?\s*([A-Z]{0,3}\d[A-Z0-9-]{5,14})"), group=1),
    Detector("ACCOUNT_NUMBER", re.compile(r"(?i)\baccount\s*(?:no\.?|number|#)?\s*(?:is|:)?\s*(\d{8,18})\b"), group=1),
    Detector("DATE_OF_BIRTH", re.compile(
        r"(?i)\b(?:dob|date\s+of\s+birth|born\s+on)\s*(?:is|:)?\s*(\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4})"), group=1),
    Detector("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), _ip_ok),
    Detector("PHONE", re.compile(
        r"(?<![\w+])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?!\w)"), _phone_ok),
]


@dataclass
class PIIFinding:
    kind: str
    start: int
    end: int
    value: str

    @property
    def masked(self) -> str:
        v = self.value
        return v[:2] + "*" * max(len(v) - 4, 1) + v[-2:] if len(v) > 4 else "****"


def find_pii(text: str, kinds: Optional[Iterable[str]] = None) -> List[PIIFinding]:
    wanted = set(kinds) if kinds else None
    found: List[PIIFinding] = []
    taken: List[Tuple[int, int]] = []
    for det in DETECTORS:
        if wanted and det.kind not in wanted:
            continue
        for m in det.pattern.finditer(text):
            start, end = m.span(det.group)
            value = m.group(det.group)
            if det.validator and not det.validator(value):
                continue
            if any(start < e and s < end for s, e in taken):
                continue
            taken.append((start, end))
            found.append(PIIFinding(det.kind, start, end, value))
    return sorted(found, key=lambda f: f.start)


def redact(text: str, findings: List[PIIFinding]) -> Tuple[str, Dict[str, str]]:
    """Replace each finding with a typed placeholder such as [EMAIL_1].

    Returns the redacted text and a placeholder -> original mapping (kept
    server-side only, never sent to the model or the audit log).
    """
    counters: Dict[str, int] = {}
    mapping: Dict[str, str] = {}
    out, last = [], 0
    for f in findings:
        counters[f.kind] = counters.get(f.kind, 0) + 1
        ph = f"[{f.kind}_{counters[f.kind]}]"
        mapping[ph] = f.value
        out.append(text[last:f.start])
        out.append(ph)
        last = f.end
    out.append(text[last:])
    return "".join(out), mapping


# Identifiers whose presence is worth warning the user about.
HIGH_RISK = {"CREDIT_CARD", "SSN", "PASSWORD", "API_KEY", "NATIONAL_ID", "IBAN", "ACCOUNT_NUMBER"}


def check_input(text: str) -> GuardrailResult:
    """Input guardrail: redact PII before the text reaches the LLM or logs."""
    findings = find_pii(text)
    if not findings:
        return GuardrailResult("pii_input", False, Action.ALLOW, sanitized_text=text)
    redacted, _ = redact(text, findings)
    kinds = sorted({f.kind for f in findings})
    notice = None
    if HIGH_RISK & set(kinds):
        notice = ("For your security, please do not share full card numbers, passwords, "
                  "or government ID numbers in chat. We removed them from your message.")
    return GuardrailResult(
        "pii_input", True, Action.REDACT,
        reason=f"Detected PII: {', '.join(kinds)}",
        details={"findings": [{"type": f.kind, "masked": f.masked} for f in findings],
                 "user_notice": notice},
        sanitized_text=redacted,
    )
