from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Sequence
from uuid import UUID, uuid4

from langchain_core.documents import Document as LcDocument
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.modules.documents.exceptions import DocumentDecodeError
from app.modules.documents.models import ChunkKind, TextChunk

IdFactory = Callable[[], UUID]

DEFAULT_HEADERS_TO_SPLIT_ON = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
]


class ParentChildTextChunker:
    """参考 Agentic RAG 的结构化父子切分器：

    1. 基于 MarkdownHeaderTextSplitter 保持章节语义完整性
    2. 小父块自适应合并（__merge_small_parents）与超大父块安全拆分（__split_large_parents）
    3. 基于 RecursiveCharacterTextSplitter 生成细粒度子块并精确记录父子映射与字符偏移
    """

    def __init__(
        self,
        *,
        parent_chars: int | None = None,
        min_parent_chars: int = 400,
        max_parent_chars: int = 3000,
        child_chars: int = 500,
        child_overlap_chars: int = 50,
        headers_to_split_on: Sequence[tuple[str, str]] | None = None,
        id_factory: IdFactory = uuid4,
    ) -> None:
        if parent_chars is not None:
            max_parent_chars = parent_chars
            min_parent_chars = min(min_parent_chars, max_parent_chars // 2 or 1)

        if min_parent_chars <= 0 or max_parent_chars < min_parent_chars:
            raise ValueError("父块大小配置无效：min_parent_chars 必须大于 0 且小于等于 max_parent_chars")
        if not 0 <= child_overlap_chars < child_chars:
            raise ValueError("子块重叠长度必须小于子块长度")

        self._min_parent_chars = min_parent_chars
        self._max_parent_chars = max_parent_chars
        self._child_chars = child_chars
        self._child_overlap_chars = child_overlap_chars
        self._id_factory = id_factory

        self._parent_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=list(headers_to_split_on or DEFAULT_HEADERS_TO_SPLIT_ON),
            strip_headers=False,
        )
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_chars,
            chunk_overlap=child_overlap_chars,
        )

    @property
    def parent_chars(self) -> int:
        return self._max_parent_chars

    @property
    def child_chars(self) -> int:
        return self._child_chars

    @staticmethod
    def _merge_metadata(
        target: dict[str, str], source: dict[str, str], *, prepend: bool = False
    ) -> None:
        for key, value in source.items():
            if key not in target:
                target[key] = value
            else:
                first, second = (value, target[key]) if prepend else (target[key], value)
                values = [
                    item.strip()
                    for raw in (first, second)
                    for item in str(raw).split(" -> ")
                    if item.strip()
                ]
                target[key] = " -> ".join(dict.fromkeys(values))

    def iter_chunks(
        self,
        document_id: UUID,
        path: Path,
        extension: str,
        now: datetime,
    ) -> Iterator[TextChunk]:
        """读取文件并生成两阶段父子块序列。"""
        try:
            raw_text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentDecodeError() from error

        if not raw_text.strip():
            return iter(())

        # 1. 提取父块初稿
        if extension.lower() in (".md", ".markdown"):
            raw_parent_docs = self._parent_splitter.split_text(raw_text)
        else:
            raw_parent_docs = [LcDocument(page_content=raw_text, metadata={})]

        # 2. 合并过小父块 & 拆分超大父块
        merged_parents = self._merge_small_parents(raw_parent_docs)
        split_parents = self._split_large_parents(merged_parents)
        cleaned_parents = self._clean_small_chunks(split_parents)

        # 3. 产出 Parent 与 Child TextChunk 实体
        output_chunks: list[TextChunk] = []
        parent_ordinal = 0

        for p_doc in cleaned_parents:
            parent_content = p_doc.page_content.strip()
            if not parent_content:
                continue

            parent_id = self._id_factory()
            heading_path = " / ".join(
                str(v) for v in p_doc.metadata.values() if isinstance(v, str)
            )

            parent_chunk = TextChunk(
                id=parent_id,
                document_id=document_id,
                parent_id=None,
                kind=ChunkKind.PARENT,
                ordinal=parent_ordinal,
                heading_path=heading_path,
                content=parent_content,
                char_count=len(parent_content),
                start_offset=0,
                end_offset=len(parent_content),
                manually_edited=False,
                created_at=now,
                updated_at=now,
            )
            output_chunks.append(parent_chunk)
            parent_ordinal += 1

            # 切分子块
            for child_ordinal, (start_offset, end_offset, child_content) in enumerate(
                self.iter_child_spans(parent_content)
            ):
                output_chunks.append(
                    TextChunk(
                        id=self._id_factory(),
                        document_id=document_id,
                        parent_id=parent_id,
                        kind=ChunkKind.CHILD,
                        ordinal=child_ordinal,
                        heading_path=heading_path,
                        content=child_content,
                        char_count=len(child_content),
                        start_offset=start_offset,
                        end_offset=end_offset,
                        manually_edited=False,
                        created_at=now,
                        updated_at=now,
                    )
                )

        return iter(output_chunks)

    def _merge_small_parents(self, chunks: list[LcDocument]) -> list[LcDocument]:
        if not chunks:
            return []
        merged: list[LcDocument] = []
        current: LcDocument | None = None

        for chunk in chunks:
            if current is None:
                current = LcDocument(
                    page_content=chunk.page_content, metadata=dict(chunk.metadata)
                )
            else:
                current.page_content += "\n\n" + chunk.page_content
                self._merge_metadata(current.metadata, chunk.metadata)

            if len(current.page_content) >= self._min_parent_chars:
                merged.append(current)
                current = None

        if current:
            if merged:
                merged[-1].page_content += "\n\n" + current.page_content
                self._merge_metadata(merged[-1].metadata, current.metadata)
            else:
                merged.append(current)

        return merged

    def _split_large_parents(self, chunks: list[LcDocument]) -> list[LcDocument]:
        split_chunks: list[LcDocument] = []
        for chunk in chunks:
            if len(chunk.page_content) <= self._max_parent_chars:
                split_chunks.append(chunk)
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self._max_parent_chars,
                    chunk_overlap=self._child_overlap_chars,
                )
                sub_chunks = splitter.split_documents([chunk])
                split_chunks.extend(sub_chunks)
        return split_chunks

    def _clean_small_chunks(self, chunks: list[LcDocument]) -> list[LcDocument]:
        cleaned: list[LcDocument] = []
        for i, chunk in enumerate(chunks):
            if len(chunk.page_content) < self._min_parent_chars:
                if (
                    cleaned
                    and len(cleaned[-1].page_content) + 2 + len(chunk.page_content)
                    <= self._max_parent_chars
                ):
                    cleaned[-1].page_content += "\n\n" + chunk.page_content
                    self._merge_metadata(cleaned[-1].metadata, chunk.metadata)
                elif (
                    i < len(chunks) - 1
                    and len(chunk.page_content) + 2 + len(chunks[i + 1].page_content)
                    <= self._max_parent_chars
                ):
                    chunks[i + 1].page_content = (
                        chunk.page_content + "\n\n" + chunks[i + 1].page_content
                    )
                    self._merge_metadata(
                        chunks[i + 1].metadata, chunk.metadata, prepend=True
                    )
                else:
                    cleaned.append(chunk)
            else:
                cleaned.append(chunk)
        return cleaned

    def iter_child_spans(self, content: str) -> Iterator[tuple[int, int, str]]:
        """计算子块在父块中的真实字符起止区间与内容。"""
        child_docs = self._child_splitter.split_text(content)
        cursor = 0
        for child_text in child_docs:
            child_text_stripped = child_text.strip()
            if not child_text_stripped:
                continue
            idx = content.find(child_text_stripped, cursor)
            if idx == -1:
                idx = content.find(child_text_stripped)
            start = idx if idx != -1 else cursor
            end = start + len(child_text_stripped)
            yield start, end, child_text_stripped
            cursor = max(cursor, start + 1)
