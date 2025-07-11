"""
agent/chains/conversational_legal_chain.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Natural conversation chain that:

• Learns/updates `document_type`
• Collects & validates `needed_fields`
• Replies naturally to the user
• Emits a *strict* JSON command set for the runner:

{
  "actions": ["update_document_type", "update_needed_values", "update_document"],
  "user_reply": "<string>",
  "update_document_type": "<DOC_TYPE|NONE>",
  "update_needed_values": { "<field>": "<value>", ... } | {},
  "update_document_instruction": "<string|NONE>"
}
"""

from typing import Dict, Any

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from agent.llm import llm_chain  # → your ChatOpenAI wrapper


_CLS_PROMPT = PromptTemplate(
    input_variables=["history", "user_input", "state"],
    template=r"""
Act as an *empathetic legal-AI assistant*.

Goal → build an accurate AgentState (shown below) and help the user.
Never violate the guard-rules afterwards.

────────────────────────────────────────────
📦 Current AgentState (read-only summary)
{state}
────────────────────────────────────────────
💬 Conversation history
{history}
────────────────────────────────────────────
🧑 Latest user message
{user_input}
────────────────────────────────────────────
🎯 MUST:

1. Carry on a *natural* dialogue. Explain, clarify, warn politely.
2. Decide which of the following *atomic* actions you must take **this turn**:
   • `update_document_type`      – we just learned / corrected the doc type
   • `update_needed_values`      – we have one or more field values to add
   • `update_document`           – ready to draft / revise the draft
   You MAY output multiple actions at once.
3. Reply to the user in `user_reply`.
4. Return **ONLY** a valid compact JSON, no markdown, no commentary.

Schema:
{{
  "actions": [...],                   // ⬆ see list
  "user_reply": "<your reply>",
  "update_document_type": "<type|NONE>",
  "update_needed_values": {{ "<field>": "<value>", ... }},
  "update_document_instruction": "<instruction|NONE>"
}}

Guard-rules:
• If AgentState.is_drafted is true → changing `document_type` is **forbidden**.
  Instead, offer to refine the existing draft.
• Politely warn & double-check if the user’s input seems wrong or contradictory.
"""
)


def get_conversational_legal_chain(memory) -> LLMChain:
    """Factory — returns an LLMChain with SQL-buffer memory attached."""
    return LLMChain(
        llm=llm_chain,
        prompt=_CLS_PROMPT,
        memory=memory,
        output_key="text",
        verbose=True   # <— runner pulls .text then parses JSON
    )
