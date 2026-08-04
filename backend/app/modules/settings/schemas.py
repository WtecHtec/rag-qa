"""系统配置数据模型。

支持 LLM Provider 配置、Embedding 模型参数、Parent-Child Chunk 切片参数、Hybrid/Vector 检索策略及连通性测试请求与响应。
"""

from typing import Literal
from pydantic import BaseModel, Field


class LlmConfig(BaseModel):
    """LLM 大语言模型配置项。"""

    provider: str = Field(default="openai_compatible", description="Provider 标识: openai / claude / gemini / ollama / openai_compatible")
    api_key_masked: str | None = Field(default=None, description="脱敏后的 API Key (如 sk-****1234)")
    api_key: str | None = Field(default=None, description="用户更新时提交的新 API Key (为空保持不变)")
    base_url: str = Field(default="https://api.siliconflow.cn/v1", description="服务接口 Base URL")
    model: str = Field(default="Pro/zai-org/GLM-4.7", description="模型标识字符串")
    timeout_seconds: float = Field(default=120.0, gt=0, description="请求超时时间 (秒)")
    max_tokens: int = Field(default=2048, gt=0, description="单次最大生成 Token 数")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="采样温度系数")


class EmbeddingConfig(BaseModel):
    """Embedding 向量模型配置项。"""

    model_name: str = Field(default="BAAI/bge-small-zh-v1.5", description="向量模型名称或本地路径")
    dimensions: int = Field(default=512, gt=0, description="向量维度数")
    batch_size: int = Field(default=64, gt=0, description="向量计算 Batch 批处理大小")
    cache_path: str = Field(default="data/models", description="本地模型缓存目录")


class ChunkingConfig(BaseModel):
    """Parent-Child Chunk 文档切片策略配置。"""

    strategy: Literal["parent_child", "recursive", "semantic"] = Field(
        default="parent_child", description="Chunk 切片策略名称"
    )
    parent_chunk_size: int = Field(default=1024, gt=0, description="Parent Chunk 大小 (字符/Token 数)")
    child_chunk_size: int = Field(default=256, gt=0, description="Child Chunk 大小 (字符/Token 数)")
    overlap_size: int = Field(default=32, ge=0, description="切片重叠区间大小")


class RetrievalConfig(BaseModel):
    """RAG 检索策略配置项。"""

    mode: Literal["hybrid", "vector"] = Field(default="hybrid", description="检索模式: 混合检索 / 纯向量检索")
    rag_top_k: int = Field(default=5, ge=1, le=50, description="返回最相关 Chunk 条数 Top-K")
    intent_classifier_enabled: bool = Field(default=True, description="是否启用意图分类器")
    intent_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="意图分类置信度阈值")


class SystemSettingsRead(BaseModel):
    """获取系统整体可调整配置响应（敏感字段已脱敏）。"""

    llm: LlmConfig = Field(description="LLM 配置信息")
    embedding: EmbeddingConfig = Field(description="Embedding 配置信息")
    chunking: ChunkingConfig = Field(description="Chunk 切片策略配置")
    retrieval: RetrievalConfig = Field(description="检索策略配置")


class SystemSettingsUpdate(BaseModel):
    """更新系统配置请求体（仅填写修改项）。"""

    llm: LlmConfig | None = Field(default=None, description="LLM 更新配置")
    embedding: EmbeddingConfig | None = Field(default=None, description="Embedding 更新配置")
    chunking: ChunkingConfig | None = Field(default=None, description="Chunk 切片更新配置")
    retrieval: RetrievalConfig | None = Field(default=None, description="检索更新配置")


class ProviderTestRequest(BaseModel):
    """Provider 连通性测试请求。"""

    provider: str = Field(description="LLM Provider 名称")
    api_key: str | None = Field(default=None, description="API Key")
    base_url: str = Field(description="Base URL")
    model: str = Field(description="测试用模型名称")


class ProviderTestResponse(BaseModel):
    """Provider 连通性测试结果。"""

    success: bool = Field(description="连通测试是否成功")
    message: str = Field(description="测试结果说明或报错调试文本")
    latency_ms: float | None = Field(default=None, description="接口往返耗时 (毫秒)")
