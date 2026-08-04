import sqlite3
import struct
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import lancedb
import pytest

from app.infrastructure.migrations.sqlite_vectors_to_lancedb import (
    SqliteVectorsToLanceDbMigration,
)
from app.infrastructure.vector_stores.lancedb_vector_store import LanceDbVectorStore
from app.modules.retrieval.models import VectorRecord

NOW = datetime(2026, 8, 4, tzinfo=UTC)
KB_ID = UUID(int=1)
DOCUMENT_ID = UUID(int=2)


def make_record(
    child_id: int,
    parent_id: int,
    embedding: tuple[float, ...],
    knowledge_base_id: UUID = KB_ID,
) -> VectorRecord:
    return VectorRecord(
        knowledge_base_id=knowledge_base_id,
        document_id=DOCUMENT_ID,
        child_id=UUID(int=child_id),
        parent_id=UUID(int=parent_id),
        embedding_model="test-model",
        embedding=embedding,
        content_hash=f"hash-{child_id}",
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_vectors_survive_reopening_and_support_cosine_search(tmp_path: Path) -> None:
    database_path = tmp_path / "vectors"
    first_store = LanceDbVectorStore(database_path, dimensions=3)
    await first_store.initialize()
    await first_store.upsert(
        (
            make_record(11, 21, (1.0, 0.0, 0.0)),
            make_record(12, 22, (0.0, 1.0, 0.0)),
        )
    )

    # 新实例模拟应用重启，查询结果必须来自磁盘而不是进程内状态。
    reopened_store = LanceDbVectorStore(database_path, dimensions=3)
    await reopened_store.initialize()
    hits = await reopened_store.search(
        KB_ID,
        (1.0, 0.0, 0.0),
        embedding_model="test-model",
        limit=2,
    )

    assert [hit.child_id for hit in hits] == [UUID(int=11), UUID(int=12)]
    assert hits[0].score == pytest.approx(1.0)
    await reopened_store.delete_document(DOCUMENT_ID)
    assert not await reopened_store.search(
        KB_ID,
        (1.0, 0.0, 0.0),
        embedding_model="test-model",
        limit=2,
    )


@pytest.mark.asyncio
async def test_global_search_returns_children_across_knowledge_bases(tmp_path: Path) -> None:
    store = LanceDbVectorStore(tmp_path / "global-vectors", dimensions=3)
    await store.initialize()
    await store.upsert(
        (
            make_record(71, 81, (1.0, 0.0, 0.0), UUID(int=501)),
            make_record(72, 82, (0.9, 0.1, 0.0), UUID(int=502)),
        )
    )

    hits = await store.search(
        None,
        (1.0, 0.0, 0.0),
        embedding_model="test-model",
        limit=2,
    )

    assert [hit.child_id for hit in hits] == [UUID(int=71), UUID(int=72)]


@pytest.mark.asyncio
async def test_legacy_sqlite_vectors_are_migrated_once(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "legacy.db"
    child_id = UUID(int=31)
    parent_id = UUID(int=41)
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute(
            """
            CREATE TABLE documents (
                id TEXT PRIMARY KEY, status TEXT, progress INTEGER,
                error_code TEXT, error_message TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO documents VALUES (?, 'ready', 100, NULL, NULL)",
            [(str(DOCUMENT_ID),), (str(UUID(int=99)),)],
        )
        connection.execute(
            """
            CREATE TABLE child_vectors (
                child_id TEXT, parent_id TEXT, document_id TEXT, knowledge_base_id TEXT,
                embedding_model TEXT, dimensions INTEGER, embedding BLOB,
                content_hash TEXT, updated_at TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO child_vectors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(child_id),
                str(parent_id),
                str(DOCUMENT_ID),
                str(KB_ID),
                "test-model",
                3,
                struct.pack("<3f", 1.0, 0.0, 0.0),
                "legacy-hash",
                NOW.isoformat(),
            ),
        )
        connection.commit()

    store = LanceDbVectorStore(tmp_path / "vectors", dimensions=3)
    await store.initialize()
    migration = SqliteVectorsToLanceDbMigration(
        sqlite_path,
        store,
        target_path=tmp_path / "vectors",
        embedding_model="test-model",
        dimensions=3,
    )
    await migration.run()
    await migration.run()
    hits = await store.search(
        KB_ID,
        (1.0, 0.0, 0.0),
        embedding_model="test-model",
        limit=5,
    )

    assert len(hits) == 1
    assert hits[0].child_id == child_id
    with sqlite3.connect(sqlite_path) as connection:
        marker_count = connection.execute("SELECT COUNT(*) FROM app_migrations").fetchone()[0]
        incompatible = connection.execute(
            "SELECT status, error_code FROM documents WHERE id = ?",
            (str(UUID(int=99)),),
        ).fetchone()
        compatible = connection.execute(
            "SELECT status, error_code FROM documents WHERE id = ?",
            (str(DOCUMENT_ID),),
        ).fetchone()
    assert marker_count == 1
    assert incompatible == ("failed", "document_reindex_required")
    assert compatible == ("ready", None)


@pytest.mark.asyncio
async def test_large_collection_builds_cosine_hnsw_index(tmp_path: Path) -> None:
    database_path = tmp_path / "indexed-vectors"
    store = LanceDbVectorStore(database_path, dimensions=8, index_threshold=50)
    await store.initialize()
    await store.upsert(
        tuple(
            make_record(
                100 + index,
                1_000 + index,
                tuple(float((index + offset) % 7) for offset in range(8)),
            )
            for index in range(100)
        )
    )

    table = lancedb.connect(database_path).open_table("child_vectors_8")
    indices = list(table.list_indices())

    assert len(indices) == 1
    assert indices[0].columns == ["vector"]
    assert "Hnsw" in indices[0].index_type
