from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from app.modules.chat.domain.state import AgentSubGraphState


def collect_answer(state: AgentSubGraphState) -> dict[str, Any]:
    """收集子图单子问题的检索结果与最终回答，打包存入 agent_answers。"""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    is_valid = (
        isinstance(last_message, AIMessage)
        and bool(last_message.content)
        and not getattr(last_message, "tool_calls", None)
    )
    answer = str(last_message.content) if is_valid and last_message is not None else "未能从文档中检索到有效回答。"
    return {
        "final_answer": answer,
        "agent_answers": [
            {
                "index": state.get("question_index", 0),
                "question": state.get("question", ""),
                "answer": answer,
                "contexts": state.get("retrieved_contexts", []),
            }
        ],
    }
