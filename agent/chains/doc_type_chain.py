# agent/chains/doc_type_chain.py

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.llm import llm_chain
from agent.prompts import DOC_TYPE_PROMPT

def get_doc_type_chain():
    """
    LangChain chain to identify the user's intended legal document type
    through conversational prompting and clarification.
    """
    prompt = PromptTemplate(
        input_variables=["history", "input"],
        template="""
You are a professional legal assistant. Your job is to help the user identify 
what kind of legal document they need. Start the conversation with a warm tone. 
If the user is unclear, ask clarifying questions. Never assume until confident.

Chat History:
{history}

User: {input}

{doc_type_prompt}
"""
    )

    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(doc_type_prompt=DOC_TYPE_PROMPT),
        output_key="document_type",
        verbose=True
    )
