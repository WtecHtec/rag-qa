"""系统设置模块业务服务单元测试。

验证配置读取脱敏、增量修改与 Provider 连通性测试。
"""

import pytest

from app.core.config import Settings
from app.modules.settings.schemas import (
    LlmConfig,
    ProviderTestRequest,
    SystemSettingsUpdate,
)
from app.modules.settings.service import SettingsService, mask_secret


def test_mask_secret_utility():
    """测试密钥脱敏遮罩辅助函数。"""
    assert mask_secret(None) is None
    assert mask_secret("short") == "********"
    assert mask_secret("sk-1234567890abcdef") == "sk-****cdef"


@pytest.mark.asyncio
async def test_settings_service_get_and_update(tmp_path):
    """测试设置的读取与增量更新逻辑。"""
    settings = Settings(
        llm_provider="openai_compatible",
        llm_base_url="https://api.siliconflow.cn/v1",
        llm_model="Pro/zai-org/GLM-4.7",
    )
    service = SettingsService(settings)

    read_cfg = await service.get_settings()
    assert read_cfg.llm.provider == "openai_compatible"
    assert read_cfg.llm.model == "Pro/zai-org/GLM-4.7"

    # 执行更新
    update_payload = SystemSettingsUpdate(
        llm=LlmConfig(
            provider="ollama",
            base_url="http://localhost:11434/v1",
            model="qwen2.5:7b",
        )
    )
    updated_cfg = await service.update_settings(update_payload)
    assert updated_cfg.llm.provider == "ollama"
    assert updated_cfg.llm.base_url == "http://localhost:11434/v1"
    assert updated_cfg.llm.model == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_settings_service_test_llm_connection(tmp_path):
    """测试 LLM 连通性验证结构。"""
    settings = Settings()
    service = SettingsService(settings)

    test_req = ProviderTestRequest(
        provider="openai_compatible",
        api_key="sk-dummy-test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-3.5-turbo",
    )
    res = await service.test_llm_connection(test_req)
    assert isinstance(res.success, bool)
    assert res.message is not None


@pytest.mark.asyncio
async def test_settings_service_hot_reload_llm(tmp_path):
    """测试设置更新时对 ChatService 运行期 LlmProvider 执行热更新。"""
    from unittest.mock import MagicMock

    from app.modules.chat.service import ChatService

    settings = Settings(
        llm_provider="openai_compatible",
        llm_model="Qwen/Qwen3-8B",
    )
    chat_service_mock = MagicMock(spec=ChatService)

    service = SettingsService(settings, chat_service=chat_service_mock)

    update_payload = SystemSettingsUpdate(
        llm=LlmConfig(
            provider="openai_compatible",
            model="deepseek-ai/DeepSeek-V3",
        )
    )
    await service.update_settings(update_payload)

    assert chat_service_mock.set_llm_provider.called
    assert chat_service_mock.set_rag_top_k.called

