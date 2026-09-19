import json
import os

import requests

import assistant
import rag

MAX_ITERS = int(os.getenv("MAX_ITERS", "6"))
MAX_SEARCHES = 3
KEEP_RESULTS = 2  # how many recent tool results stay in context
FAIL_MODE = ""  # "", "down" or "malformed", used by the failure injection test

SYSTEM = (
    "You answer questions about the course assignment documents by working in steps.\n"
    "1. Search with search_docs. Look at what came back and decide if it really answers the question.\n"
    "2. If it does not, search again with a different query. Do not repeat the same query.\n"
    "3. Use calculator for arithmetic.\n"
    "4. If the question is too vague to search (for example it says 'that' with no context), call ask_user "
    "on its own and wait.\n"
    "5. Before you finish, check every claim in your draft against the passages you found.\n"
    "6. If a tool errors or returns nothing usable, do not guess. Say you could not verify it.\n"
    "7. Do at most 3 searches. If you still cannot confirm the answer, finish anyway with verified set to false.\n"
    "Old tool results are removed from your context after a couple of steps, so write down the facts you "
    "need in your own text before moving on.\n"
    "When you are done, call final_answer. Never write the final answer as plain text."
)

TOOLS = assistant.TOOLS + [
    {
        "name": "final_answer",
        "description": "Give the final answer to the user. This ends the task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
                "verified": {"type": "boolean"},
            },
            "required": ["answer", "verified"],
        },
    },
    {
        "name": "ask_user",
        "description": "Ask the user a clarifying question when the request is too vague.",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    }
]

REQUIRED_ARG = {"search_docs": "query", "calculator": "expression", "ask_user": "question", "final_answer": "answer"}


def run_tool(name, args):
    """Returns (result text, ok). ok is False when the call was invalid or gave nothing usable."""
    key = REQUIRED_ARG.get(name)
    if key is None or not isinstance(args.get(key), str) or not args[key].strip():
        return "invalid tool call", False
    if name == "search_docs":
        if FAIL_MODE == "down":
            return "error: search service unavailable", False
        if FAIL_MODE == "malformed":
            return "@@#{{ null ]]", False
        hits = rag.search(args["query"], k=4)  # cap the number of passages
        for h in hits:
            h["text"] = h["text"][:600]  # and the size of each one
        return json.dumps(hits), bool(hits)
    result = assistant.run_tool(name, args)
    return result, not result.startswith(("error", "invalid"))


def clear_old_results(messages):
    tool_msgs = [m for m in messages if m["role"] == "tool"]
    for m in tool_msgs[:-KEEP_RESULTS]:
        m["content"] = "[old result cleared]"


def parse_args(call):
    try:
        args = json.loads(call["function"]["arguments"] or "{}")
        return args if isinstance(args, dict) else {}
    except json.JSONDecodeError:
        return {}


def salvage(err):
    """The model sometimes calls a made up tool (like 'json') with the final answer as arguments.
    If the arguments look like an answer, turn it into a normal final_answer call."""
    try:
        gen = json.loads(err.response.json()["error"]["failed_generation"])
        args = gen["arguments"]
        if isinstance(args, dict) and args.get("answer"):
            call = {"id": "salvaged", "type": "function",
                    "function": {"name": "final_answer", "arguments": json.dumps(args)}}
            return {"choices": [{"message": {"content": "", "tool_calls": [call]}}],
                    "usage": {"total_tokens": 0}}
    except Exception:
        pass
    return None


def run(question, messages=None):
    """One user turn. messages is the running history so a clarification can continue later."""
    messages = messages if messages is not None else []
    last = messages[-1] if messages else None
    if last and last["role"] == "assistant" and last.get("tool_calls"):
        # the last turn ended with ask_user, so this message is the answer to it
        for call in last["tool_calls"]:
            answer = question if call["function"]["name"] == "ask_user" else "skipped, asked the user first"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": answer})
    else:
        messages.append({"role": "user", "content": question})

    tokens, trace = 0, []
    out = {"tokens": 0, "trace": trace, "iterations": 0, "messages": messages}

    force_next = False
    for it in range(1, MAX_ITERS + 1):
        clear_old_results(messages)
        full = [{"role": "system", "content": SYSTEM}] + messages
        force = "final_answer" if (it == MAX_ITERS or force_next) else None  # force an answer
        force_next = False
        try:
            resp = assistant.with_retry(lambda: assistant.chat(full, TOOLS, force))
        except requests.HTTPError as e:
            resp = salvage(e)
            if resp is None:  # bad tool call from the model, tell it and try again
                out["iterations"] = it
                messages.append({"role": "user", "content": "Use only the tools you were given."})
                continue
        msg = resp["choices"][0]["message"]
        tokens += resp["usage"]["total_tokens"]
        out.update(tokens=tokens, iterations=it)
        calls = msg.get("tool_calls")
        stored = {"role": "assistant", "content": msg.get("content") or ""}
        if calls:
            stored["tool_calls"] = calls
        messages.append(stored)

        if not calls:  # model answered in plain text instead of calling final_answer
            text = msg.get("content") or ""
            if not text.strip():
                messages.append({"role": "user", "content": "Call final_answer with your answer."})
                force_next = True
                continue
            data = assistant.parse_json(text) or {"answer": text, "sources": []}
            data["verified"] = bool(data.get("verified", False))
            return {**out, "status": "answered", **data}

        for call in calls:
            if call["function"]["name"] == "final_answer":
                args = parse_args(call)
                trace.append({"tool": "final_answer", "args": args, "ok": bool(args.get("answer"))})
                for c in calls:  # close every tool call so the history stays valid
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": "done"})
                return {**out, "status": "answered", "answer": args.get("answer", ""),
                        "sources": args.get("sources") or [], "verified": bool(args.get("verified"))}
        for call in calls:
            if call["function"]["name"] == "ask_user":
                q = parse_args(call).get("question", "")
                trace.append({"tool": "ask_user", "args": {"question": q}, "ok": bool(q)})
                return {**out, "status": "clarify", "answer": q, "sources": [], "verified": False}
        for call in calls:
            name, args = call["function"]["name"], parse_args(call)
            if name == "search_docs" and sum(t["tool"] == "search_docs" for t in trace) >= MAX_SEARCHES:
                content, ok = "search limit reached, call final_answer now", True
            else:
                content, ok = run_tool(name, args)
            trace.append({"tool": name, "args": args, "ok": ok})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})

    return {**out, "status": "failed", "answer": "Stopped after reaching the step limit.",
            "sources": [], "verified": False}
