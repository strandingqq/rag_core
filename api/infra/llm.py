import os
from typing import Any

from dotenv import load_dotenv

from api.infra.config import ROOT


def build_llm() -> Any:
    load_dotenv(ROOT / ".env")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model="deepseek-v4-flash",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0,
        extra_body={
            "thinking": {
                "type": "disabled",
            }
        },
    )