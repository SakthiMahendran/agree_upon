import logging
import re
from langchain.schema import HumanMessage
from agent.state import AgentState
from agent.llm import call_llm_with_retry

logger = logging.getLogger("agent.handlers")

def init_handler(state: AgentState) -> AgentState:
    logger.info("Handler init")
    msg = [
        HumanMessage(role="system", content="You are a concise Canadian legal assistant."),
        HumanMessage(role="user", content="Greet the user and ask which document they’d like drafted.")
    ]
    state.draft = call_llm_with_retry(msg)
    return state

def conversation_handler(state: AgentState) -> AgentState:
    logger.info("Handler conversation; user_input=%r", state.user_input)
    if not state.document_type:
        msg = [
            HumanMessage(role="system", content="You are a helpful Canadian legal assistant."),
            HumanMessage(role="user", content="Hello! Which legal document would you like to draft? NDA, Lease, etc.")
        ]
    else:
        msg = [
            HumanMessage(role="system", content="You are a Canadian legal assistant. Reply conversationally."),
            HumanMessage(role="user", content=state.user_input)
        ]
    state.draft = call_llm_with_retry(msg)
    return state

def identify_document_handler(state: AgentState) -> AgentState:
    logger.info("Handler identify_document; user_input=%r", state.user_input)
    prompt = (
        f"User wants: “{state.user_input}”.\n"
        "Return only JSON: {\"document_name\":\"…\",\"fields\":[\"Field1\",\"Field2\",…]}"
    )
    msg = [
        HumanMessage(role="system", content="Output only valid JSON."),
        HumanMessage(role="user", content=prompt)
    ]
    resp = call_llm_with_retry(msg)
    try:
        data = __import__("json").loads(resp)
        state.document_type = data["document_name"]
        state.required_fields = data["fields"]
        logger.info("Parsed document_type=%s fields=%s", state.document_type, state.required_fields)
    except Exception:
        state.error_message = "Could not parse document type or fields."
        logger.error("Failed to parse JSON from %r", resp)
    return state

def prepare_fields_handler(state: AgentState) -> AgentState:
    logger.info("Handler prepare_fields")
    if state.required_fields:
        state.current_field = state.required_fields[0]
        logger.info("Next field: %r", state.current_field)
    return state

def collect_field_handler(state: AgentState) -> AgentState:
    logger.info("Handler collect_field; current_field=%r user_input=%r",
                state.current_field, state.user_input)
    if not state.current_field and state.required_fields:
        state.current_field = state.required_fields[0]
    if not state.current_field:
        logger.warning("No field to collect; skipping")
        return state
    if not state.user_input:
        state.error_message = f"{state.current_field} is required."
    else:
        state.collected_info[state.current_field] = state.user_input
        if state.required_fields and state.required_fields[0] == state.current_field:
            state.required_fields.pop(0)
        state.current_field = ""
    return state

def generate_draft_handler(state: AgentState) -> AgentState:
    logger.info("Handler generate_draft")
    info = "\n".join(f"- {k}: {v}" for k, v in state.collected_info.items())
    prompt = f"Draft a {state.document_type} under Canadian law using:\n{info}\n\nReturn only the document text."
    msg = [
        HumanMessage(role="system", content="Be concise."),
        HumanMessage(role="user", content=prompt)
    ]
    state.draft = call_llm_with_retry(msg)
    state.placeholders_found = re.findall(r"\[([^\]]+)\]", state.draft)
    state.has_drafted_once = True
    return state

def clarify_placeholders_handler(state: AgentState) -> AgentState:
    logger.info("Handler clarify_placeholders")
    answers = state.user_input.split("|||")
    for ph, ans in zip(state.placeholders_found, answers):
        state.collected_info[ph] = ans.strip()
    state.placeholders_found.clear()
    return state

def refine_handler(state: AgentState) -> AgentState:
    logger.info("Handler refine; request=%r", state.refine_request)
    prompt = f"Refine this {state.document_type}:\n{state.draft}\nChanges: {state.refine_request}"
    msg = [
        HumanMessage(role="system", content="Do not add placeholders."),
        HumanMessage(role="user", content=prompt)
    ]
    state.draft = call_llm_with_retry(msg)
    return state

def finalize_handler(state: AgentState) -> AgentState:
    logger.info("Handler finalize")
    state.final_document = state.draft
    return state

def answer_question_handler(state: AgentState) -> AgentState:
    logger.info("Handler answer_question; user_input=%r", state.user_input)
    prompt = f"Based on the document:\n{state.draft}\nAnswer: {state.user_input}"
    msg = [
        HumanMessage(role="system", content="Answer concisely."),
        HumanMessage(role="user", content=prompt)
    ]
    state.draft = call_llm_with_retry(msg)
    return state

def handle_error_handler(state: AgentState) -> AgentState:
    logger.info("Handler handle_error; error=%r", state.error_message)
    return state
