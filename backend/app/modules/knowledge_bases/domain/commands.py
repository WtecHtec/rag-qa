"""知识库领域命令数据载体。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateKnowledgeBaseCommand:
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class UpdateKnowledgeBaseCommand:
    name: str | None = None
    description: str | None = None
