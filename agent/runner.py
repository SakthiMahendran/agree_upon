import uuid
from langgraph.runner import GraphRunner
from agent.state import AgentState
from agent.graph import build_agent_graph

def main():
    graph = build_agent_graph()
    graph.set_finish_point("finalize")
    runner = graph.compile()

    session = str(uuid.uuid4())
    state = AgentState(session_id=session)

    # Simple loop: read stdin, write draft state
    while True:
        runner.invoke(state.model_dump(), {})
        print("\n[Agent]:", state.draft or state.error_message)
        inp = input("You: ").strip()
        if inp.lower() in ("exit","quit"):
            break
        state.user_input = inp

if __name__ == "__main__":
    main()
