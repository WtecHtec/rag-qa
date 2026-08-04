from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Memory:
    """用户明确要求保存的长期事实或偏好，不与知识库文档混合。"""

    id: UUID
    memory_key: str
    content: str
    source_conversation_id: UUID
    source_message_id: UUID
    created_at: datetime
    updated_at: datetime
