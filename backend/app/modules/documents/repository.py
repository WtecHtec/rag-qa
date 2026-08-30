"""兼容导出：仓储协议已归入 domain 目录。"""

from app.modules.documents.domain.repository import (
    DocumentRepository,
    KnowledgeBaseReader,
)

__all__ = ["DocumentRepository", "KnowledgeBaseReader"]
