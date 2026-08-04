from dataclasses import replace
from uuid import UUID

from app.modules.chat.citation_selector import select_cited_sources
from app.modules.chat.models import Citation


def make_citation(number: int) -> Citation:
    return Citation(
        id=UUID(int=number),
        message_id=UUID(int=100),
        knowledge_base_id=UUID(int=200),
        document_id=UUID(int=300),
        parent_id=UUID(int=400),
        child_id=UUID(int=500),
        citation_number=number,
        document_name=f"文档 {number}.md",
        heading_path="正文",
        parent_content="父块",
        child_preview="子块",
        child_start_offset=0,
        child_end_offset=2,
        score=0.9,
    )


def test_only_sources_explicitly_cited_by_answer_are_selected() -> None:
    candidates = (make_citation(1), make_citation(2), make_citation(3))

    selected = select_cited_sources("依据 [1]，并结合 [3] 可以确认。再次参考 [1]。", candidates)

    assert selected == (candidates[0], candidates[2])


def test_retrieval_candidates_are_hidden_when_answer_has_no_marker() -> None:
    candidate = replace(make_citation(1), document_name="仅检索到但未使用.md")

    assert select_cited_sources("这是没有引用标记的回答。", (candidate,)) == ()
