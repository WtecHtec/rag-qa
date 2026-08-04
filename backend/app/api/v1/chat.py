import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_service
from app.modules.chat.schemas import (
    ChatMessageListResponse,
    ChatMessageResponse,
    CitationResponse,
    ConversationPageResponse,
    ConversationResponse,
    FeedbackRequest,
    SendMessageRequest,
)
from app.modules.chat.service import AnswerStreamEvent, ChatService

router = APIRouter(prefix="/conversations")
ChatServiceDependency = Annotated[ChatService, Depends(get_chat_service)]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    service: ChatServiceDependency,
) -> ConversationResponse:
    return ConversationResponse.from_conversation(
        await service.create_conversation()
    )


@router.get("", response_model=ConversationPageResponse)
async def list_conversations(
    service: ChatServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationPageResponse:
    return ConversationPageResponse.from_page(
        await service.list_conversations(limit=limit, offset=offset)
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    service: ChatServiceDependency,
) -> Response:
    await service.delete_conversation(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=ChatMessageListResponse)
async def list_messages(
    conversation_id: UUID,
    service: ChatServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChatMessageListResponse:
    page = await service.list_messages(conversation_id, limit=limit, offset=offset)
    return ChatMessageListResponse(
        items=[
            ChatMessageResponse.from_message(message)
            for message in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        has_more=page.has_more,
    )


@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    service: ChatServiceDependency,
) -> StreamingResponse:
    prepared = await service.prepare_answer(conversation_id, payload.content)
    return _streaming_response(service.stream_answer(prepared))


@router.post("/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    conversation_id: UUID,
    message_id: UUID,
    service: ChatServiceDependency,
) -> StreamingResponse:
    prepared = await service.prepare_regeneration(conversation_id, message_id)
    return _streaming_response(service.stream_answer(prepared))


@router.put("/{conversation_id}/messages/{message_id}/feedback", status_code=204)
async def save_message_feedback(
    conversation_id: UUID,
    message_id: UUID,
    payload: FeedbackRequest,
    service: ChatServiceDependency,
) -> Response:
    await service.save_feedback(
        conversation_id,
        message_id,
        payload.rating,
        payload.reason,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _streaming_response(events: AsyncIterator[AnswerStreamEvent]) -> StreamingResponse:
    return StreamingResponse(
        _encode_sse(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _encode_sse(events: AsyncIterator[AnswerStreamEvent]) -> AsyncIterator[str]:
    async for event in events:
        payload: dict[str, object | None] = {}
        if event.message is not None:
            payload["message"] = ChatMessageResponse.from_message(event.message).model_dump(
                mode="json"
            )
        if event.user_message is not None:
            # 前端使用服务端真实 ID 把临时用户消息随 done 事件增量并入历史。
            payload["user_message"] = ChatMessageResponse.from_message(
                event.user_message
            ).model_dump(mode="json")
        if event.delta is not None:
            payload["content"] = event.delta
        if event.citations:
            payload["citations"] = [
                CitationResponse.from_citation(citation).model_dump(mode="json")
                for citation in event.citations
            ]
        if event.error_code:
            payload["code"] = event.error_code
            # 错误文本使用独立字段，避免覆盖已经持久化的失败消息快照。
            payload["error_message"] = event.error_message
        yield f"event: {event.kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
