"""兼容导出：命令数据载体已归入 domain 目录。"""

from app.modules.knowledge_bases.domain.commands import (
    CreateKnowledgeBaseCommand,
    UpdateKnowledgeBaseCommand,
)

__all__ = ["CreateKnowledgeBaseCommand", "UpdateKnowledgeBaseCommand"]
