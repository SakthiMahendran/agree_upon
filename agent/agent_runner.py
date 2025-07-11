"""
Single-turn orchestrator – runs conversational chain, applies JSON commands,
updates AgentState, and persists messages.

(unchanged header/comment)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from agent.state import AgentState
from agent.memory import get_memory, SQLBufferMemory
from agent.utils import (
    invoke_with_retry,
    _clean_llm_text,
    safe_parse_json_block,
    salvage_json,
)
from agent.chains.conversational_legal_chain import get_conversational_legal_chain
from agent.chains.document_drafter_chain     import get_document_drafter_chain
from api.models import Message               # adjust import path if needed

logger = logging.getLogger("agent.runner")
logger.setLevel(logging.DEBUG)

# ─────────────────────────────────────────────────────────────
# Helper – normalise raw LLM / chain return
# ─────────────────────────────────────────────────────────────
def _extract_text(res: Any) -> str:
    if isinstance(res, str):
        return res
    if isinstance(res, dict) and "text" in res:
        return str(res["text"])
    if hasattr(res, "content"):
        return str(res.content)
    if hasattr(res, "text"):
        return str(res.text)
    return str(res)

# ─────────────────────────────────────────────────────────────
def run_agent_step(state: AgentState, user_input: str, conversation_id: str):
    memory: SQLBufferMemory = get_memory(conversation_id)

    # ➊ Run conversational chain
    conv_chain = get_conversational_legal_chain(memory)
    raw_conv   = invoke_with_retry(conv_chain, {
        "user_input": user_input,
        "state":      state.summary(),
    })
    raw_text = _extract_text(raw_conv)
    print("\n🔵 RAW conversational output ↓↓↓\n", raw_text, "\n")

    cleaned = _clean_llm_text(raw_text)

    # First, try to parse the whole thing. On failure, salvage JSON that
    # contains *user_reply* (not “destination”, which is for the router).
    parsed = safe_parse_json_block(cleaned)
    if parsed is None:
        parsed = salvage_json(cleaned, required_key="user_reply")

    if parsed is None:
        fallback = "⚠️ Sorry, something got garbled. Could you rephrase?"
        _persist(memory, conversation_id, user_input, fallback, state)
        return {
            "reply":                       fallback,
            "updated_state":               state,
            "draft_document":              None,
            "document_updated_this_turn":  False,
        }

    reply_to_user: str = parsed.get("user_reply", "").strip()

    # ── Safety net: update state even if actions were missing ──
    # Some LLM outputs forget to list the action name even though the values
    # are present. We proactively merge them so the drafter sees the data.
    fallback_type = parsed.get("update_document_type", "").strip()
    if fallback_type and fallback_type != "NONE":
        if not state.is_drafted or fallback_type == state.document_type:
            state.document_type = fallback_type
    fallback_vals: Dict[str, str] = parsed.get("update_needed_values", {}) or {}
    if fallback_vals:
        state.needed_fields.update(fallback_vals)

    # ⬇⬇ NEW FAIL-SAFE ⬇⬇
    if not reply_to_user:
        logger.warning("Empty user_reply detected – substituting fallback.")
        reply_to_user = "🤔 I’m here, but I didn’t catch that. Could you rephrase?"

    actions      = parsed.get("actions", [])
    doc_updated  = False

    # ➋ Handle actions (UNCHANGED BELOW, trimmed for brevity)
    for action in actions:
        match action:
            case "update_document_type":
                new_type = parsed.get("update_document_type", "NONE").strip()
                if new_type and new_type != "NONE":
                    if state.is_drafted and new_type != state.document_type:
                        reply_to_user = (
                            "⚠️ The document is already drafted; "
                            "changing its type now isn’t allowed."
                        )
                    else:
                        state.document_type = new_type

            case "update_needed_values":
                new_vals: Dict[str, str] = parsed.get("update_needed_values", {})
                if new_vals:
                    # Merge new values with existing ones
                    state.needed_fields.update(new_vals)

            case "update_document":
                instr   = parsed.get("update_document_instruction", "")
                drafter = get_document_drafter_chain()
                drafter_raw = invoke_with_retry(drafter, {
                    "document_type":      state.document_type,
                    "filled_fields_json": json.dumps(state.needed_fields),
                    "current_draft":      state.draft,
                    "instruction":        instr or "create fresh draft",
                })
                drafter_txt = _extract_text(drafter_raw)
                print("\n🟢 RAW drafter output ↓↓↓\n", drafter_txt, "\n")

                cleaned_drafter = _clean_llm_text(drafter_txt)
                d_parsed = (
                    safe_parse_json_block(cleaned_drafter)
                    or salvage_json(cleaned_drafter, required_key="draft")
                )
                if d_parsed and d_parsed.get("draft"):
                    state.draft      = d_parsed["draft"].strip()
                    state.is_drafted = True
                    doc_updated      = True

                    # ── Post-processing: auto-fix unresolved placeholders ──
                    from agent.chains.placeholder_checker import get_placeholder_checker_chain
                    checker = get_placeholder_checker_chain()
                    check_raw = invoke_with_retry(checker, {"draft": state.draft})
                    placeholders_json = _clean_llm_text(_extract_text(check_raw))
                    try:
                        missing = json.loads(placeholders_json)
                    except Exception:
                        missing = []
                    if missing:
                        logger.info("⚠️ Detected placeholders %s – retrying drafter once", missing)
                        fix_instruction = (
                            "Replace the unresolved placeholders "
                            + ", ".join(missing)
                            + " with concrete values based on filled fields and context."
                        )
                        drafter_retry = invoke_with_retry(drafter, {
                            "document_type":      state.document_type,
                            "filled_fields_json": json.dumps(state.needed_fields),
                            "current_draft":      state.draft,
                            "instruction":        fix_instruction,
                        })
                        retry_txt = _clean_llm_text(_extract_text(drafter_retry))
                        retry_parsed = (
                            safe_parse_json_block(retry_txt)
                            or salvage_json(retry_txt, required_key="draft")
                        )
                        if retry_parsed and retry_parsed.get("draft"):
                            state.draft = retry_parsed["draft"].strip()

                else:
                    logger.error("❌ Drafter returned unparsable JSON.")
                    reply_to_user = "⚠️ Drafting failed. Please try again."

            case _:
                logger.warning("⚠️ Unknown action: %s", action)

    _persist(memory, conversation_id, user_input, reply_to_user, state)

    return {
        "reply":                       reply_to_user,
        "updated_state":               state,
        "draft_document":              state.draft if state.is_drafted else None,
        "document_updated_this_turn":  doc_updated,
    }

# ─────────────────────────────────────────────────────────────
def _persist(
    memory: SQLBufferMemory,
    conv_id: str,
    user_msg: str,
    ai_msg: str,
    state: AgentState,
):
    memory.chat_memory.add_user_message(user_msg)
    memory.chat_memory.add_ai_message(ai_msg)
    memory.db.add_all(
        [
            Message(
                conversation_id=int(conv_id), sender="user", content=user_msg
            ),
            Message(
                conversation_id=int(conv_id), sender="assistant", content=ai_msg
            ),
        ]
    )
    memory.db.commit()
