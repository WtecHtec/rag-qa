from collections.abc import Sequence

from app.modules.chat.llm import LlmMessage
from app.modules.chat.models import ChatMessage, Citation, MessageRole, MessageStatus

SYSTEM_PROMPT = """你是 BiYou 本地知识库问答助手。
请严格依据提供的知识库上下文回答，不要编造上下文中不存在的事实。
引用事实时使用 [1]、[2] 这样的编号，对应上下文中的来源编号。
如果上下文不足，请明确说明没有找到足够依据，并建议用户补充问题。
回答使用简洁、自然的中文。"""

GENERAL_SYSTEM_PROMPT = """你是 BiYou 的本地 AI 助手。
当前问题属于普通会话，请基于通用能力和会话上下文自然回答。
不要声称已经查阅本地文档，也不要生成 [1] 形式的知识库引用。
回答使用简洁、自然的中文。"""

KNOWLEDGE_FALLBACK_SYSTEM_PROMPT = """你是 BiYou 的本地 AI 助手。
本轮已经优先检索本地知识库，但没有找到足够相关的内容。
请使用通用能力回答；不要声称答案来自本地文档，也不要生成 [1] 形式的知识库引用。
若事实存在不确定性，请明确说明。回答使用简洁、自然的中文。"""


def build_llm_messages(
    history: Sequence[ChatMessage],
    user_query: str,
    citations: Sequence[Citation],
    *,
    history_limit: int = 6,
    memories: Sequence[str] = (),
) -> tuple[LlmMessage, ...]:
    context = "\n\n".join(
        f"[来源 {citation.citation_number}] {citation.document_name}"
        f" / {citation.heading_path or '正文'}\n{citation.parent_content}"
        for citation in citations
    )
    system_content = (
        f"{SYSTEM_PROMPT}{_memory_section(memories)}"
        f"\n\n以下是本轮可用知识库上下文：\n{context}"
    )
    usable_history = [
        message
        for message in history
        if message.status is MessageStatus.COMPLETE
        and message.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ][-history_limit:]
    messages = [LlmMessage("system", system_content)]
    messages.extend(LlmMessage(message.role.value, message.content) for message in usable_history)
    messages.append(LlmMessage("user", user_query))
    return tuple(messages)


def build_general_chat_messages(
    history: Sequence[ChatMessage],
    user_query: str,
    *,
    history_limit: int = 6,
    memories: Sequence[str] = (),
) -> tuple[LlmMessage, ...]:
    """构建不经过 RAG 的普通会话上下文，避免模型虚构本地文档引用。"""
    usable_history = [
        message
        for message in history
        if message.status is MessageStatus.COMPLETE
        and message.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ][-history_limit:]
    messages = [LlmMessage("system", f"{GENERAL_SYSTEM_PROMPT}{_memory_section(memories)}")]
    messages.extend(LlmMessage(message.role.value, message.content) for message in usable_history)
    messages.append(LlmMessage("user", user_query))
    return tuple(messages)


def build_knowledge_fallback_messages(
    history: Sequence[ChatMessage],
    user_query: str,
    *,
    history_limit: int = 6,
    memories: Sequence[str] = (),
) -> tuple[LlmMessage, ...]:
    """知识库无命中时回退到通用模型，同时禁止伪造本地引用。"""
    usable_history = [
        message
        for message in history
        if message.status is MessageStatus.COMPLETE
        and message.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ][-history_limit:]
    messages = [
        LlmMessage(
            "system",
            f"{KNOWLEDGE_FALLBACK_SYSTEM_PROMPT}{_memory_section(memories)}",
        )
    ]
    messages.extend(LlmMessage(message.role.value, message.content) for message in usable_history)
    messages.append(LlmMessage("user", user_query))
    return tuple(messages)


def _memory_section(memories: Sequence[str]) -> str:
    if not memories:
        return ""
    items = "\n".join(f"- {content}" for content in memories)
    return (
        "\n\n以下内容是用户明确要求长期记住的事实或偏好。"
        "回答相关问题时优先遵守；若与知识库旧内容冲突，应指出冲突，不要静默混合：\n"
        f"{items}"
    )
