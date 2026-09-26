import json
import os
import time

import requests

import rag

API_URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
VLLM_URL = os.getenv("VLLM_URL", "http://vllm:8000/v1/chat/completions")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))

SYSTEM = (
    "You answer questions about the course assignment documents. "
    "Use the search_docs tool to find facts before answering, and use calculator for arithmetic. "
    "If the documents do not contain the answer, say so. "
    'Your final reply must be only JSON: {"answer": "...", "sources": ["file p.N", ...]}'
)

TOOLS = [
    {
        "name": "search_docs",
        "description": "Search the ingested documents and return the most relevant passages.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluate a basic arithmetic expression like (3+4)*2.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
]

_calls = []


def check_rate_limit():
    now = time.time()
    _calls[:] = [t for t in _calls if now - t < 60]
    if len(_calls) >= RATE_LIMIT:
        raise RuntimeError("Rate limit reached, try again in a minute.")
    _calls.append(now)


def run_tool(name, args):
    if name == "search_docs":
        return json.dumps(rag.search(args["query"]))
    if name == "calculator":
        expr = args["expression"]
        if not set(expr) <= set("0123456789+-*/(). "):
            return "invalid expression"
        try:
            return str(eval(expr, {"__builtins__": {}}))
        except Exception as e:
            return f"error: {e}"
    return "unknown tool"


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
        if "answer" in data:
            data.setdefault("sources", [])
            return data
    except json.JSONDecodeError:
        pass
    return None



def chat(messages, tools=None, force=None):
    """One call to the hosted model (Groq, OpenAI compatible). Returns the parsed JSON response."""
    body = {"model": MODEL, "messages": messages, "temperature": TEMPERATURE, "top_p": TOP_P, "max_tokens": 2048}
    if "gpt-oss" in MODEL:
        body["include_reasoning"] = True
        body["reasoning_effort"] = "low"  # hidden reasoning also counts against max_tokens
    if tools:
        body["tools"] = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}}
            for t in tools
        ]
        if force:
            body["tool_choice"] = {"type": "function", "function": {"name": force}}
    headers = {"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}
    r = requests.post(API_URL, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


def with_retry(fn, tries=6):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            resp = getattr(e, "response", None)
            client_error = resp is not None and resp.status_code < 500 and resp.status_code != 429
            if client_error or i == tries - 1:
                raise
            wait = float(resp.headers.get("retry-after", 0)) if resp is not None else 0
            time.sleep(max(wait, 3 * (i + 1)))


def ask_llm(question):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(5):  # cap tool rounds
        msg = with_retry(lambda: chat(messages, TOOLS))["choices"][0]["message"]
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": msg.get("tool_calls")}
                        if msg.get("tool_calls") else {"role": "assistant", "content": msg.get("content") or ""})
        if not msg.get("tool_calls"):
            data = parse_json(msg.get("content") or "")
            if data is None:  # ask once more for valid JSON
                messages.append({"role": "user", "content": "Reply with only the JSON object."})
                continue
            return data
        for call in msg["tool_calls"]:
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": run_tool(call["function"]["name"], args)})
    return {"answer": "Could not finish within the step limit.", "sources": []}


def ask_local(question):
    # small local model has no tool calling, so retrieve first and stuff the context
    hits = rag.search(question)
    context = "\n".join(f"[{h['source']} p.{h['page']}] {h['text']}" for h in hits)
    body = {
        "model": VLLM_MODEL,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    }
    r = requests.post(VLLM_URL, json=body, timeout=180)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return parse_json(text) or {"answer": text, "sources": []}


def ask(question):
    check_rate_limit()
    try:
        data = ask_llm(question)
        data["provider"] = "groq"
    except Exception:
        try:
            data = ask_local(question)
            data["provider"] = "vllm (fallback)"
        except Exception:
            data = {"answer": "Both models are unavailable right now.", "sources": [], "provider": "none"}
    return data
