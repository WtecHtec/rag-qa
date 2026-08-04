from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_knowledge_base_service
from app.modules.knowledge_bases.commands import (
    CreateKnowledgeBaseCommand,
    UpdateKnowledgeBaseCommand,
)
from app.modules.knowledge_bases.schemas import (
    KnowledgeBaseCreateRequest,
    KnowledgeBasePageResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdateRequest,
)
from app.modules.knowledge_bases.service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge-bases")
KnowledgeBaseServiceDependency = Annotated[
    KnowledgeBaseService,
    Depends(get_knowledge_base_service),
]


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    payload: KnowledgeBaseCreateRequest,
    service: KnowledgeBaseServiceDependency,
) -> KnowledgeBaseResponse:
    detail = await service.create(
        CreateKnowledgeBaseCommand(name=payload.name, description=payload.description)
    )
    return KnowledgeBaseResponse.from_detail(detail)


@router.get("", response_model=KnowledgeBasePageResponse)
async def list_knowledge_bases(
    service: KnowledgeBaseServiceDependency,
    query: Annotated[str | None, Query(alias="q", max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeBasePageResponse:
    page = await service.list(query=query, limit=limit, offset=offset)
    return KnowledgeBasePageResponse.from_page(page)


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    knowledge_base_id: UUID,
    service: KnowledgeBaseServiceDependency,
) -> KnowledgeBaseResponse:
    detail = await service.get(knowledge_base_id)
    return KnowledgeBaseResponse.from_detail(detail)


@router.patch("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    knowledge_base_id: UUID,
    payload: KnowledgeBaseUpdateRequest,
    service: KnowledgeBaseServiceDependency,
) -> KnowledgeBaseResponse:
    detail = await service.update(
        knowledge_base_id,
        UpdateKnowledgeBaseCommand(name=payload.name, description=payload.description),
    )
    return KnowledgeBaseResponse.from_detail(detail)


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    knowledge_base_id: UUID,
    service: KnowledgeBaseServiceDependency,
) -> Response:
    await service.delete(knowledge_base_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
