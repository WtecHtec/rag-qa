from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

import aiosqlite

from app.modules.memory.models import Memory


class SqliteMemoryRepository:
    """长期记忆使用独立表持久化，避免与聊天历史和文档向量生命周期耦合。"""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self._database_path) as connection:
            await connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_key TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    source_conversation_id TEXT NOT NULL,
                    source_message_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_memories_updated
                    ON memories(updated_at DESC, id ASC);
                """
            )
            await connection.commit()

    async def upsert(self, memory: Memory) -> None:
        async with self._connect() as connection:
            await connection.execute(
                """
                INSERT INTO memories(
                    id, memory_key, content, source_conversation_id, source_message_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_key) DO UPDATE SET
                    content = excluded.content,
                    source_conversation_id = excluded.source_conversation_id,
                    source_message_id = excluded.source_message_id,
                    updated_at = excluded.updated_at
                """,
                (
                    str(memory.id),
                    memory.memory_key,
                    memory.content,
                    str(memory.source_conversation_id),
                    str(memory.source_message_id),
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                ),
            )
            await connection.commit()

    async def list_recent(self, *, limit: int) -> Sequence[Memory]:
        async with self._connect() as connection:
            rows = await (
                await connection.execute(
                    "SELECT * FROM memories ORDER BY updated_at DESC, id ASC LIMIT ?",
                    (limit,),
                )
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        async with aiosqlite.connect(self._database_path) as connection:
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys=ON")
            yield connection

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> Memory:
        return Memory(
            id=UUID(row["id"]),
            memory_key=row["memory_key"],
            content=row["content"],
            source_conversation_id=UUID(row["source_conversation_id"]),
            source_message_id=UUID(row["source_message_id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
