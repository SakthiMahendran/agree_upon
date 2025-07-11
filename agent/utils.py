"""
Shared helper utilities for the legal-assistant agent.

• invoke_with_retry        – resilient LLM / chain invocation
• _clean_llm_text          – strips <think> blocks, markdown fences, whitespace
• _first_json_block        – extracts first {...} that contains a key
• safe_parse_json_block    – tolerant JSON→dict loader
• salvage_json             – multi-strategy JSON extraction fallback
• detect_placeholders      – finds tokens like [DATE], [NAME]
• strip_llm_fluff          – removes “Here is …” boilerplate
• is_finalization_command  – simplistic “sign-off” detector
"""

from __future__ import annotations

import ast
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent.utils")
logger.setLevel(logging.DEBUG)

# ────────────────────────────────────────────────────────────
# Retry wrapper
# ────────────────────────────────────────────────────────────
def invoke_with_retry(
    chain_or_runnable,
    inputs: Dict[str, Any],
    max_retries: int = 100,
):
    """
    Invoke *any* LangChain object (Runnable, Chain, or plain callable)
    with simple exponential-backoff retry.
    """
    for attempt in range(1, max_retries + 1):
        try:
            if hasattr(chain_or_runnable, "invoke"):
                return chain_or_runnable.invoke(inputs)

            if hasattr(chain_or_runnable, "run"):
                if isinstance(inputs, dict):
                    return chain_or_runnable.run(**inputs)
                return chain_or_runnable.run(inputs)

            return chain_or_runnable(inputs)

        except Exception as exc:
            logger.warning(
                "⚠️ invoke_with_retry (%d/%d) failed: %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt == max_retries:
                raise
            time.sleep(10)

# ────────────────────────────────────────────────────────────
# Text-cleanup helpers
# ────────────────────────────────────────────────────────────
_THINK_END_RE        = re.compile(r"</think>", re.IGNORECASE)
_CODE_FENCE_START_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*")
_CODE_FENCE_END_RE   = re.compile(r"\s*```\s*$")

def _clean_llm_text(text: str) -> str:
    """
    Strip <think> … </think> blocks *and* leading / trailing code fences.
    """
    m = list(_THINK_END_RE.finditer(text))
    if m:
        text = text[m[-1].end():]

    text = _CODE_FENCE_START_RE.sub("", text)
    text = _CODE_FENCE_END_RE.sub("", text)
    return text.strip()

# ────────────────────────────────────────────────────────────
# Balanced-brace JSON extraction helpers
# ────────────────────────────────────────────────────────────
def _iterate_json_candidates(text: str):
    depth   = 0
    start   = None
    in_str  = False
    escape  = False

    for i, ch in enumerate(text):
        if ch == '"' and not escape:
            in_str = not in_str
        escape = (ch == "\\" and not escape)

        if in_str:
            continue

        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start : i + 1]
                start = None

_SINGLE_TO_DOUBLE_RE = re.compile(r"'([^']+?)'")

def safe_parse_json_block(block: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        pass

    try:
        converted = _SINGLE_TO_DOUBLE_RE.sub(r'"\1"', block)
        return json.loads(converted)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(block)
    except Exception:
        return None

# ────────────────────────────────────────────────────────────
# Fallback JSON-extraction strategies
# ────────────────────────────────────────────────────────────
_JSON_FENCE_RE = re.compile(
    r"```json\s*({[\s\S]+?})\s*```",
    re.IGNORECASE,
)

def salvage_json(text: str, required_key: str = "destination") -> Optional[Dict[str, Any]]:
    """
    Robust, multi-strategy JSON extraction.

    • `required_key` – only return a dict that contains this key
                       (defaults to "destination" for router output).
    """
    # 1) ```json … ``` fenced blocks
    for m in _JSON_FENCE_RE.finditer(text):
        block  = m.group(1)
        parsed = safe_parse_json_block(block)
        if parsed and required_key in parsed:
            logger.debug("🛟 Salvaged JSON from fenced block.")
            return parsed

    # 2) Any balanced { … } group
    for block in _iterate_json_candidates(text):
        if f'"{required_key}"' not in block and f"'{required_key}'" not in block:
            continue
        parsed = safe_parse_json_block(block)
        if parsed and required_key in parsed:
            logger.debug("🛟 Salvaged JSON from balanced scan.")
            return parsed

    # 3) Reverse scan – last brace group containing the key
    idx = text.rfind("}")
    while idx != -1:
        start = text.rfind("{", 0, idx)
        if start == -1:
            break
        block = text[start : idx + 1]
        if f'"{required_key}"' in block or f"'{required_key}'" in block:
            parsed = safe_parse_json_block(block)
            if parsed and required_key in parsed:
                logger.debug("🛟 Salvaged JSON from reverse scan.")
                return parsed
        idx = text.rfind("}", 0, start)

    return None

# ────────────────────────────────────────────────────────────
# Misc helpers
# ────────────────────────────────────────────────────────────
_PLACEHOLDER_RE = re.compile(r"\[[A-Z0-9_]+\]")

def detect_placeholders(doc: str) -> List[str]:
    return list(dict.fromkeys(_PLACEHOLDER_RE.findall(doc)))

_FLUFF_RE = re.compile(
    r"^\s*(Here is|Below is|Sure[,:\-]?|Certainly[,:\-]?|Here's the)\b[^\n]*\n+",
    re.IGNORECASE,
)

def strip_llm_fluff(text: str) -> str:
    return _FLUFF_RE.sub("", text).strip()

_FINAL_CMD_RE = re.compile(
    r"\b(finalise|finalize|looks\s+good|approved|no\s+further\s+changes)\b",
    re.IGNORECASE,
)

def is_finalization_command(user_input: str) -> bool:
    return bool(_FINAL_CMD_RE.search(user_input))
