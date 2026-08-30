"""文档领域仓储抽象接口。"""

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol
from uuid import UUID

from app.modules.documents.domain.models import (
    ChunkKind,
    Document,
    TextChunk,
    TextChunkSummary,
)
from app.modules.knowledge_bases.domain.models import KnowledgeBase, KnowledgeBaseMetrics


class DocumentRepository(Protocol):
    """文档与文本块持久化协议，批量写入保持事务原子性。"""

    async def add(self, document: Document) -> None: ...
    async def get(self, document_id: UUID) -> Document | None: ...
    async def get_by_hash(self, knowledge_base_id: UUID, sha256: str) -> Document | None: ...
    async def list(
        self, knowledge_base_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Document]: ...
    async def count(self, knowledge_base_id: UUID) -> int: ...
    async def update(self, document: Document) -> None: ...
    async def delete(self, document_id: UUID) -> None: ...
    async def replace_chunks(
        self, document_id: UUID, chunks: Iterable[TextChunk]
    ) -> tuple[int, int]: ...
    async def list_chunks(
        self,
        document_id: UUID,
        *,
        kind: ChunkKind,
        parent_id: UUID | None,
        limit: int,
        offset: int,
    ) -> Sequence[TextChunkSummary]: ...
    async def count_chunks(
        self,
        document_id: UUID,
        *,
        kind: ChunkKind,
        parent_id: UUID | None,
    ) -> int: ...
    async def get_chunk(self, chunk_id: UUID) -> TextChunk | None: ...
    async def get_chunks(self, chunk_ids: Sequence[UUID]) -> Mapping[UUID, TextChunk]: ...
    async def update_chunk(self, chunk: TextChunk) -> None: ...
    async def update_parent_with_children(
        self, parent: TextChunk, children: Iterable[TextChunk]
    ) -> int: ...
    async def delete_chunk(self, chunk_id: UUID) -> None: ...
    async def get_many(
        self, knowledge_base_ids: Sequence[UUID]
    ) -> Mapping[UUID, KnowledgeBaseMetrics]: ...


class KnowledgeBaseReader(Protocol):
    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None: ...
