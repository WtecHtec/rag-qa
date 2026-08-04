from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateKnowledgeBaseCommand:
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class UpdateKnowledgeBaseCommand:
    """None 表示保持不变，空字符串可用于清空描述。"""

    name: str | None = None
    description: str | None = None
