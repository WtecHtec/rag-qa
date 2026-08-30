"""兼容导出：文档异常已归入 domain 目录。"""

from app.modules.documents.domain.exceptions import (
    DocumentDecodeError,
    DocumentDuplicateError,
    DocumentError,
    DocumentNotFoundError,
    DocumentTooLargeError,
    DocumentValidationError,
    TextChunkNotFoundError,
)

__all__ = [
    "DocumentDecodeError",
    "DocumentDuplicateError",
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentTooLargeError",
    "DocumentValidationError",
    "TextChunkNotFoundError",
]
