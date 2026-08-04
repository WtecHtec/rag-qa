import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from app.infrastructure.repositories.sqlite_conversation_repository import (
    SqliteConversationRepository,
)
from app.infrastructure.repositories.sqlite_document_repository import (
    SqliteDocumentRepository,
)


@pytest.mark.asyncio
async def test_legacy_repeated_children_and_citation_receive_verified_offsets(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy-offsets.db"
    now = datetime(2026, 8, 4, tzinfo=UTC).isoformat()
    parent_id = UUID(int=701)
    first_child_id = UUID(int=702)
    second_child_id = UUID(int=703)
    conversation_id = UUID(int=704)
    message_id = UUID(int=705)
    citation_id = UUID(int=706)
    document_id = UUID(int=707)
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE text_chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, parent_id TEXT,
                kind TEXT NOT NULL, ordinal INTEGER NOT NULL, heading_path TEXT NOT NULL,
                content TEXT NOT NULL, char_count INTEGER NOT NULL,
                manually_edited INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE chat_messages (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL,
                status TEXT NOT NULL, content TEXT NOT NULL, rewritten_query TEXT, model TEXT,
                error_code TEXT, error_message TEXT, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE message_citations (
                id TEXT PRIMARY KEY, message_id TEXT NOT NULL, knowledge_base_id TEXT NOT NULL,
                document_id TEXT NOT NULL, parent_id TEXT NOT NULL, child_id TEXT NOT NULL,
                citation_number INTEGER NOT NULL, document_name TEXT NOT NULL,
                heading_path TEXT NOT NULL, parent_content TEXT NOT NULL,
                child_preview TEXT NOT NULL, score REAL NOT NULL
            );
            """
        )
        chunk_rows = (
            (
                str(parent_id), str(document_id), None, "parent", 0, "", "重复文本。重复文本。",
                10, 0, now, now,
            ),
            (
                str(first_child_id), str(document_id), str(parent_id), "child", 0, "",
                "重复文本。", 5, 0, now, now,
            ),
            (
                str(second_child_id), str(document_id), str(parent_id), "child", 1, "",
                "重复文本。", 5, 0, now, now,
            ),
        )
        connection.executemany(
            "INSERT INTO text_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            chunk_rows,
        )
        connection.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?)",
            (str(conversation_id), "旧引用", now, now),
        )
        connection.execute(
            "INSERT INTO chat_messages VALUES (?, ?, 'assistant', 'complete', '', NULL, NULL, "
            "NULL, NULL, ?, ?)",
            (str(message_id), str(conversation_id), now, now),
        )
        connection.execute(
            "INSERT INTO message_citations VALUES (?, ?, ?, ?, ?, ?, 1, ?, '', ?, ?, 0.9)",
            (
                str(citation_id), str(message_id), str(UUID(int=708)), str(document_id),
                str(parent_id), str(second_child_id), "重复.md",
                "重复文本。重复文本。", "重复文本。",
            ),
        )
        connection.commit()

    await SqliteDocumentRepository(database_path).initialize()
    await SqliteConversationRepository(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        child_offsets = connection.execute(
            "SELECT start_offset, end_offset FROM text_chunks WHERE kind = 'child' "
            "ORDER BY ordinal"
        ).fetchall()
        citation_offsets = connection.execute(
            "SELECT child_start_offset, child_end_offset FROM message_citations"
        ).fetchone()

    assert child_offsets == [(0, 5), (5, 10)]
    assert citation_offsets == (5, 10)
