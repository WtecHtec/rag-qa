from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.memory.extractor import derive_memory_key, extract_explicit_memory
from app.modules.memory.models import Memory
from app.modules.memory.repository import MemoryRepository

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


def utc_now() -> datetime:
    return datetime.now(UTC)


class MemoryService:
    """负责显式长期记忆的提取、去重更新与 Prompt 预算控制。"""

    def __init__(
        self,
        repository: MemoryRepository,
        *,
        clock: Clock = utc_now,
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._id_factory = id_factory

    @staticmethod
    def extract(message: str) -> str | None:
        return extract_explicit_memory(message)

    async def remember(
        self,
        content: str,
        *,
        conversation_id: UUID,
        message_id: UUID,
    ) -> Memory:
        now = self._clock()
        memory = Memory(
            id=self._id_factory(),
            memory_key=derive_memory_key(content),
            content=content,
            source_conversation_id=conversation_id,
            source_message_id=message_id,
            created_at=now,
            updated_at=now,
        )
        await self._repository.upsert(memory)
        return memory

    async def list_prompt_contents(
        self,
        *,
        limit: int = 20,
        max_chars: int = 3000,
    ) -> tuple[str, ...]:
        """按完整条目控制预算，避免在半句话处截断并改变记忆含义。"""
        memories = await self._repository.list_recent(limit=limit)
        selected: list[str] = []
        used_chars = 0
        for memory in memories:
            required = len(memory.content)
            if used_chars + required > max_chars:
                continue
            selected.append(memory.content)
            used_chars += required
        return tuple(selected)
