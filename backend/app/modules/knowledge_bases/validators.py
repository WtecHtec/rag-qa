import re

from app.modules.knowledge_bases.exceptions import KnowledgeBaseValidationError

MAX_NAME_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 500
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_knowledge_base_name(value: str) -> tuple[str, str]:
    """返回适合展示和唯一性比较的名称，统一空白但保留原有语言。"""

    display_name = _WHITESPACE_PATTERN.sub(" ", value).strip()
    if not display_name:
        raise KnowledgeBaseValidationError("知识库名称不能为空")
    if len(display_name) > MAX_NAME_LENGTH:
        raise KnowledgeBaseValidationError(f"知识库名称不能超过 {MAX_NAME_LENGTH} 个字符")
    return display_name, display_name.casefold()


def normalize_description(value: str) -> str:
    """描述只清理首尾空白，内部换行属于用户内容，需要保留。"""

    description = value.strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise KnowledgeBaseValidationError(f"知识库描述不能超过 {MAX_DESCRIPTION_LENGTH} 个字符")
    return description
