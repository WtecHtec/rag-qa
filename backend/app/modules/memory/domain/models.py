"""记忆领域实体与值对象。"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Memory:
    """用户显式长期记忆实体。"""

    id: UUID
    memory_key: str
    content: str
    source_conversation_id: UUID
    source_message_id: UUID
    created_at: datetime
    updated_at: datetime
