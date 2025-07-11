# agent/chains/refiner_chain.py

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.llm import llm_chain
from agent.prompts import REFINER_PROMPT

def get_refiner_chain():
    """
    Allows the user to request refinements or edits to the generated document.
    Applies changes without adding AI commentary and ensures the document remains clean and legal.
    """
    prompt = PromptTemplate(
        input_variables=["draft", "instruction"],
        template="""
You are a legal writing assistant. The user has provided a legal draft and wants to make changes.

Do not add commentary like "Here is the revised version".
Just return the clean, updated document directly.

Original Draft:
{draft}

User's Refinement Instruction:
{instruction}

{refiner_prompt}
"""
    )

    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(refiner_prompt=REFINER_PROMPT),
        output_key="refined_draft",
        verbose=True
    )
