from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from sqlite3 import IntegrityError
from uuid import UUID

import aiosqlite

from app.modules.knowledge_bases.exceptions import KnowledgeBaseNameConflictError
from app.modules.knowledge_bases.models import KnowledgeBase


class SqliteKnowledgeBaseRepository:
    """知识库 Repository 的 SQLite 实现，每次操作使用独立短连接。"""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    async def initialize(self) -> None:
        """初始化只负责本模块表结构，后续会迁移到统一 migration。"""

        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._database_path) as connection:
            await connection.execute("PRAGMA journal_mode=WAL")
            await connection.execute("PRAGMA foreign_keys=ON")
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_bases_updated_at
                ON knowledge_bases(updated_at DESC)
                """
            )
            await connection.commit()

    async def add(self, knowledge_base: KnowledgeBase) -> None:
        try:
            async with aiosqlite.connect(self._database_path) as connection:
                await connection.execute(
                    """
                    INSERT INTO knowledge_bases (
                        id, name, normalized_name, description, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    self._to_parameters(knowledge_base),
                )
                await connection.commit()
        except IntegrityError as error:
            # 数据库唯一约束负责处理并发创建，转换后不向业务层泄漏 SQLite 异常。
            raise KnowledgeBaseNameConflictError(knowledge_base.name) from error

    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT * FROM knowledge_bases WHERE id = ?",
                (str(knowledge_base_id),),
            )
            row = await cursor.fetchone()
        return self._from_row(row) if row else None

    async def get_by_normalized_name(self, normalized_name: str) -> KnowledgeBase | None:
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT * FROM knowledge_bases WHERE normalized_name = ?",
                (normalized_name,),
            )
            row = await cursor.fetchone()
        return self._from_row(row) if row else None

    async def list(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[KnowledgeBase]:
        where_clause, parameters = self._build_search_condition(query)
        parameters.extend([limit, offset])
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"""
                SELECT * FROM knowledge_bases
                {where_clause}
                ORDER BY updated_at DESC, id ASC
                LIMIT ? OFFSET ?
                """,  # noqa: S608 - where_clause 只来自内部固定模板
                parameters,
            )
            rows = await cursor.fetchall()
        return [self._from_row(row) for row in rows]

    async def count(self, *, query: str | None) -> int:
        where_clause, parameters = self._build_search_condition(query)
        async with self._connect() as connection:
            cursor = await connection.execute(
                f"SELECT COUNT(*) AS total FROM knowledge_bases {where_clause}",  # noqa: S608
                parameters,
            )
            row = await cursor.fetchone()
        return int(row["total"])

    async def update(self, knowledge_base: KnowledgeBase) -> None:
        try:
            async with aiosqlite.connect(self._database_path) as connection:
                await connection.execute(
                    """
                    UPDATE knowledge_bases
                    SET name = ?, normalized_name = ?, description = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        knowledge_base.name,
                        knowledge_base.normalized_name,
                        knowledge_base.description,
                        knowledge_base.updated_at.isoformat(),
                        str(knowledge_base.id),
                    ),
                )
                await connection.commit()
        except IntegrityError as error:
            raise KnowledgeBaseNameConflictError(knowledge_base.name) from error

    async def delete(self, knowledge_base_id: UUID) -> None:
        async with aiosqlite.connect(self._database_path) as connection:
            await connection.execute(
                "DELETE FROM knowledge_bases WHERE id = ?",
                (str(knowledge_base_id),),
            )
            await connection.commit()

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        # row_factory 只能在连接激活后设置，因此由统一上下文管理器完成配置。
        async with aiosqlite.connect(self._database_path) as connection:
            connection.row_factory = aiosqlite.Row
            yield connection

    @staticmethod
    def _to_parameters(knowledge_base: KnowledgeBase) -> tuple[str, str, str, str, str, str]:
        return (
            str(knowledge_base.id),
            knowledge_base.name,
            knowledge_base.normalized_name,
            knowledge_base.description,
            knowledge_base.created_at.isoformat(),
            knowledge_base.updated_at.isoformat(),
        )

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> KnowledgeBase:
        return KnowledgeBase(
            id=UUID(row["id"]),
            name=row["name"],
            normalized_name=row["normalized_name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _build_search_condition(query: str | None) -> tuple[str, list[object]]:
        if query is None:
            return "", []
        # 转义 LIKE 通配符，用户输入的 % 和 _ 必须按普通字符搜索。
        escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return (
            "WHERE normalized_name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\'",
            [f"%{escaped_query}%", f"%{escaped_query}%"],
        )
