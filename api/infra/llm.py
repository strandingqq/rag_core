import os
from typing import Any

from dotenv import load_dotenv

from api.infra.config import LLM_BASE_URL, LLM_MODEL, ROOT


def build_llm() -> Any:
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=api_key,
        base_url=LLM_BASE_URL,
        temperature=0,
    )

