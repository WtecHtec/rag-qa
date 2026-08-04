from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.documents.exceptions import DocumentDecodeError
from app.modules.documents.models import ChunkKind, TextChunk

IdFactory = Callable[[], UUID]
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BOUNDARY_CHARACTERS = frozenset("。！？!?；;\n")


class ParentChildTextChunker:
    """按流式段落生成父子块，内存上限由单个 Parent 大小决定而非文件大小。"""

    def __init__(
        self,
        *,
        parent_chars: int = 3000,
        child_chars: int = 500,
        child_overlap_chars: int = 50,
        id_factory: IdFactory = uuid4,
    ) -> None:
        if child_overlap_chars >= child_chars:
            raise ValueError("子块重叠长度必须小于子块长度")
        self._parent_chars = parent_chars
        self._child_chars = child_chars
        self._child_overlap_chars = child_overlap_chars
        self._id_factory = id_factory

    @property
    def parent_chars(self) -> int:
        return self._parent_chars

    @property
    def child_chars(self) -> int:
        return self._child_chars

    def iter_chunks(
        self,
        document_id: UUID,
        path: Path,
        extension: str,
        now: datetime,
    ) -> Iterator[TextChunk]:
        try:
            with path.open("r", encoding="utf-8-sig", newline=None) as source:
                yield from self._iter_source(document_id, source, extension, now)
        except UnicodeDecodeError as error:
            raise DocumentDecodeError() from error

    def _iter_source(
        self,
        document_id: UUID,
        source: Iterator[str],
        extension: str,
        now: datetime,
    ) -> Iterator[TextChunk]:
        heading_stack: list[str] = []
        buffer: list[str] = []
        buffer_length = 0
        buffer_heading_path = ""
        parent_ordinal = 0

        def flush() -> Iterator[TextChunk]:
            nonlocal buffer, buffer_length, buffer_heading_path, parent_ordinal
            content = "".join(buffer).strip()
            buffer = []
            buffer_length = 0
            heading_path = buffer_heading_path
            buffer_heading_path = ""
            if not content:
                return iter(())
            parent_id = self._id_factory()
            parent = TextChunk(
                id=parent_id,
                document_id=document_id,
                parent_id=None,
                kind=ChunkKind.PARENT,
                ordinal=parent_ordinal,
                heading_path=heading_path,
                content=content,
                char_count=len(content),
                start_offset=0,
                end_offset=len(content),
                manually_edited=False,
                created_at=now,
                updated_at=now,
            )
            parent_ordinal += 1
            output = [parent]
            # Child 序号只在所属 Parent 内递增，便于局部重切和页面展示。
            for child_ordinal, (start_offset, end_offset, child_content) in enumerate(
                self.iter_child_spans(content)
            ):
                output.append(
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
            return iter(output)

        for line in source:
            heading = HEADING_PATTERN.match(line) if extension == ".md" else None
            if heading:
                level = len(heading.group(1))
                heading_stack[level - 1 :] = [heading.group(2).strip()]

            # 标题只更新层级并保留在正文中，不立即结束 Parent；这样相邻短章节
            # 会聚合成更大的上下文块，避免 Parent/Child 大面积完全相同。
            remaining = line
            while remaining:
                if buffer_length == 0:
                    buffer_heading_path = " / ".join(heading_stack)
                capacity = self._parent_chars - buffer_length
                if capacity <= 0:
                    yield from flush()
                    capacity = self._parent_chars
                part = remaining[:capacity]
                buffer.append(part)
                buffer_length += len(part)
                remaining = remaining[capacity:]
                if buffer_length >= self._parent_chars:
                    yield from flush()

        yield from flush()

    def iter_child_contents(self, content: str) -> Iterator[str]:
        """按相同策略重切单个 Parent，供人工编辑后的局部同步复用。"""
        for _, _, child_content in self.iter_child_spans(content):
            yield child_content

    def iter_child_spans(self, content: str) -> Iterator[tuple[int, int, str]]:
        """返回 Child 的真实父块区间，避免展示层通过重复文本反推命中位置。"""
        start = 0
        content_length = len(content)
        while start < content_length:
            hard_end = min(start + self._child_chars, content_length)
            end = self._find_boundary(content, start, hard_end)
            raw_child = content[start:end]
            leading_whitespace = len(raw_child) - len(raw_child.lstrip())
            trailing_whitespace = len(raw_child) - len(raw_child.rstrip())
            child_start = start + leading_whitespace
            child_end = end - trailing_whitespace
            if child_start < child_end:
                yield child_start, child_end, content[child_start:child_end]
            if end >= content_length:
                break
            start = max(end - self._child_overlap_chars, start + 1)

    @staticmethod
    def _find_boundary(content: str, start: int, hard_end: int) -> int:
        if hard_end >= len(content):
            return len(content)
        lower_bound = start + int((hard_end - start) * 0.65)
        for index in range(hard_end - 1, lower_bound - 1, -1):
            if content[index] in BOUNDARY_CHARACTERS:
                return index + 1
        return hard_end
