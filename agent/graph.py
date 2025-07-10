# agent/graph.py

from langchain_core.runnables import RunnableBranch, RunnableLambda
from agent.state import AgentState
from agent.chains.doc_type_chain import get_doc_type_chain
from agent.chains.field_collector_chain import get_field_collector_chain
from agent.chains.draft_generator_chain import get_draft_generator_chain
from agent.chains.placeholder_checker import get_placeholder_checker_chain
from agent.chains.refiner_chain import get_refiner_chain
from agent.chains.qna_chain import get_qna_chain
from agent.utils import invoke_with_retry

AGENT_GRAPH = RunnableBranch(
    # 0️⃣ Already finalized?
    (
        lambda s: bool(s.final_document),
        RunnableLambda(lambda s: {"message": "✅ This document is already finalized."})
    ),

    # 1️⃣ Identify document type
    (
        lambda s: s.stage == "identify_doc",
        RunnableLambda(lambda s: {
            "document_type": invoke_with_retry(
                get_doc_type_chain(),
                {"history": "", "input": s.user_input}
            )
        })
    ),

    # 2️⃣ Collect required fields
    (
        lambda s: s.stage == "collect_fields",
        RunnableLambda(lambda s: {
            "fields": invoke_with_retry(
                get_field_collector_chain(s.document_type),
                {
                    "history": "",
                    "input": s.user_input,
                    "doc_type": s.document_type
                }
            )
        })
    ),

    # 3️⃣ Generate initial draft
    (
        lambda s: s.stage == "generate_draft",
        RunnableLambda(lambda s: {
            "draft": invoke_with_retry(
                get_draft_generator_chain(s.document_type, s.collected_fields),
                {
                    "history": "",
                    "input": s.user_input,
                    "doc_type": s.document_type,
                    "fields": s.collected_fields
                }
            )
        })
    ),

    # 4️⃣ Check placeholders
    (
        lambda s: s.stage == "await_placeholder",
        RunnableLambda(lambda s: {
            "placeholders": invoke_with_retry(
                get_placeholder_checker_chain(),
                {"draft": s.draft}
            )
        })
    ),

    # 5️⃣ Apply refinements
    (
        lambda s: s.stage == "await_refine" and bool(s.refine_request),
        RunnableLambda(lambda s: {
            "refined_draft": invoke_with_retry(
                get_refiner_chain(),
                {
                    "draft": s.draft,
                    "instruction": s.refine_request
                }
            )
        })
    ),

    # 🛑 Default Q&A fallback
    RunnableLambda(lambda s: {
        "message": invoke_with_retry(
            get_qna_chain(),
            {"history": "", "input": s.user_input}
        )
    })
)
