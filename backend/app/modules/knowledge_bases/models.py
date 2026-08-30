"""兼容导出：领域模型已归入 domain 目录。"""

from app.modules.knowledge_bases.domain.models import (
    KnowledgeBase,
    KnowledgeBaseDetail,
    KnowledgeBaseMetrics,
    KnowledgeBasePage,
)

__all__ = [
    "KnowledgeBase",
    "KnowledgeBaseDetail",
    "KnowledgeBaseMetrics",
    "KnowledgeBasePage",
]
