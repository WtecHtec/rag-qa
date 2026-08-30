"""兼容导出：校验函数与常量已归入 domain 目录。"""

from app.modules.knowledge_bases.domain.validators import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    normalize_description,
    normalize_knowledge_base_name,
    normalize_name,
    validate_description,
    validate_name,
)

__all__ = [
    "MAX_DESCRIPTION_LENGTH",
    "MAX_NAME_LENGTH",
    "normalize_description",
    "normalize_knowledge_base_name",
    "normalize_name",
    "validate_description",
    "validate_name",
]
