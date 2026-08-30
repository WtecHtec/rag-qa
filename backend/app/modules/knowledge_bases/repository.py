"""兼容导出：仓储协议已归入 domain 目录。"""

from app.modules.knowledge_bases.domain.repository import (
    EmptyKnowledgeBaseMetricsReader,
    KnowledgeBaseMetricsReader,
    KnowledgeBaseRepository,
)

__all__ = [
    "EmptyKnowledgeBaseMetricsReader",
    "KnowledgeBaseMetricsReader",
    "KnowledgeBaseRepository",
]
