from __future__ import annotations

from collections.abc import Sequence
from functools import partial
from typing import Any

from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.modules.chat.domain.state import AgentSubGraphState, ConversationState
from app.modules.chat.edges.routing import route_after_orchestrator, route_after_rewrite
from app.modules.chat.nodes.aggregate_answers import aggregate_answers
from app.modules.chat.nodes.collect_answer import collect_answer
from app.modules.chat.nodes.context_compressor import compress_context, should_compress_context
from app.modules.chat.nodes.fallback_response import fallback_response
from app.modules.chat.nodes.orchestrator import orchestrator
from app.modules.chat.nodes.request_clarification import request_clarification
from app.modules.chat.nodes.rewrite_query import rewrite_query
from app.modules.chat.nodes.summarize_history import summarize_history


def create_agentic_rag_graph(
    llm: Any,
    tools: Sequence[BaseTool],
    *,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Any:
    """构建并编译 Agentic RAG 双层状态机图（主图 + 子图研究循环）。"""
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    # 1. 构建子图（针对单个子问题的两阶段检索与研究循环）
    agent_builder = StateGraph(AgentSubGraphState)
    agent_builder.add_node(
        "orchestrator", partial(orchestrator, llm_with_tools=llm_with_tools)
    )
    agent_builder.add_node("tools", tool_node)
    agent_builder.add_node("compress_context", partial(compress_context, llm=llm))
    agent_builder.add_node("fallback_response", partial(fallback_response, llm=llm))
    agent_builder.add_node("should_compress_context", should_compress_context)
    agent_builder.add_node("collect_answer", collect_answer)

    agent_builder.add_edge(START, "orchestrator")
    agent_builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "tools": "tools",
            "fallback_response": "fallback_response",
            "collect_answer": "collect_answer",
        },
    )
    agent_builder.add_edge("tools", "should_compress_context")
    agent_builder.add_edge("compress_context", "orchestrator")
    agent_builder.add_edge("fallback_response", "collect_answer")
    agent_builder.add_edge("collect_answer", END)

    agent_subgraph = agent_builder.compile()

    # 2. 构建主图（全局历史摘要、意图拆解、Map-Reduce 扇出与结果综合）
    graph_builder = StateGraph(ConversationState)
    graph_builder.add_node("summarize_history", partial(summarize_history, llm=llm))
    graph_builder.add_node("rewrite_query", partial(rewrite_query, llm=llm))
    graph_builder.add_node("request_clarification", request_clarification)
    graph_builder.add_node("agent", agent_subgraph)
    graph_builder.add_node("aggregate_answers", partial(aggregate_answers, llm=llm))

    graph_builder.add_edge(START, "summarize_history")
    graph_builder.add_edge("summarize_history", "rewrite_query")
    graph_builder.add_conditional_edges("rewrite_query", route_after_rewrite)
    graph_builder.add_edge("request_clarification", "rewrite_query")
    graph_builder.add_edge(["agent"], "aggregate_answers")
    graph_builder.add_edge("aggregate_answers", END)

    active_checkpointer = checkpointer or InMemorySaver()
    return graph_builder.compile(
        checkpointer=active_checkpointer,
        interrupt_before=["request_clarification"],
    )
