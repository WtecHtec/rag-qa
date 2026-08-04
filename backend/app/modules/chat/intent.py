from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ClassifiedIntent(StrEnum):
    """分类器只表达用户意图，不直接执行检索或记忆副作用。"""

    GENERAL = "general"
    KNOWLEDGE = "knowledge"
    CLARIFICATION = "clarification"
    MEMORY_RECALL = "memory_recall"
    MEMORY_WRITE = "memory_write"


@dataclass(frozen=True, slots=True)
class IntentDecision:
    intent: ClassifiedIntent
    confidence: float
    rewritten_query: str | None = None


class IntentClassifier(Protocol):
    """意图分类边界可替换为本地模型、远程模型或测试替身。"""

    async def classify(
        self,
        query: str,
        previous_user_query: str | None,
        previous_rag_enabled: bool,
    ) -> IntentDecision: ...
