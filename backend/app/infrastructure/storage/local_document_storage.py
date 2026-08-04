import asyncio
import hashlib
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from app.modules.documents.exceptions import DocumentTooLargeError
from app.modules.documents.models import StoredDocument


class LocalDocumentStorage:
    """本地文件存储使用临时文件原子替换，失败上传不会留下半文件。"""

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path

    async def save(
        self,
        document_id: UUID,
        extension: str,
        stream: AsyncIterator[bytes],
        *,
        max_size_bytes: int,
    ) -> StoredDocument:
        await asyncio.to_thread(self._root_path.mkdir, parents=True, exist_ok=True)
        storage_key = f"{document_id}{extension}"
        destination = self._root_path / storage_key
        temporary = self._root_path / f".{document_id}.uploading"
        digest = hashlib.sha256()
        size_bytes = 0

        try:
            handle = await asyncio.to_thread(temporary.open, "wb")
            try:
                async for block in stream:
                    if not block:
                        continue
                    size_bytes += len(block)
                    if size_bytes > max_size_bytes:
                        raise DocumentTooLargeError(max_size_bytes)
                    digest.update(block)
                    await asyncio.to_thread(handle.write, block)
                await asyncio.to_thread(handle.flush)
            finally:
                await asyncio.to_thread(handle.close)
            await asyncio.to_thread(temporary.replace, destination)
        except Exception:
            if temporary.exists():
                await asyncio.to_thread(temporary.unlink)
            raise

        return StoredDocument(storage_key, size_bytes, digest.hexdigest())

    async def resolve(self, storage_key: str) -> Path:
        path = (self._root_path / storage_key).resolve()
        if path.parent != self._root_path.resolve():
            raise ValueError("非法存储键")
        return path

    async def delete(self, storage_key: str) -> None:
        path = await self.resolve(storage_key)
        if path.exists():
            await asyncio.to_thread(path.unlink)
