from collections.abc import AsyncIterator, Sequence

import pytest
from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage, SystemMessage

from app.modules.chat.exceptions import LlmConfigurationError
from app.modules.chat.llm import LlmMessage
from app.providers.llm.factory import LlmRuntimeConfig, build_openai_compatible_provider
from app.providers.llm.langchain_provider import LangChainLlmProvider


class FakeChatModel:
    def __init__(self) -> None:
        self.requests: list[Sequence[BaseMessage]] = []

    async def astream(
        self,
        messages: Sequence[BaseMessage],
    ) -> AsyncIterator[AIMessageChunk]:
        self.requests.append(messages)
        yield AIMessageChunk(content="你好")
        yield AIMessageChunk(
            content=[{"type": "text", "text": "，[1]"}],
            response_metadata={
                "headers": {"x-siliconcloud-trace-id": "provider-trace"}
            },
        )


@pytest.mark.asyncio
async def test_langchain_provider_streams_text_and_converts_roles() -> None:
    model = FakeChatModel()
    provider = LangChainLlmProvider(
        model,
        model_name="Pro/zai-org/GLM-4.7",
        provider_name="openai_compatible",
    )

    chunks = [
        chunk
        async for chunk in provider.stream(
            [LlmMessage("system", "系统"), LlmMessage("user", "你好")]
        )
    ]

    assert chunks == ["你好", "，[1]"]
    assert isinstance(model.requests[0][0], SystemMessage)
    assert isinstance(model.requests[0][1], HumanMessage)


@pytest.mark.asyncio
async def test_openai_compatible_provider_requires_api_key_without_network() -> None:
    provider = build_openai_compatible_provider(
        LlmRuntimeConfig(
            provider="openai_compatible",
            api_key=None,
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/zai-org/GLM-4.7",
            timeout_seconds=30,
            max_tokens=100,
            temperature=0.2,
        )
    )

    with pytest.raises(LlmConfigurationError):
        _ = [chunk async for chunk in provider.stream([LlmMessage("user", "你好")])]
