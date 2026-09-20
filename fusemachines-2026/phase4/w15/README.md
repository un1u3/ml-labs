# Course Assistant (W15)

A small RAG assistant that answers questions about the assignment PDFs in `docs/`. A Groq hosted model (`openai/gpt-oss-120b`) is the main model, and a local vLLM model is the fallback.

## Architecture

```
            +-------------------+
 user ----> |  Streamlit (app)  |
            +---------+---------+
                      |
                      v
              assistant.py
       (rate limit, retry, fallback)
             |                  |
     primary |                  | fallback
             v                  v
     Groq API              vLLM (CPU, Qwen2.5-0.5B)
   (tool calling)          (context stuffed in prompt)
        |    |                   |
   search_docs  calculator       |
        |                        |
        +-----------+------------+
                    v
                rag.py  ->  ChromaDB (embeddings)
                    ^
            docs/*.pdf (chunked at startup)
```

## How it works

- **Ingestion and chunking:** `rag.py` reads each PDF page with pypdf and splits it into 80 word chunks with 20 words of overlap. Chunks are embedded with Chroma's default embedding model and stored in a persistent ChromaDB collection.
- **LLM integration:** `assistant.py` calls Groq's OpenAI compatible chat endpoint with `requests`. The model name comes from `LLM_MODEL`.
- **Prompt engineering:** the system prompt tells the model to search before answering, admit when the docs do not have the answer, and reply in a fixed JSON shape. Temperature defaults to 0.2 and is set through `TEMPERATURE`. `top_p` (`TOP_P`, default 0.9) is sent with every request.
- **Structured output:** the final reply must be `{"answer": ..., "sources": [...]}`. It is parsed, and if parsing fails the model is asked once more for valid JSON.
- **Tool calling:** The model has two tools, `search_docs` (queries ChromaDB) and `calculator`. The tool loop is capped at 5 rounds.
- **Local deployment:** the `vllm` service in `docker-compose.yml` serves `Qwen/Qwen2.5-0.5B-Instruct` on CPU through vLLM's OpenAI compatible API. This machine has no GPU and 6 GB of RAM, so a very small model is used. It has no tool calling, so retrieved chunks are put directly in the prompt.

## Production features (Task 2)

- **UI:** Streamlit, connected directly to `assistant.ask`.
- **Retry:** each model call retries up to 4 times with a growing delay. Groq's free tier has a tokens per minute limit, so 429 errors do happen. Client errors (4xx other than 429) are not retried.
- **Rate limiting:** in memory limit of 20 requests per minute (`RATE_LIMIT_PER_MIN`).
- **Fallback:** if Groq fails after retries, the question goes to the local vLLM model. If that also fails, the user sees a plain message instead of a stack trace. The UI shows which model answered.
- **Concurrency:** Streamlit runs each user session in its own thread, and the calls are simple blocking requests, so several users can be served at once. There is no batching layer.
- **ONNX:** not applied. The models are served through the Groq API and vLLM, and I did not train a model of my own. Chroma's default embedder already runs on ONNX runtime.
- **Caching:** not implemented (it was optional).

## Run it

You need Docker and a Groq API key.

```
export GROQ_API_KEY=your_key_here
docker compose up --build
```

Then open http://localhost:8501. The first start downloads the embedding model and the Qwen weights, so it takes a few minutes. The vLLM CPU image tag in the compose file may need updating, check the vLLM docs for the current CPU image.

To run without Docker: `pip install -r requirements.txt`, then `streamlit run app.py`. The vLLM fallback will not be reachable unless you set `VLLM_URL`.

## Files

- `app.py`: Streamlit UI
- `assistant.py`: Groq calls, tools, JSON parsing, retry, rate limit, fallback
- `rag.py`: ingestion, chunking, ChromaDB search
- `docs/`: the PDFs that get ingested
- `Dockerfile`, `docker-compose.yml`
