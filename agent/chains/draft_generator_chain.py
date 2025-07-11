# agent/chains/draft_generator_chain.py

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.llm import llm_chain
from agent.prompts import DRAFT_GENERATOR_PROMPT

def get_draft_generator_chain(doc_type: str, fields: dict):
    """
    Generates a clean, professional legal document draft using the collected fields.
    Ensures no fluff, AI phrases, or incomplete placeholders.
    """
    prompt = PromptTemplate(
        input_variables=["history", "input", "doc_type", "fields"],
        template="""
You are an expert legal document drafter. Using the provided document type and user data,
generate a complete and professional draft. Avoid phrases like "Here's your document" or 
"Below is the content". Use formal, clear legal language. Do not include any placeholders 
like [DATE], [NAME], etc.

Document Type: {doc_type}
Collected Fields:
{fields}

Chat History:
{history}

User: {input}

{draft_generator_prompt}
"""
    )

    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(
            draft_generator_prompt=DRAFT_GENERATOR_PROMPT,
            doc_type=doc_type,
            fields=fields
        ),
        output_key="draft",
        verbose=True
    )
