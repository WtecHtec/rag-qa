from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import aiosqlite

from app.modules.chat.models import (
    ChatMessage,
    Citation,
    Conversation,
    FeedbackRating,
    MessageRole,
    MessageStatus,
)


class SqliteConversationRepository:
    """会话、消息、引用与反馈统一在 SQLite 事务边界内持久化。"""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self._database_path) as connection:
            # 早期版本把会话绑定到单个知识库；重建轻量主表可保留消息并解除该约束。
            await connection.execute("PRAGMA foreign_keys=OFF")
            columns = await (
                await connection.execute("PRAGMA table_info(conversations)")
            ).fetchall()
            if any(column[1] == "knowledge_base_id" for column in columns):
                await connection.executescript(
                    """
                    CREATE TABLE conversations_without_scope (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    INSERT INTO conversations_without_scope(id, title, created_at, updated_at)
                        SELECT id, title, created_at, updated_at FROM conversations;
                    DROP TABLE conversations;
                    ALTER TABLE conversations_without_scope RENAME TO conversations;
                    """
                )
                await connection.commit()
            await connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content TEXT NOT NULL,
                    rewritten_query TEXT,
                    model TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    rag_enabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS message_citations (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    knowledge_base_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    citation_number INTEGER NOT NULL,
                    document_name TEXT NOT NULL,
                    heading_path TEXT NOT NULL,
                    parent_content TEXT NOT NULL,
                    child_preview TEXT NOT NULL,
                    child_start_offset INTEGER NOT NULL DEFAULT 0,
                    child_end_offset INTEGER NOT NULL DEFAULT 0,
                    score REAL NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                    UNIQUE (message_id, citation_number)
                );

                CREATE TABLE IF NOT EXISTS message_feedback (
                    message_id TEXT PRIMARY KEY,
                    rating TEXT NOT NULL,
                    reason TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS retrieval_traces (
                    id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    rewritten_query TEXT,
                    intent_category TEXT,
                    retrieved_chunks_count INTEGER NOT NULL,
                    top_score REAL,
                    retrieval_latency_ms REAL NOT NULL,
                    llm_latency_ms REAL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON chat_messages(conversation_id, created_at ASC, id ASC);
                CREATE INDEX IF NOT EXISTS idx_citations_message
                    ON message_citations(message_id, citation_number ASC);
                CREATE INDEX IF NOT EXISTS idx_traces_created
                    ON retrieval_traces(created_at DESC);
                """
            )
            message_columns = await (
                await connection.execute("PRAGMA table_info(chat_messages)")
            ).fetchall()
            if not any(column[1] == "rag_enabled" for column in message_columns):
                # SQLite 通过轻量加列兼容已有会话，无需重建消息和引用表。
                await connection.execute(
                    "ALTER TABLE chat_messages "
                    "ADD COLUMN rag_enabled INTEGER NOT NULL DEFAULT 0"
                )
            citation_columns = await (
                await connection.execute("PRAGMA table_info(message_citations)")
            ).fetchall()
            if not any(column[1] == "child_start_offset" for column in citation_columns):
                await connection.execute(
                    "ALTER TABLE message_citations "
                    "ADD COLUMN child_start_offset INTEGER NOT NULL DEFAULT 0"
                )
            if not any(column[1] == "child_end_offset" for column in citation_columns):
                await connection.execute(
                    "ALTER TABLE message_citations "
                    "ADD COLUMN child_end_offset INTEGER NOT NULL DEFAULT 0"
                )
            await self._backfill_citation_offsets(connection)
            await connection.commit()
            await connection.execute("PRAGMA foreign_keys=ON")

    async def add_conversation(self, conversation: Conversation) -> None:
        async with self._connect() as connection:
            await connection.execute(
                """
                INSERT INTO conversations(id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                self._conversation_parameters(conversation),
            )
            await connection.commit()

    @staticmethod
    async def _backfill_citation_offsets(connection: aiosqlite.Connection) -> None:
        """历史引用仅在 Child 与当时 Parent 快照仍完全一致时回填，禁止模糊猜测。"""
        chunk_table = await (
            await connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'text_chunks'"
            )
        ).fetchone()
        if chunk_table is None:
            # 会话模块可独立测试或部署；没有文档表时无需执行跨模块兼容迁移。
            return
        rows = await (
            await connection.execute(
                """
                SELECT citation.id, citation.parent_content, child.content,
                    child.start_offset, child.end_offset
                FROM message_citations AS citation
                JOIN text_chunks AS child ON child.id = citation.child_id
                WHERE citation.child_end_offset <= citation.child_start_offset
                """
            )
        ).fetchall()
        updates: list[tuple[int, int, str]] = []
        for row in rows:
            citation_id, parent_content, child_content = row[0], row[1], row[2]
            start_offset, end_offset = int(row[3]), int(row[4])
            if (
                end_offset > start_offset
                and parent_content[start_offset:end_offset] == child_content
            ):
                updates.append((start_offset, end_offset, citation_id))
        if updates:
            await connection.executemany(
                """
                UPDATE message_citations
                SET child_start_offset = ?, child_end_offset = ? WHERE id = ?
                """,
                updates,
            )

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        async with self._connect() as connection:
            row = await (
                await connection.execute(
                    "SELECT * FROM conversations WHERE id = ?",
                    (str(conversation_id),),
                )
            ).fetchone()
        return self._conversation_from_row(row) if row else None

    async def list_conversations(self, *, limit: int, offset: int) -> Sequence[Conversation]:
        async with self._connect() as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT * FROM conversations
                    ORDER BY updated_at DESC, id ASC LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
            ).fetchall()
        return [self._conversation_from_row(row) for row in rows]

    async def count_conversations(self) -> int:
        async with self._connect() as connection:
            row = await (
                await connection.execute("SELECT COUNT(*) AS total FROM conversations")
            ).fetchone()
        return int(row["total"])

    async def delete_conversation(self, conversation_id: UUID) -> None:
        async with self._connect() as connection:
            await connection.execute(
                "DELETE FROM conversations WHERE id = ?", (str(conversation_id),)
            )
            await connection.commit()

    async def commit_turn(
        self,
        conversation: Conversation,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        citations: Sequence[Citation],
    ) -> None:
        """完整回答生成后原子写入整轮，任何中断都不会留下半成品。"""
        async with self._connect() as connection:
            cursor = await connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (conversation.title, conversation.updated_at.isoformat(), str(conversation.id)),
            )
            if cursor.rowcount == 0:
                # 删除会话与流式收尾可能并发；会话已删除时直接放弃迟到结果。
                await connection.rollback()
                return
            await connection.executemany(
                """
                INSERT INTO chat_messages(
                    id, conversation_id, role, status, content, rewritten_query,
                    model, error_code, error_message, rag_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    self._message_parameters(user_message),
                    self._message_parameters(assistant_message),
                ],
            )
            if citations:
                await connection.executemany(
                    """
                    INSERT INTO message_citations(
                        id, message_id, knowledge_base_id, document_id, parent_id,
                        child_id, citation_number, document_name, heading_path,
                        parent_content, child_preview, child_start_offset,
                        child_end_offset, score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [self._citation_parameters(citation) for citation in citations],
                )
            await connection.commit()

    async def list_messages(self, conversation_id: UUID) -> Sequence[ChatMessage]:
        async with self._connect() as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT * FROM chat_messages WHERE conversation_id = ?
                    ORDER BY created_at ASC, rowid ASC
                    """,
                    (str(conversation_id),),
                )
            ).fetchall()
            citations = await self._citations_for_messages(
                connection,
                [UUID(row["id"]) for row in rows],
            )
        return [self._message_from_row(row, citations.get(UUID(row["id"]), ())) for row in rows]

    async def list_message_page(
        self,
        conversation_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[ChatMessage]:
        """从最新消息向前分页，返回值仍保持正序，便于前端直接向顶部追加。"""
        async with self._connect() as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT * FROM chat_messages WHERE conversation_id = ?
                    ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?
                    """,
                    (str(conversation_id), limit, offset),
                )
            ).fetchall()
            rows.reverse()
            citations = await self._citations_for_messages(
                connection,
                [UUID(row["id"]) for row in rows],
            )
        return [self._message_from_row(row, citations.get(UUID(row["id"]), ())) for row in rows]

    async def count_messages(self, conversation_id: UUID) -> int:
        async with self._connect() as connection:
            row = await (
                await connection.execute(
                    "SELECT COUNT(*) AS total FROM chat_messages WHERE conversation_id = ?",
                    (str(conversation_id),),
                )
            ).fetchone()
        return int(row["total"])

    async def get_message(self, message_id: UUID) -> ChatMessage | None:
        async with self._connect() as connection:
            row = await (
                await connection.execute(
                    "SELECT * FROM chat_messages WHERE id = ?", (str(message_id),)
                )
            ).fetchone()
            if row is None:
                return None
            citations = await self._citations_for_messages(connection, [message_id])
        return self._message_from_row(row, citations.get(message_id, ()))

    async def complete_message(
        self,
        message: ChatMessage,
        citations: Sequence[Citation],
    ) -> None:
        async with self._connect() as connection:
            updated = await self._update_message(connection, message)
            if not updated:
                # 删除会话与流式收尾可能并发；父消息已级联删除时不得重新插入引用。
                await connection.rollback()
                return
            await connection.execute(
                "DELETE FROM message_citations WHERE message_id = ?",
                (str(message.id),),
            )
            if citations:
                await connection.executemany(
                    """
                    INSERT INTO message_citations(
                        id, message_id, knowledge_base_id, document_id, parent_id,
                        child_id, citation_number, document_name, heading_path,
                        parent_content, child_preview, child_start_offset,
                        child_end_offset, score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [self._citation_parameters(citation) for citation in citations],
                )
            await connection.commit()

    async def save_feedback(
        self,
        message_id: UUID,
        rating: FeedbackRating,
        reason: str | None,
    ) -> None:
        async with self._connect() as connection:
            await connection.execute(
                """
                INSERT INTO message_feedback(message_id, rating, reason, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    rating = excluded.rating,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (
                    str(message_id),
                    rating.value,
                    reason,
                    datetime.now(UTC).isoformat(),
                ),
            )
            await connection.commit()

    async def save_retrieval_trace(
        self,
        *,
        trace_id: str,
        query: str,
        rewritten_query: str | None,
        intent_category: str | None,
        retrieved_chunks_count: int,
        top_score: float | None,
        retrieval_latency_ms: float,
        llm_latency_ms: float | None = None,
    ) -> None:
        async with self._connect() as connection:
            now_str = datetime.now(UTC).isoformat()
            row_id = str(uuid4())
            await connection.execute(
                """
                INSERT INTO retrieval_traces(
                    id, trace_id, query, rewritten_query, intent_category,
                    retrieved_chunks_count, top_score, retrieval_latency_ms,
                    llm_latency_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    trace_id,
                    query,
                    rewritten_query,
                    intent_category,
                    retrieved_chunks_count,
                    top_score,
                    retrieval_latency_ms,
                    llm_latency_ms,
                    now_str,
                ),
            )
            await connection.commit()

    @staticmethod
    async def _update_message(
        connection: aiosqlite.Connection,
        message: ChatMessage,
    ) -> bool:
        cursor = await connection.execute(
            """
            UPDATE chat_messages SET status = ?, content = ?, rewritten_query = ?,
                model = ?, error_code = ?, error_message = ?, rag_enabled = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                message.status.value,
                message.content,
                message.rewritten_query,
                message.model,
                message.error_code,
                message.error_message,
                int(message.rag_enabled),
                message.updated_at.isoformat(),
                str(message.id),
            ),
        )
        return cursor.rowcount > 0

    async def _citations_for_messages(
        self,
        connection: aiosqlite.Connection,
        message_ids: Sequence[UUID],
    ) -> dict[UUID, tuple[Citation, ...]]:
        if not message_ids:
            return {}
        placeholders = ",".join("?" for _ in message_ids)
        rows = await (
            await connection.execute(
                f"""
                SELECT * FROM message_citations WHERE message_id IN ({placeholders})
                ORDER BY message_id ASC, citation_number ASC
                """,  # noqa: S608 - placeholders 数量来自 UUID 列表
                [str(message_id) for message_id in message_ids],
            )
        ).fetchall()
        grouped: dict[UUID, list[Citation]] = {}
        for row in rows:
            citation = self._citation_from_row(row)
            grouped.setdefault(citation.message_id, []).append(citation)
        return {message_id: tuple(items) for message_id, items in grouped.items()}

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        async with aiosqlite.connect(self._database_path) as connection:
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys=ON")
            yield connection

    @staticmethod
    def _conversation_parameters(conversation: Conversation) -> tuple[str, ...]:
        return (
            str(conversation.id),
            conversation.title,
            conversation.created_at.isoformat(),
            conversation.updated_at.isoformat(),
        )

    @staticmethod
    def _message_parameters(message: ChatMessage) -> tuple[object, ...]:
        return (
            str(message.id),
            str(message.conversation_id),
            message.role.value,
            message.status.value,
            message.content,
            message.rewritten_query,
            message.model,
            message.error_code,
            message.error_message,
            int(message.rag_enabled),
            message.created_at.isoformat(),
            message.updated_at.isoformat(),
        )

    @staticmethod
    def _citation_parameters(citation: Citation) -> tuple[object, ...]:
        return (
            str(citation.id),
            str(citation.message_id),
            str(citation.knowledge_base_id),
            str(citation.document_id),
            str(citation.parent_id),
            str(citation.child_id),
            citation.citation_number,
            citation.document_name,
            citation.heading_path,
            citation.parent_content,
            citation.child_preview,
            citation.child_start_offset,
            citation.child_end_offset,
            citation.score,
        )

    @staticmethod
    def _conversation_from_row(row: aiosqlite.Row) -> Conversation:
        return Conversation(
            id=UUID(row["id"]),
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _message_from_row(
        row: aiosqlite.Row,
        citations: Sequence[Citation],
    ) -> ChatMessage:
        return ChatMessage(
            id=UUID(row["id"]),
            conversation_id=UUID(row["conversation_id"]),
            role=MessageRole(row["role"]),
            status=MessageStatus(row["status"]),
            content=row["content"],
            rewritten_query=row["rewritten_query"],
            model=row["model"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            rag_enabled=bool(row["rag_enabled"]),
            citations=tuple(citations),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _citation_from_row(row: aiosqlite.Row) -> Citation:
        return Citation(
            id=UUID(row["id"]),
            message_id=UUID(row["message_id"]),
            knowledge_base_id=UUID(row["knowledge_base_id"]),
            document_id=UUID(row["document_id"]),
            parent_id=UUID(row["parent_id"]),
            child_id=UUID(row["child_id"]),
            citation_number=int(row["citation_number"]),
            document_name=row["document_name"],
            heading_path=row["heading_path"],
            parent_content=row["parent_content"],
            child_preview=row["child_preview"],
            child_start_offset=int(row["child_start_offset"]),
            child_end_offset=int(row["child_end_offset"]),
            score=float(row["score"]),
        )
