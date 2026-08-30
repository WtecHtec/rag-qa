"""诊断模块 API 路由定义。

提供系统健康检查、数据指标、点赞点踩/重新生成分析、RAG Trace 与日志查询接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_diagnostics_service
from app.modules.diagnostics.schemas import (
    FeedbackStatsResponse,
    LogEventListResponse,
    RetrievalTraceListResponse,
    SystemHealthResponse,
    SystemMetricsResponse,
)
from app.modules.diagnostics.service import DiagnosticsService

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])
DiagnosticsServiceDep = Annotated[DiagnosticsService, Depends(get_diagnostics_service)]


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    service: DiagnosticsServiceDep,
) -> SystemHealthResponse:
    """获取系统总体与子组件健康状态与延迟。"""
    return await service.get_system_health()


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    service: DiagnosticsServiceDep,
) -> SystemMetricsResponse:
    """获取知识库数、文档数、向量数、消息数与存储体积等系统指标。"""
    return await service.get_system_metrics()


@router.get("/feedback-stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    service: DiagnosticsServiceDep,
) -> FeedbackStatsResponse:
    """获取 AI 回复点赞、点踩（含具体原因分布）与重新生成统计。"""
    return await service.get_feedback_stats()


@router.get("/traces", response_model=RetrievalTraceListResponse)
async def get_retrieval_traces(
    service: DiagnosticsServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RetrievalTraceListResponse:
    """获取最近 RAG 检索链路 Trace 样本。"""
    return await service.get_retrieval_traces(limit=limit)


@router.get("/logs", response_model=LogEventListResponse)
async def get_system_logs(
    service: DiagnosticsServiceDep,
    level: Annotated[str | None, Query(description="日志级别筛选: INFO / WARNING / ERROR")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> LogEventListResponse:
    """查询系统运行审计控制台日志。"""
    return await service.get_system_logs(level=level, limit=limit)
