import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def build_llm() -> ChatOpenAI:
    load_dotenv()
    return ChatOpenAI(
        model="deepseek-v4-flash",
        api_key=os.environ["DEEPSEEK_API_KEY"], # 从环境变量里读取你的 API key 使用之前需要load_dotenv()
        base_url="https://api.deepseek.com", # DeepSeek 的 OpenAI 兼容接口地址
        temperature=0,
    )