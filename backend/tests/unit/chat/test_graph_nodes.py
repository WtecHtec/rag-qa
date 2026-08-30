from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.modules.chat.domain.state import AgentSubGraphState, ConversationState, QueryAnalysis
from app.modules.chat.nodes.aggregate_answers import aggregate_answers
from app.modules.chat.nodes.collect_answer import collect_answer
from app.modules.chat.nodes.context_compressor import compress_context, should_compress_context
from app.modules.chat.nodes.fallback_response import fallback_response
from app.modules.chat.nodes.orchestrator import orchestrator
from app.modules.chat.nodes.rewrite_query import rewrite_query
from app.modules.chat.nodes.summarize_history import summarize_history


@pytest.mark.asyncio
async def test_summarize_history_node() -> None:
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AIMessage(content="用户关注系统的架构与性能。")

    messages = [
        HumanMessage(content=f"历史消息 {i}", id=f"msg_{i}")
        for i in range(10)
    ]
    state: ConversationState = {  # type: ignore[typeddict-item]
        "messages": messages,
        "conversation_summary": "旧摘要",
    }
    updates = await summarize_history(state, fake_llm)
    assert updates["conversation_summary"] == "用户关注系统的架构与性能。"
    assert "messages" in updates


@pytest.mark.asyncio
async def test_rewrite_query_node_clear() -> None:
    fake_llm = MagicMock()
    structured_llm = AsyncMock()
    structured_llm.ainvoke.return_value = QueryAnalysis(
        is_clear=True,
        questions=["BiYou 系统的核心架构是什么？"],
        clarification_needed=None,
    )
    fake_llm.with_structured_output.return_value = structured_llm

    state: ConversationState = {  # type: ignore[typeddict-item]
        "messages": [HumanMessage(content="BiYou 系统的核心架构是什么？")],
    }
    updates = await rewrite_query(state, fake_llm)
    assert updates["questionIsClear"] is True
    assert updates["rewrittenQuestions"] == ["BiYou 系统的核心架构是什么？"]


@pytest.mark.asyncio
async def test_rewrite_query_node_unclear() -> None:
    fake_llm = MagicMock()
    structured_llm = AsyncMock()
    structured_llm.ainvoke.return_value = QueryAnalysis(
        is_clear=False,
        questions=[],
        clarification_needed="请说明您指的是哪一个文件？",
    )
    fake_llm.with_structured_output.return_value = structured_llm

    state: ConversationState = {  # type: ignore[typeddict-item]
        "messages": [HumanMessage(content="它在哪里？")],
    }
    updates = await rewrite_query(state, fake_llm)
    assert updates["questionIsClear"] is False
    assert updates["rewrittenQuestions"] == []
    assert len(updates["messages"]) == 1
    assert "请说明您指的是哪一个文件？" in updates["messages"][0].content


@pytest.mark.asyncio
async def test_orchestrator_first_step_force_search() -> None:
    fake_llm_with_tools = AsyncMock()
    fake_llm_with_tools.ainvoke.return_value = AIMessage(
        content="",
        tool_calls=[{"name": "search_child_chunks", "args": {"query": "测试"}, "id": "tc_1"}],
    )
    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "question": "测试问题",
        "messages": [],
    }
    updates = await orchestrator(state, fake_llm_with_tools)
    assert updates["iteration_count"] == 1
    assert updates["tool_call_count"] == 1
    assert len(updates["messages"]) == 2


def test_should_compress_context_under_threshold() -> None:
    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "messages": [
            HumanMessage(content="短提问"),
            AIMessage(
                content="",
                tool_calls=[{"name": "search_child_chunks", "args": {"query": "q1"}, "id": "1"}],
            ),
            ToolMessage(content="短内容", tool_call_id="1", name="search_child_chunks"),
        ],
        "context_summary": "",
    }
    command = should_compress_context(state)
    assert command.goto == "orchestrator"
    assert "search::q1" in command.update["retrieval_keys"]


@pytest.mark.asyncio
async def test_compress_context_node() -> None:
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AIMessage(content="压缩后的研究摘要内容")

    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "question": "用户问题",
        "messages": [
            HumanMessage(content="用户问题", id="m1"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "retrieve_parent_chunks", "args": {"parent_id": "p1"}, "id": "tc1"}
                ],
                id="m2",
            ),
            ToolMessage(
                content="父块大段正文", tool_call_id="tc1", name="retrieve_parent_chunks", id="m3"
            ),
        ],
        "retrieval_keys": {"parent::p1"},
    }
    updates = await compress_context(state, fake_llm)
    assert "压缩后的研究摘要内容" in updates["context_summary"]
    assert "p1" in updates["context_summary"]


@pytest.mark.asyncio
async def test_fallback_response_node() -> None:
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AIMessage(content="基于已有数据生成的兜底答案。")

    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "question": "测试问题",
        "messages": [
            ToolMessage(content="片段数据内容", tool_call_id="1", name="search_child_chunks"),
        ],
    }
    updates = await fallback_response(state, fake_llm)
    assert len(updates["messages"]) == 1
    assert updates["messages"][0].content == "基于已有数据生成的兜底答案。"


def test_collect_answer_node() -> None:
    state: AgentSubGraphState = {  # type: ignore[typeddict-item]
        "question": "子问题1",
        "question_index": 0,
        "messages": [AIMessage(content="单子问题的有效回答")],
        "retrieved_contexts": ["证据1"],
    }
    updates = collect_answer(state)
    assert updates["final_answer"] == "单子问题的有效回答"
    assert len(updates["agent_answers"]) == 1
    assert updates["agent_answers"][0]["answer"] == "单子问题的有效回答"


@pytest.mark.asyncio
async def test_aggregate_answers_node() -> None:
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AIMessage(content="综合汇总后的回答。")

    state: ConversationState = {  # type: ignore[typeddict-item]
        "originalQuery": "原问题",
        "messages": [],
        "agent_answers": [
            {"index": 0, "question": "子问题1", "answer": "回答1"},
            {"index": 1, "question": "子问题2", "answer": "回答2"},
        ],
    }
    updates = await aggregate_answers(state, fake_llm)
    assert len(updates["messages"]) == 1
    assert updates["messages"][0].content == "综合汇总后的回答。"
