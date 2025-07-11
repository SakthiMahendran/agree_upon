"""
Detect unresolved placeholders in a draft.

Changes
• Returns structured list via PydanticOutputParser
"""

import logging
from typing import List
from pydantic import BaseModel, Field

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser

from agent.llm import llm_chain
from agent.memory import SQLBufferMemory
from agent.prompts import PLACEHOLDER_CHECKER_PROMPT

logger = logging.getLogger("agent.placeholder_checker")
logger.setLevel(logging.DEBUG)

# ────────────────────────────
# JSON schema
# ────────────────────────────
class PlaceholderCheckOut(BaseModel):
    is_success: bool
    missing_desc: str
    ask_user: str

parser = PydanticOutputParser(pydantic_object=PlaceholderCheckOut)

# ────────────────────────────
# Prompt
# ────────────────────────────
prompt = PromptTemplate(
    input_variables=["draft", "history"],
    template="""
Refer to the conversation history (you can also refer deep into this history to extract key details) to cross-check missing details.
Scan the draft below.

• If NO placeholders like [DATE] [NAME] [PARTY A]... etc remain:
  return {{"is_success": true, "missing_desc": "", "ask_user": ""}}

• Otherwise:
  return {{"is_success": false, "missing_desc": "<short English list of what’s missing>", "ask_user": "<single concise question to get all missing info>"}}

Return ONLY that JSON. No other text.

Conversation history:
{history}

Draft:
{draft}
"""
)

# ────────────────────────────
# Chain
# ────────────────────────────
def get_placeholder_checker_chain(memory: "SQLBufferMemory | None" = None) -> LLMChain:
    # If memory is provided and 'user_input' is not among input_variables, set input_key=None to avoid KeyError
    use_input_key = memory is None or "user_input" in prompt.input_variables
    llmchain_kwargs = dict(
        llm=llm_chain,
        prompt=prompt.partial(placeholder_checker_prompt=PLACEHOLDER_CHECKER_PROMPT),
        memory=memory,
        output_key="text",      # raw text; we'll parse separately
        verbose=True,
    )
    if use_input_key:
        llmchain_kwargs["input_key"] = "user_input"
    return LLMChain(**llmchain_kwargs)
