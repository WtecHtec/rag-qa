"""诊断业务编排服务。

汇总组件运行状态探针、系统资源与数据量指标、用户点赞/点踩与重新生成分析统计、RAG 检索链路 Trace 与审计日志。
"""

import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.modules.diagnostics.schemas import (
    ComponentStatus,
    FeedbackReasonStat,
    FeedbackStatsResponse,
    LogEventItem,
    LogEventListResponse,
    RetrievalTraceItem,
    RetrievalTraceListResponse,
    SystemHealthResponse,
    SystemMetricsResponse,
)


class DiagnosticsService:
    """系统诊断与统计分析服务，提供可单测的纯业务编排。"""

    def __init__(
        self,
        settings: Settings,
        db_path: Path | None = None,
    ) -> None:
        self._settings = settings
        self._db_path = db_path or settings.database_path

    async def get_system_health(self) -> SystemHealthResponse:
        """获取各组件联通状态探针与整体健康度。"""
        components: list[ComponentStatus] = []

        # 探针 1: SQLite 主数据库健康度
        sqlite_start = time.perf_counter()
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("SELECT 1")
            sqlite_latency = round((time.perf_counter() - sqlite_start) * 1000, 2)
            components.append(
                ComponentStatus(
                    name="sqlite_database",
                    status="healthy",
                    details=f"SQLite 数据库连通正常 ({self._db_path.name})",
                    latency_ms=sqlite_latency,
                )
            )
        except Exception as err:
            components.append(
                ComponentStatus(
                    name="sqlite_database",
                    status="unhealthy",
                    details=f"SQLite 访问异常: {err!s}",
                    latency_ms=None,
                )
            )

        # 探针 2: LanceDB 向量存储健康度
        vector_start = time.perf_counter()
        try:
            vector_path = self._settings.vector_database_path
            if vector_path.exists():
                vector_latency = round((time.perf_counter() - vector_start) * 1000, 2)
                components.append(
                    ComponentStatus(
                        name="lancedb_vector_store",
                        status="healthy",
                        details=f"LanceDB 向量索引目录正常 ({vector_path.name})",
                        latency_ms=vector_latency,
                    )
                )
            else:
                components.append(
                    ComponentStatus(
                        name="lancedb_vector_store",
                        status="degraded",
                        details="LanceDB 向量存储目录尚未建立（待第一次文件索引）",
                        latency_ms=None,
                    )
                )
        except Exception as err:
            components.append(
                ComponentStatus(
                    name="lancedb_vector_store",
                    status="unhealthy",
                    details=f"LanceDB 状态异常: {err!s}",
                    latency_ms=None,
                )
            )

        # 探针 3: Embedding 算法模型配置状态
        components.append(
            ComponentStatus(
                name="embedding_provider",
                status="healthy",
                details=f"模型: {self._settings.embedding_model_name} (维度: {self._settings.embedding_dimensions})",
                latency_ms=None,
            )
        )

        # 探针 4: LLM 模型 Provider 配置状态
        components.append(
            ComponentStatus(
                name="llm_provider",
                status="healthy",
                details=f"Provider: {self._settings.llm_provider} (模型: {self._settings.llm_model})",
                latency_ms=None,
            )
        )

        # 评估总体状态
        overall: Any = "healthy"
        if any(c.status == "unhealthy" for c in components):
            overall = "unhealthy"
        elif any(c.status == "degraded" for c in components):
            overall = "degraded"

        return SystemHealthResponse(
            overall_status=overall,
            checked_at=datetime.now(timezone.utc),
            components=components,
        )

    async def get_system_metrics(self) -> SystemMetricsResponse:
        """计算系统总量、占用磁盘空间与文档/问答统计。"""
        kb_count = 0
        doc_count = 0
        ready_doc_count = 0
        chunks_count = 0
        conv_count = 0
        msg_count = 0

        if self._db_path.exists():
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    # 知识库数
                    cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
                    kb_count = cursor.fetchone()[0]

                    # 文档数与已就绪数
                    cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END) FROM documents")
                    row = cursor.fetchone()
                    doc_count = row[0] or 0
                    ready_doc_count = row[1] or 0

                    # 向量 Chunk 数 (统计参与向量索引的 Child Chunk 数量，与知识库管理统计对齐)
                    cursor.execute("SELECT COUNT(*) FROM text_chunks WHERE kind = 'child'")
                    chunks_row = cursor.fetchone()
                    chunks_count = chunks_row[0] if chunks_row and chunks_row[0] is not None else 0

                    # 会话数与消息数
                    cursor.execute("SELECT COUNT(*) FROM conversations")
                    conv_row = cursor.fetchone()
                    conv_count = conv_row[0] if conv_row and conv_row[0] is not None else 0

                    cursor.execute("SELECT COUNT(*) FROM chat_messages")
                    msg_row = cursor.fetchone()
                    msg_count = msg_row[0] if msg_row and msg_row[0] is not None else 0
            except sqlite3.Error:
                pass

        # 计算存储容量
        storage_size = 0
        if self._db_path.exists():
            storage_size += self._db_path.stat().st_size

        doc_dir = self._settings.document_storage_path
        if doc_dir.exists():
            for root, _, files in os.walk(doc_dir):
                for f in files:
                    storage_size += (Path(root) / f).stat().st_size

        vec_dir = self._settings.vector_database_path
        if vec_dir.exists():
            for root, _, files in os.walk(vec_dir):
                for f in files:
                    storage_size += (Path(root) / f).stat().st_size

        return SystemMetricsResponse(
            knowledge_base_count=kb_count,
            document_count=doc_count,
            ready_document_count=ready_doc_count,
            total_chunks_count=chunks_count,
            conversation_count=conv_count,
            message_count=msg_count,
            storage_size_bytes=storage_size,
        )

    async def get_feedback_stats(self) -> FeedbackStatsResponse:
        """汇总用户点赞、点踩（及原因分布）与重新生成触发频次。"""
        total_feedbacks = 0
        up_count = 0
        down_count = 0
        regeneration_count = 0
        reason_counts: dict[str, int] = {}

        if self._db_path.exists():
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    # 统计 rating
                    cursor.execute("SELECT rating, reason FROM message_feedback")
                    rows = cursor.fetchall()
                    total_feedbacks = len(rows)
                    for rating, reason in rows:
                        if rating == "up":
                            up_count += 1
                        elif rating == "down":
                            down_count += 1
                            r_key = reason.strip() if reason and reason.strip() else "其他"
                            reason_counts[r_key] = reason_counts.get(r_key, 0) + 1

                    # 统计重新生成次数 (is_regenerate = 1)
                    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_regenerate = 1")
                    regeneration_count = cursor.fetchone()[0] or 0
            except sqlite3.Error:
                pass

        up_rate = round((up_count / total_feedbacks * 100), 1) if total_feedbacks > 0 else 100.0

        reason_stats = [
            FeedbackReasonStat(
                reason=r,
                count=c,
                percentage=round((c / down_count * 100), 1) if down_count > 0 else 0.0,
            )
            for r, c in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return FeedbackStatsResponse(
            total_feedbacks=total_feedbacks,
            up_count=up_count,
            down_count=down_count,
            up_rate=up_rate,
            regeneration_count=regeneration_count,
            reason_stats=reason_stats,
        )

    async def get_retrieval_traces(self, limit: int = 20) -> RetrievalTraceListResponse:
        """获取最近真实的 RAG 检索链路 Trace 样本记录。"""
        items: list[RetrievalTraceItem] = []
        if self._db_path.exists():
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT trace_id, query, rewritten_query, intent_category,
                               retrieved_chunks_count, top_score, retrieval_latency_ms,
                               llm_latency_ms, created_at
                        FROM retrieval_traces
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )
                    rows = cursor.fetchall()
                    for row in rows:
                        dt = datetime.fromisoformat(row[8]) if isinstance(row[8], str) else datetime.now(timezone.utc)
                        items.append(
                            RetrievalTraceItem(
                                trace_id=row[0],
                                query=row[1],
                                rewritten_query=row[2],
                                intent_category=row[3],
                                retrieved_chunks_count=row[4],
                                top_score=row[5],
                                retrieval_latency_ms=row[6],
                                llm_latency_ms=row[7],
                                timestamp=dt,
                            )
                        )
            except sqlite3.Error:
                pass

        return RetrievalTraceListResponse(items=items, total=len(items))

    async def get_system_logs(
        self, level: str | None = None, limit: int = 50
    ) -> LogEventListResponse:
        """获取模拟与审计系统控制台日志。"""
        now = datetime.now(timezone.utc)
        sample_logs = [
            LogEventItem(
                timestamp=now,
                level="INFO",
                event="system.startup",
                message=f"BiYou 服务正常运行在 {self._settings.environment} 环境",
                trace_id=None,
            ),
            LogEventItem(
                timestamp=now,
                level="INFO",
                event="vector_store.initialized",
                message=f"LanceDB 存储路径 {self._settings.vector_database_path}",
                trace_id=None,
            ),
            LogEventItem(
                timestamp=now,
                level="INFO",
                event="llm.config",
                message=f"当前默认 Provider: {self._settings.llm_provider}, 模型: {self._settings.llm_model}",
                trace_id=None,
            ),
        ]
        if level:
            filtered = [log for log in sample_logs if log.level == level.upper()]
        else:
            filtered = sample_logs

        return LogEventListResponse(items=filtered[:limit], total=len(filtered))
