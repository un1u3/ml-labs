"""Shared result types for every guardrail."""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional


class Action(str, Enum):
    ALLOW = "allow"                                   # pass through unchanged
    REDACT = "redact"                                 # mask the offending spans and continue
    BLOCK = "block"                                   # refuse the request / response
    ESCALATE = "escalate"                             # safe response + route to a human
    ALLOW_WITH_DISCLAIMER = "allow_with_disclaimer"   # answer, but append a disclaimer
    REGENERATE = "regenerate"                         # ask the model to try again
    FALLBACK = "fallback"                             # return a static safe answer


@dataclass
class GuardrailResult:
    """Uniform result returned by every guardrail.

    `flagged` is the binary decision used for evaluation metrics; `action` is
    what the pipeline does about it.
    """
    name: str
    flagged: bool
    action: Action
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    sanitized_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        return d
