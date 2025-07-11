"""
agent/router.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Defines a conversational router that:
  • Inspects conversation `history`, incoming `user_input`, and current `state_json`.
  • Routes to one of six stages or replies directly (qna).

Outputs a JSON string matching `RouterOutput` schema:
  {"destination": "<stage>", "next_inputs": { ... }}

Stages: identify_doc · collect_fields · generate_draft · await_placeholder · await_refine · qna
"""
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field, validator
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from agent.llm import llm_chain


# ────────────────────────────────────────────────────────────
# Stage enumeration
# ────────────────────────────────────────────────────────────
class StageEnum(str, Enum):
    identify_doc      = "identify_doc"
    collect_fields    = "collect_fields"
    generate_draft    = "generate_draft"
    await_placeholder = "await_placeholder"
    await_refine      = "await_refine"
    qna               = "qna"


# ────────────────────────────────────────────────────────────
# Router output schema (validated in agent_runner)
# ────────────────────────────────────────────────────────────
class RouterOutput(BaseModel):
    destination: StageEnum = Field(..., description="Next chain/stage to invoke")
    next_inputs: Dict[str, Any] = Field(
        ..., description="Inputs for the next stage or direct reply"
    )

    @validator("next_inputs")
    def ensure_input_key(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if "input" not in v:
            raise ValueError("`next_inputs` must include an `input` key")
        return v


# ────────────────────────────────────────────────────────────
# Prompt template
# ────────────────────────────────────────────────────────────
router_prompt = PromptTemplate(
    input_variables=["user_input", "history", "state_json"],
    template=r"""
You are the **controller** for a legal‑document assistant.

Your job is to:
1. **Select exactly one stage** from the options below.
2. Produce the JSON payload described after the stage list.

---
🧭 **Stages & what to do**

• "identify_doc"      → Ask clarifying question(s) to discover doc type.
• "collect_fields"     → Ask for ONE missing field.
• "generate_draft"     → Output a clean, filler‑free legal draft.
• "await_placeholder"  → Ask for concrete value for each [PLACEHOLDER].
• "await_refine"       → Confirm / apply user’s refine instructions.
• "qna"                → Casual Q&A / small talk (no doc workflow).

---
🧠 **Message formatting rule**
If destination == "qna" → `next_inputs.input` = direct user reply (natural language).
Otherwise                → `next_inputs.input` = instruction for the downstream chain.

---
🧾 **Return ONLY valid JSON. No markdown, no commentary.**

{{
  "destination": "<stage>",
  "next_inputs": {{ "input": "<message>" }}
}}

---
💬 **History**
{history}

🧑 **User**
{user_input}

📦 **State**
{state_json}
"""
)


# ────────────────────────────────────────────────────────────
# Factory
# ────────────────────────────────────────────────────────────
def build_conversational_router(memory) -> LLMChain:
    """Return an LLMChain that emits the routing JSON."""
    return LLMChain(
        llm=llm_chain,
        prompt=router_prompt,
        memory=memory,
        output_key="text"  # Required by LangChain ≥0.1; our runner extracts .text
    )
