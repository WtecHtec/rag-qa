from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.retrieval.models import Embedding, VectorHit, VectorRecord


class VectorStore(Protocol):
    """向量库端口，默认 SQLite 实现可替换为 sqlite-vec、Qdrant 等。"""

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
