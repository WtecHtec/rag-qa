from langchain_core.messages import AIMessage
from langgraph.types import Send

from app.modules.chat.domain.state import AgentSubGraphState, ConversationState
from app.modules.chat.edges.routing import route_after_orchestrator, route_after_rewrite


def test_route_after_rewrite_unclear() -> None:
    state: ConversationState = {"questionIsClear": False, "rewrittenQuestions": []}  # type: ignore[typeddict-item]
    result = route_after_rewrite(state)
    assert result == "request_clarification"


def test_route_after_rewrite_clear_single_question() -> None:
    state: ConversationState = {  # type: ignore[typeddict-item]
        "questionIsClear": True,
        "rewrittenQuestions": ["BiYou 系统的主要功能是什么？"],
    }
    result = route_after_rewrite(state)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Send)
    assert result[0].node == "agent"
    assert result[0].arg["question"] == "BiYou 系统的主要功能是什么？"
    assert result[0].arg["question_index"] == 0


def test_route_after_rewrite_clear_multiple_questions() -> None:
    state: ConversationState = {  # type: ignore[typeddict-item]
        "questionIsClear": True,
        "rewrittenQuestions": ["子问题1", "子问题2"],
    }
    result = route_after_rewrite(state)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].arg["question"] == "子问题1"
    assert result[1].arg["question"] == "子问题2"


def test_route_after_orchestrator_no_tool_calls() -> None:
    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "messages": [AIMessage(content="最终生成的答案文本")],
        "iteration_count": 1,
        "tool_call_count": 0,
    }
    result = route_after_orchestrator(state)
    assert result == "collect_answer"


def test_route_after_orchestrator_with_tool_calls_under_budget() -> None:
    msg = AIMessage(
        content="",
        tool_calls=[{"name": "search_child_chunks", "args": {"query": "关键词"}, "id": "1"}],
    )
    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "messages": [msg],
        "iteration_count": 2,
        "tool_call_count": 2,
    }
    result = route_after_orchestrator(state)
    assert result == "tools"


def test_route_after_orchestrator_exceeded_budget() -> None:
    msg = AIMessage(
        content="",
        tool_calls=[{"name": "search_child_chunks", "args": {"query": "关键词"}, "id": "1"}],
    )
    # 达到最大迭代轮次 (MAX_ITERATIONS = 5)
    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "messages": [msg],
        "iteration_count": 5,
        "tool_call_count": 3,
    }
    result = route_after_orchestrator(state)
    assert result == "fallback_response"
