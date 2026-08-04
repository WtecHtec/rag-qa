from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.modules.chat.models import ChatMessage, MessageRole

CONTEXT_DEPENDENT_QUERIES = frozenset(
    {
        "为什么",
        "继续",
        "然后呢",
        "再说说",
        "详细点",
        "它呢",
        "他呢",
        "她呢",
        "这个呢",
        "那个呢",
        "它是什么",
        "这个是什么",
    }
)
GENERAL_CONVERSATION_QUERIES = frozenset(
    {
        "你好",
        "您好",
        "嗨",
        "哈喽",
        "hello",
        "hi",
        "早上好",
        "下午好",
        "晚上好",
        "谢谢",
        "感谢",
        "再见",
        "你是谁",
        "你叫什么",
        "你能做什么",
    }
)
SELF_INTRODUCTION_PHRASES = (
    "介绍一下你自己",
    "介绍下你自己",
    "自我介绍",
    "有什么可以帮",
)
STRIPPED_PUNCTUATION = " \t\r\n，。！？!?；;：:、~～"


class QueryIntent(StrEnum):
    GENERAL = "general"
    KNOWLEDGE = "knowledge"
    CLARIFICATION = "clarification"
    MEMORY_CONFIRMATION = "memory_confirmation"


@dataclass(frozen=True, slots=True)
class QueryPlan:
    intent: QueryIntent
    retrieval_query: str

    @property
    def use_rag(self) -> bool:
        return self.intent is QueryIntent.KNOWLEDGE


def find_latest_user_query(messages: Sequence[ChatMessage]) -> str | None:
    for message in reversed(messages):
        if message.role is MessageRole.USER and message.content.strip():
            return message.content.strip()
    return None


def find_latest_answer_rag_mode(messages: Sequence[ChatMessage]) -> bool:
    """短追问继承上一轮回答策略，避免普通寒暄被错误送入知识库检索。"""
    for message in reversed(messages):
        if message.role in (MessageRole.ASSISTANT, MessageRole.CLARIFICATION):
            return message.rag_enabled
    return False


def plan_query(
    query: str,
    previous_user_query: str | None,
    previous_rag_enabled: bool,
) -> QueryPlan:
    """保留无分类器时的稳定回退策略，知识型问题默认优先本地检索。"""
    deterministic = plan_query_deterministic(
        query,
        previous_user_query,
        previous_rag_enabled,
    )
    if deterministic is not None:
        return deterministic
    return QueryPlan(QueryIntent.KNOWLEDGE, query.strip())


def plan_query_deterministic(
    query: str,
    previous_user_query: str | None,
    previous_rag_enabled: bool,
) -> QueryPlan | None:
    """只处理无需模型判断的高置信规则，其余请求交给分类器。"""
    normalized = query.strip()
    compact = _compact_query(normalized)
    if _is_general_conversation(compact):
        return QueryPlan(QueryIntent.GENERAL, normalized)
    if compact in CONTEXT_DEPENDENT_QUERIES:
        if previous_user_query is None:
            return QueryPlan(QueryIntent.CLARIFICATION, normalized)
        rewritten = f"上一问题：{previous_user_query}\n当前追问：{normalized}"
        intent = QueryIntent.KNOWLEDGE if previous_rag_enabled else QueryIntent.GENERAL
        return QueryPlan(intent, rewritten)
    return None


def rewrite_query(query: str, previous_user_query: str | None) -> tuple[str, bool]:
    """保留旧的纯函数入口，供查询重写边界测试和其他调用方使用。"""
    normalized = query.strip()
    compact = _compact_query(normalized)
    is_context_dependent = compact in CONTEXT_DEPENDENT_QUERIES
    if not is_context_dependent or previous_user_query is None:
        return normalized, is_context_dependent
    return f"上一问题：{previous_user_query}\n当前追问：{normalized}", False


def _compact_query(query: str) -> str:
    return query.strip(STRIPPED_PUNCTUATION).lower()


def _is_general_conversation(compact_query: str) -> bool:
    if compact_query in GENERAL_CONVERSATION_QUERIES:
        return True
    return any(phrase in compact_query for phrase in SELF_INTRODUCTION_PHRASES)
