# agent/llm.py

import os
import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("OPENROUTER_API_KEY")
if not HF_TOKEN:
    raise RuntimeError("Missing HF_TOKEN / OPENROUTER_API_KEY in environment")

llm = ChatOpenAI(
    openai_api_base="https://oaitzvyxm6614ekn.us-east-1.aws.endpoints.huggingface.cloud/v1",
    openai_api_key=HF_TOKEN,
    temperature=0.3,
    max_tokens=8192,
)

def call_llm_with_retry(messages: list[HumanMessage]) -> str:
    """Call the LLM, retrying on 503s."""
    while True:
        try:
            resp = llm.generate([messages])
            return resp.generations[0][0].text.strip()
        except Exception as e:
            if "503" in str(e) or "ServiceUnavailable" in str(e):
                print("[llm] warming up; retrying in 5s…")
                time.sleep(5)
                continue
            raise
