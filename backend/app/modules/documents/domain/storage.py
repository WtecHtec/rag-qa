"""文档文件存储领域协议。"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.modules.documents.domain.models import StoredDocument


class DocumentStorage(Protocol):
    """原始文件存储协议，支持流式写入并控制最大字节数。"""

    async def save(
        self,
        document_id: UUID,
        extension: str,
        stream: AsyncIterator[bytes],
        *,
        max_size_bytes: int,
    ) -> StoredDocument: ...

    async def resolve(self, storage_key: str) -> Path: ...
    async def delete(self, storage_key: str) -> None: ...
