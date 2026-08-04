import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.knowledge_bases.commands import (
    CreateKnowledgeBaseCommand,
    UpdateKnowledgeBaseCommand,
)
from app.modules.knowledge_bases.exceptions import (
    KnowledgeBaseNameConflictError,
    KnowledgeBaseNotEmptyError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseValidationError,
)
from app.modules.knowledge_bases.models import (
    KnowledgeBase,
    KnowledgeBaseDetail,
    KnowledgeBaseMetrics,
    KnowledgeBasePage,
)
from app.modules.knowledge_bases.repository import (
    KnowledgeBaseMetricsReader,
    KnowledgeBaseRepository,
)
from app.modules.knowledge_bases.validators import (
    normalize_description,
    normalize_knowledge_base_name,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


def utc_now() -> datetime:
    return datetime.now(UTC)


class KnowledgeBaseService:
    """编排知识库用例，不依赖具体数据库或 Web 框架。"""

    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        metrics_reader: KnowledgeBaseMetricsReader,
        *,
        clock: Clock = utc_now,
        id_factory: IdFactory = uuid4,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._metrics_reader = metrics_reader
        self._clock = clock
        self._id_factory = id_factory
        self._logger = logger or logging.getLogger(__name__)

    async def create(self, command: CreateKnowledgeBaseCommand) -> KnowledgeBaseDetail:
        name, normalized_name = normalize_knowledge_base_name(command.name)
        description = normalize_description(command.description)
        await self._ensure_name_available(normalized_name, name)

        now = self._clock()
        knowledge_base = KnowledgeBase(
            id=self._id_factory(),
            name=name,
            normalized_name=normalized_name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        await self._repository.add(knowledge_base)
        self._logger.info(
            "knowledge_base.created",
            extra={"knowledge_base_id": str(knowledge_base.id)},
        )
        return KnowledgeBaseDetail(knowledge_base, KnowledgeBaseMetrics())

    async def list(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> KnowledgeBasePage:
        if limit < 1 or limit > 100:
            raise KnowledgeBaseValidationError("每页数量必须在 1 到 100 之间")
        if offset < 0:
            raise KnowledgeBaseValidationError("分页偏移量不能小于 0")

        normalized_query = query.strip().casefold() if query and query.strip() else None
        knowledge_bases = tuple(
            await self._repository.list(query=normalized_query, limit=limit, offset=offset)
        )
        total = await self._repository.count(query=normalized_query)
        metrics_by_id = await self._metrics_reader.get_many(
            [knowledge_base.id for knowledge_base in knowledge_bases]
        )
        items = tuple(
            KnowledgeBaseDetail(
                knowledge_base,
                metrics_by_id.get(knowledge_base.id, KnowledgeBaseMetrics()),
            )
            for knowledge_base in knowledge_bases
        )
        return KnowledgeBasePage(items=items, total=total, limit=limit, offset=offset)

    async def get(self, knowledge_base_id: UUID) -> KnowledgeBaseDetail:
        knowledge_base = await self._get_or_raise(knowledge_base_id)
        metrics_by_id = await self._metrics_reader.get_many([knowledge_base_id])
        return KnowledgeBaseDetail(
            knowledge_base,
            metrics_by_id.get(knowledge_base_id, KnowledgeBaseMetrics()),
        )

    async def update(
        self,
        knowledge_base_id: UUID,
        command: UpdateKnowledgeBaseCommand,
    ) -> KnowledgeBaseDetail:
        if command.name is None and command.description is None:
            raise KnowledgeBaseValidationError("至少需要提供一个要修改的字段")

        current = await self._get_or_raise(knowledge_base_id)
        name = current.name
        normalized_name = current.normalized_name
        description = current.description

        if command.name is not None:
            name, normalized_name = normalize_knowledge_base_name(command.name)
            await self._ensure_name_available(normalized_name, name, exclude_id=knowledge_base_id)
        if command.description is not None:
            description = normalize_description(command.description)

        updated = replace(
            current,
            name=name,
            normalized_name=normalized_name,
            description=description,
            updated_at=self._clock(),
        )
        await self._repository.update(updated)
        self._logger.info(
            "knowledge_base.updated",
            extra={"knowledge_base_id": str(updated.id)},
        )
        metrics_by_id = await self._metrics_reader.get_many([knowledge_base_id])
        return KnowledgeBaseDetail(
            updated,
            metrics_by_id.get(knowledge_base_id, KnowledgeBaseMetrics()),
        )

    async def delete(self, knowledge_base_id: UUID) -> None:
        await self._get_or_raise(knowledge_base_id)
        metrics_by_id = await self._metrics_reader.get_many([knowledge_base_id])
        metrics = metrics_by_id.get(knowledge_base_id, KnowledgeBaseMetrics())
        if metrics.document_count > 0:
            # 级联删除属于文档模块的编排职责，知识库模块不能绕过该边界。
            raise KnowledgeBaseNotEmptyError(metrics.document_count)

        await self._repository.delete(knowledge_base_id)
        self._logger.info(
            "knowledge_base.deleted",
            extra={"knowledge_base_id": str(knowledge_base_id)},
        )

    async def _get_or_raise(self, knowledge_base_id: UUID) -> KnowledgeBase:
        knowledge_base = await self._repository.get(knowledge_base_id)
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError()
        return knowledge_base

    async def _ensure_name_available(
        self,
        normalized_name: str,
        display_name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        existing = await self._repository.get_by_normalized_name(normalized_name)
        if existing is not None and existing.id != exclude_id:
            raise KnowledgeBaseNameConflictError(display_name)
