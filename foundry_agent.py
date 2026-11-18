"""The entry point for Microsoft Foundry. It gives the chat to the Foundry hosting package.

Foundry starts the agent with:
    python -m langchain_azure_ai.agents.hosting.run --protocol responses
That command reads langgraph.json. langgraph.json points to `graph` in this file.

Why a wrapper graph?
The hosting package sends the person every message that the hosted graph makes: the planner's notes, the
text of each search agent and the tool results. Plain code checks only the answer writer's reply (the
grounding check). So only that reply may reach the person.
This graph has ONE node. The node runs the normal chat workflow (src/workflow.py) out of sight, and returns
only the final reply. The chat workflow itself does not change.

Memory:
The host gives each conversation a thread ID. The chat workflow keeps the full conversation of that thread
ID in its own memory, the same as `python main.py chat`. The memory lasts until the agent restarts.

Run it on this computer (the same command that Foundry uses):
    .venv/Scripts/python -m langchain_azure_ai.agents.hosting.run --protocol responses
"""

import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from src.state import ChatState
from src.workflow import build_chat_workflow

# One chat workflow for all conversations. Its memory keeps each thread ID apart.
CHAT_WORKFLOW = build_chat_workflow()


def answer_question(state: ChatState, config: RunnableConfig):
    """The only node. Run one message of the chat out of sight. Return only the checked reply."""
    question = state["messages"][-1].text
    thread_id = config.get("configurable", {}).get("thread_id") or str(uuid.uuid4())
    # callbacks=[] and metadata={}: the inner run does not report to the host, so the host cannot show
    # the inner messages. configurable: only the thread ID, so the inner run uses its own memory.
    final_state = CHAT_WORKFLOW.invoke(
        {"messages": [HumanMessage(question)]},
        {"configurable": {"thread_id": thread_id}, "callbacks": [], "metadata": {}},
    )
    return {"messages": [AIMessage(final_state["messages"][-1].text)]}


def build_hosted_graph():
    """START -> answer_question -> END. The checkpointer lets the host give each conversation a thread ID."""
    builder = StateGraph(ChatState)
    builder.add_node("answer_question", answer_question)
    builder.add_edge(START, "answer_question")
    builder.add_edge("answer_question", END)
    return builder.compile(checkpointer=InMemorySaver())


graph = build_hosted_graph()
