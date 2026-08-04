from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_retrieval_service
from app.modules.retrieval.schemas import VectorSearchRequest, VectorSearchResponse
from app.modules.retrieval.service import RetrievalService

router = APIRouter(prefix="/knowledge-bases/{knowledge_base_id}/search")
RetrievalServiceDependency = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.post("", response_model=VectorSearchResponse)
async def search_knowledge_base(
    knowledge_base_id: UUID,
    payload: VectorSearchRequest,
    service: RetrievalServiceDependency,
) -> VectorSearchResponse:
    """返回命中的完整 Parent，并附带用于召回的 Child 证据。"""
    result = await service.search(
        knowledge_base_id,
        payload.query,
        top_k=payload.top_k,
    )
    return VectorSearchResponse.from_result(result)
