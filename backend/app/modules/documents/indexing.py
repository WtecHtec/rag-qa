"""兼容导出：索引协议已归入 domain 目录。"""

from app.modules.documents.domain.indexing import (
    DocumentIndexer,
    IndexingStageCallback,
)

__all__ = ["DocumentIndexer", "IndexingStageCallback"]
