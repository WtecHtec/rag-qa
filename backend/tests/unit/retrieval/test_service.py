from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.modules.documents.models import ChunkKind, Document, DocumentStatus, TextChunk
from app.modules.retrieval.models import Embedding, VectorHit, VectorRecord
from app.modules.retrieval.service import RetrievalService

NOW = datetime(2026, 8, 4, tzinfo=UTC)
KB_ID = UUID(int=1)
DOCUMENT_ID = UUID(int=2)
PARENT_ID = UUID(int=10)


def make_chunk(
    chunk_id: int,
    kind: ChunkKind,
    content: str,
    *,
    parent_id: UUID | None = None,
    ordinal: int = 0,
    start_offset: int = 0,
) -> TextChunk:
    return TextChunk(
        id=UUID(int=chunk_id),
        document_id=DOCUMENT_ID,
        parent_id=parent_id,
        kind=kind,
        ordinal=ordinal,
        heading_path="退款策略",
        content=content,
        char_count=len(content),
        start_offset=start_offset,
        end_offset=start_offset + len(content),
        manually_edited=False,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeChunkReader:
    def __init__(self, chunks: Sequence[TextChunk]) -> None:
        self.chunks = {chunk.id: chunk for chunk in chunks}
        self.children = [chunk for chunk in chunks if chunk.kind is ChunkKind.CHILD]

    async def list_child_chunks(
        self, document_id: UUID, *, limit: int, after_id: UUID | None
    ) -> Sequence[TextChunk]:
        assert document_id == DOCUMENT_ID
        candidates = [child for child in self.children if after_id is None or child.id > after_id]
        return candidates[:limit]

    async def get_chunks(self, chunk_ids: Sequence[UUID]) -> Mapping[UUID, TextChunk]:
        return {chunk_id: self.chunks[chunk_id] for chunk_id in chunk_ids}


class FakeKnowledgeBaseReader:
    async def get(self, knowledge_base_id: UUID) -> object | None:
        return object() if knowledge_base_id == KB_ID else None


class FakeEmbeddingProvider:
    model_name = "fake-embedding"
    dimensions = 3

    async def embed_documents(self, texts: Sequence[str]) -> Sequence[Embedding]:
        vectors = {
            "退款将在三日内到账": (1.0, 0.0, 0.0),
            "原路退回支付账户": (0.9, 0.1, 0.0),
            "退款": (1.0, 0.0, 0.0),
        }
        return [vectors[text] for text in texts]

    async def embed_query(self, text: str) -> Embedding:
        assert text == "退款"
        return (1.0, 0.0, 0.0)


class FakeVectorStore:
    def __init__(self) -> None:
        self.records: list[VectorRecord] = []

    async def delete_document(self, document_id: UUID) -> None:
        self.records = [record for record in self.records if record.document_id != document_id]

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.records.extend(records)

    async def search(
        self,
        knowledge_base_id: UUID | None,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> Sequence[VectorHit]:
        records = [
            record
            for record in self.records
            if (knowledge_base_id is None or record.knowledge_base_id == knowledge_base_id)
            and record.embedding_model == embedding_model
        ]
        scored = sorted(
            records,
            key=lambda record: sum(
                left * right for left, right in zip(record.embedding, embedding, strict=True)
            ),
            reverse=True,
        )
        return [
            VectorHit(
                child_id=record.child_id,
                parent_id=record.parent_id,
                document_id=record.document_id,
                score=sum(
                    left * right for left, right in zip(record.embedding, embedding, strict=True)
                ),
            )
            for record in scored[:limit]
        ]


@pytest.mark.asyncio
async def test_only_child_is_embedded_and_hits_are_grouped_back_to_parent() -> None:
    parent = make_chunk(10, ChunkKind.PARENT, "退款完整政策：退款将在三日内原路到账。")
    child_one = make_chunk(
        11,
        ChunkKind.CHILD,
        "退款将在三日内到账",
        parent_id=PARENT_ID,
        start_offset=6,
    )
    child_two = make_chunk(
        12,
        ChunkKind.CHILD,
        "原路退回支付账户",
        parent_id=PARENT_ID,
        ordinal=1,
        start_offset=14,
    )
    chunk_reader = FakeChunkReader([parent, child_one, child_two])
    vector_store = FakeVectorStore()
    service = RetrievalService(
        chunk_reader,
        FakeKnowledgeBaseReader(),  # type: ignore[arg-type]
        FakeEmbeddingProvider(),
        vector_store,
        embedding_batch_size=1,
    )
    document = Document(
        id=DOCUMENT_ID,
        knowledge_base_id=KB_ID,
        filename="refund.md",
        extension=".md",
        media_type="text/markdown",
        storage_key="refund.md",
        size_bytes=100,
        sha256="hash",
        status=DocumentStatus.CHUNKED,
        progress=65,
        parent_chunk_count=1,
        child_chunk_count=2,
        error_code=None,
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
    )
    indexing_events = 0

    async def on_indexing() -> None:
        nonlocal indexing_events
        indexing_events += 1

    indexed_count = await service.index_document(document, on_indexing)
    result = await service.search(KB_ID, "退款", top_k=5)

    assert indexed_count == 2
    assert indexing_events == 1
    assert {record.child_id for record in vector_store.records} == {child_one.id, child_two.id}
    assert all(record.parent_id == parent.id for record in vector_store.records)
    assert len(result.matches) == 1
    assert result.matches[0].content == parent.content
    assert len(result.matches[0].matched_children) == 2
    assert result.matches[0].matched_children[0].start_offset == 6
