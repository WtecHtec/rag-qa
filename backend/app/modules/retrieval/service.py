import hashlib
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.modules.documents.indexing import IndexingStageCallback
from app.modules.documents.models import ChunkKind, Document
from app.modules.documents.repository import KnowledgeBaseReader
from app.modules.retrieval.embedding import EmbeddingProvider
from app.modules.retrieval.exceptions import EmbeddingProviderError, RetrievalValidationError
from app.modules.retrieval.models import (
    MatchedChild,
    ParentSearchMatch,
    VectorHit,
    VectorRecord,
    VectorSearchResult,
)
from app.modules.retrieval.repository import RetrievalChunkReader
from app.modules.retrieval.vector_store import VectorStore

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


class RetrievalService:
    """负责 Child 向量化，以及命中 Child 后聚合回取 Parent。"""

    def __init__(
        self,
        chunk_reader: RetrievalChunkReader,
        knowledge_base_reader: KnowledgeBaseReader,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        embedding_batch_size: int = 64,
        clock: Clock = utc_now,
        logger: logging.Logger | None = None,
    ) -> None:
        if embedding_batch_size < 1:
            raise ValueError("Embedding 批次必须大于 0")
        self._chunk_reader = chunk_reader
        self._knowledge_base_reader = knowledge_base_reader
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._embedding_batch_size = embedding_batch_size
        self._clock = clock
        self._logger = logger or logging.getLogger(__name__)

    async def index_document(
        self,
        document: Document,
        on_indexing: IndexingStageCallback,
    ) -> int:
        await self._vector_store.delete_document(document.id)
        after_id: UUID | None = None
        indexed_count = 0
        indexing_stage_started = False
        try:
            while True:
                children = await self._chunk_reader.list_child_chunks(
                    document.id,
                    limit=self._embedding_batch_size,
                    after_id=after_id,
                )
                if not children:
                    break
                if any(
                    child.kind is not ChunkKind.CHILD or child.parent_id is None
                    for child in children
                ):
                    raise RetrievalValidationError("向量索引只能接收带 parent_id 的 Child")
                embeddings = await self._embedding_provider.embed_documents(
                    [child.content for child in children]
                )
                self._validate_embeddings(embeddings, len(children))
                if not indexing_stage_started:
                    await on_indexing()
                    indexing_stage_started = True
                records = tuple(
                    VectorRecord(
                        knowledge_base_id=document.knowledge_base_id,
                        document_id=document.id,
                        child_id=child.id,
                        parent_id=child.parent_id,
                        embedding_model=self._embedding_provider.model_name,
                        embedding=embedding,
                        content_hash=hashlib.sha256(child.content.encode("utf-8")).hexdigest(),
                        updated_at=self._clock(),
                    )
                    for child, embedding in zip(children, embeddings, strict=True)
                )
                await self._vector_store.upsert(records)
                indexed_count += len(records)
                after_id = children[-1].id
            if indexed_count == 0:
                raise RetrievalValidationError("文档没有可用于 Embedding 的 Child")
        except Exception:
            # 失败索引必须清空，避免搜索读到只有部分批次的文档。
            await self._vector_store.delete_document(document.id)
            raise

        self._logger.info(
            "retrieval.document_indexed",
            extra={
                "document_id": str(document.id),
                "embedding_model": self._embedding_provider.model_name,
                "vector_count": indexed_count,
            },
        )
        return indexed_count

    async def delete_document(self, document_id: UUID) -> None:
        await self._vector_store.delete_document(document_id)

    async def search(
        self,
        knowledge_base_id: UUID,
        query: str,
        *,
        top_k: int,
    ) -> VectorSearchResult:
        normalized_query = query.strip()
        if not normalized_query or len(normalized_query) > 2000:
            raise RetrievalValidationError("查询不能为空且不能超过 2000 个字符")
        if top_k < 1 or top_k > 20:
            raise RetrievalValidationError("top_k 必须在 1 到 20 之间")
        if await self._knowledge_base_reader.get(knowledge_base_id) is None:
            raise RetrievalValidationError("知识库不存在或已被删除")

        return await self._search_scope(
            normalized_query,
            top_k=top_k,
            knowledge_base_id=knowledge_base_id,
        )

    async def search_all(
        self,
        query: str,
        *,
        top_k: int,
    ) -> VectorSearchResult:
        """跨全部知识库搜索，供不绑定知识库的自然语言会话使用。"""
        normalized_query = query.strip()
        if not normalized_query or len(normalized_query) > 2000:
            raise RetrievalValidationError("查询不能为空且不能超过 2000 个字符")
        if top_k < 1 or top_k > 20:
            raise RetrievalValidationError("top_k 必须在 1 到 20 之间")
        return await self._search_scope(
            normalized_query,
            top_k=top_k,
            knowledge_base_id=None,
        )

    async def _search_scope(
        self,
        normalized_query: str,
        *,
        top_k: int,
        knowledge_base_id: UUID | None,
    ) -> VectorSearchResult:

        from time import perf_counter

        start_time = perf_counter()
        query_embedding = await self._embedding_provider.embed_query(normalized_query)
        embed_time = perf_counter()
        embedding_latency_ms = round((embed_time - start_time) * 1000, 2)

        self._validate_embeddings((query_embedding,), 1)
        # 多取 Child 候选，再按 parent_id 聚合，避免同一 Parent 占满结果。
        hits = await self._vector_store.search(
            knowledge_base_id,
            query_embedding,
            embedding_model=self._embedding_provider.model_name,
            limit=min(100, top_k * 4),
        )
        lancedb_time = perf_counter()
        vector_store_latency_ms = round((lancedb_time - embed_time) * 1000, 2)

        chunk_ids = tuple(
            dict.fromkeys([hit.parent_id for hit in hits] + [hit.child_id for hit in hits])
        )
        chunks = await self._chunk_reader.get_chunks(chunk_ids)
        grouped_hits: dict[UUID, list[VectorHit]] = defaultdict(list)
        for hit in hits:
            if hit.score > 0:
                grouped_hits[hit.parent_id].append(hit)

        matches: list[ParentSearchMatch] = []
        for parent_id, parent_hits in grouped_hits.items():
            parent = chunks.get(parent_id)
            if parent is None or parent.kind is not ChunkKind.PARENT:
                continue
            matched_children = tuple(
                MatchedChild(
                    child_id=hit.child_id,
                    ordinal=child.ordinal,
                    preview=child.content[:240],
                    start_offset=child.start_offset,
                    end_offset=child.end_offset,
                    score=hit.score,
                )
                for hit in sorted(parent_hits, key=lambda item: -item.score)
                if (child := chunks.get(hit.child_id)) is not None and child.kind is ChunkKind.CHILD
            )
            if not matched_children:
                continue
            matches.append(
                ParentSearchMatch(
                    parent_id=parent.id,
                    document_id=parent.document_id,
                    heading_path=parent.heading_path,
                    content=parent.content,
                    score=max(child.score for child in matched_children),
                    matched_children=matched_children,
                )
            )
        matches.sort(key=lambda item: (-item.score, str(item.parent_id)))
        result = VectorSearchResult(
            query=normalized_query,
            embedding_model=self._embedding_provider.model_name,
            matches=tuple(matches[:top_k]),
        )
        total_latency_ms = round((perf_counter() - start_time) * 1000, 2)
        self._logger.info(
            "retrieval.vector_searched",
            extra={
                "knowledge_base_id": (
                    str(knowledge_base_id) if knowledge_base_id is not None else "all"
                ),
                "child_hit_count": len(hits),
                "parent_match_count": len(result.matches),
                "embedding_latency_ms": embedding_latency_ms,
                "vector_store_latency_ms": vector_store_latency_ms,
                "total_retrieval_latency_ms": total_latency_ms,
            },
        )
        return result

    def _validate_embeddings(self, embeddings: Sequence[tuple[float, ...]], expected: int) -> None:
        if len(embeddings) != expected:
            raise EmbeddingProviderError("Embedding Provider 返回数量与输入不一致")
        if any(len(item) != self._embedding_provider.dimensions for item in embeddings):
            raise EmbeddingProviderError("Embedding Provider 返回维度不一致")
