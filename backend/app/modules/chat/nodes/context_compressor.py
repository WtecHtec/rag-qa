from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.types import Command

from app.modules.chat.domain.state import AgentSubGraphState
from app.modules.chat.domain.utils import (
    BASE_TOKEN_THRESHOLD,
    TOKEN_GROWTH_FACTOR,
    estimate_context_tokens,
    extract_retrieval_contexts,
)
from app.modules.chat.prompts.agent_prompts import get_context_compression_prompt


def should_compress_context(
    state: AgentSubGraphState,
) -> Command[Literal["compress_context", "orchestrator"]]:
    """检查工具调用后累计的上下文 Token，超过阈值则动态路由到压缩节点以防超出 Prompt 预算。"""
    messages = state["messages"]
    new_ids: set[str] = set()

    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                if tc["name"] == "retrieve_parent_chunks":
                    raw = (
                        tc["args"].get("parent_id")
                        or tc["args"].get("id")
                        or tc["args"].get("ids")
                        or []
                    )
                    if isinstance(raw, str):
                        new_ids.add(f"parent::{raw}")
                    else:
                        new_ids.update(f"parent::{r}" for r in raw)
                elif tc["name"] == "search_child_chunks":
                    query = tc["args"].get("query", "")
                    if query:
                        new_ids.add(f"search::{query}")
            break

    updated_ids = state.get("retrieval_keys", set()) | new_ids
    current_token_messages = estimate_context_tokens(messages)
    current_token_summary = estimate_context_tokens(
        [HumanMessage(content=state.get("context_summary", ""))]
    )
    current_tokens = current_token_messages + current_token_summary

    max_allowed = BASE_TOKEN_THRESHOLD + int(current_token_summary * TOKEN_GROWTH_FACTOR)
    goto = "compress_context" if current_tokens > max_allowed else "orchestrator"

    return Command(
        update={
            "retrieval_keys": updated_ids,
            "retrieved_contexts": extract_retrieval_contexts(messages),
        },
        goto=goto,
    )


async def compress_context(state: AgentSubGraphState, llm: Any) -> dict[str, Any]:
    """对多轮工具调用的历史做归纳压缩，记录已检索 Key，防止循环冗余检索。"""
    messages = state["messages"]
    existing_summary = state.get("context_summary", "").strip()

    if not messages:
        return {}

    conversation_text = f"用户提问：\n{state.get('question')}\n\n待压缩的上下文记录：\n\n"
    if existing_summary:
        conversation_text += f"[已有压缩上下文]\n{existing_summary}\n\n"

    for msg in messages[1:]:
        if isinstance(msg, AIMessage):
            tool_calls_info = ""
            if getattr(msg, "tool_calls", None):
                calls = ", ".join(f"{tc['name']}({tc['args']})" for tc in msg.tool_calls)
                tool_calls_info = f" | 工具调用: {calls}"
            conversation_text += f"[助理回复{tool_calls_info}]\n{msg.content or '(调用工具)'}\n\n"
        elif isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", "tool")
            conversation_text += f"[工具返回 — {tool_name}]\n{msg.content}\n\n"

    prompt = [
        SystemMessage(content=get_context_compression_prompt()),
        HumanMessage(content=conversation_text),
    ]
    if hasattr(llm, "ainvoke"):
        summary_response = await llm.ainvoke(prompt)
    else:
        summary_response = llm.invoke(prompt)

    new_summary = str(summary_response.content)
    retrieved_ids: set[str] = state.get("retrieval_keys", set())
    if retrieved_ids:
        parent_ids = sorted(r for r in retrieved_ids if r.startswith("parent::"))
        search_queries = sorted(
            r.replace("search::", "") for r in retrieved_ids if r.startswith("search::")
        )
        block = "\n\n---\n**已执行操作记录（切勿重复调用）：**\n"
        if parent_ids:
            block += "已调取的父块 ID：\n" + "\n".join(f"- {p.replace('parent::', '')}" for p in parent_ids) + "\n"
        if search_queries:
            block += "已执行的搜索关键词：\n" + "\n".join(f"- {q}" for q in search_queries) + "\n"
        new_summary += block

    return {
        "context_summary": new_summary,
        "messages": [RemoveMessage(id=m.id) for m in messages[1:] if getattr(m, "id", None)],
    }
