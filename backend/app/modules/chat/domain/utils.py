from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)

CHILD_CHUNK_SEPARATOR = "\n\n---\n\n"
BASE_TOKEN_THRESHOLD = 2000
TOKEN_GROWTH_FACTOR = 0.5
MAIN_HISTORY_MESSAGES_TO_KEEP = 6
PRE_ANSWER_HISTORY_MESSAGES_TO_KEEP = max(MAIN_HISTORY_MESSAGES_TO_KEEP - 1, 0)


@lru_cache(maxsize=1)
def _get_token_encoding() -> Any:
    """按需加载分词编码器。"""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def estimate_context_tokens(messages: list[Any]) -> int:
    """估算消息列表的 Token 总数。"""
    contents = [
        str(msg.content)
        for msg in messages
        if hasattr(msg, "content") and msg.content
    ]
    encoding = _get_token_encoding()
    if encoding is None:
        return sum(max(1, len(content) // 4) for content in contents)
    return sum(len(encoding.encode(content)) for content in contents)


def is_plain_conversation_message(msg: BaseMessage) -> bool:
    """判断是否为标准的用户/助理纯对话消息（排除中间工具调用和内部临时消息）。"""
    return (
        isinstance(msg, (HumanMessage, AIMessage))
        and not getattr(msg, "tool_calls", None)
        and not getattr(msg, "name", None)
    )


def name_internal_message(message: BaseMessage, name: str) -> BaseMessage:
    """为内部临时消息打上标识，避免被错误持久化为用户可读的历史记录。"""
    return message.model_copy(update={"name": name})


def extract_retrieval_contexts(messages: list[BaseMessage]) -> list[str]:
    """从 ToolMessage 中提取检索到的正文片段列表。"""
    contexts: list[str] = []
    ignored_prefixes = (
        "NO_RELEVANT_CHUNKS",
        "NO_PARENT_DOCUMENT",
        "RETRIEVAL_ERROR:",
        "PARENT_RETRIEVAL_ERROR:",
    )
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        content = str(message.content).strip()
        if content and not content.startswith(ignored_prefixes):
            parts = (
                content.split(CHILD_CHUNK_SEPARATOR)
                if message.name == "search_child_chunks"
                else [content]
            )
            contexts.extend(part for part in parts if part)
    return list(dict.fromkeys(contexts))


def format_conversation(messages: list[BaseMessage]) -> str:
    """将消息列表格式化为人类可读的问答文本。"""
    lines: list[str] = []
    for msg in messages:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def filter_messages_to_remove(
    messages: list[BaseMessage], keep_ids: set[str | None]
) -> list[RemoveMessage]:
    """生成需要从状态中移出的 RemoveMessage 列表。"""
    removals: list[RemoveMessage] = []
    for msg in messages:
        msg_id = getattr(msg, "id", None)
        if isinstance(msg, SystemMessage) or not msg_id:
            continue
        if msg_id not in keep_ids:
            removals.append(RemoveMessage(id=msg_id))
    return removals


def get_recent_conversation(messages: list[BaseMessage], pending_query: str = "") -> list[BaseMessage]:
    """获取当前用户提问之前的最近对话上下文。"""
    plain_messages = [msg for msg in messages if is_plain_conversation_message(msg)]
    recent_messages = plain_messages[:-1]

    if pending_query:
        for index in range(len(recent_messages) - 1, -1, -1):
            msg = recent_messages[index]
            if isinstance(msg, HumanMessage) and str(msg.content).strip() == pending_query:
                return recent_messages[:index]

    return recent_messages
