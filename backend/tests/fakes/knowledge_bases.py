from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from app.modules.knowledge_bases.exceptions import KnowledgeBaseNameConflictError
from app.modules.knowledge_bases.models import KnowledgeBase, KnowledgeBaseMetrics


class FakeKnowledgeBaseRepository:
    """用于 Service 与 API 单测的内存 Repository。"""

    def __init__(self) -> None:
        self.items: dict[UUID, KnowledgeBase] = {}

    async def add(self, knowledge_base: KnowledgeBase) -> None:
        if await self.get_by_normalized_name(knowledge_base.normalized_name):
            raise KnowledgeBaseNameConflictError(knowledge_base.name)
        self.items[knowledge_base.id] = knowledge_base

    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        return self.items.get(knowledge_base_id)

    async def get_by_normalized_name(self, normalized_name: str) -> KnowledgeBase | None:
        return next(
            (item for item in self.items.values() if item.normalized_name == normalized_name),
            None,
        )

    async def list(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[KnowledgeBase]:
        items = self._filtered(query)
        items.sort(key=lambda item: (item.updated_at, str(item.id)), reverse=True)
        return items[offset : offset + limit]

    async def count(self, *, query: str | None) -> int:
        return len(self._filtered(query))

    async def update(self, knowledge_base: KnowledgeBase) -> None:
        conflict = await self.get_by_normalized_name(knowledge_base.normalized_name)
        if conflict is not None and conflict.id != knowledge_base.id:
            raise KnowledgeBaseNameConflictError(knowledge_base.name)
        self.items[knowledge_base.id] = knowledge_base

    async def delete(self, knowledge_base_id: UUID) -> None:
        self.items.pop(knowledge_base_id, None)

    def _filtered(self, query: str | None) -> list[KnowledgeBase]:
        if query is None:
            return list(self.items.values())
        return [
            item
            for item in self.items.values()
            if query in item.normalized_name or query in item.description.casefold()
        ]


class FakeKnowledgeBaseMetricsReader:
    """通过显式字典控制文档统计，便于验证模块隔离规则。"""

    def __init__(self) -> None:
        self.metrics: dict[UUID, KnowledgeBaseMetrics] = {}
        self.requested_ids: list[tuple[UUID, ...]] = []

    async def get_many(
        self,
        knowledge_base_ids: Sequence[UUID],
    ) -> Mapping[UUID, KnowledgeBaseMetrics]:
        ids = tuple(knowledge_base_ids)
        self.requested_ids.append(ids)
        return {
            knowledge_base_id: self.metrics.get(knowledge_base_id, KnowledgeBaseMetrics())
            for knowledge_base_id in ids
        }
