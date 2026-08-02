from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def get_db() -> Any:
    from api.infra.chroma_store import init_chroma_db
    from api.infra.config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR

    return init_chroma_db(
        persist_dir=str(CHROMA_PERSIST_DIR),
        collection_name=CHROMA_COLLECTION_NAME,
    )


@lru_cache(maxsize=1)
def get_llm() -> Any:
    from api.infra.llm import build_llm

    return build_llm()
