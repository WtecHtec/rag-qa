from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from app.api.dependencies import get_document_service
from app.modules.documents.models import ChunkKind
from app.modules.documents.schemas import (
    DocumentPageResponse,
    DocumentResponse,
    TextChunkPageResponse,
    TextChunkResponse,
    TextChunkUpdateRequest,
)
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/knowledge-bases/{knowledge_base_id}/documents")
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    knowledge_base_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    service: DocumentServiceDependency,
    filename: Annotated[str, Query(min_length=1, max_length=255)],
) -> DocumentResponse:
    # 使用原始请求体而不是 multipart，浏览器无需把大文件复制成 FormData，服务端也可逐块落盘。
    document = await service.upload(
        knowledge_base_id,
        filename,
        request.headers.get("content-type", "application/octet-stream"),
        request.stream(),
    )
    background_tasks.add_task(service.process, document.id)
    return DocumentResponse.from_document(document)


@router.get("", response_model=DocumentPageResponse)
async def list_documents(
    knowledge_base_id: UUID,
    service: DocumentServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentPageResponse:
    return DocumentPageResponse.from_page(
        await service.list(knowledge_base_id, limit=limit, offset=offset)
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    service: DocumentServiceDependency,
) -> DocumentResponse:
    return DocumentResponse.from_document(await service.get(knowledge_base_id, document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    service: DocumentServiceDependency,
) -> Response:
    await service.delete(knowledge_base_id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    background_tasks: BackgroundTasks,
    service: DocumentServiceDependency,
) -> DocumentResponse:
    document = await service.prepare_reprocess(knowledge_base_id, document_id)
    background_tasks.add_task(service.process, document.id)
    return DocumentResponse.from_document(document)


@router.get("/{document_id}/chunks", response_model=TextChunkPageResponse)
async def list_text_chunks(
    knowledge_base_id: UUID,
    document_id: UUID,
    service: DocumentServiceDependency,
    kind: Annotated[ChunkKind, Query()] = ChunkKind.PARENT,
    parent_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TextChunkPageResponse:
    page = await service.list_chunks(
        knowledge_base_id,
        document_id,
        kind=kind,
        parent_id=parent_id,
        limit=limit,
        offset=offset,
    )
    return TextChunkPageResponse.from_page(page)


@router.get("/{document_id}/chunks/{chunk_id}", response_model=TextChunkResponse)
async def get_text_chunk(
    knowledge_base_id: UUID,
    document_id: UUID,
    chunk_id: UUID,
    service: DocumentServiceDependency,
) -> TextChunkResponse:
    return TextChunkResponse.from_chunk(
        await service.get_chunk(knowledge_base_id, document_id, chunk_id)
    )


@router.patch("/{document_id}/chunks/{chunk_id}", response_model=TextChunkResponse)
async def update_text_chunk(
    knowledge_base_id: UUID,
    document_id: UUID,
    chunk_id: UUID,
    payload: TextChunkUpdateRequest,
    service: DocumentServiceDependency,
) -> TextChunkResponse:
    return TextChunkResponse.from_chunk(
        await service.update_chunk(knowledge_base_id, document_id, chunk_id, payload.content)
    )


@router.delete("/{document_id}/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_text_chunk(
    knowledge_base_id: UUID,
    document_id: UUID,
    chunk_id: UUID,
    service: DocumentServiceDependency,
) -> Response:
    await service.delete_chunk(knowledge_base_id, document_id, chunk_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
