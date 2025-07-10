# agent/agent_runner.py

from agent.state import AgentState
from agent.memory import get_memory
from agent.graph import AGENT_GRAPH
from agent.utils import detect_placeholders, strip_llm_fluff

def run_agent_step(state: AgentState, user_input: str, conversation_id: str):
    """
    Executes one step of the agent pipeline.
    Args:
        state: current AgentState object
        user_input: latest message from user
        conversation_id: ID of the chat session
    Returns:
        dict: { reply: str, updated_state: AgentState }
    """

    memory = get_memory(conversation_id)

    # Prevent multiple documents in same session
    if state.final_document:
        reply = "✅ This conversation already has a finalized document. Start a new one to create another."
        memory.save_context({"user_input": user_input}, {"output": reply})
        return {"reply": reply, "updated_state": state}

    # Update state with new input
    state.user_input = user_input

    # ──────────────────────────────────────────────
    # 🔁 Main Orchestration: stage → chain → result
    # ──────────────────────────────────────────────
    try:
        result = AGENT_GRAPH.invoke(state)
    except Exception:
        reply = "⚠️ Sorry, something went wrong while processing your request. Please try again."
        memory.save_context({"user_input": user_input}, {"output": reply})
        return {"reply": reply, "updated_state": state}

    # ──────────────────────────────────────────────
    # 🔄 Output Handling & State Updates
    # ──────────────────────────────────────────────
    if "document_type" in result:
        state.document_type = result["document_type"]
        state.stage = "collect_fields"
        reply = f"📄 Got it! We'll draft a {state.document_type}. Let's collect required information."

    elif "fields" in result:
        state.collected_fields.update(result["fields"])
        state.required_fields = result.get("missing", [])
        if state.required_fields:
            state.stage = "collect_fields"
            reply = f"❓ Please provide: {state.required_fields[0]}"
        else:
            state.stage = "generate_draft"
            reply = "✅ All details collected. Generating your draft..."

    elif "draft" in result:
        state.draft = strip_llm_fluff(result["draft"])
        state.stage = "await_placeholder"
        state.placeholders_found = detect_placeholders(state.draft)
        if state.placeholders_found:
            reply = f"⚠️ Found placeholders: {state.placeholders_found}. Please provide missing values."
        else:
            state.stage = "await_refine"
            reply = "✅ Draft is ready. Would you like any refinements?"

    elif "placeholders" in result:
        # Placeholder resolution loop
        if state.placeholders_found:
            placeholder = state.placeholders_found.pop(0)
            state.collected_fields[placeholder] = user_input.strip()
            for ph, val in state.collected_fields.items():
                state.draft = state.draft.replace(ph, val)
            if state.placeholders_found:
                reply = f"🔁 Got it. Next: {state.placeholders_found[0]}"
            else:
                state.stage = "await_refine"
                reply = "✅ All placeholders resolved. Want to refine the draft?"
        else:
            # No placeholders found unexpectedly
            state.stage = "await_refine"
            reply = "✅ No placeholders detected. Ready for refinements?"

    elif "refined_draft" in result:
        state.draft = strip_llm_fluff(result["refined_draft"])
        reply = "✏️ I've updated the draft as requested. Any further changes?"

    elif "message" in result:
        # Q&A fallback or simple messages
        reply = result["message"]

    else:
        reply = "🤔 I'm not sure how to proceed. Could you clarify?"

    # Finalize on user command
    if state.stage == "await_refine" and user_input.lower().strip() in {"no", "none", "done", "final", "finalize"}:
        state.final_document = state.draft
        reply = "📝 Your document has been finalized. Thank you!"

    # Save turn to memory exactly once
    memory.save_context({"user_input": user_input}, {"output": reply})

    return {
        "reply": reply,
        "updated_state": state,
    }
