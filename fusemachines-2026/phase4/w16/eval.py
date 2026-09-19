"""Small evaluation harness. Run with: python eval.py (needs GROQ_API_KEY)."""
import time

import agent
import rag

BAD_WORDS = ("could not", "cannot", "can't", "unable", "unavailable", "not verified", "not sure", "no information", "not found", "does not")

CASES = [
    {"name": "single fact", "q": "What stopping condition must the agentic loop have?",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and "iteration" in r["answer"].lower()},
    {"name": "two sources", "q": "Which model server does W15 require for local deployment, and what does W16 say about the evaluation harness framework?",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and "vllm" in r["answer"].lower() and "scratch" in r["answer"].lower()},
    {"name": "search plus math", "q": "W16 lists five structural failures and three failure classes. What is the total of the two counts?",
     "tools": {"search_docs", "calculator"}, "check": lambda r: r["status"] == "answered" and "8" in r["answer"]},
    {"name": "vague question", "q": "What does it say about that?",
     "tools": {"ask_user"}, "check": lambda r: r["status"] == "clarify"},
    {"name": "not in docs", "q": "What is the submission deadline for W16?",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and (not r["verified"] or any(w in r["answer"].lower() for w in BAD_WORDS))},
    {"name": "inject: search down", "q": "What stopping condition must the agentic loop have?", "inject": "down",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and (not r["verified"] or any(w in r["answer"].lower() for w in BAD_WORDS))},
    {"name": "inject: malformed", "q": "How many context engineering techniques are listed?", "inject": "malformed",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and (not r["verified"] or any(w in r["answer"].lower() for w in BAD_WORDS))},
]


def classify(res, passed):
    if passed:
        return ""
    if res.get("error") or res.get("status") == "failed":
        return "hard"
    if any(not t["ok"] for t in res.get("trace", [])):
        return "cascading soft"
    return "soft"


def main():
    rag.ingest()
    rows, failures = [], []
    for c in CASES:
        agent.FAIL_MODE = c.get("inject", "")
        start = time.time()
        try:
            res = agent.run(c["q"])
        except Exception as e:
            res = {"error": str(e), "trace": [], "iterations": 0, "tokens": 0, "status": "error", "answer": ""}
        agent.FAIL_MODE = ""
        used = {t["tool"] for t in res["trace"]}
        calls_ok = all(t["ok"] for t in res["trace"] if not c.get("inject")) and c["tools"] <= used
        passed = "error" not in res and c["check"](res)
        kind = classify(res, passed)
        rows.append((c["name"], passed, calls_ok, res["iterations"], res["tokens"], round(time.time() - start, 1)))
        if kind:
            failures.append((c["name"], kind, res.get("error") or res["answer"][:120]))

    n = len(rows)
    lines = ["# Evaluation results", "",
             f"Task completion: {sum(r[1] for r in rows)}/{n}",
             f"Tool-call correctness: {sum(r[2] for r in rows)}/{n}",
             f"Average trajectory length: {sum(r[3] for r in rows) / n:.1f} iterations",
             f"Average tokens per query: {sum(r[4] for r in rows) / n:.0f}", "",
             "| case | completed | tool calls correct | iterations | tokens | seconds |", "|---|---|---|---|---|---|"]
    lines += [f"| {r[0]} | {'yes' if r[1] else 'no'} | {'yes' if r[2] else 'no'} | {r[3]} | {r[4]} | {r[5]} |" for r in rows]
    lines += ["", "## Failure log", ""]
    lines += [f"- {f[0]}: {f[1]} ({f[2]})" for f in failures] or ["No failures."]
    open("results.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
