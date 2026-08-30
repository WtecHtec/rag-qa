"""Chat 领域大语言模型 Provider 抽象接口。"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LlmMessage:
    """统一模型消息载体，隔离不同厂商的消息结构差异。"""

    role: str
    content: str


class LlmProvider(Protocol):
    """LLM Provider 领域抽象端口，既暴露稳定流式文本，又为 LangGraph 节点提供统合模型访问。"""

    @property
    def model_name(self) -> str:
        """模型名称标识。"""
        ...

    @property
    def chat_model(self) -> Any:
        """底层统一的 BaseChatModel 实例，用于 LangGraph 节点的 bind_tools 与结构化输出。"""
        ...

    def stream(self, messages: Sequence[LlmMessage]) -> AsyncIterator[str]:
        """异步流式输出生成文本。"""
        ...
