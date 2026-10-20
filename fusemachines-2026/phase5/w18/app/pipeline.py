"""Guarded request pipeline.

    user text
      -> [input]  PII redaction -> prompt-injection check -> sensitive-topic policy
      -> retrieval (on redacted text)
      -> LLM (sees only redacted text + retrieved documents)
      -> [output] schema validation -> sensitive-information check (redact, or block -> fallback)
                  -> groundedness   (schema / groundedness failure: regenerate once, else fallback)
      -> topic disclaimer / escalation flag -> audit log -> response
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardrails import groundedness, injection, output_sensitive, pii, schema, topics
from guardrails.types import Action, GuardrailResult

from .audit import AuditLogger
from .knowledge_base import KnowledgeBase
from .llm import CANARY, SYSTEM_PROMPT, LLMClient, MockLLM

MAX_ATTEMPTS = 2  # first try + one regeneration

INJECTION_REFUSAL = ("I can't follow that request. I can only help with questions about Kestrel Bank "
                     "products and your accounts.")
FALLBACK_ANSWER = ("I'm sorry, I couldn't produce a verified answer to that. I've passed your question "
                   "to a support agent, or you can reach us at support@kestrelbank.example.")


@dataclass
class PipelineResult:
    status: str                       # answered | escalated | refused | fallback
    answer: str
    citations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_human: bool = False
    notices: List[str] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    attempts: int = 0
    llm_input: Optional[str] = None   # exactly what the model saw (redacted)
    retrieved: List[str] = field(default_factory=list)

    def flagged(self, name: str) -> bool:
        return any(t["name"] == name and t["flagged"] for t in self.trace)

    def public(self) -> Dict[str, Any]:
        return {"status": self.status, "answer": self.answer, "citations": self.citations,
                "confidence": self.confidence, "needs_human": self.needs_human, "notices": self.notices}


class GuardedAssistant:
    def __init__(self, llm: Optional[LLMClient] = None, kb: Optional[KnowledgeBase] = None,
                 audit_path: Optional[Path] = None):
        self.llm = llm or MockLLM()
        self.kb = kb or KnowledgeBase()
        self.audit = AuditLogger(audit_path)

    def handle(self, text: str) -> PipelineResult:
        trace: List[Dict[str, Any]] = []

        def record(r: GuardrailResult, stage: str, attempt: Optional[int] = None) -> GuardrailResult:
            d = r.to_dict()
            d.pop("sanitized_text", None)
            d["stage"] = stage
            if attempt is not None:
                d["attempt"] = attempt
            trace.append(d)
            return r

        # ---------------- input guardrails ----------------
        pii_r = record(pii.check_input(text), "input")
        clean = pii_r.sanitized_text
        notices = [pii_r.details["user_notice"]] if pii_r.details.get("user_notice") else []
        inj_r = record(injection.check(text), "input")
        topic_r = record(topics.check(clean), "input")

        if inj_r.action == Action.BLOCK:
            return self._finish(text, clean, trace, PipelineResult("refused", INJECTION_REFUSAL, notices=notices))
        if topic_r.flagged and not topic_r.details["call_llm"]:
            status = "refused" if topic_r.action == Action.BLOCK else "escalated"
            return self._finish(text, clean, trace, PipelineResult(
                status, topic_r.details["message"], needs_human=topic_r.details["needs_human"], notices=notices))

        # ---------------- generation + output guardrails ----------------
        docs = self.kb.search(clean)
        doc_map = {d.id: d.text for d in docs}
        feedback, accepted = None, None
        attempts = 0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            attempts = attempt
            raw = self.llm.generate(clean, docs, feedback)
            sch = record(schema.validate(raw, doc_map), "output", attempt)
            if sch.flagged:
                feedback = sch.reason
                continue
            parsed = sch.details["parsed"]
            # Sensitive-information check runs on every candidate, before groundedness, so a
            # leak is detected (and logged) even when the draft is later rejected for other reasons.
            sens = record(output_sensitive.check(parsed["answer"], SYSTEM_PROMPT, CANARY, doc_map.values()), "output", attempt)
            if sens.action == Action.BLOCK:
                break
            if sens.action == Action.REDACT:
                parsed["answer"] = sens.sanitized_text
            gr = record(groundedness.check(parsed["answer"], parsed["citations"], doc_map), "output", attempt)
            if gr.flagged:
                bad = [c["claim"] for c in gr.details["claims"] if not c["supported"]]
                feedback = "these claims are not supported by the documents: " + " | ".join(bad)
                continue
            accepted = parsed
            break

        base = dict(notices=notices, attempts=attempts, llm_input=clean, retrieved=list(doc_map))
        if accepted is None:
            # Covers both exhausted regenerations and a confidential-context leak (never retried:
            # a leak suggests the model has been manipulated, so we do not give it another try).
            return self._finish(text, clean, trace, PipelineResult("fallback", FALLBACK_ANSWER, needs_human=True, **base))

        result = PipelineResult("answered", accepted["answer"], accepted["citations"], float(accepted["confidence"]),
                                accepted["needs_human"], **base)
        if topic_r.flagged:
            result.answer += "\n\n" + topic_r.details["message"]
            if topic_r.details["needs_human"]:
                result.needs_human = True
                result.status = "escalated"
        return self._finish(text, clean, trace, result)

    def _finish(self, original: str, clean: str, trace: List[Dict[str, Any]], result: PipelineResult) -> PipelineResult:
        result.trace = trace
        self.audit.log(original, {
            "input_redacted": clean,
            "status": result.status,
            "flagged": sorted({t["name"] for t in trace if t["flagged"]}),
            "attempts": result.attempts,
            "citations": result.citations,
        })
        return result
