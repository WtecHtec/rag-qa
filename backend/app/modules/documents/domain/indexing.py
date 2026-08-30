"""文档向量索引用例领域协议。"""

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from app.modules.documents.domain.models import Document

IndexingStageCallback = Callable[[], Awaitable[None]]


class DocumentIndexer(Protocol):
    """文档向量索引协议，不感知具体向量库实现。"""

    async def index_document(
        self,
        document: Document,
        on_indexing: IndexingStageCallback,
    ) -> int: ...

    async def delete_document(self, document_id: UUID) -> None: ...
