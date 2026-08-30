from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.modules.chat.domain.state import AgentSubGraphState
from app.modules.chat.domain.utils import name_internal_message
from app.modules.chat.prompts.agent_prompts import get_orchestrator_prompt


async def orchestrator(state: AgentSubGraphState, llm_with_tools: Any) -> dict[str, Any]:
    """Agent 子图编排核心节点：负责决定是否调用检索工具或产出最终子回答。"""
    context_summary = state.get("context_summary", "").strip()
    sys_msg = SystemMessage(content=get_orchestrator_prompt())
    summary_injection = (
        [HumanMessage(content=f"[前期检索沉淀的研究上下文]\n\n{context_summary}")]
        if context_summary
        else []
    )

    if not state.get("messages"):
        human_msg = HumanMessage(content=state["question"], name="agent_question")
        force_search = HumanMessage(
            content="请首先调用 'search_child_chunks' 工具检索与该问题相关的文档线索。"
        )
        prompt = [sys_msg] + summary_injection + [human_msg, force_search]
        if hasattr(llm_with_tools, "ainvoke"):
            response = await llm_with_tools.ainvoke(prompt)
        else:
            response = llm_with_tools.invoke(prompt)

        response = name_internal_message(response, "agent_response")
        tool_calls = getattr(response, "tool_calls", None) or []
        return {
            "messages": [human_msg, response],
            "tool_call_count": len(tool_calls),
            "iteration_count": 1,
        }

    prompt = [sys_msg] + summary_injection + state["messages"]
    if hasattr(llm_with_tools, "ainvoke"):
        response = await llm_with_tools.ainvoke(prompt)
    else:
        response = llm_with_tools.invoke(prompt)

    response = name_internal_message(response, "agent_response")
    tool_calls = getattr(response, "tool_calls", None) or []
    return {
        "messages": [response],
        "tool_call_count": len(tool_calls),
        "iteration_count": 1,
    }
