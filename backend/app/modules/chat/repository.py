from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.chat.models import (
    ChatMessage,
    Citation,
    Conversation,
    FeedbackRating,
)


class ConversationRepository(Protocol):
    async def add_conversation(self, conversation: Conversation) -> None: ...
    async def get_conversation(self, conversation_id: UUID) -> Conversation | None: ...
    async def list_conversations(self, *, limit: int, offset: int) -> Sequence[Conversation]: ...
    async def count_conversations(self) -> int: ...
    async def delete_conversation(self, conversation_id: UUID) -> None: ...
    async def start_turn(
        self,
        conversation: Conversation,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None: ...
    async def list_messages(self, conversation_id: UUID) -> Sequence[ChatMessage]: ...
    async def list_message_page(
        self,
        conversation_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[ChatMessage]: ...
    async def count_messages(self, conversation_id: UUID) -> int: ...
    async def get_message(self, message_id: UUID) -> ChatMessage | None: ...
    async def complete_message(
        self,
        message: ChatMessage,
        citations: Sequence[Citation],
    ) -> None: ...
    async def update_message(self, message: ChatMessage) -> None: ...
    async def save_feedback(
        self,
        message_id: UUID,
        rating: FeedbackRating,
        reason: str | None,
    ) -> None: ...
