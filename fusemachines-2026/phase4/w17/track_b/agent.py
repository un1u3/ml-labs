import json
import os
from pathlib import Path

import requests

import assistant
import rag

PROMPTS = Path(__file__).resolve().parent / "prompts"

CONFIG = {
    "prompt_version": os.getenv("PROMPT_VERSION", "v1"),
    "model": assistant.MODEL,
    "temperature": assistant.TEMPERATURE,
    "max_iters": int(os.getenv("MAX_ITERS", "6")),
    "max_searches": 3,
    "top_k": 4,
    "chunk_chars": 600,
    "keep_results": 2,  # how many recent tool results stay in context
    "chunk_size": rag.CHUNK_SIZE,
    "chunk_overlap": rag.CHUNK_OVERLAP,
}
FAIL_MODE = ""  # "", "down" or "malformed", used by the failure injection test
SYSTEM = (PROMPTS / f"prompt_{CONFIG['prompt_version']}.txt").read_text()


def configure(**cfg):
    global SYSTEM
    CONFIG.update(cfg)
    SYSTEM = (PROMPTS / f"prompt_{CONFIG['prompt_version']}.txt").read_text()
    assistant.MODEL = CONFIG["model"]
    assistant.TEMPERATURE = CONFIG["temperature"]
    rag.use_chunking(CONFIG["chunk_size"], CONFIG["chunk_overlap"])
    return CONFIG


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
        hits = rag.search(args["query"], k=CONFIG["top_k"])  # cap the number of passages
        for h in hits:
            h["text"] = h["text"][:CONFIG["chunk_chars"]]  # and the size of each one
        return json.dumps(hits), bool(hits)
    result = assistant.run_tool(name, args)
    return result, not result.startswith(("error", "invalid"))


def clear_old_results(messages):
    tool_msgs = [m for m in messages if m["role"] == "tool"]
    for m in tool_msgs[:-CONFIG["keep_results"]] if CONFIG["keep_results"] else tool_msgs:
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
                    "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}}
    except Exception:
        pass
    return None


def reasoning_of(msg):
    return (msg.get("reasoning") or msg.get("content") or "").strip()


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

    trace = []
    out = {"tokens": 0, "input_tokens": 0, "output_tokens": 0, "trace": trace, "iterations": 0,
           "messages": messages, "question": question, "config": dict(CONFIG)}

    def finish(status, termination, **data):
        return {**out, "status": status, "termination": termination, **data}

    max_iters = CONFIG["max_iters"]
    force_next = False
    for it in range(1, max_iters + 1):
        clear_old_results(messages)
        full = [{"role": "system", "content": SYSTEM}] + messages
        force = "final_answer" if (it == max_iters or force_next) else None  # force an answer
        force_next = False
        try:
            resp = assistant.with_retry(lambda: assistant.chat(full, TOOLS, force))
        except requests.HTTPError as e:
            resp = salvage(e)
            if resp is None:  # bad tool call from the model, tell it and try again
                out["iterations"] = it
                trace.append({"step": it, "tool": "<invalid>", "args": {}, "ok": False,
                              "result": str(e)[:300], "reasoning": ""})
                messages.append({"role": "user", "content": "Use only the tools you were given."})
                continue
        msg = resp["choices"][0]["message"]
        usage = resp["usage"]
        out["tokens"] += usage.get("total_tokens", 0)
        out["input_tokens"] += usage.get("prompt_tokens", 0)
        out["output_tokens"] += usage.get("completion_tokens", 0)
        out["iterations"] = it
        reason = reasoning_of(msg)
        calls = msg.get("tool_calls")
        stored = {"role": "assistant", "content": msg.get("content") or ""}
        if calls:
            stored["tool_calls"] = calls
        messages.append(stored)

        if not calls:  # model answered in plain text instead of calling final_answer
            text = msg.get("content") or ""
            if not text.strip():
                trace.append({"step": it, "tool": "<none>", "args": {}, "ok": False,
                              "result": "empty reply, forcing final_answer", "reasoning": reason})
                messages.append({"role": "user", "content": "Call final_answer with your answer."})
                force_next = True
                continue
            data = assistant.parse_json(text) or {"answer": text, "sources": []}
            data["verified"] = bool(data.get("verified", False))
            trace.append({"step": it, "tool": "<plain text>", "args": {}, "ok": True, "result": text[:500],
                          "reasoning": reason})
            return finish("answered", "plain_text_answer", **data)

        for call in calls:
            if call["function"]["name"] == "final_answer":
                args = parse_args(call)
                trace.append({"step": it, "tool": "final_answer", "args": args, "ok": bool(args.get("answer")),
                              "result": "done", "reasoning": reason})
                for c in calls:  # close every tool call so the history stays valid
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": "done"})
                return finish("answered", "forced_final_answer" if force else "final_answer",
                              answer=args.get("answer", ""), sources=args.get("sources") or [],
                              verified=bool(args.get("verified")))
        for call in calls:
            if call["function"]["name"] == "ask_user":
                q = parse_args(call).get("question", "")
                trace.append({"step": it, "tool": "ask_user", "args": {"question": q}, "ok": bool(q),
                              "result": "waiting for user", "reasoning": reason})
                return finish("clarify", "ask_user", answer=q, sources=[], verified=False)
        for call in calls:
            name, args = call["function"]["name"], parse_args(call)
            if name == "search_docs" and sum(t["tool"] == "search_docs" for t in trace) >= CONFIG["max_searches"]:
                content, ok = "search limit reached, call final_answer now", True
            else:
                content, ok = run_tool(name, args)
            trace.append({"step": it, "tool": name, "args": args, "ok": ok, "result": content,
                          "reasoning": reason})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})

    return finish("failed", "max_iterations", answer="Stopped after reaching the step limit.",
                  sources=[], verified=False)
