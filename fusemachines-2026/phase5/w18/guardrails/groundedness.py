"""Groundedness validation: are the answer's claims supported by the sources?

Approach (lexical, no extra model):
  1. Split the answer into sentence-level claims; skip non-factual sentences
     (questions, "I don't have that information").
  2. Lexical support: share of the claim's content words (stop words removed,
     light stemming) that appear in the cited documents.
  3. Numeric check: every number in the claim ($25, 4.2%, 10) must appear in
     the cited documents. Hallucinated figures are the most damaging error in
     a banking assistant, so this is a hard rule.
  4. Polarity check: if the claim and its best-matching source sentence
     disagree on negation ("is available" vs "is not available") the claim is
     treated as contradicted.
A response is grounded only if every claim passes.
"""
import re
from typing import Dict, Iterable, List, Set, Tuple

from .types import Action, GuardrailResult

SUPPORT_THRESHOLD = 0.6

STOPWORDS = set("""
a an the and or but if then so of to in on at by for with from as is are was were be been being
it its this that these those there here you your yours we our us i me my they them their he she
his her can could will would shall should may might must do does did done has have had having
also any all each per such than too very just about into over under up down out more most less
which who whom what when where why how please kestrel bank s t
""".split())
NEGATIONS = {"not", "no", "never", "cannot", "none", "without", "nor"}
_CONTRACTIONS = [(r"\bcan't\b", "can not"), (r"\bwon't\b", "will not"), (r"n't\b", " not")]
_NON_CLAIM = re.compile(
    r"(?i)^(?:i\s+(?:do\s+not|don'?t|cannot|can'?t)\s+have\s+(?:any\s+)?(?:information|details)|i'?m\s+not\s+sure|"
    r"i\s+couldn'?t\s+find|is\s+there\s+anything\s+else|let\s+me\s+know|hope\s+this\s+helps)")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_PLACEHOLDER = re.compile(r"\[[A-Z_]+_\d+\]")  # redaction markers such as [EMAIL_1]


def _expand(text: str) -> str:
    t = text.lower().replace("’", "'")
    for pat, rep in _CONTRACTIONS:
        t = re.sub(pat, rep, t)
    return t


def _stem(w: str) -> str:
    for suf, rep in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + rep
    return w


def content_tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-z]+", _expand(text))
    return {_stem(w) for w in words if w not in STOPWORDS and w not in NEGATIONS and len(w) > 1}


def numbers(text: str) -> Set[str]:
    return {n.replace(",", "") for n in _NUM.findall(text)}


def has_negation(text: str) -> bool:
    return bool(set(re.findall(r"[a-z]+", _expand(text))) & NEGATIONS)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def is_claim(sentence: str) -> bool:
    if sentence.endswith("?") or _NON_CLAIM.search(sentence):
        return False
    return len(content_tokens(sentence)) >= 2


def assess_claim(claim: str, source_sentences: List[str]) -> Dict:
    toks = content_tokens(claim)
    src_tokens = set().union(*(content_tokens(s) for s in source_sentences)) if source_sentences else set()
    support = len(toks & src_tokens) / len(toks) if toks else 1.0

    missing_numbers = sorted(numbers(claim) - set().union(*(numbers(s) for s in source_sentences))) if source_sentences else sorted(numbers(claim))

    best, best_overlap = "", -1.0
    for s in source_sentences:
        st = content_tokens(s)
        ov = len(toks & st) / len(toks | st) if toks | st else 0.0
        if ov > best_overlap:
            best, best_overlap = s, ov
    polarity_conflict = bool(best) and best_overlap >= 0.3 and has_negation(claim) != has_negation(best)

    reasons = []
    if support < SUPPORT_THRESHOLD:
        reasons.append(f"low lexical support {support:.2f}")
    if missing_numbers:
        reasons.append(f"numbers not in sources: {', '.join(missing_numbers)}")
    if polarity_conflict:
        reasons.append("negation conflicts with source")
    return {"claim": claim, "support": round(support, 2), "best_source": best,
            "supported": not reasons, "reasons": reasons}


def check(answer: str, citations: Iterable[str], documents: Dict[str, str]) -> GuardrailResult:
    """`documents` maps doc_id -> text for the documents retrieved this turn."""
    cited = [documents[c] for c in citations if c in documents]
    source_sentences = [s for doc in cited for s in split_sentences(doc)]
    claims = [s for s in split_sentences(_PLACEHOLDER.sub("", answer)) if is_claim(s)]

    if claims and not source_sentences:
        return GuardrailResult(
            "groundedness", True, Action.REGENERATE,
            reason="Answer makes factual claims but cites no retrieved source",
            details={"claims": [{"claim": c, "supported": False, "reasons": ["no citation"]} for c in claims]})

    results = [assess_claim(c, source_sentences) for c in claims]
    unsupported = [r for r in results if not r["supported"]]
    flagged = bool(unsupported)
    return GuardrailResult(
        "groundedness", flagged, Action.REGENERATE if flagged else Action.ALLOW,
        reason=(f"{len(unsupported)}/{len(results)} claims unsupported" if flagged
                else f"All {len(results)} claims supported"),
        details={"claims": results},
    )
