from typing import Any

from api.infra.config import EMBEDDING_DEVICE, EMBEDDING_MODEL


def init_chroma_db(persist_dir: str, collection_name: str) -> Any:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    embedding = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )

    return Chroma(
        persist_directory=persist_dir,
        collection_name=collection_name,
        embedding_function=embedding,
    )


def add_documents_to_chroma(db: Any, documents: list[Any], ids: list[str]) -> Any:
    db.add_documents(documents, ids=ids)
    return db

