"""诊断模块业务服务与 API 逻辑的单元测试。

验证组件探针检测、数据指标计算、点赞点踩/重新生成汇总及日志 Trace 接口。
"""

import pytest

from app.core.config import Settings
from app.modules.diagnostics.service import DiagnosticsService


@pytest.mark.asyncio
async def test_diagnostics_service_health_check(tmp_path):
    """测试探针健康检查逻辑。"""
    db_file = tmp_path / "test.db"
    settings = Settings(database_path=db_file, vector_database_path=tmp_path / "vectors")

    service = DiagnosticsService(settings, db_path=db_file)
    health = await service.get_system_health()

    assert health.overall_status in ["healthy", "degraded", "unhealthy"]
    assert len(health.components) >= 4
    comp_names = [c.name for c in health.components]
    assert "sqlite_database" in comp_names
    assert "lancedb_vector_store" in comp_names
    assert "embedding_provider" in comp_names
    assert "llm_provider" in comp_names


@pytest.mark.asyncio
async def test_diagnostics_service_feedback_stats(tmp_path):
    """测试点赞/点踩统计分析逻辑。"""
    db_file = tmp_path / "test_feedback.db"
    settings = Settings(database_path=db_file, vector_database_path=tmp_path / "vectors")

    service = DiagnosticsService(settings, db_path=db_file)
    feedback_stats = await service.get_feedback_stats()

    assert feedback_stats.total_feedbacks == 0
    assert feedback_stats.up_count == 0
    assert feedback_stats.down_count == 0
    assert feedback_stats.up_rate == 100.0
    assert feedback_stats.regeneration_count == 0
    assert isinstance(feedback_stats.reason_stats, list)


@pytest.mark.asyncio
async def test_diagnostics_service_metrics(tmp_path):
    """测试系统容量与计数指标统计。"""
    db_file = tmp_path / "test_metrics.db"
    settings = Settings(database_path=db_file, vector_database_path=tmp_path / "vectors")

    service = DiagnosticsService(settings, db_path=db_file)
    metrics = await service.get_system_metrics()

    assert metrics.knowledge_base_count == 0
    assert metrics.document_count == 0
    assert metrics.storage_size_bytes >= 0


@pytest.mark.asyncio
async def test_sqlite_conversation_repository_initialize(tmp_path):
    """测试 SqliteConversationRepository 表与索引初始化 (验证多语句 SQL 规范)。"""
    from app.infrastructure.repositories.sqlite_conversation_repository import (
        SqliteConversationRepository,
    )

    db_file = tmp_path / "test_init.db"
    repo = SqliteConversationRepository(db_file)
    await repo.initialize()
    assert db_file.exists()

