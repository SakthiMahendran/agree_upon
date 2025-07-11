import os
import time
import logging

from dotenv import load_dotenv
from fastapi import HTTPException
from httpx import HTTPStatusError
from langchain_core.runnables.base import Runnable
from langchain_openai import ChatOpenAI  # Hugging Face-compatible OpenAI wrapper

# ────────────────────────────────
# 🛠️ Logging Setup
# ────────────────────────────────
logger = logging.getLogger("agent.llm")
logger.setLevel(logging.INFO)

# ────────────────────────────────
# 🔐 Load Environment Variables
# ────────────────────────────────
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
print("HF_TOKEN", HF_TOKEN)
if not HF_TOKEN:
    raise RuntimeError("Missing HF_TOKEN environment variable")

# ────────────────────────────────
# 🤖 DeepSeek Model via HF Endpoint
# ────────────────────────────────
#DeepSeek-LlaMa-Distilled
# llm_chain: Runnable = ChatOpenAI(
#     model="deepseek-chat",  # Optional for HF OpenAI-compatible endpoints, but kept for clarity
#     openai_api_base="https://oaitzvyxm6614ekn.us-east-1.aws.endpoints.huggingface.cloud/v1/",
#     openai_api_key=os.getenv("HF_TOKEN"),
#     temperature=0.3,
#     max_tokens=8192,
#     streaming=True,
# )

#DeepSeekOpenRouter
llm_chain: Runnable = ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free",  # Optional for HF OpenAI-compatible endpoints, but kept for clarity
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.3,
    max_tokens=8192,
    streaming=True,
)

#DeepSeekR1-1q1
# llm_chain: Runnable = ChatOpenAI(
#     model="deepseek-chat",  # Optional for HF OpenAI-compatible endpoints, but kept for clarity
#     openai_api_base="https://qwryad273mlndckn.us-east-1.aws.endpoints.huggingface.cloud/v1/",
#     openai_api_key=os.getenv("HF_TOKEN"),
#     temperature=0.3,
#     max_tokens=8192,
#     streaming=True,
# )


# ────────────────────────────────
# 🔁 Retry Logic for Cold Start / 503
# ────────────────────────────────
def invoke_with_retry(executor: Runnable, inputs, max_retries=1000, delay=5, **kwargs) -> str:
    """
    Calls the LangChain Runnable with retry handling for Hugging Face cold-starts (503).
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = executor.invoke(inputs, **kwargs)
            break
        except HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 503:
                logger.warning(f"[Retry {attempt}/{max_retries}] 503 Cold Start – Retrying in {delay}s...")
            else:
                logger.error(f"[Retry {attempt}/{max_retries}] HTTP {e.response.status_code}: {e}")
                raise HTTPException(502, f"LLM HTTP error {e.response.status_code}: {e}")
        except Exception as e:
            last_error = e
            if "503" in str(e):
                logger.warning(f"[Retry {attempt}/{max_retries}] 503-like error: {e} – Retrying in {delay}s...")
            else:
                logger.error(f"[Retry {attempt}/{max_retries}] Fatal error: {e}")
                raise HTTPException(500, f"Unexpected LLM error: {e}")
        time.sleep(delay)
    else:
        logger.error(f"All {max_retries} retries failed: {last_error}")
        raise HTTPException(502, f"LLM service unavailable after multiple retries: {last_error}")

    # ────────────────────────────────
    # 🧠 Parse LLM Output
    # ────────────────────────────────
    if isinstance(result, dict) and "output" in result:
        raw = result["output"]
    elif hasattr(result, "content"):
        raw = result.content
    elif isinstance(result, str):
        raw = result
    else:
        logger.warning(f"Unrecognized LLM output format: {type(result)}")
        raw = str(result)

    raw_reply = raw.strip()
    if "</think>" in raw_reply:
        return raw_reply.split("</think>")[-1].strip()
    return raw_reply
