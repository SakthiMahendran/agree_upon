# agent/agent.py

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor, Tool

from .tools import legal_web_search

logger = logging.getLogger("agent.agent")
logger.setLevel(logging.INFO)
logging.basicConfig()

def get_drafting_prompt():
    system_prompt = """
You are an expert AI legal assistant operating in Canada.
Speak formally and professionally.
1. Greet the user and ask what document they wish to draft.
2. Ask one question at a time to gather all required details.
3. If you need statutes or case law, say "I will now search…" then use the Legal_Web_Search tool.
4. When ready, output exactly: DRAFT_COMPLETE: <full document>
"""
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

def get_refinement_prompt(document: str, user_request: str) -> str:
    return f"""
You are refining an existing Canadian legal document.
Original draft:
---
{document}
---
User requests:
"{user_request}"
---
Return the full updated document text only.
"""

def get_agent_executor(api_key: str) -> AgentExecutor:
    # 1) LLM
    llm = ChatOpenAI(
        openai_api_base="https://oaitzvyxm6614ekn.us-east-1.aws.endpoints.huggingface.cloud/v1",
        openai_api_key=api_key,
        temperature=0.3,
        max_tokens=8192,
    )

    # 2) Wrap your function in a Tool
    tools = [
        Tool(
            name="Legal_Web_Search",
            func=legal_web_search,
            description="Fetch Canadian statutes or case law references."
        )
    ]

    # 3) Prompt template
    prompt = get_drafting_prompt()

    # 4) Build and return a verbose AgentExecutor
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return executor
