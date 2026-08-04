from collections.abc import Callable
from dataclasses import dataclass

from langchain_openai import ChatOpenAI

from app.modules.chat.exceptions import LlmConfigurationError
from app.modules.chat.llm import LlmProvider
from app.providers.llm.langchain_provider import LangChainLlmProvider


@dataclass(frozen=True, slots=True)
class LlmRuntimeConfig:
    provider: str
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    max_tokens: int
    temperature: float


ProviderBuilder = Callable[[LlmRuntimeConfig], LlmProvider]


class LlmProviderFactory:
    """按稳定 provider 标识构建实现，新增厂商时只注册新的 Builder。"""

    def __init__(self, builders: dict[str, ProviderBuilder] | None = None) -> None:
        self._builders = (
            {"openai_compatible": build_openai_compatible_provider}
            if builders is None
            else builders
        )

    def create(self, config: LlmRuntimeConfig) -> LlmProvider:
        builder = self._builders.get(config.provider)
        if builder is None:
            raise LlmConfigurationError(f"暂不支持 LLM Provider：{config.provider}")
        return builder(config)


def build_openai_compatible_provider(config: LlmRuntimeConfig) -> LlmProvider:
    if not config.base_url.strip() or not config.model.strip():
        raise LlmConfigurationError("模型服务地址和模型名称不能为空")
    model = ChatOpenAI(
        model=config.model,
        # 缺少密钥时 Provider 会在真正调用前给出中文配置错误，应用仍可正常启动。
        api_key=config.api_key or "missing-local-key",
        base_url=config.base_url.rstrip("/"),
        timeout=config.timeout_seconds,
        max_completion_tokens=config.max_tokens,
        temperature=config.temperature,
        max_retries=1,
        streaming=True,
        include_response_headers=True,
    )
    return LangChainLlmProvider(
        model,
        model_name=config.model,
        provider_name=config.provider,
        configuration_error=(
            None
            if config.api_key
            else "尚未配置模型 API Key，请设置 BIYOU_LLM_API_KEY"
        ),
    )
