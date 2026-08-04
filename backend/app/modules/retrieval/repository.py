from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from app.modules.documents.models import TextChunk


class RetrievalChunkReader(Protocol):
    """检索模块只读取 Child 批次和命中后的父子正文。"""

    async def list_child_chunks(
        self,
        document_id: UUID,
        *,
        limit: int,
        after_id: UUID | None,
    ) -> Sequence[TextChunk]: ...

    async def get_chunks(self, chunk_ids: Sequence[UUID]) -> Mapping[UUID, TextChunk]: ...
