from langgraph.graph import StateGraph
from agent.state import AgentState
from agent.handlers import (
    conversation_handler,
    identify_document_handler,
    prepare_fields_handler,
    collect_field_handler,
    generate_draft_handler,
    clarify_placeholders_handler,
    refine_handler,
    finalize_handler,
    answer_question_handler,
    handle_error_handler,
)

def build_agent_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # Nodes
    g.add_node("conversation", conversation_handler)
    g.add_node("identify_document", identify_document_handler)
    g.add_node("prepare_fields", prepare_fields_handler)
    g.add_node("collect_field", collect_field_handler)
    g.add_node("generate_draft", generate_draft_handler)
    g.add_node("clarify_placeholders", clarify_placeholders_handler)
    g.add_node("refine", refine_handler)
    g.add_node("finalize", finalize_handler)
    g.add_node("answer_question", answer_question_handler)
    g.add_node("handle_error", handle_error_handler)

    # Entry
    g.set_entry_point("conversation")

    # From conversation choose branch
    def conv_next(st: AgentState):
        t = st.user_input.lower().strip()
        if not st.document_type and any(w in t for w in ["draft", "create", "generate"]):
            return "identify_document"
        if t.endswith("?"):
            return "answer_question"
        if st.refine_request:
            return "refine"
        return "conversation"

    g.add_conditional_edges(
        "conversation",
        conv_next,
        {
            "identify_document": "identify_document",
            "answer_question": "answer_question",
            "refine": "refine",
            "conversation": "conversation",
        },
    )

    # Drafting workflow
    g.add_edge("identify_document", "prepare_fields")
    g.add_edge("prepare_fields", "collect_field")
    g.add_conditional_edges(
        "collect_field",
        lambda st: "collect_field" if st.required_fields else "generate_draft",
        {"collect_field": "collect_field", "generate_draft": "generate_draft", "handle_error": "handle_error"},
    )
    g.add_edge("generate_draft", "clarify_placeholders")
    g.add_conditional_edges(
        "clarify_placeholders",
        lambda st: "clarify_placeholders" if st.placeholders_found else "finalize",
        {"clarify_placeholders": "clarify_placeholders", "finalize": "finalize"},
    )

    # Return to conversation
    for node in ("finalize", "refine", "answer_question", "handle_error"):
        g.add_edge(node, "conversation")

    return g
