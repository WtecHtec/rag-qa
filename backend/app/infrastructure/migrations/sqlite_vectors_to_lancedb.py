import asyncio
import hashlib
import logging
import sqlite3
import struct
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.modules.retrieval.models import VectorRecord
from app.modules.retrieval.vector_store import VectorStore


class SqliteVectorsToLanceDbMigration:
    """将早期 SQLite BLOB 向量一次性复制到 LanceDB。"""

    def __init__(
        self,
        sqlite_path: Path,
        vector_store: VectorStore,
        *,
        target_path: Path,
        embedding_model: str,
        dimensions: int,
        batch_size: int = 400,
        logger: logging.Logger | None = None,
    ) -> None:
        self._sqlite_path = sqlite_path
        self._vector_store = vector_store
        self._dimensions = dimensions
        self._embedding_model = embedding_model
        self._batch_size = batch_size
        target_hash = hashlib.sha256(str(target_path.resolve()).encode("utf-8")).hexdigest()[:12]
        model_hash = hashlib.sha256(embedding_model.encode("utf-8")).hexdigest()[:12]
        self._migration_name = (
            f"sqlite_vectors_to_lancedb_v1_{dimensions}_{model_hash}_{target_hash}"
        )
        self._logger = logger or logging.getLogger(__name__)

    async def run(self) -> None:
        if await asyncio.to_thread(self._is_completed):
            return
        after_row_id = 0
        migrated_count = 0
        while True:
            rows = await asyncio.to_thread(self._read_batch, after_row_id)
            if not rows:
                break
            after_row_id = rows[-1][0]
            records = tuple(self._record_from_row(row) for row in rows)
            await self._vector_store.upsert(records)
            migrated_count += len(records)
        reindex_count = await asyncio.to_thread(self._mark_incompatible_documents)
        await asyncio.to_thread(self._mark_completed)
        self._logger.info(
            "vector_store.sqlite_migrated",
            extra={
                "dimensions": self._dimensions,
                "vector_count": migrated_count,
                "reindex_document_count": reindex_count,
            },
        )

    def _is_completed(self) -> bool:
        with sqlite3.connect(self._sqlite_path) as connection:
            self._ensure_migration_table(connection)
            row = connection.execute(
                "SELECT 1 FROM app_migrations WHERE name = ?",
                (self._migration_name,),
            ).fetchone()
            connection.commit()
        return row is not None

    def _read_batch(self, after_row_id: int) -> list[sqlite3.Row]:
        with sqlite3.connect(self._sqlite_path) as connection:
            connection.row_factory = sqlite3.Row
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'child_vectors'"
            ).fetchone()
            if table_exists is None:
                return []
            return connection.execute(
                """
                SELECT rowid, child_id, parent_id, document_id, knowledge_base_id,
                    embedding_model, dimensions, embedding, content_hash, updated_at
                FROM child_vectors
                WHERE rowid > ? AND dimensions = ? AND embedding_model = ?
                ORDER BY rowid ASC LIMIT ?
                """,
                (
                    after_row_id,
                    self._dimensions,
                    self._embedding_model,
                    self._batch_size,
                ),
            ).fetchall()

    def _mark_incompatible_documents(self) -> int:
        with sqlite3.connect(self._sqlite_path) as connection:
            documents_exist = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents'"
            ).fetchone()
            vectors_exist = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'child_vectors'"
            ).fetchone()
            if documents_exist is None:
                return 0
            if vectors_exist is None:
                cursor = connection.execute(
                    """
                    UPDATE documents SET status = 'failed', progress = 0,
                        error_code = 'document_reindex_required',
                        error_message = '向量模型或向量库已升级，请重新处理文档'
                    WHERE status IN ('ready', 'chunked')
                    """
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE documents SET status = 'failed', progress = 0,
                        error_code = 'document_reindex_required',
                        error_message = '向量模型或向量库已升级，请重新处理文档'
                    WHERE status IN ('ready', 'chunked') AND NOT EXISTS (
                        SELECT 1 FROM child_vectors
                        WHERE child_vectors.document_id = documents.id
                            AND child_vectors.dimensions = ?
                            AND child_vectors.embedding_model = ?
                    )
                    """,
                    (self._dimensions, self._embedding_model),
                )
            connection.commit()
            return max(0, cursor.rowcount)

    def _mark_completed(self) -> None:
        with sqlite3.connect(self._sqlite_path) as connection:
            self._ensure_migration_table(connection)
            connection.execute(
                "INSERT OR IGNORE INTO app_migrations(name, completed_at) VALUES (?, ?)",
                (self._migration_name, datetime.now().astimezone().isoformat()),
            )
            connection.commit()

    def _record_from_row(self, row: sqlite3.Row) -> VectorRecord:
        vector = tuple(
            struct.unpack(
                f"<{self._dimensions}f",
                row["embedding"],
            )
        )
        return VectorRecord(
            knowledge_base_id=UUID(row["knowledge_base_id"]),
            document_id=UUID(row["document_id"]),
            child_id=UUID(row["child_id"]),
            parent_id=UUID(row["parent_id"]),
            embedding_model=row["embedding_model"],
            embedding=vector,
            content_hash=row["content_hash"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _ensure_migration_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_migrations (
                name TEXT PRIMARY KEY,
                completed_at TEXT NOT NULL
            )
            """
        )
