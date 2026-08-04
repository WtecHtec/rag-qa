import re
from collections.abc import Sequence

from app.modules.chat.models import Citation

CITATION_MARKER_PATTERN = re.compile(r"\[(\d+)]")


def select_cited_sources(
    content: str,
    candidates: Sequence[Citation],
) -> tuple[Citation, ...]:
    """只保留回答正文明确引用的来源，检索候选不能直接冒充回答依据。"""
    cited_numbers = {int(number) for number in CITATION_MARKER_PATTERN.findall(content)}
    return tuple(
        citation
        for citation in candidates
        if citation.citation_number in cited_numbers
    )
