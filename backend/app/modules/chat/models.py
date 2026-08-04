from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    CLARIFICATION = "clarification"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    COMPLETE = "complete"
    GENERATING = "generating"
    FAILED = "failed"
    STOPPED = "stopped"


class FeedbackRating(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class Citation:
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


@dataclass(frozen=True, slots=True)
class ChatMessage:
    id: UUID
    conversation_id: UUID
    role: MessageRole
    status: MessageStatus
    content: str
    rewritten_query: str | None
    model: str | None
    error_code: str | None
    error_message: str | None
    rag_enabled: bool
    citations: tuple[Citation, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationPage:
    items: tuple[Conversation, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ChatMessagePage:
    items: tuple[ChatMessage, ...]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
