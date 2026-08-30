"""兼容导出层：仓储协议已归入 domain 目录。"""

from app.modules.chat.domain.repository import ConversationRepository

__all__ = ["ConversationRepository"]
