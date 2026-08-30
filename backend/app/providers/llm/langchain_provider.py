import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Protocol

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from app.modules.chat.exceptions import LlmConfigurationError, LlmProviderError
from app.modules.chat.llm import LlmMessage


class AsyncChatModel(Protocol):
    """只声明项目使用的 LangChain 最小能力，测试可注入轻量替身。"""

    def astream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[AIMessageChunk]: ...


class LangChainLlmProvider:
    """把 LangChain ChatModel 适配为业务层稳定的流式文本接口。"""

    def __init__(
        self,
        chat_model: AsyncChatModel,
        *,
        model_name: str,
        provider_name: str,
        configuration_error: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._chat_model = chat_model
        self._model_name = model_name
        self._provider_name = provider_name
        self._configuration_error = configuration_error
        self._logger = logger or logging.getLogger(__name__)

    @property
    def model_name(self) -> str:
        """获取当前模型名称。"""
        return self._model_name

    @property
    def chat_model(self) -> AsyncChatModel:
        """获取底层 ChatModel 实例，用于 LangGraph 节点和工具绑定。"""
        return self._chat_model

    async def stream(self, messages: Sequence[LlmMessage]) -> AsyncIterator[str]:
        if self._configuration_error:
            raise LlmConfigurationError(self._configuration_error)
        trace_id = "-"
        from time import perf_counter

        start_time = perf_counter()
        first_token_at: float | None = None
        chunk_count = 0
        total_chars = 0
        try:
            langchain_messages = tuple(self._to_langchain_message(message) for message in messages)
            async for chunk in self._chat_model.astream(langchain_messages):
                trace_id = self._trace_id(chunk.response_metadata) or trace_id
                content = self._text_content(chunk.content)
                if content:
                    if first_token_at is None:
                        first_token_at = perf_counter()
                        ttft_ms = round((first_token_at - start_time) * 1000, 2)
                        self._logger.info(
                            "llm.first_token_received",
                            extra={
                                "provider": self._provider_name,
                                "model": self._model_name,
                                "ttft_ms": ttft_ms,
                            },
                        )
                    chunk_count += 1
                    total_chars += len(content)
                    yield content

            end_time = perf_counter()
            total_llm_latency_ms = round((end_time - start_time) * 1000, 2)
            ttft_ms = (
                round((first_token_at - start_time) * 1000, 2)
                if first_token_at
                else total_llm_latency_ms
            )
            self._logger.info(
                "llm.langchain_stream_completed",
                extra={
                    "provider": self._provider_name,
                    "model": self._model_name,
                    "provider_trace_id": trace_id,
                    "ttft_ms": ttft_ms,
                    "total_llm_latency_ms": total_llm_latency_ms,
                    "chunk_count": chunk_count,
                    "total_chars": total_chars,
                },
            )
        except LlmProviderError:
            raise
        except Exception as error:
            # 不记录消息和密钥，异常细节只保留在受控日志堆栈中。
            self._logger.exception(
                "llm.langchain_stream_failed",
                extra={
                    "provider": self._provider_name,
                    "model": self._model_name,
                    "provider_trace_id": trace_id,
                },
            )
            raise LlmProviderError("模型服务调用失败，请检查配置与服务状态") from error

    @staticmethod
    def _to_langchain_message(message: LlmMessage) -> BaseMessage:
        if message.role == "system":
            return SystemMessage(content=message.content)
        if message.role == "assistant":
            return AIMessage(content=message.content)
        return HumanMessage(content=message.content)

    @staticmethod
    def _text_content(content: str | list[str | dict[str, object]]) -> str:
        if isinstance(content, str):
            return content
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(str(item["text"]))
        return "".join(parts)

    @staticmethod
    def _trace_id(metadata: Mapping[str, object]) -> str | None:
        headers = metadata.get("headers")
        if not isinstance(headers, Mapping):
            return None
        value = headers.get("x-siliconcloud-trace-id") or headers.get("x-request-id")
        return str(value) if value else None
