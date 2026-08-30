from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.chat.tools.retrieval_tools import RetrievalToolFactory
from app.modules.retrieval.models import ChildChunkItem, ParentChunkDetail


@pytest.mark.asyncio
async def test_search_child_chunks_tool_success() -> None:
    retrieval_service = AsyncMock()
    parent_id = uuid4()
    child_id = uuid4()
    doc_id = uuid4()

    retrieval_service.search_child_chunks.return_value = (
        ChildChunkItem(
            parent_id=parent_id,
            child_id=child_id,
            document_id=doc_id,
            heading_path="Section 1",
            content="这是子块内容",
            score=0.95,
        ),
    )

    factory = RetrievalToolFactory(retrieval_service)
    tools = factory.create_tools()
    assert len(tools) == 2

    search_tool = next(t for t in tools if t.name == "search_child_chunks")
    result = await search_tool.ainvoke({"query": "测试查询", "limit": 5})

    assert f"Parent ID: {parent_id}" in result
    assert "Heading: Section 1" in result
    assert "Content: 这是子块内容" in result
    retrieval_service.search_child_chunks.assert_awaited_once_with(
        "测试查询", limit=5, knowledge_base_id=None
    )


@pytest.mark.asyncio
async def test_search_child_chunks_tool_empty() -> None:
    retrieval_service = AsyncMock()
    retrieval_service.search_child_chunks.return_value = ()

    factory = RetrievalToolFactory(retrieval_service)
    tools = factory.create_tools()
    search_tool = next(t for t in tools if t.name == "search_child_chunks")

    result = await search_tool.ainvoke({"query": "未命中查询"})
    assert result == "NO_RELEVANT_CHUNKS"


@pytest.mark.asyncio
async def test_retrieve_parent_chunks_tool_success() -> None:
    retrieval_service = AsyncMock()
    parent_id = uuid4()
    doc_id = uuid4()

    retrieval_service.get_parent_chunk.return_value = ParentChunkDetail(
        parent_id=parent_id,
        document_id=doc_id,
        heading_path="Root / Chapter 1",
        content="这是完整的父块大上下文内容...",
        char_count=500,
    )

    factory = RetrievalToolFactory(retrieval_service)
    tools = factory.create_tools()
    retrieve_tool = next(t for t in tools if t.name == "retrieve_parent_chunks")

    result = await retrieve_tool.ainvoke({"parent_id": str(parent_id)})
    assert f"Parent ID: {parent_id}" in result
    assert "Heading: Root / Chapter 1" in result
    assert "Content: 这是完整的父块大上下文内容..." in result
    retrieval_service.get_parent_chunk.assert_awaited_once_with(parent_id)


@pytest.mark.asyncio
async def test_retrieve_parent_chunks_tool_not_found() -> None:
    retrieval_service = AsyncMock()
    retrieval_service.get_parent_chunk.return_value = None

    factory = RetrievalToolFactory(retrieval_service)
    tools = factory.create_tools()
    retrieve_tool = next(t for t in tools if t.name == "retrieve_parent_chunks")

    result = await retrieve_tool.ainvoke({"parent_id": str(uuid4())})
    assert result == "NO_PARENT_DOCUMENT"


@pytest.mark.asyncio
async def test_retrieve_parent_chunks_tool_invalid_uuid() -> None:
    retrieval_service = AsyncMock()
    factory = RetrievalToolFactory(retrieval_service)
    tools = factory.create_tools()
    retrieve_tool = next(t for t in tools if t.name == "retrieve_parent_chunks")

    result = await retrieve_tool.ainvoke({"parent_id": "invalid-uuid-string"})
    assert "PARENT_RETRIEVAL_ERROR: Invalid parent_id UUID format." in result
