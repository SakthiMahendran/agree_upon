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
from agent.prompts import PLACEHOLDER_CHECKER_PROMPT

logger = logging.getLogger("agent.placeholder_checker")
logger.setLevel(logging.DEBUG)

# ────────────────────────────
# JSON schema
# ────────────────────────────
class PlaceholderOutput(BaseModel):
    placeholders: List[str] = Field(
        ..., description="List of unresolved placeholder tokens"
    )

parser = PydanticOutputParser(pydantic_object=PlaceholderOutput)

# ────────────────────────────
# Prompt
# ────────────────────────────
prompt = PromptTemplate(
    input_variables=["draft"],
    template="""
You are reviewing a legal draft for unresolved placeholders such as
[DATE], [NAME], [ADDRESS], [PLACEHOLDER], etc.

Draft:
{draft}

{placeholder_checker_prompt}

Return ONLY a JSON list, e.g.  ["[DATE]", "[NAME]"]  or [].
"""
)

# ────────────────────────────
# Chain
# ────────────────────────────
def get_placeholder_checker_chain() -> LLMChain:
    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(placeholder_checker_prompt=PLACEHOLDER_CHECKER_PROMPT),
        output_key="text",      # raw text; we'll parse separately
        verbose=True,
    )
