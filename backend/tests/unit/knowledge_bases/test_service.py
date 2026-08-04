from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

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
from app.modules.knowledge_bases.models import KnowledgeBaseMetrics
from app.modules.knowledge_bases.service import KnowledgeBaseService
from tests.fakes.knowledge_bases import (
    FakeKnowledgeBaseMetricsReader,
    FakeKnowledgeBaseRepository,
)

FIRST_ID = UUID("11111111-1111-1111-1111-111111111111")
SECOND_ID = UUID("22222222-2222-2222-2222-222222222222")
START_TIME = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)


def build_service(
    *,
    ids: tuple[UUID, ...] = (FIRST_ID,),
) -> tuple[KnowledgeBaseService, FakeKnowledgeBaseRepository, FakeKnowledgeBaseMetricsReader]:
    repository = FakeKnowledgeBaseRepository()
    metrics_reader = FakeKnowledgeBaseMetricsReader()
    id_iterator = iter(ids)
    times = iter(
        (
            START_TIME,
            START_TIME + timedelta(minutes=5),
            START_TIME + timedelta(minutes=10),
        )
    )
    service = KnowledgeBaseService(
        repository,
        metrics_reader,
        id_factory=lambda: next(id_iterator),
        clock=lambda: next(times),
    )
    return service, repository, metrics_reader


@pytest.mark.asyncio
async def test_create_normalizes_input_and_persists_entity() -> None:
    service, repository, _ = build_service()

    detail = await service.create(
        CreateKnowledgeBaseCommand(name="  产品   文档  ", description="  产品资料  ")
    )

    assert detail.knowledge_base.id == FIRST_ID
    assert detail.knowledge_base.name == "产品 文档"
    assert detail.knowledge_base.normalized_name == "产品 文档"
    assert detail.knowledge_base.description == "产品资料"
    assert repository.items[FIRST_ID] == detail.knowledge_base


@pytest.mark.asyncio
async def test_duplicate_name_is_case_insensitive_and_does_not_create_second_entity() -> None:
    service, repository, _ = build_service(ids=(FIRST_ID, SECOND_ID))
    await service.create(CreateKnowledgeBaseCommand(name="Product Docs"))

    with pytest.raises(KnowledgeBaseNameConflictError):
        await service.create(CreateKnowledgeBaseCommand(name=" product   DOCS "))

    assert len(repository.items) == 1


@pytest.mark.asyncio
async def test_update_can_keep_name_and_clear_description() -> None:
    service, _, _ = build_service()
    created = await service.create(CreateKnowledgeBaseCommand(name="产品文档", description="说明"))

    updated = await service.update(
        created.knowledge_base.id,
        UpdateKnowledgeBaseCommand(description=""),
    )

    assert updated.knowledge_base.name == "产品文档"
    assert updated.knowledge_base.description == ""
    assert updated.knowledge_base.updated_at > updated.knowledge_base.created_at


@pytest.mark.asyncio
async def test_update_requires_at_least_one_field() -> None:
    service, _, _ = build_service()
    created = await service.create(CreateKnowledgeBaseCommand(name="产品文档"))

    with pytest.raises(KnowledgeBaseValidationError, match="至少"):
        await service.update(created.knowledge_base.id, UpdateKnowledgeBaseCommand())


@pytest.mark.asyncio
async def test_list_reads_metrics_through_batch_boundary() -> None:
    service, _, metrics_reader = build_service(ids=(FIRST_ID, SECOND_ID))
    first = await service.create(CreateKnowledgeBaseCommand(name="产品文档"))
    await service.create(CreateKnowledgeBaseCommand(name="个人笔记"))
    metrics_reader.metrics[first.knowledge_base.id] = KnowledgeBaseMetrics(
        document_count=3,
        ready_document_count=2,
        failed_document_count=1,
        chunk_count=42,
    )

    page = await service.list(query="产品", limit=20, offset=0)

    assert page.total == 1
    assert page.items[0].metrics.document_count == 3
    assert metrics_reader.requested_ids[-1] == (FIRST_ID,)


@pytest.mark.asyncio
async def test_delete_non_empty_knowledge_base_is_rejected_without_touching_repository() -> None:
    service, repository, metrics_reader = build_service()
    created = await service.create(CreateKnowledgeBaseCommand(name="产品文档"))
    metrics_reader.metrics[FIRST_ID] = KnowledgeBaseMetrics(document_count=2)

    with pytest.raises(KnowledgeBaseNotEmptyError) as error:
        await service.delete(created.knowledge_base.id)

    assert error.value.document_count == 2
    assert FIRST_ID in repository.items


@pytest.mark.asyncio
async def test_missing_knowledge_base_is_reported_by_service() -> None:
    service, _, _ = build_service()

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.get(FIRST_ID)
