"""向量存储抽象协议。"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.retrieval.domain.models import Embedding, VectorHit, VectorRecord


class VectorStore(Protocol):
    """向量库领域端口协议。"""

    async def delete_document(self, document_id: UUID) -> None: ...

    async def upsert(self, records: Sequence[VectorRecord]) -> None: ...

    async def search(
        self,
        knowledge_base_id: UUID | None,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> Sequence[VectorHit]: ...
