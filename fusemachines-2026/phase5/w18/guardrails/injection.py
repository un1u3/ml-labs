"""Prompt-injection detection.

Approach: normalise the text to defeat cheap obfuscation (Unicode NFKC,
zero-width characters, leetspeak, embedded base64), then score it against
weighted signal families. Scores combine as 1 - prod(1 - w) so several weak
signals can add up to a block while a single strong one is enough on its own.
"""
import base64
import binascii
import re
import unicodedata
from typing import Dict, List, Tuple

from .types import Action, GuardrailResult

BLOCK_THRESHOLD = 0.5

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"})

_INSTR = r"(?:instructions?|rules|prompts?|guidelines|directions|polic(?:y|ies)|guardrails|restrictions|programming)"

# (signal name, weight, pattern) - patterns run on normalised, lowercased text.
SIGNALS: List[Tuple[str, float, "re.Pattern[str]"]] = [
    ("instruction_override", 0.65, re.compile(
        rf"\b(?:ignore|disregard|forget|override|skip|bypass)\b(?:\W+\w+){{0,4}}?\W+(?:previous|prior|above|earlier|preceding|all|any|your|the|system|original)\b(?:\W+\w+){{0,3}}?\W+{_INSTR}")),
    ("new_instructions", 0.45, re.compile(
        rf"\b(?:new|updated|real|actual)\s+(?:system\s+)?{_INSTR}\s*[:\-]|\bfrom now on,?\s+(?:you|ignore|respond|answer|act)")),
    ("role_hijack", 0.55, re.compile(
        r"\byou\s+are\s+(?:now|no\s+longer)\b|\b(?:act|behave|respond)\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:an?\s+)?(?:unrestricted|unfiltered|uncensored|evil|jailbroken|dan)\b"
        r"|\bpretend\s+(?:to\s+be|you\s+are)\b|\b(?:developer|god|admin|debug)\s+mode\b|\bjailbreak|\bdan\b(?:\s+mode)?")),
    ("prompt_extraction", 0.6, re.compile(
        r"\b(?:reveal|show|print|display|repeat|output|tell\s+me|what\s+(?:is|are)|leak|share|give\s+me|dump|recite|read\s+(?:me|out))\b(?:\W+\w+){0,4}?\W+"
        r"(?:system\s+prompt|(?:hidden|initial|original|secret|internal|confidential)\s+(?:instructions?|prompt|notes|config(?:uration)?|rules)|your\s+(?:instructions|prompt|rules|configuration))")),
    ("restriction_bypass", 0.5, re.compile(
        r"\b(?:bypass|disable|turn\s+off|deactivate|remove|without(?:\s+any)?)\s+(?:your\s+|the\s+|all\s+)?(?:safety|content\s+)?(?:filters?|safeguards|guardrails|restrictions|censorship|safety|limitations)\b")),
    ("delimiter_injection", 0.45, re.compile(
        r"</?\s*(?:system|user|assistant|instructions?)\s*>|<\|im_(?:start|end)\|>|\[/?inst\]|^\s*#{2,}\s*(?:system|instruction)|^\s*system\s*:", re.M)),
    ("data_exfiltration", 0.4, re.compile(
        r"\b(?:list|show|give|dump|export|disclose|send)\b(?:\W+\w+){0,3}?\W+(?:all|every|other)\s+(?:customers?|users?|accounts?|account\s+holders?)(?:'s?)?\b|\bdatabase\s+dump\b|\ball\s+account\s+balances\b")),
    ("authority_claim", 0.3, re.compile(
        r"\bi\s+am\s+(?:the|an?|your)\s+(?:admin(?:istrator)?|developer|ceo|bank\s+manager|system\s+owner|security\s+team)\b|\b(?:authorized|authorised|emergency)\s+override\b")),
]


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH).lower()
    return re.sub(r"[ \t]+", " ", t)


def _decoded_payloads(text: str) -> List[str]:
    out = []
    for blob in re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", text):
        try:
            decoded = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if decoded.isprintable() and sum(c.isalpha() for c in decoded) > len(decoded) * 0.6:
            out.append(decoded)
    return out


def _signals(text: str) -> Dict[str, float]:
    hits: Dict[str, float] = {}
    for name, weight, pat in SIGNALS:
        if pat.search(text):
            hits[name] = weight
    return hits


def score(text: str) -> Tuple[float, Dict[str, float], List[str]]:
    base = normalise(text)
    variants = {"normalised": base, "leetspeak": base.translate(_LEET)}
    for i, payload in enumerate(_decoded_payloads(text)):
        variants[f"base64_{i}"] = normalise(payload)

    hits: Dict[str, float] = {}
    sources: List[str] = []
    for label, variant in variants.items():
        for name, w in _signals(variant).items():
            if name not in hits:
                hits[name] = w
                sources.append(label)
    if any(s.startswith("base64") for s in sources):
        hits["encoded_payload"] = 0.3

    remaining = 1.0
    for w in hits.values():
        remaining *= 1 - w
    return round(1 - remaining, 3), hits, sorted(set(sources))


def check(text: str) -> GuardrailResult:
    s, hits, sources = score(text)
    flagged = s >= BLOCK_THRESHOLD
    return GuardrailResult(
        "injection", flagged, Action.BLOCK if flagged else Action.ALLOW,
        reason=(f"Injection risk {s:.2f} >= {BLOCK_THRESHOLD}: {', '.join(hits)}" if flagged
                else (f"Low risk {s:.2f}" + (f" (signals: {', '.join(hits)})" if hits else ""))),
        details={"score": s, "signals": hits, "matched_in": sources},
    )
