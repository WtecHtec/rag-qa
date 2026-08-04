import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.infrastructure.repositories.sqlite_conversation_repository import (
    SqliteConversationRepository,
)
from app.modules.chat.models import (
    ChatMessage,
    Citation,
    Conversation,
    MessageRole,
    MessageStatus,
)


@pytest.mark.asyncio
async def test_legacy_scoped_conversation_is_migrated_without_losing_messages(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy-chat.db"
    conversation_id = UUID(int=601)
    message_id = UUID(int=602)
    now = datetime(2026, 8, 4, tzinfo=UTC).isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                content TEXT NOT NULL,
                rewritten_query TEXT,
                model TEXT,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            """
        )
        connection.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
            (str(conversation_id), str(UUID(int=603)), "旧会话", now, now),
        )
        connection.execute(
            "INSERT INTO chat_messages VALUES (?, ?, 'user', 'complete', ?, NULL, NULL, "
            "NULL, NULL, ?, ?)",
            (str(message_id), str(conversation_id), "保留这条消息", now, now),
        )
        connection.commit()

    repository = SqliteConversationRepository(database_path)
    await repository.initialize()
    conversation = await repository.get_conversation(conversation_id)
    messages = await repository.list_messages(conversation_id)
    with sqlite3.connect(database_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(conversations)")]

    assert conversation is not None
    assert conversation.title == "旧会话"
    assert "knowledge_base_id" not in columns
    assert [message.content for message in messages] == ["保留这条消息"]


@pytest.mark.asyncio
async def test_stream_completion_after_conversation_delete_is_ignored(tmp_path: Path) -> None:
    """删除请求赢得竞态后，迟到的流式收尾不得写回消息或引用。"""
    repository = SqliteConversationRepository(tmp_path / "delete-race.db")
    await repository.initialize()
    now = datetime(2026, 8, 4, tzinfo=UTC)
    conversation = Conversation(uuid4(), "待删除", now, now)
    user_message = ChatMessage(
        uuid4(), conversation.id, MessageRole.USER, MessageStatus.COMPLETE,
        "问题", None, None, None, None, False, (), now, now,
    )
    assistant_message = ChatMessage(
        uuid4(), conversation.id, MessageRole.ASSISTANT, MessageStatus.GENERATING,
        "", None, "fake-model", None, None, True, (), now, now,
    )
    await repository.add_conversation(conversation)
    await repository.start_turn(conversation, user_message, assistant_message)
    await repository.delete_conversation(conversation.id)
    completed = replace(
        assistant_message,
        status=MessageStatus.COMPLETE,
        content="迟到回答 [1]",
    )
    citation = Citation(
        uuid4(), assistant_message.id, uuid4(), uuid4(), uuid4(), uuid4(),
        1, "文档.md", "章节", "父块内容", "子块", 0, 2, 0.9,
    )

    await repository.complete_message(completed, (citation,))

    assert await repository.get_conversation(conversation.id) is None
    assert await repository.get_message(assistant_message.id) is None
