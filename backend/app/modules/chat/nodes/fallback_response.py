from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.modules.chat.domain.state import AgentSubGraphState
from app.modules.chat.domain.utils import name_internal_message
from app.modules.chat.prompts.agent_prompts import get_fallback_response_prompt


async def fallback_response(state: AgentSubGraphState, llm: Any) -> dict[str, Any]:
    """当检索轮次或工具调用达到预算上限时，基于已检索到的证据生成降级兜底回答。"""
    seen: set[str] = set()
    unique_contents: list[str] = []
    for m in state.get("messages", []):
        if isinstance(m, ToolMessage) and m.content not in seen:
            unique_contents.append(str(m.content))
            seen.add(str(m.content))

    context_summary = state.get("context_summary", "").strip()
    context_parts: list[str] = []
    if context_summary:
        context_parts.append(
            f"## 前期检索总结的研究上下文\n\n{context_summary}"
        )
    if unique_contents:
        context_parts.append(
            "## 当前最新检索到的片段数据\n\n"
            + "\n\n".join(
                f"--- 检索数据源 {i} ---\n{content}"
                for i, content in enumerate(unique_contents, 1)
            )
        )

    context_text = (
        "\n\n".join(context_parts)
        if context_parts
        else "未能从文档中检索到有效数据。"
    )

    prompt_content = (
        f"用户提问：{state.get('question')}\n\n"
        f"{context_text}\n\n"
        f"任务要求：\n请仅根据上述已有数据给出最佳回答。"
    )
    prompt = [
        SystemMessage(content=get_fallback_response_prompt()),
        HumanMessage(content=prompt_content),
    ]

    if hasattr(llm, "ainvoke"):
        response = await llm.ainvoke(prompt)
    else:
        response = llm.invoke(prompt)

    response = name_internal_message(response, "agent_response")
    return {"messages": [response]}
