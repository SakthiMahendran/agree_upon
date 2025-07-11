"""
agent/agent_runner.py
──────────────────────────────────────────────────────────────────────────────
Single-turn orchestrator.

1. Runs the conversational chain and parses its JSON commands.
2. Applies those commands to `AgentState`.
3. When asked to draft or revise, calls the drafter → placeholder-checker loop:
      • if `is_success == True`   → saves clean draft
      • else (≤ 2 tries)          → injects a system prompt telling the
        conversational chain what data to collect from the user
4. Persists both user & AI messages plus the updated state.
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
from api.models import Message

logger = logging.getLogger("agent.runner")
logger.setLevel(logging.DEBUG)


# ─────────────────────────────────────────────────────────────
# Helper – normalise LLM / chain return types
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
    """One interaction turn."""
    memory: SQLBufferMemory = get_memory(conversation_id)

    # Ensure new counter exists
    if not hasattr(state, "missing_prompt_count"):
        state.missing_prompt_count = 0

    # ────────────────── ➊ Conversational chain ──────────────────
    conv_chain = get_conversational_legal_chain(memory)
    raw_conv   = invoke_with_retry(conv_chain, {
        "user_input": user_input,
        "state":      state.summary(),
    })
    conv_text  = _clean_llm_text(_extract_text(raw_conv))
    logger.debug("\n🔵 RAW conversational output ↓↓↓\n%s\n", conv_text)

    parsed = (safe_parse_json_block(conv_text)
              or salvage_json(conv_text, required_key="user_reply"))

    if parsed is None:
        fallback = "⚠️ Sorry, something got garbled. Could you rephrase?"
        _persist(memory, conversation_id, user_input, fallback, state)
        return {
            "reply":                       fallback,
            "updated_state":               state,
            "draft_document":              None,
            "document_updated_this_turn":  False,
        }

    # ────────────────── ➋ Basic state updates & safety nets ──────────────────
    reply_to_user: str = parsed.get("user_reply", "").strip()

    # Fallback in case user_reply missing
    if not reply_to_user:
        reply_to_user = "🤔 I’m here, but I didn’t catch that. Could you rephrase?"

    # Merge any doc-type / field values even if action list was malformed
    doc_type_fallback = parsed.get("update_document_type", "").strip()
    if doc_type_fallback and doc_type_fallback != "NONE":
        if not state.is_drafted or doc_type_fallback == state.document_type:
            state.document_type = doc_type_fallback

    # Safely merge any provided field values even if they are not a direct mapping.
    field_fallback_raw = parsed.get("update_needed_values", {}) or {}
    if field_fallback_raw:
        if isinstance(field_fallback_raw, dict):
            state.needed_fields.update(field_fallback_raw)
        else:
            # Handle cases where the LLM returns a list/tuple of key–value pairs
            try:
                field_pairs = dict(field_fallback_raw)  # will succeed for list[(k,v)]
                state.needed_fields.update(field_pairs)
            except Exception:
                logger.warning("⚠️ Invalid format for update_needed_values: %s", field_fallback_raw)

    actions      = parsed.get("actions", [])
    doc_updated  = False

    # ────────────────── ➌ Execute JSON actions ──────────────────
    for action in actions:
        match action:

            # ─── update_document_type ───────────────────────────
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

            # ─── update_needed_values ───────────────────────────
            case "update_needed_values":
                # Accept both dict and list-of-pairs for new field values
                new_vals_raw = parsed.get("update_needed_values", {})
                if new_vals_raw:
                    if isinstance(new_vals_raw, dict):
                        state.needed_fields.update(new_vals_raw)
                    else:
                        try:
                            state.needed_fields.update(dict(new_vals_raw))
                        except Exception:
                            logger.warning("⚠️ Invalid format for update_needed_values in action: %s", new_vals_raw)

            # ─── update_document  →  drafter + checker loop ─────
            case "update_document":
                instr = parsed.get("update_document_instruction", "").strip() \
                        or "create fresh draft"

                # 1️⃣ Draft / revise
                history_text = memory.load_memory_variables({}).get("history", "")
                drafter   = get_document_drafter_chain(memory)
                drafter_raw = invoke_with_retry(drafter, {
                     "document_type":      state.document_type,
                     "filled_fields_json": json.dumps(state.needed_fields),
                     "current_draft":      state.draft,
                     "instruction":        instr,
                     "history":            history_text,
                     "user_input":         user_input,  # for memory.save_context
                 })
                drafter_txt   = _clean_llm_text(_extract_text(drafter_raw))
                d_parsed = (safe_parse_json_block(drafter_txt)
                            or salvage_json(drafter_txt, required_key="draft"))
                if not d_parsed or not d_parsed.get("draft"):
                    reply_to_user = "⚠️ Drafting failed. Please try again."
                    break

                draft = d_parsed["draft"].strip()

                # 2️⃣ Placeholder check
                from agent.chains.placeholder_checker import (
                    get_placeholder_checker_chain, parser as checker_parser
                )
                checker     = get_placeholder_checker_chain(memory)
                check_raw   = invoke_with_retry(checker, {
                     "draft": draft,
                     "history": history_text,
                     "user_input": user_input,  # for memory.save_context
                 })
                check_txt   = _clean_llm_text(_extract_text(check_raw))

                try:
                    check = checker_parser.parse(check_txt)
                except Exception:
                    reply_to_user = "⚠️ Placeholder check failed. Please try again."
                    break

                MAX_USER_PROMPTS = 2

                if check.is_success:
                    # Success → save draft
                    state.draft      = draft
                    state.is_drafted = True
                    doc_updated      = True
                    reply_to_user    = (
                        "✅ All set! Your document is fully drafted. "
                        "Let me know if you'd like any edits."
                    )

                else:
                    # Still missing info
                    if state.missing_prompt_count >= MAX_USER_PROMPTS:
                        reply_to_user = (
                            "I'm still missing details ("
                            + check.missing_desc +
                            "). Let's continue once you have them."
                        )
                    else:
                        # Ask the user via conversational chain
                        state.missing_prompt_count += 1
                        system_addition = (
                            "I am an internal checker. The draft is missing: "
                            + check.missing_desc +
                            ". Please ask the user for these details."
                        )

                        follow_conv = get_conversational_legal_chain(memory)
                        follow_raw  = invoke_with_retry(follow_conv, {
                            "user_input":      user_input,
                            "state":           state.summary(),
                            "system_addition": system_addition,
                        })
                        follow_text = _clean_llm_text(_extract_text(follow_raw))
                        follow_parsed = (safe_parse_json_block(follow_text)
                                         or salvage_json(follow_text,
                                                         required_key="update_needed_values"))

                        if follow_parsed:
                            new_vals = follow_parsed.get("update_needed_values", {})
                            state.needed_fields.update(new_vals)

                        # We echo the missing description back to the user
                        reply_to_user = check.missing_desc

            # ─── fall-through ───────────────────────────────────
            case _:
                logger.warning("⚠️ Unknown action: %s", action)

    # ────────────────── ➍ Persist & return ──────────────────
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
    """Save chat messages + commit DB."""
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
