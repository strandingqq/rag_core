from datetime import datetime
import os
from pathlib import Path
import sys

import chromadb
import langchain_chroma

from app_config import collection_name
from chroma_store import add_documents_to_chroma, init_chroma_db
from question_loader import load_documents_and_ids_from_jsonl


BATCH_SIZE = 1000
QUESTION_FILE = Path(__file__).resolve().with_name("all_questions.jsonl")
persist_dir = Path(
    os.environ.get(
        "CHROMA_PERSIST_DIR",
        Path(__file__).resolve().with_name("chroma_all_v2"),
    )
).resolve()

def backup_existing_db(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = path.with_name(f"{path.name}_backup_{timestamp}")
    try:
        path.rename(backup_path)
    except PermissionError as exc:
        raise PermissionError(
            "Cannot rename the existing Chroma database because one of its files "
            "is still open. Close notebook kernels, Python processes, or apps that "
            f"may be using this directory, then run again: {path}"
        ) from exc
    return backup_path


def rebuild_chroma_db() -> None:
    print("python:", sys.executable)
    print("cwd:", os.getcwd())
    print("chromadb:", chromadb.__version__)
    print("langchain_chroma:", langchain_chroma.__file__)
    print("question_file:", QUESTION_FILE)
    print("persist_dir:", persist_dir)
    print("collection_name:", collection_name)
    if not str(persist_dir).isascii():
        print("warning: persist_dir contains non-ASCII characters; Chroma on Windows may fail to load HNSW indexes.")

    if not QUESTION_FILE.exists():
        raise FileNotFoundError(f"Question file not found: {QUESTION_FILE}")

    backup_path = backup_existing_db(Path(persist_dir))
    if backup_path:
        print("backup:", backup_path)

    documents, ids = load_documents_and_ids_from_jsonl(QUESTION_FILE)
    print("loaded documents:", len(documents))

    db = init_chroma_db(str(persist_dir), collection_name)

    for start in range(0, len(documents), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(documents))
        add_documents_to_chroma(
            db,
            documents=documents[start:end],
            ids=ids[start:end],
        )
        print(f"added: {end}/{len(documents)}")

    print("final count:", db._collection.count())


if __name__ == "__main__":
    rebuild_chroma_db()
