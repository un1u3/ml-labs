"""Sensitive-topic classification.

Approach: a priority-ordered set of regex keyword classifiers. The first
(highest-priority) category that matches wins, and each category carries an
explicit handling policy. This is transparent and auditable, but it has no
understanding of context; see REPORT.md for limitations.
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from .types import Action, GuardrailResult


@dataclass(frozen=True)
class TopicPolicy:
    category: str
    action: Action
    call_llm: bool          # whether the request still goes to the model
    needs_human: bool       # route the conversation to a human agent
    message: str            # crisis/refusal text or disclaimer
    patterns: List["re.Pattern[str]"]


def _p(*pats: str) -> List["re.Pattern[str]"]:
    return [re.compile(p, re.I) for p in pats]


# Ordered by priority: safety of the person first, then legality, then the rest.
POLICIES: List[TopicPolicy] = [
    TopicPolicy(
        "self_harm", Action.ESCALATE, call_llm=False, needs_human=True,
        message=("I'm really sorry you're feeling this way. You don't have to go through it alone. "
                 "If you are in immediate danger please call your local emergency number. You can "
                 "also reach a crisis line any time (in the US call or text 988). A member of our "
                 "care team will contact you, and our Financial Hardship Program can help with debt "
                 "worries."),
        patterns=_p(r"\b(?:kill|hurt|harm)\s+myself\b", r"\bsuicid", r"\bend(?:ing)?\s+(?:my|it\s+all|my\s+own)\s*life\b",
                    r"\bend(?:ing)?\s+it\s+all\b", r"\bself[-\s]?harm", r"\b(?:don'?t|do\s+not)\s+want\s+to\s+(?:live|be\s+alive)\b",
                    r"\bno\s+reason\s+to\s+live\b", r"\bbetter\s+off\s+dead\b"),
    ),
    TopicPolicy(
        "illegal_activity", Action.BLOCK, call_llm=False, needs_human=False,
        message=("I can't help with that request because it may involve illegal activity. "
                 "If you have a question about your own account, I'm happy to help."),
        patterns=_p(r"\blaunder(?:ing)?\b", r"\b(?:evade|dodge|avoid\s+paying)\s+(?:my\s+)?tax", r"\bfake\s+(?:id|identity|documents?|pay\s*slips?)\b",
                    r"\b(?:steal|clone|skim)\s+(?:a\s+|someone'?s\s+)?(?:card|identity|credit\s+card)", r"\bphishing\b",
                    r"\b(?:structure|structuring)\s+(?:deposits|cash)", r"\bwithout\s+(?:getting\s+caught|being\s+detected|the\s+bank\s+noticing)\b",
                    r"\b(?:hack|break)\s+into\b", r"\bsomeone\s+else'?s\s+account\b"),
    ),
    TopicPolicy(
        "account_security", Action.ESCALATE, call_llm=True, needs_human=True,
        message="I've flagged this conversation for our security team, who will follow up with you.",
        patterns=_p(r"\b(?:lost|stolen|missing)\s+(?:my\s+)?(?:debit\s+|credit\s+)?card\b", r"\b(?:lose|losing)\s+(?:my\s+|the\s+)?(?:debit\s+|credit\s+)?card\b", r"\bcard\b.{0,40}\b(?:lost|stolen|lose|losing)\b",
                    r"\bunauthori[sz]ed\s+(?:transaction|charge|payment|access)", r"\b(?:transaction|charge|payment)s?\s+i\s+did\s?n[o']t\s+make\b",
                    r"\b(?:account|card)\s+(?:was\s+|has\s+been\s+)?(?:hacked|compromised)\b", r"\bidentity\s+theft\b", r"\bscam(?:med)?\b|\bfraud(?:ulent)?\b"),
    ),
    TopicPolicy(
        "financial_hardship", Action.ESCALATE, call_llm=True, needs_human=True,
        message="I've also asked a hardship specialist to reach out to you.",
        patterns=_p(r"\b(?:can'?t|cannot|unable\s+to)\s+(?:afford|pay|make)\b.{0,30}\b(?:loan|repayments?|mortgage|bills?|payments?)",
                    r"\bstruggling\s+(?:to\s+pay|with\s+(?:debt|repayments|payments))", r"\b(?:lost|losing)\s+my\s+job\b", r"\bbankrupt"),
    ),
    TopicPolicy(
        "investment_advice", Action.ALLOW_WITH_DISCLAIMER, call_llm=True, needs_human=False,
        message=("This is general information, not personal financial advice. Consider speaking with "
                 "a licensed financial adviser before making investment decisions."),
        patterns=_p(r"\bshould\s+i\s+(?:invest|buy|sell|put)\b", r"\b(?:crypto(?:currency)?|bitcoin|stocks?|shares|portfolio)\b",
                    r"\bbest\s+investment\b", r"\binvest\s+(?:all\s+)?my\b"),
    ),
    TopicPolicy(
        "legal_tax", Action.ALLOW_WITH_DISCLAIMER, call_llm=True, needs_human=False,
        message="This is not legal or tax advice. Please consult a qualified professional for your situation.",
        patterns=_p(r"\b(?:sue|lawsuit|lawyer|attorney|legal\s+action)\b", r"\btax\s+(?:return|deduct|liabilit)", r"\binheritance\b|\bwill\s+and\s+estate\b"),
    ),
]


def classify(text: str) -> Optional[TopicPolicy]:
    for policy in POLICIES:
        if any(p.search(text) for p in policy.patterns):
            return policy
    return None


def check(text: str) -> GuardrailResult:
    policy = classify(text)
    if policy is None:
        return GuardrailResult("sensitive_topic", False, Action.ALLOW, reason="No sensitive topic")
    return GuardrailResult(
        "sensitive_topic", True, policy.action,
        reason=f"Category: {policy.category}",
        details={"category": policy.category, "call_llm": policy.call_llm,
                 "needs_human": policy.needs_human, "message": policy.message},
    )
