"""系统配置管理服务。

负责读取当前生效的系统配置（实现敏感 Key 安全脱敏）、增量更新运行期参数，以及测试 LLM/Embedding 的在线连通性。
"""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import SecretStr

from app.core.config import Settings
from app.modules.chat.query_router import QueryRouter
from app.modules.settings.schemas import (
    ChunkingConfig,
    EmbeddingConfig,
    LlmConfig,
    ProviderTestRequest,
    ProviderTestResponse,
    RetrievalConfig,
    SystemSettingsRead,
    SystemSettingsUpdate,
)
from app.providers.intent.llm_intent_classifier import LlmIntentClassifier
from app.providers.llm.factory import LlmProviderFactory, LlmRuntimeConfig

if TYPE_CHECKING:
    from app.modules.chat.service import ChatService


def mask_secret(secret: str | None) -> str | None:
    """工具函数：对敏感 API Key 进行中间遮罩保护。"""
    if not secret:
        return None
    s = secret.strip()
    if len(s) <= 8:
        return "********"
    return f"{s[:3]}****{s[-4:]}"


class SettingsService:
    """系统设置业务服务，解耦数据读取、热更新与配置持久化。"""

    def __init__(
        self,
        settings: Settings,
        chat_service: "ChatService | None" = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings
        self._chat_service = chat_service
        self._logger = logger or logging.getLogger(__name__)

    async def get_settings(self) -> SystemSettingsRead:
        """获取当前脱敏后的系统完整配置。"""
        raw_key = (
            self._settings.llm_api_key.get_secret_value()
            if self._settings.llm_api_key
            else None
        )
        llm_cfg = LlmConfig(
            provider=self._settings.llm_provider,
            api_key_masked=mask_secret(raw_key),
            api_key=None,
            base_url=self._settings.llm_base_url,
            model=self._settings.llm_model,
            timeout_seconds=self._settings.llm_timeout_seconds,
            max_tokens=self._settings.llm_max_tokens,
            temperature=self._settings.llm_temperature,
        )

        emb_cfg = EmbeddingConfig(
            model_name=self._settings.embedding_model_name,
            dimensions=self._settings.embedding_dimensions,
            batch_size=self._settings.embedding_batch_size,
            cache_path=str(self._settings.embedding_cache_path),
        )

        chunk_cfg = ChunkingConfig(
            strategy="parent_child",
            parent_chunk_size=1024,
            child_chunk_size=256,
            overlap_size=32,
        )

        ret_cfg = RetrievalConfig(
            mode="hybrid",
            rag_top_k=self._settings.rag_top_k,
            intent_classifier_enabled=self._settings.intent_classifier_enabled,
            intent_confidence_threshold=self._settings.intent_confidence_threshold,
        )

        return SystemSettingsRead(
            llm=llm_cfg,
            embedding=emb_cfg,
            chunking=chunk_cfg,
            retrieval=ret_cfg,
        )

    async def update_settings(
        self, payload: SystemSettingsUpdate
    ) -> SystemSettingsRead:
        """增量更新运行期系统配置，同步对问答服务执行热更新并落盘至 .env。"""
        if payload.llm:
            if payload.llm.provider:
                self._settings.llm_provider = payload.llm.provider
            if payload.llm.base_url:
                self._settings.llm_base_url = payload.llm.base_url
            if payload.llm.model:
                self._settings.llm_model = payload.llm.model
            if payload.llm.timeout_seconds:
                self._settings.llm_timeout_seconds = payload.llm.timeout_seconds
            if payload.llm.max_tokens:
                self._settings.llm_max_tokens = payload.llm.max_tokens
            if payload.llm.temperature is not None:
                self._settings.llm_temperature = payload.llm.temperature
            if payload.llm.api_key:
                self._settings.llm_api_key = SecretStr(payload.llm.api_key)

        if payload.embedding:
            if payload.embedding.model_name:
                self._settings.embedding_model_name = payload.embedding.model_name
            if payload.embedding.dimensions:
                self._settings.embedding_dimensions = payload.embedding.dimensions
            if payload.embedding.batch_size:
                self._settings.embedding_batch_size = payload.embedding.batch_size

        if payload.retrieval:
            if payload.retrieval.rag_top_k:
                self._settings.rag_top_k = payload.retrieval.rag_top_k
            if payload.retrieval.intent_classifier_enabled is not None:
                self._settings.intent_classifier_enabled = (
                    payload.retrieval.intent_classifier_enabled
                )
            if payload.retrieval.intent_confidence_threshold is not None:
                self._settings.intent_confidence_threshold = (
                    payload.retrieval.intent_confidence_threshold
                )

        self._rebuild_runtime_services()
        self._persist_to_env()

        self._logger.info(
            "settings.updated",
            extra={
                "provider": self._settings.llm_provider,
                "model": self._settings.llm_model,
                "rag_top_k": self._settings.rag_top_k,
            },
        )
        return await self.get_settings()

    def _rebuild_runtime_services(self) -> None:
        """重新生成运行期 LLM Provider 和 QueryRouter 并热更新至 ChatService。"""
        if self._chat_service is None:
            return
        api_key = (
            self._settings.llm_api_key.get_secret_value()
            if self._settings.llm_api_key
            else None
        )
        llm_factory = LlmProviderFactory()
        new_llm_provider = llm_factory.create(
            LlmRuntimeConfig(
                provider=self._settings.llm_provider,
                api_key=api_key,
                base_url=self._settings.llm_base_url,
                model=self._settings.llm_model,
                timeout_seconds=self._settings.llm_timeout_seconds,
                max_tokens=self._settings.llm_max_tokens,
                temperature=self._settings.llm_temperature,
            )
        )
        self._chat_service.set_llm_provider(new_llm_provider)

        intent_classifier = None
        if self._settings.intent_classifier_enabled:
            intent_llm_provider = llm_factory.create(
                LlmRuntimeConfig(
                    provider=self._settings.llm_provider,
                    api_key=api_key,
                    base_url=self._settings.llm_base_url,
                    model=self._settings.intent_model or self._settings.llm_model,
                    timeout_seconds=self._settings.intent_timeout_seconds,
                    max_tokens=self._settings.intent_max_tokens,
                    temperature=0,
                )
            )
            intent_classifier = LlmIntentClassifier(intent_llm_provider)

        new_query_router = QueryRouter(
            intent_classifier,
            timeout_seconds=self._settings.intent_timeout_seconds,
            confidence_threshold=self._settings.intent_confidence_threshold,
        )
        self._chat_service.set_query_router(new_query_router)
        self._chat_service.set_rag_top_k(self._settings.rag_top_k)

    def _persist_to_env(self) -> None:
        """将最新的 LLM/RAG 设置持久化写入后端 .env 文件，保证重启后依然生效。"""
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if not env_path.exists():
            return
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            env_dict: dict[str, str] = {}
            for line in lines:
                if line.strip() and not line.strip().startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_dict[k.strip()] = v.strip()

            env_dict["BIYOU_LLM_PROVIDER"] = self._settings.llm_provider
            if self._settings.llm_api_key:
                env_dict["BIYOU_LLM_API_KEY"] = self._settings.llm_api_key.get_secret_value()
            if self._settings.llm_base_url:
                env_dict["BIYOU_LLM_BASE_URL"] = self._settings.llm_base_url
            if self._settings.llm_model:
                env_dict["BIYOU_LLM_MODEL"] = self._settings.llm_model
                env_dict["BIYOU_INTENT_MODEL"] = self._settings.intent_model or self._settings.llm_model
            env_dict["BIYOU_RAG_TOP_K"] = str(self._settings.rag_top_k)

            new_content = "\n".join(f"{k}={v}" for k, v in env_dict.items()) + "\n"
            env_path.write_text(new_content, encoding="utf-8")
        except Exception as err:
            self._logger.warning("settings.persist_env_failed: %s", err)

    async def test_llm_connection(
        self, payload: ProviderTestRequest
    ) -> ProviderTestResponse:
        """测试用户填写的 LLM 连通性。"""
        start = time.perf_counter()
        try:
            factory = LlmProviderFactory()
            api_key = (
                payload.api_key
                if payload.api_key
                else (
                    self._settings.llm_api_key.get_secret_value()
                    if self._settings.llm_api_key
                    else None
                )
            )
            provider = factory.create(
                LlmRuntimeConfig(
                    provider=payload.provider,
                    api_key=api_key,
                    base_url=payload.base_url,
                    model=payload.model,
                    timeout_seconds=10.0,
                    max_tokens=16,
                    temperature=0.0,
                )
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            if provider:
                self._logger.info(
                    "settings.test_llm_success",
                    extra={
                        "provider": payload.provider,
                        "model": payload.model,
                        "latency_ms": latency,
                    },
                )
                return ProviderTestResponse(
                    success=True,
                    message=f"成功连接至 {payload.provider} (模型: {payload.model})",
                    latency_ms=latency,
                )
            self._logger.warning(
                "settings.test_llm_failed",
                extra={"provider": payload.provider, "model": payload.model},
            )
            return ProviderTestResponse(
                success=False,
                message="初始化 LLM Provider 失败",
                latency_ms=None,
            )
        except Exception as err:
            self._logger.exception(
                "settings.test_llm_exception",
                extra={"provider": payload.provider, "model": payload.model},
            )
            return ProviderTestResponse(
                success=False,
                message=f"LLM 连通性测试异常: {err!s}",
                latency_ms=None,
            )
