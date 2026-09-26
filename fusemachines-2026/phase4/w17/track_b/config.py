import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{ROOT / 'mlflow.db'}")
ARTIFACT_ROOT = (ROOT / "mlartifacts").as_uri()
EXPERIMENT = "course-assistant-prompts"
REPORTS = ROOT / "reports"

BASE = {"model": "openai/gpt-oss-120b", "temperature": 0.2, "max_iters": 6, "max_searches": 3,
        "top_k": 4, "chunk_chars": 600, "keep_results": 2, "chunk_size": 80, "chunk_overlap": 20}
VERSIONS = {
    "v1": {**BASE, "prompt_version": "v1"},
}
PRODUCTION_VERSION = os.getenv("PRODUCTION_VERSION", "v1")

JUDGE_PROVIDER = "groq"
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "llama-3.3-70b-versatile")
PROMOTION_THRESHOLD = 0.8

# groq price per 1M tokens (in, out)
PRICES = {
    "openai/gpt-oss-120b": (0.15, 0.60),
    "openai/gpt-oss-20b": (0.075, 0.30),
    "llama-3.3-70b-versatile": (0.59, 0.79),
}


def cost(input_tokens, output_tokens, model):
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    return (input_tokens * p_in + output_tokens * p_out) / 1e6
