"""知识库领域仓储与统计读取协议接口。"""

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from app.modules.knowledge_bases.domain.models import KnowledgeBase, KnowledgeBaseMetrics


class KnowledgeBaseRepository(Protocol):
    """知识库持久化协议，业务层只依赖此抽象接口。"""

    async def add(self, knowledge_base: KnowledgeBase) -> None: ...
    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None: ...
    async def get_by_normalized_name(self, normalized_name: str) -> KnowledgeBase | None: ...
    async def list(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[KnowledgeBase]: ...
    async def count(self, *, query: str | None) -> int: ...
    async def update(self, knowledge_base: KnowledgeBase) -> None: ...
    async def delete(self, knowledge_base_id: UUID) -> None: ...


class KnowledgeBaseMetricsReader(Protocol):
    """文档统计读取端口，批量接口避免知识库列表 N+1 查询。"""

    async def get_many(
        self,
        knowledge_base_ids: Sequence[UUID],
    ) -> Mapping[UUID, KnowledgeBaseMetrics]: ...


class EmptyKnowledgeBaseMetricsReader:
    """空统计实现替身。"""

    async def get_many(
        self,
        knowledge_base_ids: Sequence[UUID],
    ) -> Mapping[UUID, KnowledgeBaseMetrics]:
        return {
            knowledge_base_id: KnowledgeBaseMetrics() for knowledge_base_id in knowledge_base_ids
        }
