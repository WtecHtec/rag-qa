"""系统配置模块 API 路由定义。

提供配置查询、增量更新及在线连通性测试接口。
"""

from typing import Annotated
from fastapi import APIRouter, Depends

from app.api.dependencies import get_settings_service
from app.modules.settings.schemas import (
    ProviderTestRequest,
    ProviderTestResponse,
    SystemSettingsRead,
    SystemSettingsUpdate,
)
from app.modules.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]


@router.get("", response_model=SystemSettingsRead)
async def get_system_settings(
    service: SettingsServiceDep,
) -> SystemSettingsRead:
    """获取当前生效的系统配置 (API Key 敏感信息已掩码)。"""
    return await service.get_settings()


@router.patch("", response_model=SystemSettingsRead)
async def update_system_settings(
    payload: SystemSettingsUpdate,
    service: SettingsServiceDep,
) -> SystemSettingsRead:
    """增量修改系统配置项。"""
    return await service.update_settings(payload)


@router.post("/test-llm", response_model=ProviderTestResponse)
async def test_llm_connection(
    payload: ProviderTestRequest,
    service: SettingsServiceDep,
) -> ProviderTestResponse:
    """测试指定 LLM Provider 参数与 API Key 的网络连通性。"""
    return await service.test_llm_connection(payload)
