import pytest

from app.modules.knowledge_bases.exceptions import KnowledgeBaseValidationError
from app.modules.knowledge_bases.validators import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    normalize_description,
    normalize_knowledge_base_name,
)


def test_name_normalization_collapses_whitespace_and_builds_casefold_key() -> None:
    display_name, normalized_name = normalize_knowledge_base_name("  Product   DOCS  ")

    assert display_name == "Product DOCS"
    assert normalized_name == "product docs"


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_empty_name_is_rejected(value: str) -> None:
    with pytest.raises(KnowledgeBaseValidationError, match="不能为空"):
        normalize_knowledge_base_name(value)


def test_name_over_max_length_is_rejected() -> None:
    with pytest.raises(KnowledgeBaseValidationError, match="不能超过"):
        normalize_knowledge_base_name("知" * (MAX_NAME_LENGTH + 1))


def test_description_preserves_internal_line_breaks() -> None:
    assert normalize_description("  第一行\n第二行  ") == "第一行\n第二行"


def test_description_over_max_length_is_rejected() -> None:
    with pytest.raises(KnowledgeBaseValidationError, match="不能超过"):
        normalize_description("描" * (MAX_DESCRIPTION_LENGTH + 1))
