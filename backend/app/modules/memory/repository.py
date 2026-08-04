from collections.abc import Sequence
from typing import Protocol

from app.modules.memory.models import Memory


class MemoryRepository(Protocol):
    async def upsert(self, memory: Memory) -> None: ...
    async def list_recent(self, *, limit: int) -> Sequence[Memory]: ...
