# agent/chains/field_collector_chain.py

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.llm import llm_chain
from agent.prompts import FIELD_COLLECTOR_PROMPT

def get_field_collector_chain(doc_type: str):
    """
    LangChain chain to determine and collect all required fields for a given document type.
    Ensures clarity and structure in the questions asked.
    """
    prompt = PromptTemplate(
        input_variables=["history", "input", "doc_type"],
        template="""
You are a legal assistant tasked with collecting all necessary information to draft a {doc_type}.
Be precise. Do not assume anything. Ask one field at a time and ensure it's complete and unambiguous.

Chat History:
{history}

User: {input}

{field_collector_prompt}
"""
    )

    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(field_collector_prompt=FIELD_COLLECTOR_PROMPT, doc_type=doc_type),
        output_key="fields"
    )
