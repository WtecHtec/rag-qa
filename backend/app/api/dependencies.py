from fastapi import Request

from app.container import AppContainer
from app.modules.chat.service import ChatService
from app.modules.diagnostics.service import DiagnosticsService
from app.modules.documents.service import DocumentService
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.retrieval.service import RetrievalService
from app.modules.settings.service import SettingsService


def get_container(request: Request) -> AppContainer:
    """依赖从当前应用实例读取，避免测试之间共享全局容器。"""

    return request.app.state.container


def get_knowledge_base_service(request: Request) -> KnowledgeBaseService:
    return get_container(request).knowledge_base_service


def get_document_service(request: Request) -> DocumentService:
    service = get_container(request).document_service
    if service is None:
        raise RuntimeError("当前应用未装配文档服务")
    return service


def get_retrieval_service(request: Request) -> RetrievalService:
    service = get_container(request).retrieval_service
    if service is None:
        raise RuntimeError("当前应用未装配检索服务")
    return service


def get_chat_service(request: Request) -> ChatService:
    service = get_container(request).chat_service
    if service is None:
        raise RuntimeError("当前应用未装配会话服务")
    return service


def get_diagnostics_service(request: Request) -> DiagnosticsService:
    service = get_container(request).diagnostics_service
    if service is None:
        raise RuntimeError("当前应用未装配诊断服务")
    return service


def get_settings_service(request: Request) -> SettingsService:
    service = get_container(request).settings_service
    if service is None:
        raise RuntimeError("当前应用未装配设置服务")
    return service

