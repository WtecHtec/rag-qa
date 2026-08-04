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
    source.write_text("# 架构\n第一段。\n## 存储\n第二段。", encoding="utf-8")
    chunker = ParentChildTextChunker(
        parent_chars=100,
        child_chars=12,
        child_overlap_chars=2,
        id_factory=SequentialIdFactory(),
    )

    chunks = list(
        chunker.iter_chunks(UUID(int=99), source, ".md", datetime(2026, 8, 4, tzinfo=UTC))
    )
    parents = [chunk for chunk in chunks if chunk.kind is ChunkKind.PARENT]
    children = [chunk for chunk in chunks if chunk.kind is ChunkKind.CHILD]

    assert [parent.heading_path for parent in parents] == ["架构"]
    assert "# 架构" in parents[0].content
    assert "## 存储" in parents[0].content
    assert all(parent.char_count <= 100 for parent in parents)
    assert len(children) > 1
    assert all(child.parent_id == parents[0].id for child in children)
    assert all(child.content != parents[0].content for child in children)
    assert all(
        parents[0].content[child.start_offset : child.end_offset] == child.content
        for child in children
    )


def test_repeated_child_text_keeps_its_real_parent_offset() -> None:
    chunker = ParentChildTextChunker(
        parent_chars=100,
        child_chars=5,
        child_overlap_chars=0,
        id_factory=SequentialIdFactory(),
    )

    spans = list(chunker.iter_child_spans("重复文本。重复文本。"))

    assert spans == [
        (0, 5, "重复文本。"),
        (5, 10, "重复文本。"),
    ]


def test_short_parent_keeps_one_child_for_embedding_fallback() -> None:
    chunker = ParentChildTextChunker(
        parent_chars=100,
        child_chars=30,
        child_overlap_chars=5,
        id_factory=SequentialIdFactory(),
    )

    short_content = "短 Parent 仍需一个可向量化的 Child。"
    assert list(chunker.iter_child_contents(short_content)) == [short_content]
    children = list(chunker.iter_child_contents("需要拆分的长 Parent。" * 6))
    assert len(children) > 1
    assert all(child != "需要拆分的长 Parent。" * 6 for child in children)


def test_single_huge_line_is_split_without_building_file_sized_parent(tmp_path: Path) -> None:
    source = tmp_path / "huge.txt"
    source.write_text("很" * 15_500, encoding="utf-8")
    chunker = ParentChildTextChunker(
        parent_chars=1_000,
        child_chars=300,
        child_overlap_chars=30,
        id_factory=SequentialIdFactory(),
    )

    chunks = list(
        chunker.iter_chunks(UUID(int=88), source, ".txt", datetime(2026, 8, 4, tzinfo=UTC))
    )
    parents = [chunk for chunk in chunks if chunk.kind is ChunkKind.PARENT]
    children = [chunk for chunk in chunks if chunk.kind is ChunkKind.CHILD]

    assert len(parents) == 16
    assert max(parent.char_count for parent in parents) == 1_000
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
