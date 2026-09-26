"""Run with: uv run python eval.py v1 (needs GROQ_API_KEY)."""
import sys
import time

import agent
import config

BAD_WORDS = ("could not", "cannot", "can't", "unable", "unavailable", "not verified", "not sure", "no information",
             "not found", "does not", "doesn't", "not mention", "not specified", "not state", "not provide")


def admits(r):
    return not r["verified"] or any(w in r["answer"].lower() for w in BAD_WORDS)


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
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and admits(r)},
    {"name": "inject: search down", "q": "What stopping condition must the agentic loop have?", "inject": "down",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and admits(r)},
    {"name": "inject: malformed", "q": "How many context engineering techniques are listed?", "inject": "malformed",
     "tools": {"search_docs"}, "check": lambda r: r["status"] == "answered" and admits(r)},
]


def classify(res, passed):
    if passed:
        return ""
    if res.get("error") or res.get("status") == "failed":
        return "hard"
    if any(not t["ok"] for t in res.get("trace", [])):
        return "cascading soft"
    return "soft"


def evaluate(cases=CASES):
    results = []
    for c in cases:
        agent.FAIL_MODE = c.get("inject", "")
        start = time.time()
        try:
            res = agent.run(c["q"])
        except Exception as e:
            res = {"error": str(e), "trace": [], "iterations": 0, "tokens": 0, "input_tokens": 0,
                   "output_tokens": 0, "status": "error", "termination": "exception", "answer": "",
                   "sources": [], "verified": False, "question": c["q"]}
        agent.FAIL_MODE = ""
        res.pop("messages", None)
        used = {t["tool"] for t in res["trace"]}
        calls_ok = all(t["ok"] for t in res["trace"] if not c.get("inject")) and c["tools"] <= used
        passed = "error" not in res and c["check"](res)
        results.append({**res, "case": c["name"], "passed": passed, "tool_calls_correct": calls_ok,
                        "failure": classify(res, passed), "seconds": round(time.time() - start, 1),
                        "cost_usd": config.cost(res["input_tokens"], res["output_tokens"], res["config"]["model"])})
    return results


def summarize(results):
    n = len(results)
    return {
        "task_completion": sum(r["passed"] for r in results) / n,
        "tool_call_correctness": sum(r["tool_calls_correct"] for r in results) / n,
        "avg_iterations": sum(r["iterations"] for r in results) / n,
        "avg_tokens": sum(r["tokens"] for r in results) / n,
        "avg_seconds": sum(r["seconds"] for r in results) / n,
        "total_cost_usd": sum(r["cost_usd"] for r in results),
        "hard_failures": sum(r["failure"] == "hard" for r in results),
        "soft_failures": sum(r["failure"] == "soft" for r in results),
        "cascading_soft_failures": sum(r["failure"] == "cascading soft" for r in results),
        "max_iteration_hits": sum(r.get("termination") == "max_iterations" or
                                  r.get("termination") == "forced_final_answer" for r in results),
    }


def report(results, title="Evaluation results"):
    s, n = summarize(results), len(results)
    lines = [f"# {title}", "",
             f"Task completion: {sum(r['passed'] for r in results)}/{n}",
             f"Tool-call correctness: {sum(r['tool_calls_correct'] for r in results)}/{n}",
             f"Average trajectory length: {s['avg_iterations']:.1f} iterations",
             f"Average tokens per query: {s['avg_tokens']:.0f}",
             f"Total cost: ${s['total_cost_usd']:.4f}", "",
             "| case | completed | tool calls correct | iterations | termination | tokens | seconds |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['case']} | {'yes' if r['passed'] else 'no'} | {'yes' if r['tool_calls_correct'] else 'no'} | "
              f"{r['iterations']} | {r.get('termination', '')} | {r['tokens']} | {r['seconds']} |" for r in results]
    lines += ["", "## Failure log", ""]
    lines += [f"- {r['case']}: {r['failure']} ({(r.get('error') or r['answer'])[:160]})"
              for r in results if r["failure"]] or ["No failures."]
    return "\n".join(lines) + "\n"


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else config.PRODUCTION_VERSION
    agent.configure(**config.VERSIONS[version])
    text = report(evaluate(), f"Evaluation results ({version})")
    open("results.md", "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
