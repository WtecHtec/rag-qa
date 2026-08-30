from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from app.modules.chat.domain.state import AgentSubGraphState, ConversationState

MAX_ITERATIONS = 5
MAX_TOOL_CALLS = 8


def route_after_rewrite(
    state: ConversationState,
) -> Literal["request_clarification"] | list[Send]:
    """主图重写后条件路由：未通过清晰度判定则流向澄清，否则扇出给子图处理各个子问题。"""
    if not state.get("questionIsClear", False):
        return "request_clarification"

    rewritten = state.get("rewrittenQuestions") or []
    if not rewritten:
        return "request_clarification"

    return [
        Send("agent", {"question": query, "question_index": idx, "messages": []})
        for idx, query in enumerate(rewritten)
    ]


def route_after_orchestrator(
    state: AgentSubGraphState,
    *,
    max_iterations: int = MAX_ITERATIONS,
    max_tool_calls: int = MAX_TOOL_CALLS,
) -> Literal["tools", "fallback_response", "collect_answer"]:
    """子图编排后条件路由：无工具调用则收集答案，超预算则降级兜底，否则继续调用工具。"""
    iteration = state.get("iteration_count", 0)
    tool_count = state.get("tool_call_count", 0)

    messages = state.get("messages", [])
    if not messages:
        return "collect_answer"

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []

    if not tool_calls:
        return "collect_answer"

    if iteration >= max_iterations or tool_count > max_tool_calls:
        return "fallback_response"

    return "tools"
