# Course Assistant (W16)

The W15 RAG assistant with an added agentic loop (`agent.py`). Everything from W15 (ingestion, ChromaDB, vLLM fallback, Docker) is still here, see the W15 notes at the bottom.

## Architecture

```
 user --> Streamlit (app.py, keeps chat history)
              |
              v
        agent.py loop  (max 6 iterations)
   +------------------------------------------+
   |  clear old tool results                  |
   |  Claude decides next step                |
   |     |-- search_docs --> ChromaDB (top 3, |
   |     |                    400 chars each) |
   |     |-- calculator                       |
   |     |-- ask_user  --> stop, show question|
   |     '-- final JSON --> stop              |
   |  tool result goes back into the loop     |
   +------------------------------------------+
              |
              v
   answer + sources + verified flag
```

Single agent, one loop. The W15 vLLM fallback is not used inside the loop (the tiny local model cannot do tool calling), only by the old `assistant.py` path.

## The new feature: verify before answering

Why a fixed pipeline is not enough: whether one search is enough, whether a second query is needed, and whether the question is even answerable depends on what the previous search returned, so the number and order of steps cannot be decided in advance.

The agent searches, judges whether the passages answer the question, searches again with a new query if not, does arithmetic with the calculator, asks the user when the question is too vague, and checks its draft against the passages before answering. The reply includes a `verified` flag. If it cannot verify something it has to say so.

## a. Context engineering technique

**Clearing tool results, plus capping retrieval.** In `agent.run`, `clear_old_results` replaces every tool result older than the last two with a stub before each model call. `search_docs` also returns only 3 passages of at most 400 characters. Each search result is about a full page of text, and over 6 iterations they piled up and pushed the question out of focus and raised the token count. The system prompt tells the model to write down the facts it needs in its own text before moving on, since the raw result will be gone.

## b. Agentic pattern

**Single-agent loop.** The documents are small and the steps depend on each other (search, then judge, then search again), so splitting into agents would add coordination tokens without a real gain. Context saturation is handled by clearing and capping instead of a sub-agent. The one weakness from the five failures list that applies is the self-verification paradox: the same model checks its own draft. I reduced it by making it verify against retrieved passages instead of its own memory, but it is not fully removed.

## c. Evaluation harness

`eval.py` was written from scratch (no framework). It runs 7 cases (single fact, two sources, search plus math, vague question, not in docs, two injected failures) and writes `results.md` with:

- task completion rate (each case has its own pass check)
- tool-call correctness (valid tool name and arguments, and the expected tools were used)
- trajectory length (iterations per query)
- tokens per query (input plus output, summed over all iterations)
- a failure log, classified as **hard** (exception or hit the step limit), **cascading soft** (wrong answer after a tool call earlier in the run errored or came back empty), or **soft** (wrong answer with no bad tool call)

Results are in `results.md` after running `python eval.py`.

## Additional requirements

1. **Skill vs agent:** the verify-and-retry behavior could not be a Skill, because a Skill only loads instructions into context and this feature needs the model to run tools in a loop and react to their results. I did not add a separate agent either, the loop is one agent with three tools.
2. **Token accounting:** tokens are recorded per query in the eval table and shown in the UI. It is a single agent, so there is no multi-agent comparison to make.
3. **Failure injection:** `FAIL_MODE` in `agent.py` makes `search_docs` return either an error ("down") or garbage ("malformed"). The eval has one case for each. The pass condition is that the agent either sets `verified` to false or says it could not verify, instead of answering confidently. The observed behavior is in `results.md`.
4. **Tool vs agent boundary:** ChromaDB is stateful, but I treat it as a bounded tool call. `search_docs` takes one query and returns once, with no memory between calls, so the model only needs its result and not a conversation with it. The Claude API is the model itself and not a service the agent talks to. Modeling search as its own agent would add a hop and tokens for something that is one lookup.

## How to run

```
export ANTHROPIC_API_KEY=your_key_here
docker compose up --build      # UI on http://localhost:8501
python eval.py                 # writes results.md (run inside the app container or a venv)
```

Inside Docker: `docker compose run --rm app python eval.py`.

## W15 notes
### How it works

- **Ingestion and chunking:** `rag.py` reads each PDF page with pypdf and splits it into 150 word chunks with 30 words of overlap. Chunks are embedded with Chroma's default embedding model and stored in a persistent ChromaDB collection.
- **LLM integration:** `assistant.py` calls Claude through the Anthropic SDK. The model name comes from `CLAUDE_MODEL`.
- **Prompt engineering:** the system prompt tells the model to search before answering, admit when the docs do not have the answer, and reply in a fixed JSON shape. Temperature defaults to 0.2 and is set through `TEMPERATURE`. `top_p` (`TOP_P`, default 0.9) is sent to the vLLM model. It is not sent to Claude because some Claude models reject having both temperature and top_p set.
- **Structured output:** the final reply must be `{"answer": ..., "sources": [...]}`. It is parsed, and if parsing fails the model is asked once more for valid JSON.
- **Tool calling:** Claude has two tools, `search_docs` (queries ChromaDB) and `calculator`. The tool loop is capped at 5 rounds.
- **Local deployment:** the `vllm` service in `docker-compose.yml` serves `Qwen/Qwen2.5-0.5B-Instruct` on CPU through vLLM's OpenAI compatible API. This machine has no GPU and 6 GB of RAM, so a very small model is used. It has no tool calling, so retrieved chunks are put directly in the prompt.

### Production features (Task 2)

- **UI:** Streamlit, connected directly to `assistant.ask`.
- **Retry:** each Claude call retries 3 times with exponential backoff.
- **Rate limiting:** in memory limit of 20 requests per minute (`RATE_LIMIT_PER_MIN`).
- **Fallback:** if Claude fails after retries, the question goes to the local vLLM model. If that also fails, the user sees a plain message instead of a stack trace. The UI shows which model answered.
- **Concurrency:** Streamlit runs each user session in its own thread, and the calls are simple blocking requests, so several users can be served at once. There is no batching layer.
- **ONNX:** not applied. The models are served through the Claude API and vLLM, and I did not train a model of my own. Chroma's default embedder already runs on ONNX runtime.
- **Caching:** not implemented (it was optional).

### Run it

You need Docker and an Anthropic API key.

```
export ANTHROPIC_API_KEY=your_key_here
docker compose up --build
```

Then open http://localhost:8501. The first start downloads the embedding model and the Qwen weights, so it takes a few minutes. The vLLM CPU image tag in the compose file may need updating, check the vLLM docs for the current CPU image.

To run without Docker: `pip install -r requirements.txt`, then `streamlit run app.py`. The vLLM fallback will not be reachable unless you set `VLLM_URL`.

### Files

- `agent.py`: the W16 agentic loop
- `eval.py`: evaluation harness
- `app.py`: Streamlit UI (now uses the agent)
- `assistant.py`: Claude calls, tools, JSON parsing, retry, rate limit, fallback
- `rag.py`: ingestion, chunking, ChromaDB search
- `docs/`: the PDFs that get ingested
- `Dockerfile`, `docker-compose.yml`
