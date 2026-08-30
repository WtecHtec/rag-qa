from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.modules.chat.domain.state import ConversationState, QueryAnalysis
from app.modules.chat.domain.utils import (
    format_conversation,
    get_recent_conversation,
    name_internal_message,
)
from app.modules.chat.prompts.agent_prompts import get_rewrite_query_prompt


async def rewrite_query(state: ConversationState, llm: Any) -> dict[str, Any]:
    """利用结构化输出识别用户查询清晰度，并拆解为 1~3 个适合向量检索的独立子问题。"""
    messages = state.get("messages", [])
    if not messages:
        return {"questionIsClear": False, "rewrittenQuestions": []}

    last_message = messages[-1]
    current_query = str(last_message.content).strip()
    conversation_summary = state.get("conversation_summary", "").strip()
    pending_query = state.get("pendingQuery", "").strip()
    pending_clarifications = state.get("pendingClarifications", [])
    recent_messages = get_recent_conversation(messages, pending_query)

    context_parts: list[str] = []
    if conversation_summary:
        context_parts.append(f"历史会话摘要：\n{conversation_summary}")
    if recent_messages:
        context_parts.append(f"最近对话记录：\n{format_conversation(recent_messages)}")

    if pending_query:
        clarifications = [*pending_clarifications, current_query]
        clarification_text = "\n".join(
            f"{index}. {value}" for index, value in enumerate(clarifications, start=1)
        )
        context_parts.append(
            f"未解决的原始提问：\n{pending_query}\n\n"
            f"用户补充的澄清说明：\n{clarification_text}"
        )
        original_query = f"{pending_query}\n澄清说明：\n{clarification_text}"
    else:
        clarifications = []
        context_parts.append(f"用户提问：\n{current_query}")
        original_query = current_query

    context_section = "\n\n".join(context_parts)
    prompt = [
        SystemMessage(content=get_rewrite_query_prompt()),
        HumanMessage(content=context_section),
    ]

    llm_with_structure = llm.with_structured_output(QueryAnalysis)
    if hasattr(llm_with_structure, "ainvoke"):
        response: QueryAnalysis = await llm_with_structure.ainvoke(prompt)
    else:
        response: QueryAnalysis = llm_with_structure.invoke(prompt)

    clarification_message_update = (
        [name_internal_message(last_message, "clarification_response")]
        if pending_query
        else []
    )

    if response.questions and response.is_clear:
        return {
            "questionIsClear": True,
            "originalQuery": original_query,
            "pendingQuery": "",
            "pendingClarifications": [],
            "rewrittenQuestions": response.questions,
            "messages": clarification_message_update,
        }

    clarification = (
        response.clarification_needed
        if response.clarification_needed and len(response.clarification_needed.strip()) > 5
        else "请补充更多具体背景信息，以便我能更准确地检索文档并为您解答。"
    )
    return {
        "questionIsClear": False,
        "originalQuery": "",
        "pendingQuery": pending_query or current_query,
        "pendingClarifications": clarifications,
        "rewrittenQuestions": [],
        "messages": clarification_message_update + [
            AIMessage(content=clarification, name="clarification")
        ],
    }
