from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.modules.chat.domain.state import ConversationState
from app.modules.chat.domain.utils import (
    PRE_ANSWER_HISTORY_MESSAGES_TO_KEEP,
    filter_messages_to_remove,
    format_conversation,
    is_plain_conversation_message,
)
from app.modules.chat.prompts.agent_prompts import get_conversation_summary_prompt


async def summarize_history(state: ConversationState, llm: Any) -> dict[str, Any]:
    """对较旧的历史消息做滚动增量摘要压缩，保持最近消息窗口。"""
    messages = state.get("messages", [])
    updates: dict[str, Any] = {"agent_answers": [{"__reset__": True}]}

    if not messages:
        return updates

    plain_messages = [msg for msg in messages if is_plain_conversation_message(msg)]
    keep_count = PRE_ANSWER_HISTORY_MESSAGES_TO_KEEP
    messages_to_summarize = plain_messages[:-keep_count] if len(plain_messages) > keep_count else []
    keep_ids = {getattr(msg, "id", None) for msg in plain_messages[-keep_count:]}
    keep_ids.discard(None)

    removals = filter_messages_to_remove(messages, keep_ids)
    if removals:
        updates["messages"] = removals

    if not messages_to_summarize:
        return updates

    existing_summary = state.get("conversation_summary", "").strip()
    conversation = "现有历史摘要：\n"
    conversation += f"{existing_summary or '(暂无)'}\n\n"
    conversation += "待合并的较早对话记录：\n"
    conversation += format_conversation(messages_to_summarize)

    prompt = [
        SystemMessage(content=get_conversation_summary_prompt()),
        HumanMessage(content=conversation),
    ]
    if hasattr(llm, "ainvoke"):
        summary_response = await llm.ainvoke(prompt)
    else:
        summary_response = llm.invoke(prompt)

    updates["conversation_summary"] = str(summary_response.content).strip()
    return updates
