import asyncio
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar
from uuid import UUID

import lancedb
import pyarrow as pa
from lancedb.index import HnswSq
from lancedb.table import Table

from app.modules.retrieval.exceptions import VectorStoreError
from app.modules.retrieval.models import Embedding, VectorHit, VectorRecord

Result = TypeVar("Result")


class LanceDbVectorStore:
    """将 Child 向量持久化到本地 LanceDB，并使用原生 cosine 查询。"""

    def __init__(
        self,
        database_path: Path,
        *,
        dimensions: int,
        index_threshold: int = 5_000,
    ) -> None:
        if dimensions < 1 or index_threshold < 1:
            raise ValueError("向量维度和索引阈值必须大于 0")
        self._database_path = database_path
        self._dimensions = dimensions
        self._index_threshold = index_threshold
        # 不同维度使用独立表，切换模型维度时不会破坏既有表结构。
        self._table_name = f"child_vectors_{dimensions}"
        self._write_lock = threading.Lock()

    async def initialize(self) -> None:
        await self._run(self._initialize_sync)

    async def delete_document(self, document_id: UUID) -> None:
        await self._run(self._delete_document_sync, document_id)

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        if any(len(record.embedding) != self._dimensions for record in records):
            raise VectorStoreError("写入向量的维度与 LanceDB 表结构不一致")
        await self._run(self._upsert_sync, records)

    async def search(
        self,
        knowledge_base_id: UUID | None,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> Sequence[VectorHit]:
        if limit < 1:
            return ()
        if len(embedding) != self._dimensions:
            raise VectorStoreError("查询向量的维度与 LanceDB 表结构不一致")
        return await self._run(
            self._search_sync,
            knowledge_base_id,
            embedding,
            embedding_model,
            limit,
        )

    def _initialize_sync(self) -> None:
        with self._write_lock:
            self._database_path.mkdir(parents=True, exist_ok=True)
            database = lancedb.connect(self._database_path)
            database.create_table(
                self._table_name,
                schema=self._schema(),
                exist_ok=True,
            )

    def _delete_document_sync(self, document_id: UUID) -> None:
        with self._write_lock:
            table = self._open_table()
            table.delete(f"document_id = {self._quote(str(document_id))}")

    def _upsert_sync(self, records: Sequence[VectorRecord]) -> None:
        rows = [
            {
                "child_id": str(record.child_id),
                "parent_id": str(record.parent_id),
                "document_id": str(record.document_id),
                "knowledge_base_id": str(record.knowledge_base_id),
                "embedding_model": record.embedding_model,
                "dimensions": len(record.embedding),
                "vector": list(record.embedding),
                "content_hash": record.content_hash,
                "updated_at": record.updated_at.isoformat(),
            }
            for record in records
        ]
        with self._write_lock:
            table = self._open_table()
            (
                table.merge_insert("child_id")
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .execute(rows)
            )
            self._ensure_vector_index(table)

    def _search_sync(
        self,
        knowledge_base_id: UUID | None,
        embedding: Embedding,
        embedding_model: str,
        limit: int,
    ) -> Sequence[VectorHit]:
        condition = f"embedding_model = {self._quote(embedding_model)}"
        if knowledge_base_id is not None:
            condition = (
                f"knowledge_base_id = {self._quote(str(knowledge_base_id))} AND {condition}"
            )
        rows = (
            self._open_table()
            .search(list(embedding), vector_column_name="vector")
            .distance_type("cosine")
            .where(condition, prefilter=True)
            .limit(limit)
            .select(["child_id", "parent_id", "document_id", "_distance"])
            .to_arrow()
            .to_pylist()
        )
        return tuple(
            VectorHit(
                child_id=UUID(row["child_id"]),
                parent_id=UUID(row["parent_id"]),
                document_id=UUID(row["document_id"]),
                # LanceDB 返回 cosine distance；业务层统一使用越大越相关的 similarity。
                score=max(-1.0, min(1.0, 1.0 - float(row["_distance"]))),
            )
            for row in rows
        )

    def _open_table(self) -> Table:
        return lancedb.connect(self._database_path).open_table(self._table_name)

    def _ensure_vector_index(self, table: Table) -> None:
        has_vector_index = any("vector" in index.columns for index in table.list_indices())
        if table.count_rows() < self._index_threshold or has_vector_index:
            return
        # 小数据量精确搜索更省维护成本；达到阈值后再建立压缩 HNSW 索引。
        table.create_index(
            "vector",
            config=HnswSq(distance_type="cosine"),
            replace=False,
        )

    async def _run(
        self,
        operation: Callable[..., Result],
        *arguments: object,
    ) -> Result:
        try:
            return await asyncio.to_thread(operation, *arguments)
        except VectorStoreError:
            raise
        except Exception as error:
            raise VectorStoreError("LanceDB 本地向量库操作失败，请查看日志") from error

    def _schema(self) -> pa.Schema:
        return pa.schema(
            [
                pa.field("child_id", pa.string(), nullable=False),
                pa.field("parent_id", pa.string(), nullable=False),
                pa.field("document_id", pa.string(), nullable=False),
                pa.field("knowledge_base_id", pa.string(), nullable=False),
                pa.field("embedding_model", pa.string(), nullable=False),
                pa.field("dimensions", pa.int32(), nullable=False),
                pa.field(
                    "vector",
                    pa.list_(pa.float32(), list_size=self._dimensions),
                    nullable=False,
                ),
                pa.field("content_hash", pa.string(), nullable=False),
                pa.field("updated_at", pa.string(), nullable=False),
            ]
        )

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"
