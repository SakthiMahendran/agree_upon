# agent/chains/placeholder_checker.py

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.llm import llm_chain
from agent.prompts import PLACEHOLDER_CHECKER_PROMPT

def get_placeholder_checker_chain():
    """
    Detects if the generated draft contains unresolved placeholders like [NAME], [DATE], etc.
    If found, these should be confirmed with the user and replaced before finalizing the document.
    """
    prompt = PromptTemplate(
        input_variables=["draft"],
        template="""
You are reviewing a legal document draft to detect any unresolved placeholders such as:
[DATE], [NAME], [ADDRESS], etc.

Document:
{draft}

{placeholder_checker_prompt}
"""
    )

    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(placeholder_checker_prompt=PLACEHOLDER_CHECKER_PROMPT),
        output_key="placeholders"
    )
