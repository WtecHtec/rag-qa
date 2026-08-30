from __future__ import annotations

import operator
from typing import Annotated, Any

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


def accumulate_or_reset(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """答案累加器：当传入包含 __reset__ 标记时清空重置，否则追加子图回答。"""
    if new and any(item.get("__reset__") for item in new):
        return []
    return existing + new


def set_union(a: set[str], b: set[str]) -> set[str]:
    """已执行检索 Key 集合的并集合并。"""
    return a | b


def append_unique(existing: list[str], new: list[str]) -> list[str]:
    """保持元素唯一性的列表合并。"""
    return list(dict.fromkeys(existing + new))


class QueryAnalysis(BaseModel):
    """查询意图结构化分析结果。"""

    is_clear: bool = Field(
        description="问题是否表意清晰且具备独立的检索条件，无需反问用户澄清"
    )
    questions: list[str] = Field(
        default_factory=list,
        description="重写后适合向量检索的独立子问题列表（最多 3 个）",
    )
    clarification_needed: str | None = Field(
        default=None,
        description="当问题不清晰（例如存在模糊代词）时向用户反问的澄清提示语",
    )


class ConversationState(MessagesState):
    """主图（Main Graph）全局状态。"""

    questionIsClear: bool = False
    conversation_summary: str = ""
    originalQuery: str = ""
    pendingQuery: str = ""
    pendingClarifications: list[str] = []
    rewrittenQuestions: list[str] = []
    agent_answers: Annotated[list[dict[str, Any]], accumulate_or_reset] = []


class AgentSubGraphState(MessagesState):
    """子图（Agent Subgraph）单个子问题的检索与研究循环状态。"""

    question: str = ""
    question_index: int = 0
    context_summary: str = ""
    retrieval_keys: Annotated[set[str], set_union] = set()
    retrieved_contexts: Annotated[list[str], append_unique] = []
    final_answer: str = ""
    agent_answers: list[dict[str, Any]] = []
    tool_call_count: Annotated[int, operator.add] = 0
    iteration_count: Annotated[int, operator.add] = 0
