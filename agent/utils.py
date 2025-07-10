# agent/utils.py

import time
import re
import logging
from typing import List
from langchain.chains.base import Chain
from fastapi import HTTPException
from httpx import HTTPStatusError

logger = logging.getLogger("agent.utils")
logger.setLevel(logging.INFO)

# ──────────────────────────────────────────────
# 🔁 LLM Retry Wrapper (Cold Start Aware)
# ──────────────────────────────────────────────
def invoke_with_retry(chain_or_runnable, inputs: dict, max_retries: int = 1000, delay: int = 5) -> str:
    """
    Calls any LangChain chain or runnable with retry logic for HF 503 errors.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = chain_or_runnable.invoke(inputs)
            break
        except HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 503:
                logger.warning(f"[Retry {attempt}] 503 cold start, retrying in {delay}s...")
            else:
                logger.error(f"[Retry {attempt}] HTTP {e.response.status_code}: {e}")
                raise HTTPException(502, f"LLM error {e.response.status_code}")
        except Exception as e:
            last_error = e
            if "503" in str(e):
                logger.warning(f"[Retry {attempt}] 503-like error: {e}")
            else:
                logger.error(f"[Retry {attempt}] Unexpected error: {e}")
                raise HTTPException(500, f"LLM call failed: {e}")
        time.sleep(delay)
    else:
        logger.error(f"❌ All {max_retries} retries failed. Last error: {last_error}")
        raise HTTPException(502, "LLM service unavailable. Please try again later.")

    # Clean up and return
    if isinstance(result, dict) and "output" in result:
        return result["output"].strip()
    elif hasattr(result, "content"):
        return result.content.strip()
    elif isinstance(result, str):
        return result.strip()
    else:
        return str(result).strip()

# ──────────────────────────────────────────────
# 🧠 Placeholder Detection
# ──────────────────────────────────────────────
def detect_placeholders(text: str) -> List[str]:
    """
    Detects unresolved placeholders like [NAME], [DATE], etc.
    """
    return re.findall(r"\[[A-Z_ ]+\]", text or "")

# ──────────────────────────────────────────────
# 🧹 Remove LLM boilerplate
# ──────────────────────────────────────────────
def strip_llm_fluff(text: str) -> str:
    """
    Removes typical LLM output fluff like:
    - "Here is your document:"
    - "Below is the draft:"
    """
    text = re.sub(r'^(Here is|Below is|The following is).{0,100}?:\s*', '', text, flags=re.IGNORECASE)
    return text.strip()

# ──────────────────────────────────────────────
# ✅ Finalize Command Detector (Optional)
# ──────────────────────────────────────────────
def is_finalization_command(user_input: str) -> bool:
    return user_input.strip().lower() in {"final", "done", "finalize", "no", "none"}
