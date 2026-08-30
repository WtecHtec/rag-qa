"""检索模块数据读取抽象接口。"""

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from app.modules.documents.domain.models import TextChunk


class RetrievalChunkReader(Protocol):
    """检索模块子块与父块读取协议。"""

    async def list_child_chunks(
        self,
        document_id: UUID,
        *,
        limit: int,
        after_id: UUID | None,
    ) -> Sequence[TextChunk]: ...

    async def get_chunk(self, chunk_id: UUID) -> TextChunk | None: ...

    async def get_chunks(self, chunk_ids: Sequence[UUID]) -> Mapping[UUID, TextChunk]: ...
