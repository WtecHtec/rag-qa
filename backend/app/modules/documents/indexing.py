from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from app.modules.documents.models import Document

IndexingStageCallback = Callable[[], Awaitable[None]]


class DocumentIndexer(Protocol):
    """文档模块只依赖索引用例端口，不感知 Embedding 或向量库实现。"""

    async def index_document(
        self,
        document: Document,
        on_indexing: IndexingStageCallback,
    ) -> int: ...

    async def delete_document(self, document_id: UUID) -> None: ...
