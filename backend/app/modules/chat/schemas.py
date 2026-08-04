from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.chat.models import (
    ChatMessage,
    Citation,
    Conversation,
    ConversationPage,
    FeedbackRating,
)


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_conversation(cls, conversation: Conversation) -> "ConversationResponse":
        return cls(**{field: getattr(conversation, field) for field in cls.model_fields})


class ConversationPageResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: ConversationPage) -> "ConversationPageResponse":
        return cls(
            items=[ConversationResponse.from_conversation(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class CitationResponse(BaseModel):
    id: UUID
    message_id: UUID
    knowledge_base_id: UUID
    document_id: UUID
    parent_id: UUID
    child_id: UUID
    citation_number: int
    document_name: str
    heading_path: str
    parent_content: str
    child_preview: str
    child_start_offset: int
    child_end_offset: int
    score: float

    @classmethod
    def from_citation(cls, citation: Citation) -> "CitationResponse":
        return cls(**{field: getattr(citation, field) for field in cls.model_fields})


class ChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    status: str
    content: str
    rewritten_query: str | None
    model: str | None
    error_code: str | None
    error_message: str | None
    rag_enabled: bool
    citations: list[CitationResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_message(cls, message: ChatMessage) -> "ChatMessageResponse":
        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            status=message.status.value,
            content=message.content,
            rewritten_query=message.rewritten_query,
            model=message.model,
            error_code=message.error_code,
            error_message=message.error_message,
            rag_enabled=message.rag_enabled,
            citations=[CitationResponse.from_citation(item) for item in message.citations],
            created_at=message.created_at,
            updated_at=message.updated_at,
        )


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    rating: FeedbackRating
    reason: str | None = Field(default=None, max_length=500)
