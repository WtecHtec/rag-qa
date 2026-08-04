from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.infrastructure.repositories.sqlite_knowledge_base_repository import (
    SqliteKnowledgeBaseRepository,
)
from app.modules.knowledge_bases.exceptions import KnowledgeBaseNameConflictError
from app.modules.knowledge_bases.models import KnowledgeBase

FIRST_ID = UUID("11111111-1111-1111-1111-111111111111")
SECOND_ID = UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)


def make_knowledge_base(
    knowledge_base_id: UUID,
    name: str,
    normalized_name: str,
) -> KnowledgeBase:
    return KnowledgeBase(
        id=knowledge_base_id,
        name=name,
        normalized_name=normalized_name,
        description=f"{name}的说明",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_sqlite_repository_crud_uses_isolated_temporary_database(tmp_path) -> None:
    repository = SqliteKnowledgeBaseRepository(tmp_path / "knowledge-bases.db")
    await repository.initialize()
    knowledge_base = make_knowledge_base(FIRST_ID, "产品文档", "产品文档")

    await repository.add(knowledge_base)
    loaded = await repository.get(FIRST_ID)
    items = await repository.list(query="产品", limit=10, offset=0)

    assert loaded == knowledge_base
    assert items == [knowledge_base]
    assert await repository.count(query=None) == 1

    updated = make_knowledge_base(FIRST_ID, "产品资料", "产品资料")
    await repository.update(updated)
    assert await repository.get(FIRST_ID) == updated

    await repository.delete(FIRST_ID)
    assert await repository.get(FIRST_ID) is None


@pytest.mark.asyncio
async def test_sqlite_unique_constraint_is_translated_to_domain_error(tmp_path) -> None:
    repository = SqliteKnowledgeBaseRepository(tmp_path / "knowledge-bases.db")
    await repository.initialize()
    await repository.add(make_knowledge_base(FIRST_ID, "Product Docs", "product docs"))

    with pytest.raises(KnowledgeBaseNameConflictError):
        await repository.add(make_knowledge_base(SECOND_ID, "PRODUCT DOCS", "product docs"))


@pytest.mark.asyncio
async def test_sqlite_search_treats_wildcards_as_plain_text(tmp_path) -> None:
    repository = SqliteKnowledgeBaseRepository(tmp_path / "knowledge-bases.db")
    await repository.initialize()
    await repository.add(make_knowledge_base(FIRST_ID, "百分百", "百分百"))

    assert await repository.count(query="%") == 0
