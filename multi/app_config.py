import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
QUESTION_DIR =  ROOT / "all_questions.jsonl"
persist_dir = Path(os.environ.get("CHROMA_PERSIST_DIR", ROOT / "chroma_all_v2"))
collection_name = "question"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "deepseek-v4-flash"
LLM_BASE_URL = "https://api.deepseek.com"
