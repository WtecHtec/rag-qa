import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.documents.exceptions import (
    DocumentDuplicateError,
    DocumentError,
    DocumentNotFoundError,
    DocumentValidationError,
    TextChunkNotFoundError,
)
from app.modules.documents.indexing import DocumentIndexer
from app.modules.documents.models import (
    ChunkKind,
    Document,
    DocumentPage,
    DocumentStatus,
    TextChunk,
    TextChunkPage,
)
from app.modules.documents.repository import DocumentRepository, KnowledgeBaseReader
from app.modules.documents.storage import DocumentStorage
from app.providers.chunking.text_chunker import ParentChildTextChunker

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]
SUPPORTED_EXTENSIONS = {".txt": "text/plain", ".md": "text/markdown"}


def utc_now() -> datetime:
    return datetime.now(UTC)


class DocumentService:
    """编排流式上传与切块用例，文件系统、数据库和切块算法均可替换。"""

    def __init__(
        self,
        repository: DocumentRepository,
        knowledge_base_reader: KnowledgeBaseReader,
        storage: DocumentStorage,
        chunker: ParentChildTextChunker,
        *,
        max_size_bytes: int,
        indexer: DocumentIndexer | None = None,
        clock: Clock = utc_now,
        id_factory: IdFactory = uuid4,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._knowledge_base_reader = knowledge_base_reader
        self._storage = storage
        self._chunker = chunker
        self._max_size_bytes = max_size_bytes
        self._indexer = indexer
        self._clock = clock
        self._id_factory = id_factory
        self._logger = logger or logging.getLogger(__name__)

    async def upload(
        self,
        knowledge_base_id: UUID,
        filename: str,
        media_type: str,
        stream: AsyncIterator[bytes],
    ) -> Document:
        await self._ensure_knowledge_base_exists(knowledge_base_id)
        safe_filename, extension = self._validate_filename(filename)
        document_id = self._id_factory()
        stored = await self._storage.save(
            document_id,
            extension,
            stream,
            max_size_bytes=self._max_size_bytes,
        )
        if stored.size_bytes == 0:
            await self._storage.delete(stored.storage_key)
            raise DocumentValidationError("不能上传空文档")
        if await self._repository.get_by_hash(knowledge_base_id, stored.sha256):
            await self._storage.delete(stored.storage_key)
            raise DocumentDuplicateError()

        now = self._clock()
        document = Document(
            id=document_id,
            knowledge_base_id=knowledge_base_id,
            filename=safe_filename,
            extension=extension,
            media_type=media_type if media_type else SUPPORTED_EXTENSIONS[extension],
            storage_key=stored.storage_key,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            status=DocumentStatus.PENDING,
            progress=10,
            parent_chunk_count=0,
            child_chunk_count=0,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        try:
            await self._repository.add(document)
        except DocumentDuplicateError:
            await self._storage.delete(stored.storage_key)
            raise
        self._logger.info(
            "document.uploaded",
            extra={
                "document_id": str(document.id),
                "knowledge_base_id": str(knowledge_base_id),
                "size_bytes": stored.size_bytes,
            },
        )
        return document

    async def process(self, document_id: UUID) -> None:
        document = await self._get_or_raise(document_id)
        try:
            document = await self._set_status(document, DocumentStatus.PARSING, 30)
            source_path = await self._storage.resolve(document.storage_key)
            document = await self._set_status(document, DocumentStatus.CHUNKING, 55)
            chunks = self._chunker.iter_chunks(
                document.id,
                source_path,
                document.extension,
                self._clock(),
            )
            parent_count, child_count = await self._repository.replace_chunks(document.id, chunks)
            if parent_count == 0:
                raise DocumentValidationError("文档不包含可切分的有效文本")
            chunked = replace(
                document,
                status=DocumentStatus.CHUNKED,
                progress=65 if self._indexer else 100,
                parent_chunk_count=parent_count,
                child_chunk_count=child_count,
                error_code=None,
                error_message=None,
                updated_at=self._clock(),
            )
            await self._repository.update(chunked)
            document = chunked
            self._logger.info(
                "document.chunked",
                extra={
                    "document_id": str(document.id),
                    "parent_chunk_count": parent_count,
                    "child_chunk_count": child_count,
                },
            )
            await self._index_document(document)
        except Exception as error:  # 后台任务必须把失败固化为状态，不能只写未捕获堆栈。
            code = error.code if isinstance(error, DocumentError) else "document_processing_failed"
            message = (
                error.message
                if isinstance(error, DocumentError)
                else "文档处理失败，请查看本地日志"
            )
            failed = replace(
                document,
                status=DocumentStatus.FAILED,
                progress=0,
                error_code=code,
                error_message=message,
                updated_at=self._clock(),
            )
            await self._repository.update(failed)
            self._logger.exception(
                "document.processing_failed",
                extra={"document_id": str(document.id), "error_code": code},
            )

    async def list(self, knowledge_base_id: UUID, *, limit: int, offset: int) -> DocumentPage:
        await self._ensure_knowledge_base_exists(knowledge_base_id)
        self._validate_page(limit, offset, max_limit=100)
        items = tuple(await self._repository.list(knowledge_base_id, limit=limit, offset=offset))
        return DocumentPage(items, await self._repository.count(knowledge_base_id), limit, offset)

    async def get(self, knowledge_base_id: UUID, document_id: UUID) -> Document:
        document = await self._get_or_raise(document_id)
        if document.knowledge_base_id != knowledge_base_id:
            raise DocumentNotFoundError()
        return document

    async def delete(self, knowledge_base_id: UUID, document_id: UUID) -> None:
        document = await self.get(knowledge_base_id, document_id)
        if self._indexer:
            await self._indexer.delete_document(document.id)
        await self._storage.delete(document.storage_key)
        await self._repository.delete(document.id)
        self._logger.info("document.deleted", extra={"document_id": str(document.id)})

    async def prepare_reprocess(self, knowledge_base_id: UUID, document_id: UUID) -> Document:
        document = await self.get(knowledge_base_id, document_id)
        if self._indexer:
            # 重处理期间不允许继续命中旧向量，避免正文和索引版本不一致。
            await self._indexer.delete_document(document.id)
        pending = replace(
            document,
            status=DocumentStatus.PENDING,
            progress=10,
            error_code=None,
            error_message=None,
            updated_at=self._clock(),
        )
        await self._repository.update(pending)
        return pending

    async def list_chunks(
        self,
        knowledge_base_id: UUID,
        document_id: UUID,
        *,
        kind: ChunkKind,
        parent_id: UUID | None,
        limit: int,
        offset: int,
    ) -> TextChunkPage:
        await self.get(knowledge_base_id, document_id)
        self._validate_page(limit, offset, max_limit=100)
        if kind is ChunkKind.PARENT:
            parent_id = None
        items = tuple(
            await self._repository.list_chunks(
                document_id,
                kind=kind,
                parent_id=parent_id,
                limit=limit,
                offset=offset,
            )
        )
        total = await self._repository.count_chunks(document_id, kind=kind, parent_id=parent_id)
        return TextChunkPage(items, total, limit, offset)

    async def get_chunk(
        self, knowledge_base_id: UUID, document_id: UUID, chunk_id: UUID
    ) -> TextChunk:
        await self.get(knowledge_base_id, document_id)
        chunk = await self._repository.get_chunk(chunk_id)
        if chunk is None or chunk.document_id != document_id:
            raise TextChunkNotFoundError()
        return chunk

    async def update_chunk(
        self,
        knowledge_base_id: UUID,
        document_id: UUID,
        chunk_id: UUID,
        content: str,
    ) -> TextChunk:
        chunk = await self.get_chunk(knowledge_base_id, document_id, chunk_id)
        normalized = content.strip()
        if not normalized:
            raise DocumentValidationError("文本块内容不能为空")
        max_chars = (
            self._chunker.parent_chars
            if chunk.kind is ChunkKind.PARENT
            else self._chunker.child_chars
        )
        if len(normalized) > max_chars:
            kind_label = "Parent" if chunk.kind is ChunkKind.PARENT else "Child"
            raise DocumentValidationError(f"{kind_label} 不能超过 {max_chars} 个字符")
        updated = replace(
            chunk,
            content=normalized,
            char_count=len(normalized),
            manually_edited=True,
            updated_at=self._clock(),
        )
        if updated.kind is ChunkKind.PARENT:
            now = self._clock()
            children = tuple(
                TextChunk(
                    id=self._id_factory(),
                    document_id=updated.document_id,
                    parent_id=updated.id,
                    kind=ChunkKind.CHILD,
                    ordinal=ordinal,
                    heading_path=updated.heading_path,
                    content=child_content,
                    char_count=len(child_content),
                    start_offset=start_offset,
                    end_offset=end_offset,
                    manually_edited=False,
                    created_at=now,
                    updated_at=now,
                )
                for ordinal, (start_offset, end_offset, child_content) in enumerate(
                    self._chunker.iter_child_spans(normalized)
                )
            )
            await self._repository.update_parent_with_children(updated, children)
            document = await self._refresh_document_chunk_counts(document_id)
            self._logger.info(
                "document.parent_chunk_rechunked",
                extra={
                    "document_id": str(document_id),
                    "parent_id": str(updated.id),
                    "child_chunk_count": len(children),
                },
            )
        else:
            await self._repository.update_chunk(updated)
            document = await self._get_or_raise(document_id)
        await self._reindex_after_chunk_mutation(document)
        return updated

    async def delete_chunk(
        self, knowledge_base_id: UUID, document_id: UUID, chunk_id: UUID
    ) -> None:
        chunk = await self.get_chunk(knowledge_base_id, document_id, chunk_id)
        if chunk.kind is ChunkKind.CHILD:
            sibling_count = await self._repository.count_chunks(
                document_id,
                kind=ChunkKind.CHILD,
                parent_id=chunk.parent_id,
            )
            if sibling_count <= 1:
                raise DocumentValidationError(
                    "每个 Parent 至少保留一个 Child，请修改 Parent 内容或删除整个 Parent"
                )
        else:
            parent_count = await self._repository.count_chunks(
                document_id,
                kind=ChunkKind.PARENT,
                parent_id=None,
            )
            if parent_count <= 1:
                raise DocumentValidationError("文档至少需要保留一个 Parent 及其 Child")
        await self._repository.delete_chunk(chunk.id)
        document = await self._refresh_document_chunk_counts(document_id)
        await self._reindex_after_chunk_mutation(document)

    async def _refresh_document_chunk_counts(self, document_id: UUID) -> Document:
        document = await self._get_or_raise(document_id)
        parent_count = await self._repository.count_chunks(
            document_id, kind=ChunkKind.PARENT, parent_id=None
        )
        child_count = await self._repository.count_chunks(
            document_id, kind=ChunkKind.CHILD, parent_id=None
        )
        updated = replace(
            document,
            parent_chunk_count=parent_count,
            child_chunk_count=child_count,
            updated_at=self._clock(),
        )
        await self._repository.update(updated)
        return updated

    async def _index_document(self, document: Document) -> Document:
        if self._indexer is None:
            return document
        document = await self._set_status(document, DocumentStatus.EMBEDDING, 75)

        async def on_indexing() -> None:
            nonlocal document
            document = await self._set_status(document, DocumentStatus.INDEXING, 90)

        await self._indexer.index_document(document, on_indexing)
        ready = replace(
            document,
            status=DocumentStatus.READY,
            progress=100,
            error_code=None,
            error_message=None,
            updated_at=self._clock(),
        )
        await self._repository.update(ready)
        self._logger.info(
            "document.ready",
            extra={"document_id": str(document.id)},
        )
        return ready

    async def _reindex_after_chunk_mutation(self, document: Document) -> None:
        if self._indexer is None:
            return
        try:
            await self._index_document(document)
        except Exception:
            failed = replace(
                document,
                status=DocumentStatus.FAILED,
                progress=0,
                error_code="document_indexing_failed",
                error_message="文本块已保存，但向量索引更新失败，请重试处理",
                updated_at=self._clock(),
            )
            await self._repository.update(failed)
            self._logger.exception(
                "document.reindex_failed",
                extra={"document_id": str(document.id)},
            )
            raise

    async def _set_status(
        self, document: Document, status: DocumentStatus, progress: int
    ) -> Document:
        updated = replace(document, status=status, progress=progress, updated_at=self._clock())
        await self._repository.update(updated)
        return updated

    async def _get_or_raise(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()
        return document

    async def _ensure_knowledge_base_exists(self, knowledge_base_id: UUID) -> None:
        if await self._knowledge_base_reader.get(knowledge_base_id) is None:
            raise DocumentValidationError("知识库不存在或已被删除")

    @staticmethod
    def _validate_filename(filename: str) -> tuple[str, str]:
        safe_filename = filename.strip()
        if not safe_filename or len(safe_filename) > 255:
            raise DocumentValidationError("文件名不能为空且不能超过 255 个字符")
        if Path(safe_filename).name != safe_filename or "\\" in safe_filename:
            raise DocumentValidationError("文件名不能包含路径")
        extension = Path(safe_filename).suffix.casefold()
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentValidationError("目前只支持 TXT 和 Markdown 文档")
        return safe_filename, extension

    @staticmethod
    def _validate_page(limit: int, offset: int, *, max_limit: int) -> None:
        if limit < 1 or limit > max_limit:
            raise DocumentValidationError(f"每页数量必须在 1 到 {max_limit} 之间")
        if offset < 0:
            raise DocumentValidationError("分页偏移量不能小于 0")
