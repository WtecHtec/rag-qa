"""知识库领域校验纯函数。"""

from app.modules.knowledge_bases.domain.exceptions import KnowledgeBaseValidationError

MAX_NAME_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500


def normalize_knowledge_base_name(name: str) -> tuple[str, str]:
    """校验并返回 (显示名称, 小写去重归一化名称)。"""
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        raise KnowledgeBaseValidationError("知识库名称不能为空")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise KnowledgeBaseValidationError(f"知识库名称长度不能超过 {MAX_NAME_LENGTH} 个字符")
    return cleaned, cleaned.casefold()


def normalize_description(description: str) -> str:
    """去除首尾空白并校验描述长度。"""
    cleaned = description.strip()
    if len(cleaned) > MAX_DESCRIPTION_LENGTH:
        raise KnowledgeBaseValidationError(
            f"知识库描述长度不能超过 {MAX_DESCRIPTION_LENGTH} 个字符"
        )
    return cleaned


def normalize_name(name: str) -> str:
    """兼容辅助函数。"""
    _, normalized = normalize_knowledge_base_name(name)
    return normalized


def validate_name(name: str) -> str:
    """兼容辅助函数。"""
    display, _ = normalize_knowledge_base_name(name)
    return display


def validate_description(description: str) -> str:
    """兼容辅助函数。"""
    return normalize_description(description)
