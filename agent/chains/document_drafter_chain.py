"""
agent/chains/document_drafter_chain.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generates or edits the legal draft *purely* from AgentState + instruction.

INPUT keys:
• document_type          – str
• filled_fields_json     – str  (JSON object of {field: value})
• current_draft          – str  (may be empty)
• instruction            – str  (e.g. "create fresh draft" | "swap Party A …")

OUTPUT (strict JSON):
{
  "draft": "<complete draft>",
  "is_drafted": true
}
"""

import json
import logging
from typing import Dict

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from pydantic import BaseModel, Field

from agent.llm import llm_chain

logger = logging.getLogger("agent.drafter")
logger.setLevel(logging.DEBUG)


# ────────────────────────────
# JSON schema & parser
# ────────────────────────────
from agent.utils import safe_parse_json_block, _iterate_json_candidates

class SimpleDraftOutputParser:
    def get_format_instructions(self) -> str:
        return 'Return ONLY a JSON object with keys "draft" and "is_drafted".'

    def parse(self, text: str) -> dict:
        # Try all balanced-brace JSON blocks
        for candidate in _iterate_json_candidates(text):
            parsed = safe_parse_json_block(candidate)
            if parsed and 'draft' in parsed and 'is_drafted' in parsed:
                return parsed
        raise ValueError(f"No valid draft JSON found in output:\n{text}")

parser = SimpleDraftOutputParser()

# ────────────────────────────
# Prompt
# ────────────────────────────
_DRAFTER_PROMPT = PromptTemplate(
    input_variables=["document_type", "filled_fields_json",
                     "current_draft", "instruction", "history"],
    template=r"""
You are a veteran legal drafter.

────────────────────────────────────────────
Conversation history (for reference, you can also refer deep into this history to extract key details):
{history}
────────────────────────────────────────────
📝 Document type: {document_type}
📑 Field values (JSON): {filled_fields_json}
📄 Existing draft: <<<START>>>
{current_draft}
<<<END>>>
🛈 Instruction: {instruction}
────────────────────────────────────────────

TASK:
• Produce a *clean*, professional draft in plain text.
• STRICT: Only use the provided field values in your draft. Do NOT invent or guess any values.
• Placeholders or tokens like [DATE], [NAME], etc. are STRICTLY FORBIDDEN – your draft MUST NOT contain any placeholders under any circumstances.
• Carefully review your draft before returning: ensure every field is filled with real, concrete values from the input and that no placeholders remain.
• NO boilerplate like "Here is your draft".
• Return only compact JSON exactly:

{{
  "draft": "<the complete draft here>",
  "is_drafted": true
}}

No markdown, no commentary.

{format_instructions}
"""
)


from agent.memory import SQLBufferMemory

def get_document_drafter_chain(memory: "SQLBufferMemory | None" = None) -> LLMChain:
    # If memory is provided and 'user_input' is not among input_variables, set input_key=None to avoid KeyError
    use_input_key = memory is None or "user_input" in _DRAFTER_PROMPT.input_variables
    llmchain_kwargs = dict(
        llm=llm_chain,
        prompt=_DRAFTER_PROMPT.partial(format_instructions=parser.get_format_instructions()),
        memory=memory,
        output_key="text",
        verbose=True,
    )
    if use_input_key:
        llmchain_kwargs["input_key"] = "user_input"
    return LLMChain(**llmchain_kwargs)
