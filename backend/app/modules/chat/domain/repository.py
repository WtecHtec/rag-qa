"""Chat 领域仓储抽象接口。"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.chat.domain.models import (
    ChatMessage,
    Citation,
    Conversation,
    FeedbackRating,
)


class ConversationRepository(Protocol):
    """会话与消息持久化领域仓储协议。"""

    async def add_conversation(self, conversation: Conversation) -> None: ...
    async def get_conversation(self, conversation_id: UUID) -> Conversation | None: ...
    async def list_conversations(self, *, limit: int, offset: int) -> Sequence[Conversation]: ...
    async def count_conversations(self) -> int: ...
    async def delete_conversation(self, conversation_id: UUID) -> None: ...
    async def commit_turn(
        self,
        conversation: Conversation,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        citations: Sequence[Citation],
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
    async def save_feedback(
        self,
        message_id: UUID,
        rating: FeedbackRating,
        reason: str | None,
    ) -> None: ...
    async def save_retrieval_trace(
        self,
        *,
        trace_id: str,
        query: str,
        rewritten_query: str | None,
        intent_category: str | None,
        retrieved_chunks_count: int,
        top_score: float | None,
        retrieval_latency_ms: float,
        llm_latency_ms: float | None = None,
        ai_response: str | None = None,
        recalled_chunks_json: str | None = None,
    ) -> None: ...
    async def update_retrieval_trace_response(
        self,
        *,
        trace_id: str,
        ai_response: str,
        llm_latency_ms: float | None = None,
    ) -> None: ...
