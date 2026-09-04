from datetime import datetime
from pathlib import Path

from api.infra.chroma_store import add_documents_to_chroma, init_chroma_db
from api.infra.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    QUESTION_FILE,
)
from api.infra.question_loader import load_documents_and_ids_from_jsonl


BATCH_SIZE = 1000


def backup_existing_db(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = path.with_name(f"{path.name}_backup_{timestamp}")
    path.rename(backup_path)
    return backup_path


def rebuild_chroma_db() -> None:
    print("question_file:", QUESTION_FILE)
    print("persist_dir:", CHROMA_PERSIST_DIR)
    print("collection_name:", CHROMA_COLLECTION_NAME)

    if not QUESTION_FILE.exists():
        raise FileNotFoundError(f"Question file not found: {QUESTION_FILE}")

    backup_path = backup_existing_db(CHROMA_PERSIST_DIR)
    if backup_path:
        print("backup:", backup_path)

    documents, ids = load_documents_and_ids_from_jsonl(QUESTION_FILE)
    print("loaded documents:", len(documents))

    db = init_chroma_db(
        persist_dir=str(CHROMA_PERSIST_DIR),
        collection_name=CHROMA_COLLECTION_NAME,
    )

    for start in range(0, len(documents), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(documents))
        add_documents_to_chroma(
            db=db,
            documents=documents[start:end],
            ids=ids[start:end],
        )
        print(f"added: {end}/{len(documents)}")

    print("final count:", db._collection.count())


if __name__ == "__main__":
    rebuild_chroma_db()
