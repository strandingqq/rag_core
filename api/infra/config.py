import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUESTION_FILE = ROOT / "all_questions.jsonl"

CHROMA_PERSIST_DIR = Path(
    os.environ.get("CHROMA_PERSIST_DIR", ROOT / "chroma_all_v2")
).resolve()
CHROMA_COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "question")

EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
EMBEDDING_DEVICE = os.environ.get("EMBEDDING_DEVICE", "cuda")

LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")

