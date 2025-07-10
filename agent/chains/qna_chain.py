from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.llm import llm_chain

QNA_PROMPT = """
You are a professional legal document drafting assistant.  
Engage the user in a back-and-forth Q&A to gather every detail needed to draft their document.
If something is still missing, ask a clear follow-up question.
"""

def get_qna_chain() -> LLMChain:
    prompt = PromptTemplate(
        input_variables=["history", "input"],
        template="""
Chat History:
{history}

User: {input}

{qna_prompt}
"""
    )
    return LLMChain(
        llm=llm_chain,
        prompt=prompt.partial(qna_prompt=QNA_PROMPT),
        output_key="message"
    )
