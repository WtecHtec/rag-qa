"""检索领域模型与值对象。"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

Embedding = tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VectorRecord:
    knowledge_base_id: UUID
    document_id: UUID
    child_id: UUID
    parent_id: UUID
    embedding_model: str
    embedding: Embedding
    content_hash: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class VectorHit:
    child_id: UUID
    parent_id: UUID
    document_id: UUID
    score: float


@dataclass(frozen=True, slots=True)
class MatchedChild:
    child_id: UUID
    ordinal: int
    preview: str
    start_offset: int
    end_offset: int
    score: float


@dataclass(frozen=True, slots=True)
class ParentSearchMatch:
    parent_id: UUID
    document_id: UUID
    heading_path: str
    content: str
    score: float
    matched_children: tuple[MatchedChild, ...]


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    query: str
    embedding_model: str
    matches: tuple[ParentSearchMatch, ...]


@dataclass(frozen=True, slots=True)
class ChildChunkItem:
    """第一阶段子块向量检索命中条目，供 Agent 初筛与定位线索。"""

    parent_id: UUID
    child_id: UUID
    document_id: UUID
    heading_path: str
    content: str
    score: float


@dataclass(frozen=True, slots=True)
class ParentChunkDetail:
    """第二阶段按需读取的父块完整大上下文详情。"""

    parent_id: UUID
    document_id: UUID
    heading_path: str
    content: str
    char_count: int
