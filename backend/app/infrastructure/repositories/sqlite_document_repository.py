from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from sqlite3 import IntegrityError
from uuid import UUID

import aiosqlite

from app.modules.documents.exceptions import DocumentDuplicateError
from app.modules.documents.models import (
    ChunkKind,
    Document,
    DocumentStatus,
    TextChunk,
    TextChunkSummary,
)
from app.modules.knowledge_bases.models import KnowledgeBaseMetrics


class SqliteDocumentRepository:
    """文档仓储将大批文本块放到工作线程中分批写入，避免阻塞事件循环。"""

    def __init__(self, database_path: Path, *, write_batch_size: int = 400) -> None:
        self._database_path = database_path
        self._write_batch_size = write_batch_size

    async def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._database_path) as connection:
            await connection.execute("PRAGMA foreign_keys=ON")
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    knowledge_base_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    storage_key TEXT NOT NULL UNIQUE,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    parent_chunk_count INTEGER NOT NULL DEFAULT 0,
                    child_chunk_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (knowledge_base_id)
                        REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                    UNIQUE (knowledge_base_id, sha256)
                )
                """
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS text_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    parent_id TEXT,
                    kind TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    heading_path TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    start_offset INTEGER NOT NULL DEFAULT 0,
                    end_offset INTEGER NOT NULL DEFAULT 0,
                    manually_edited INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES text_chunks(id) ON DELETE CASCADE
                )
                """
            )
            chunk_columns = await (
                await connection.execute("PRAGMA table_info(text_chunks)")
            ).fetchall()
            if not any(column[1] == "start_offset" for column in chunk_columns):
                await connection.execute(
                    "ALTER TABLE text_chunks ADD COLUMN start_offset INTEGER NOT NULL DEFAULT 0"
                )
            if not any(column[1] == "end_offset" for column in chunk_columns):
                await connection.execute(
                    "ALTER TABLE text_chunks ADD COLUMN end_offset INTEGER NOT NULL DEFAULT 0"
                )
            await self._backfill_chunk_offsets(connection)
            await connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_kb
                ON documents(knowledge_base_id, created_at DESC)
                """
            )
            await connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_document
                ON text_chunks(document_id, kind, ordinal)
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_parent ON text_chunks(parent_id, ordinal)"
            )
            await connection.commit()

    @staticmethod
    async def _backfill_chunk_offsets(connection: aiosqlite.Connection) -> None:
        """为旧 Child 顺序回填区间；只有正文完全匹配时才写入，避免迁移制造假位置。"""
        rows = await (
            await connection.execute(
                """
                SELECT child.id, child.parent_id, child.content, child.start_offset,
                    child.end_offset, parent.content AS parent_content
                FROM text_chunks AS child
                JOIN text_chunks AS parent ON parent.id = child.parent_id
                WHERE child.kind = 'child'
                ORDER BY child.parent_id ASC, child.ordinal ASC
                """
            )
        ).fetchall()
        updates: list[tuple[int, int, str]] = []
        current_parent_id: str | None = None
        previous_start = -1
        for row in rows:
            child_id, parent_id, child_content = row[0], row[1], row[2]
            start_offset, end_offset, parent_content = int(row[3]), int(row[4]), row[5]
            if parent_id != current_parent_id:
                current_parent_id = parent_id
                previous_start = -1
            if (
                end_offset > start_offset
                and parent_content[start_offset:end_offset] == child_content
            ):
                previous_start = start_offset
                continue
            # 相邻 Child 存在 overlap，因此只要求下一个区间起点晚于上一个起点。
            found_start = parent_content.find(child_content, previous_start + 1)
            if found_start < 0:
                continue
            found_end = found_start + len(child_content)
            updates.append((found_start, found_end, child_id))
            previous_start = found_start
        if updates:
            await connection.executemany(
                "UPDATE text_chunks SET start_offset = ?, end_offset = ? WHERE id = ?",
                updates,
            )

    async def add(self, document: Document) -> None:
        try:
            async with self._connect() as connection:
                await connection.execute(
                    """
                    INSERT INTO documents (
                        id, knowledge_base_id, filename, extension, media_type, storage_key,
                        size_bytes, sha256, status, progress, parent_chunk_count,
                        child_chunk_count, error_code, error_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._document_parameters(document),
                )
                await connection.commit()
        except IntegrityError as error:
            raise DocumentDuplicateError() from error

    async def get(self, document_id: UUID) -> Document | None:
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT * FROM documents WHERE id = ?", (str(document_id),)
            )
            row = await cursor.fetchone()
        return self._document_from_row(row) if row else None

    async def get_by_hash(self, knowledge_base_id: UUID, sha256: str) -> Document | None:
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT * FROM documents WHERE knowledge_base_id = ? AND sha256 = ?",
                (str(knowledge_base_id), sha256),
            )
            row = await cursor.fetchone()
        return self._document_from_row(row) if row else None

    async def list(self, knowledge_base_id: UUID, *, limit: int, offset: int) -> Sequence[Document]:
        async with self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT * FROM documents WHERE knowledge_base_id = ?
                ORDER BY created_at DESC, id ASC LIMIT ? OFFSET ?
                """,
                (str(knowledge_base_id), limit, offset),
            )
            rows = await cursor.fetchall()
        return [self._document_from_row(row) for row in rows]

    async def count(self, knowledge_base_id: UUID) -> int:
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT COUNT(*) AS total FROM documents WHERE knowledge_base_id = ?",
                (str(knowledge_base_id),),
            )
            row = await cursor.fetchone()
        return int(row["total"])

    async def update(self, document: Document) -> None:
        async with self._connect() as connection:
            await connection.execute(
                """
                UPDATE documents SET filename = ?, media_type = ?, status = ?, progress = ?,
                    parent_chunk_count = ?, child_chunk_count = ?, error_code = ?,
                    error_message = ?, updated_at = ? WHERE id = ?
                """,
                (
                    document.filename,
                    document.media_type,
                    document.status.value,
                    document.progress,
                    document.parent_chunk_count,
                    document.child_chunk_count,
                    document.error_code,
                    document.error_message,
                    document.updated_at.isoformat(),
                    str(document.id),
                ),
            )
            await connection.commit()

    async def delete(self, document_id: UUID) -> None:
        async with self._connect() as connection:
            await connection.execute("DELETE FROM documents WHERE id = ?", (str(document_id),))
            await connection.commit()

    async def replace_chunks(
        self, document_id: UUID, chunks: Iterable[TextChunk]
    ) -> tuple[int, int]:
        return await asyncio.to_thread(self._replace_chunks_sync, document_id, chunks)

    def _replace_chunks_sync(
        self, document_id: UUID, chunks: Iterable[TextChunk]
    ) -> tuple[int, int]:
        parent_count = 0
        child_count = 0
        batch: list[tuple[object, ...]] = []
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("DELETE FROM text_chunks WHERE document_id = ?", (str(document_id),))
            for chunk in chunks:
                batch.append(self._chunk_parameters(chunk))
                if chunk.kind is ChunkKind.PARENT:
                    parent_count += 1
                else:
                    child_count += 1
                if len(batch) >= self._write_batch_size:
                    connection.executemany(self._insert_chunk_sql(), batch)
                    batch.clear()
            if batch:
                connection.executemany(self._insert_chunk_sql(), batch)
            connection.commit()
        return parent_count, child_count

    async def list_chunks(
        self,
        document_id: UUID,
        *,
        kind: ChunkKind,
        parent_id: UUID | None,
        limit: int,
        offset: int,
    ) -> Sequence[TextChunkSummary]:
        condition, parameters = self._chunk_condition(document_id, kind, parent_id)
        parameters.extend([limit, offset])
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"""
                SELECT id, document_id, parent_id, kind, ordinal, heading_path,
                    substr(content, 1, 240) AS preview, char_count, start_offset,
                    end_offset, manually_edited
                FROM text_chunks WHERE {condition}
                ORDER BY ordinal ASC LIMIT ? OFFSET ?
                """,  # noqa: S608 - condition 只由内部固定模板生成
                parameters,
            )
            rows = await cursor.fetchall()
        return [self._chunk_summary_from_row(row) for row in rows]

    async def count_chunks(
        self, document_id: UUID, *, kind: ChunkKind, parent_id: UUID | None
    ) -> int:
        condition, parameters = self._chunk_condition(document_id, kind, parent_id)
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"SELECT COUNT(*) AS total FROM text_chunks WHERE {condition}",  # noqa: S608
                parameters,
            )
            row = await cursor.fetchone()
        return int(row["total"])

    async def get_chunk(self, chunk_id: UUID) -> TextChunk | None:
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT * FROM text_chunks WHERE id = ?", (str(chunk_id),)
            )
            row = await cursor.fetchone()
        return self._chunk_from_row(row) if row else None

    async def list_child_chunks(
        self, document_id: UUID, *, limit: int, after_id: UUID | None
    ) -> Sequence[TextChunk]:
        """用主键游标分页，避免大文档后段出现 OFFSET 线性跳过成本。"""
        condition = "document_id = ? AND kind = 'child'"
        parameters: list[object] = [str(document_id)]
        if after_id is not None:
            condition += " AND id > ?"
            parameters.append(str(after_id))
        parameters.append(limit)
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"""
                SELECT * FROM text_chunks
                WHERE {condition}
                ORDER BY id ASC LIMIT ?
                """,  # noqa: S608 - condition 只追加内部固定模板
                parameters,
            )
            rows = await cursor.fetchall()
        return [self._chunk_from_row(row) for row in rows]

    async def get_chunks(self, chunk_ids: Sequence[UUID]) -> Mapping[UUID, TextChunk]:
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" for _ in chunk_ids)
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"SELECT * FROM text_chunks WHERE id IN ({placeholders})",  # noqa: S608
                [str(chunk_id) for chunk_id in chunk_ids],
            )
            rows = await cursor.fetchall()
        chunks = [self._chunk_from_row(row) for row in rows]
        return {chunk.id: chunk for chunk in chunks}

    async def update_chunk(self, chunk: TextChunk) -> None:
        async with self._connect() as connection:
            await connection.execute(
                """
                UPDATE text_chunks SET content = ?, char_count = ?, manually_edited = 1,
                    end_offset = start_offset + ?, updated_at = ? WHERE id = ?
                """,
                (
                    chunk.content,
                    chunk.char_count,
                    chunk.char_count,
                    chunk.updated_at.isoformat(),
                    str(chunk.id),
                ),
            )
            await connection.commit()

    async def update_parent_with_children(
        self, parent: TextChunk, children: Iterable[TextChunk]
    ) -> int:
        """Parent 正文和所属 Child 在同一事务更新，避免检索层级短暂不一致。"""
        return await asyncio.to_thread(self._update_parent_with_children_sync, parent, children)

    def _update_parent_with_children_sync(
        self, parent: TextChunk, children: Iterable[TextChunk]
    ) -> int:
        child_rows = [self._chunk_parameters(child) for child in children]
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                """
                UPDATE text_chunks SET content = ?, char_count = ?, manually_edited = 1,
                    start_offset = 0, end_offset = ?, updated_at = ?
                WHERE id = ? AND kind = 'parent'
                """,
                (
                    parent.content,
                    parent.char_count,
                    parent.char_count,
                    parent.updated_at.isoformat(),
                    str(parent.id),
                ),
            )
            connection.execute("DELETE FROM text_chunks WHERE parent_id = ?", (str(parent.id),))
            if child_rows:
                connection.executemany(self._insert_chunk_sql(), child_rows)
            connection.commit()
        return len(child_rows)

    async def delete_chunk(self, chunk_id: UUID) -> None:
        async with self._connect() as connection:
            await connection.execute("DELETE FROM text_chunks WHERE id = ?", (str(chunk_id),))
            await connection.commit()

    async def get_many(
        self, knowledge_base_ids: Sequence[UUID]
    ) -> Mapping[UUID, KnowledgeBaseMetrics]:
        if not knowledge_base_ids:
            return {}
        placeholders = ",".join("?" for _ in knowledge_base_ids)
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"""
                SELECT knowledge_base_id, COUNT(*) AS document_count,
                    SUM(CASE WHEN status IN ('chunked', 'ready') THEN 1 ELSE 0 END)
                        AS ready_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
                    SUM(child_chunk_count) AS chunk_count
                FROM documents WHERE knowledge_base_id IN ({placeholders})
                GROUP BY knowledge_base_id
                """,  # noqa: S608 - placeholders 数量来自 UUID 列表
                [str(item) for item in knowledge_base_ids],
            )
            rows = await cursor.fetchall()
        return {
            UUID(row["knowledge_base_id"]): KnowledgeBaseMetrics(
                document_count=int(row["document_count"] or 0),
                ready_document_count=int(row["ready_count"] or 0),
                failed_document_count=int(row["failed_count"] or 0),
                chunk_count=int(row["chunk_count"] or 0),
            )
            for row in rows
        }

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        async with aiosqlite.connect(self._database_path) as connection:
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys=ON")
            yield connection

    @staticmethod
    def _insert_chunk_sql() -> str:
        return """
            INSERT INTO text_chunks (
                id, document_id, parent_id, kind, ordinal, heading_path, content,
                char_count, start_offset, end_offset, manually_edited, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

    @staticmethod
    def _chunk_condition(
        document_id: UUID, kind: ChunkKind, parent_id: UUID | None
    ) -> tuple[str, list[object]]:
        if parent_id is None:
            return "document_id = ? AND kind = ?", [str(document_id), kind.value]
        return "document_id = ? AND kind = ? AND parent_id = ?", [
            str(document_id),
            kind.value,
            str(parent_id),
        ]

    @staticmethod
    def _document_parameters(document: Document) -> tuple[object, ...]:
        return (
            str(document.id),
            str(document.knowledge_base_id),
            document.filename,
            document.extension,
            document.media_type,
            document.storage_key,
            document.size_bytes,
            document.sha256,
            document.status.value,
            document.progress,
            document.parent_chunk_count,
            document.child_chunk_count,
            document.error_code,
            document.error_message,
            document.created_at.isoformat(),
            document.updated_at.isoformat(),
        )

    @staticmethod
    def _chunk_parameters(chunk: TextChunk) -> tuple[object, ...]:
        return (
            str(chunk.id),
            str(chunk.document_id),
            str(chunk.parent_id) if chunk.parent_id else None,
            chunk.kind.value,
            chunk.ordinal,
            chunk.heading_path,
            chunk.content,
            chunk.char_count,
            chunk.start_offset,
            chunk.end_offset,
            int(chunk.manually_edited),
            chunk.created_at.isoformat(),
            chunk.updated_at.isoformat(),
        )

    @staticmethod
    def _document_from_row(row: aiosqlite.Row) -> Document:
        return Document(
            id=UUID(row["id"]),
            knowledge_base_id=UUID(row["knowledge_base_id"]),
            filename=row["filename"],
            extension=row["extension"],
            media_type=row["media_type"],
            storage_key=row["storage_key"],
            size_bytes=int(row["size_bytes"]),
            sha256=row["sha256"],
            status=DocumentStatus(row["status"]),
            progress=int(row["progress"]),
            parent_chunk_count=int(row["parent_chunk_count"]),
            child_chunk_count=int(row["child_chunk_count"]),
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _chunk_from_row(row: aiosqlite.Row) -> TextChunk:
        return TextChunk(
            id=UUID(row["id"]),
            document_id=UUID(row["document_id"]),
            parent_id=UUID(row["parent_id"]) if row["parent_id"] else None,
            kind=ChunkKind(row["kind"]),
            ordinal=int(row["ordinal"]),
            heading_path=row["heading_path"],
            content=row["content"],
            char_count=int(row["char_count"]),
            start_offset=int(row["start_offset"]),
            end_offset=int(row["end_offset"]),
            manually_edited=bool(row["manually_edited"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _chunk_summary_from_row(row: aiosqlite.Row) -> TextChunkSummary:
        return TextChunkSummary(
            id=UUID(row["id"]),
            document_id=UUID(row["document_id"]),
            parent_id=UUID(row["parent_id"]) if row["parent_id"] else None,
            kind=ChunkKind(row["kind"]),
            ordinal=int(row["ordinal"]),
            heading_path=row["heading_path"],
            preview=row["preview"],
            char_count=int(row["char_count"]),
            start_offset=int(row["start_offset"]),
            end_offset=int(row["end_offset"]),
            manually_edited=bool(row["manually_edited"]),
        )
