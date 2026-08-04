from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.modules.documents.models import StoredDocument


class DocumentStorage(Protocol):
    """原始文件存储端口，上传流不能要求调用方一次性读取完整文件。"""

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
