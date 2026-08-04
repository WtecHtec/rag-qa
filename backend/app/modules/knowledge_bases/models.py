from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    """知识库领域实体，不依赖 FastAPI、Pydantic 或数据库实现。"""

    id: UUID
    name: str
    normalized_name: str
    description: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeBaseMetrics:
    """由文档模块提供的只读统计，避免知识库模块反向访问文档内部数据。"""

    document_count: int = 0
    ready_document_count: int = 0
    failed_document_count: int = 0
    chunk_count: int = 0


@dataclass(frozen=True, slots=True)
class KnowledgeBaseDetail:
    knowledge_base: KnowledgeBase
    metrics: KnowledgeBaseMetrics


@dataclass(frozen=True, slots=True)
class KnowledgeBasePage:
    items: tuple[KnowledgeBaseDetail, ...]
    total: int
    limit: int
    offset: int
