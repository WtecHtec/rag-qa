"""系统诊断与统计分析数据模型。

包含系统健康状态、组件在线状态、资源统计指标、点赞点踩/重新生成分析、RAG 检索链路 Trace 及日志条目。
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """底层组件状态模型。"""

    name: str = Field(description="组件名称，如 sqlite / lancedb / embedding / llm")
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="组件运行状态"
    )
    details: str = Field(description="详细状态描述或异常信息")
    latency_ms: float | None = Field(default=None, description="组件响应与探针延迟 (毫秒)")


class SystemHealthResponse(BaseModel):
    """系统总体健康检查响应。"""

    overall_status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="系统整体健康度"
    )
    checked_at: datetime = Field(description="检查时间戳")
    components: list[ComponentStatus] = Field(description="各核心组件的健康状态列表")


class SystemMetricsResponse(BaseModel):
    """系统资源与业务数据指标。"""

    knowledge_base_count: int = Field(description="知识库总数量")
    document_count: int = Field(description="文档总数量")
    ready_document_count: int = Field(description="已就绪文档数量")
    total_chunks_count: int = Field(description="向量索引 Chunk 总条数")
    conversation_count: int = Field(description="会话总数")
    message_count: int = Field(description="消息总数")
    storage_size_bytes: int = Field(description="文档及向量存储占用总字节数")


class FeedbackReasonStat(BaseModel):
    """点踩具体原因分布统计项。"""

    reason: str = Field(description="点踩原因描述，如'回答错误'、'内容不完整'")
    count: int = Field(description="该原因出现的频次")
    percentage: float = Field(description="占总点踩量的百分比 (0-100)")


class FeedbackStatsResponse(BaseModel):
    """AI 回复反馈与重新生成统计分析。"""

    total_feedbacks: int = Field(description="收到反馈的总消息数")
    up_count: int = Field(description="点赞 (👍) 总数")
    down_count: int = Field(description="点踩 (👎) 总数")
    up_rate: float = Field(description="好评率百分比 (0-100)")
    regeneration_count: int = Field(description="重新生成触发总次数")
    reason_stats: list[FeedbackReasonStat] = Field(description="点踩具体原因分布")


class RecalledChunkDetail(BaseModel):
    """召回的 Chunk 节点明细。"""

    document_name: str = Field(description="所属文档名称")
    heading_path: str = Field(default="", description="标题层级路径")
    score: float = Field(default=0.0, description="匹配得分")
    child_preview: str = Field(default="", description="Child Chunk 预览文本")
    parent_content: str = Field(default="", description="Parent Chunk 完整上下文")


class RetrievalTraceItem(BaseModel):
    """单条 RAG 检索链路耗时与细节记录。"""

    trace_id: str = Field(description="请求链路唯一 Identifier")
    query: str = Field(description="原始用户查询字符串")
    rewritten_query: str | None = Field(default=None, description="改写后的检索查询")
    intent_category: str | None = Field(default=None, description="意图识别分类 (Detail/Summary/General)")
    retrieved_chunks_count: int = Field(description="检索到的 Chunk 候选条数")
    top_score: float | None = Field(default=None, description="最高检索相似度得分")
    retrieval_latency_ms: float = Field(description="向量/混合检索总耗时 (毫秒)")
    llm_latency_ms: float | None = Field(default=None, description="LLM 生成首字/总耗时 (毫秒)")
    timestamp: datetime = Field(description="请求发生时间")
    ai_response: str | None = Field(default=None, description="AI 生成的回复内容")
    recalled_chunks: list[RecalledChunkDetail] = Field(default_factory=list, description="召回的文本块明细列表")


class RetrievalTraceListResponse(BaseModel):
    """检索 Trace 记录列表响应。"""

    items: list[RetrievalTraceItem] = Field(description="检索 Trace 列表")
    total: int = Field(description="Trace 总记录数")


class LogEventItem(BaseModel):
    """结构化系统日志审计条目。"""

    timestamp: datetime = Field(description="日志发生时间")
    level: Literal["INFO", "WARNING", "ERROR"] = Field(description="日志级别")
    event: str = Field(description="事件标识符")
    message: str = Field(description="日志具体说明文字")
    trace_id: str | None = Field(default=None, description="关联的请求 Trace ID")


class LogEventListResponse(BaseModel):
    """系统日志列表响应。"""

    items: list[LogEventItem] = Field(description="日志列表")
    total: int = Field(description="匹配的日志总条数")
