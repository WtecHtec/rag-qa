from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.modules.chat.domain.state import ConversationState
from app.modules.chat.domain.utils import (
    PRE_ANSWER_HISTORY_MESSAGES_TO_KEEP,
    filter_messages_to_remove,
    is_plain_conversation_message,
)
from app.modules.chat.prompts.agent_prompts import get_aggregation_prompt


async def aggregate_answers(state: ConversationState, llm: Any) -> dict[str, Any]:
    """主图聚合节点：对各个子问题收集到的检索结论进行综合归纳润色。"""
    messages = state.get("messages", [])
    plain_messages = [msg for msg in messages if is_plain_conversation_message(msg)]
    keep_ids = {
        getattr(msg, "id", None)
        for msg in plain_messages[-PRE_ANSWER_HISTORY_MESSAGES_TO_KEEP:]
    }
    keep_ids.discard(None)
    removals = filter_messages_to_remove(messages, keep_ids)

    agent_answers = state.get("agent_answers", [])
    if not agent_answers:
        return {"messages": removals + [AIMessage(content="未能从文档中生成有效回答。")]}

    sorted_answers = sorted(agent_answers, key=lambda x: x.get("index", 0))
    formatted_answers = ""
    for i, ans in enumerate(sorted_answers, start=1):
        formatted_answers += f"\n子问题检索回答 {i}（针对：{ans.get('question')}）：\n{ans.get('answer')}\n"

    user_message = HumanMessage(
        content=f"用户原始提问：{state.get('originalQuery')}\n各子问题检索回答：{formatted_answers}"
    )
    prompt = [SystemMessage(content=get_aggregation_prompt()), user_message]

    if hasattr(llm, "ainvoke"):
        synthesis_response = await llm.ainvoke(prompt)
    else:
        synthesis_response = llm.invoke(prompt)

    return {"messages": removals + [AIMessage(content=str(synthesis_response.content))]}
