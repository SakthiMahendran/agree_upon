# agent/memory.py

from langchain.memory import ConversationBufferMemory

def get_memory(conversation_id: str) -> ConversationBufferMemory:
    """
    Returns a LangChain memory object for a given conversation.
    Uses a simple chat buffer since token-counting isn't supported by deepseek-chat.
    """
    return ConversationBufferMemory(
        memory_key="chat_history",
        input_key="user_input",
        return_messages=True,
    )
