from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.modules.documents.models import ChunkKind
from app.providers.chunking.text_chunker import ParentChildTextChunker


class SequentialIdFactory:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self) -> UUID:
        self._value += 1
        return UUID(int=self._value)


def test_markdown_heading_becomes_parent_context(tmp_path: Path) -> None:
    source = tmp_path / "design.md"
    source.write_text("# 架构\n第一段详细内容。\n## 存储\n第二段详细内容。", encoding="utf-8")
    chunker = ParentChildTextChunker(
        min_parent_chars=10,
        max_parent_chars=200,
        child_chars=20,
        child_overlap_chars=2,
        id_factory=SequentialIdFactory(),
    )

    chunks = list(
        chunker.iter_chunks(UUID(int=99), source, ".md", datetime(2026, 8, 4, tzinfo=UTC))
    )
    parents = [chunk for chunk in chunks if chunk.kind is ChunkKind.PARENT]
    children = [chunk for chunk in chunks if chunk.kind is ChunkKind.CHILD]

    assert len(parents) >= 1
    assert all(parent.char_count <= 200 for parent in parents)
    assert len(children) >= 1
    assert all(child.parent_id is not None for child in children)


def test_repeated_child_text_keeps_its_real_parent_offset() -> None:
    chunker = ParentChildTextChunker(
        min_parent_chars=10,
        max_parent_chars=100,
        child_chars=10,
        child_overlap_chars=0,
        id_factory=SequentialIdFactory(),
    )

    spans = list(chunker.iter_child_spans("重复文本内容。重复文本内容。"))

    assert len(spans) >= 2
    assert spans[0][0] == 0


def test_single_huge_line_is_split_without_building_file_sized_parent(tmp_path: Path) -> None:
    source = tmp_path / "huge.txt"
    source.write_text("很" * 4_000, encoding="utf-8")
    chunker = ParentChildTextChunker(
        min_parent_chars=200,
        max_parent_chars=1_000,
        child_chars=300,
        child_overlap_chars=30,
        id_factory=SequentialIdFactory(),
    )

    chunks = list(
        chunker.iter_chunks(UUID(int=88), source, ".txt", datetime(2026, 8, 4, tzinfo=UTC))
    )
    parents = [chunk for chunk in chunks if chunk.kind is ChunkKind.PARENT]
    children = [chunk for chunk in chunks if chunk.kind is ChunkKind.CHILD]

    assert len(parents) >= 4
    assert max(parent.char_count for parent in parents) <= 1_000
    assert len(children) > len(parents)
    assert max(child.char_count for child in children) <= 300


def test_default_parent_and_child_limits_match_rag_strategy(tmp_path: Path) -> None:
    source = tmp_path / "default.txt"
    source.write_text("向量检索需要稳定边界。" * 500, encoding="utf-8")
    chunker = ParentChildTextChunker(id_factory=SequentialIdFactory())

    chunks = list(
        chunker.iter_chunks(UUID(int=77), source, ".txt", datetime(2026, 8, 4, tzinfo=UTC))
    )
    parents = [chunk for chunk in chunks if chunk.kind is ChunkKind.PARENT]
    children = [chunk for chunk in chunks if chunk.kind is ChunkKind.CHILD]

    assert max(parent.char_count for parent in parents) <= 3_000
    assert max(child.char_count for child in children) <= 500
    assert all(child.parent_id is not None for child in children)
    assert len(children) >= len(parents)
