"""记忆领域仓储抽象接口。"""

from collections.abc import Sequence
from typing import Protocol

from app.modules.memory.domain.models import Memory


class MemoryRepository(Protocol):
    """显式记忆持久化协议。"""

    async def upsert(self, memory: Memory) -> None: ...
    async def list_recent(self, *, limit: int) -> Sequence[Memory]: ...
