"""Tests of foundry_agent.py: the wrapper graph that Foundry hosts.

The Foundry host streams the graph with stream_mode ["updates", "messages"] and shows the person every
message it gets. These tests stream the wrapper graph in the same way. Only the final reply may come out.
The LLM is a fake with scripted answers (a greeting needs no agent, so Neo4j is not used).
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

import foundry_agent
from src.agents import answer_writer, planner


@pytest.fixture
def model(monkeypatch):
    """Scripted answers for the planner and the writer. Records what the planner received."""

    class FakeModel:
        def __init__(self):
            self.script, self.received = [], []

        def __call__(
            self, messages, tools, system_prompt, one_tool_at_a_time=False, **settings
        ):
            self.received.append(list(messages))
            return self.script.pop(0)

    fakes = {"planner": FakeModel(), "writer": FakeModel()}
    monkeypatch.setattr(planner, "ask_llm_with_tools", fakes["planner"])
    monkeypatch.setattr(answer_writer, "ask_llm_with_tools", fakes["writer"])
    return fakes


def stream_like_the_host(graph, question, thread_id):
    """All the messages that the host would show the person for one question."""
    shown = []
    for mode, payload in graph.stream(
        {"messages": [HumanMessage(question)]},
        {"configurable": {"thread_id": thread_id}},
        stream_mode=["updates", "messages"],
    ):
        if mode == "messages":
            shown.append(payload[0])
        else:
            for update in payload.values():
                shown.extend(update["messages"])
    return [message for message in shown if not isinstance(message, HumanMessage)]


def test_only_the_final_reply_reaches_the_person(model):
    model["planner"].script = [AIMessage("Note: greet the person.")]
    model["writer"].script = [AIMessage("Hello. Ask me about claims.")]
    shown = stream_like_the_host(foundry_agent.build_hosted_graph(), "Hi", "t-1")
    assert {message.text for message in shown} == {"Hello. Ask me about claims."}


def test_the_chat_remembers_the_conversation_of_a_thread(model):
    graph = foundry_agent.build_hosted_graph()
    model["planner"].script = [AIMessage("Note: greet."), AIMessage("Note: greet.")]
    model["writer"].script = [AIMessage("Hello."), AIMessage("Hello again.")]
    stream_like_the_host(graph, "Hi", "t-2")
    stream_like_the_host(graph, "Hi again", "t-2")
    # The planner of the second message sees the first question, its note, the reply and the new question.
    assert [message.text for message in model["planner"].received[1]][0] == "Hi"
    assert len(model["planner"].received[1]) == 4
