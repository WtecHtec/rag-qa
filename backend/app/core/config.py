from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BIYOU_",
        extra="ignore",
    )

    app_name: str = "biyou-api"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    database_path: Path = Path(__file__).resolve().parents[3] / "data" / "biyou.db"
    document_storage_path: Path = Path(__file__).resolve().parents[3] / "data" / "documents"
    max_document_size_bytes: int = 100 * 1024 * 1024
    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    embedding_dimensions: int = 512
    embedding_batch_size: int = 64
    embedding_cache_path: Path = Path(__file__).resolve().parents[3] / "data" / "models"
    vector_database_path: Path = Path(__file__).resolve().parents[3] / "data" / "vectors"
    vector_index_threshold: int = 5_000
    llm_provider: str = "openai_compatible"
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.siliconflow.cn/v1"
    llm_model: str = "Pro/zai-org/GLM-4.7"
    llm_timeout_seconds: float = 120
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.2
    intent_classifier_enabled: bool = True
    intent_model: str | None = None
    intent_timeout_seconds: float = Field(default=8, gt=0)
    intent_max_tokens: int = Field(default=256, gt=0, le=2048)
    intent_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    rag_top_k: int = 5
    cors_origins: list[str] = [
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
