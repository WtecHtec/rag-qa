from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: str
    content: str


class LlmProvider(Protocol):
    """LLM Provider 只暴露流式文本，业务层不依赖厂商响应格式。"""

    @property
    def model_name(self) -> str: ...

    def stream(self, messages: Sequence[LlmMessage]) -> AsyncIterator[str]: ...
