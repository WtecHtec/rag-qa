from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.modules.chat.domain import (
    ChatError,
    ChatMessage,
    ChatMessagePage,
    ChatValidationError,
    Citation,
    Conversation,
    ConversationNotFoundError,
    ConversationPage,
    FeedbackRating,
    LlmMessage,
    LlmProvider,
    MessageNotFoundError,
    MessageRole,
    MessageStatus,
)
from app.modules.chat.domain.repository import ConversationRepository
from app.modules.chat.graph_builder import create_agentic_rag_graph
from app.modules.chat.tools.retrieval_tools import create_retrieval_tools
from app.modules.documents.repository import DocumentRepository
from app.modules.memory.service import MemoryService
from app.modules.retrieval.service import RetrievalService

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PreparedAnswer:
    conversation: Conversation
    user_message: ChatMessage
    assistant_message: ChatMessage
    citations: tuple[Citation, ...]
    llm_messages: tuple[LlmMessage, ...]
    direct_answer: str | None
    is_regeneration: bool = False
    memory_content: str | None = None


@dataclass(frozen=True, slots=True)
class AnswerStreamEvent:
    kind: str
    message: ChatMessage | None = None
    user_message: ChatMessage | None = None
    delta: str | None = None
    citations: tuple[Citation, ...] = ()
    error_code: str | None = None
    error_message: str | None = None


class ChatService:
    """Chat 领域应用服务：编排会话持久化、记忆提取、LangGraph Agentic RAG 图流式执行与事件分发。"""

    def __init__(
        self,
        repository: ConversationRepository,
        document_repository: DocumentRepository,
        retrieval_service: RetrievalService,
        llm_provider: LlmProvider,
        *,
        rag_top_k: int = 5,
        memory_service: MemoryService | None = None,
        clock: Clock = utc_now,
        id_factory: IdFactory = uuid4,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._document_repository = document_repository
        self._retrieval_service = retrieval_service
        self._llm_provider = llm_provider
        self._rag_top_k = rag_top_k
        self._memory_service = memory_service
        self._clock = clock
        self._id_factory = id_factory
        self._logger = logger or logging.getLogger(__name__)

    def set_llm_provider(self, llm_provider: LlmProvider) -> None:
        """运行期热替换 LLM 大模型 Provider。"""
        self._llm_provider = llm_provider

    def set_rag_top_k(self, rag_top_k: int) -> None:
        """运行期热替换 RAG 检索 TopK 参数。"""
        self._rag_top_k = rag_top_k

    def _get_chat_model(self) -> Any:
        """获取底层供 LangGraph 和 Tool 使用的统一模型实例。"""
        if hasattr(self._llm_provider, "chat_model"):
            return self._llm_provider.chat_model
        return self._llm_provider

    async def create_conversation(self) -> Conversation:
        now = self._clock()
        conversation = Conversation(
            id=self._id_factory(),
            title="新对话",
            created_at=now,
            updated_at=now,
        )
        await self._repository.add_conversation(conversation)
        self._logger.info(
            "chat.conversation_created",
            extra={"conversation_id": str(conversation.id)},
        )
        return conversation

    async def list_conversations(self, *, limit: int, offset: int) -> ConversationPage:
        self._validate_page(limit, offset)
        items = tuple(await self._repository.list_conversations(limit=limit, offset=offset))
        return ConversationPage(
            items=items,
            total=await self._repository.count_conversations(),
            limit=limit,
            offset=offset,
        )

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = await self._repository.get_conversation(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()
        return conversation

    async def delete_conversation(self, conversation_id: UUID) -> None:
        await self.get_conversation(conversation_id)
        await self._repository.delete_conversation(conversation_id)

    async def list_messages(
        self,
        conversation_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> ChatMessagePage:
        await self.get_conversation(conversation_id)
        self._validate_page(limit, offset)
        items = tuple(
            await self._repository.list_message_page(
                conversation_id,
                limit=limit,
                offset=offset,
            )
        )
        return ChatMessagePage(
            items=items,
            total=await self._repository.count_messages(conversation_id),
            limit=limit,
            offset=offset,
        )

    async def prepare_answer(
        self,
        conversation_id: UUID,
        content: str,
    ) -> PreparedAnswer:
        normalized = self._validate_content(content)
        conversation = await self.get_conversation(conversation_id)
        history = tuple(await self._repository.list_messages(conversation_id))
        now = self._clock()

        user_message = self._new_message(
            conversation.id,
            MessageRole.USER,
            MessageStatus.COMPLETE,
            normalized,
            now,
        )

        memory_content = (
            self._memory_service.extract(normalized)
            if self._memory_service
            else None
        )

        assistant_message = self._new_message(
            conversation.id,
            MessageRole.ASSISTANT,
            MessageStatus.GENERATING,
            "",
            now,
            model=self._llm_provider.model_name,
            rag_enabled=True,
        )

        if conversation.title == "新对话":
            conversation = replace(
                conversation,
                title=self._title_from_query(normalized),
                updated_at=now,
            )
        else:
            conversation = replace(conversation, updated_at=now)

        if memory_content is not None and self._memory_service is not None:
            return PreparedAnswer(
                conversation,
                user_message,
                assistant_message,
                (),
                (),
                f"好的，已记住：{memory_content}",
                memory_content=memory_content,
            )

        return PreparedAnswer(
            conversation,
            user_message,
            assistant_message,
            (),
            (),
            None,
        )

    async def prepare_regeneration(
        self,
        conversation_id: UUID,
        message_id: UUID,
    ) -> PreparedAnswer:
        conversation = await self.get_conversation(conversation_id)
        messages = tuple(await self._repository.list_messages(conversation_id))
        target_index = next(
            (index for index, message in enumerate(messages) if message.id == message_id),
            None,
        )
        if target_index is None:
            raise MessageNotFoundError()
        target = messages[target_index]
        if target.role not in (MessageRole.ASSISTANT, MessageRole.CLARIFICATION):
            raise ChatValidationError("只能重新生成助手回答")

        latest_answer = next(
            (
                message
                for message in reversed(messages)
                if message.role in (MessageRole.ASSISTANT, MessageRole.CLARIFICATION)
            ),
            None,
        )
        if latest_answer is None or latest_answer.id != target.id:
            raise ChatValidationError("只能重新生成最新一条助手回答")

        user_index = next(
            (
                index
                for index in range(target_index - 1, -1, -1)
                if messages[index].role is MessageRole.USER
            ),
            None,
        )
        if user_index is None:
            raise ChatValidationError("回答缺少对应的用户问题")

        user_message = messages[user_index]
        memory_content = (
            self._memory_service.extract(user_message.content)
            if self._memory_service
            else None
        )

        generating = replace(
            target,
            role=MessageRole.ASSISTANT,
            status=MessageStatus.GENERATING,
            content="",
            model=self._llm_provider.model_name,
            error_code=None,
            error_message=None,
            rag_enabled=True,
            citations=(),
            updated_at=self._clock(),
            is_regenerate=True,
        )

        if memory_content is not None:
            return PreparedAnswer(
                conversation,
                user_message,
                generating,
                (),
                (),
                f"好的，已记住：{memory_content}",
                True,
            )

        return PreparedAnswer(
            conversation,
            user_message,
            generating,
            (),
            (),
            None,
            is_regeneration=True,
        )

    async def stream_answer(
        self,
        prepared: PreparedAnswer,
    ) -> AsyncIterator[AnswerStreamEvent]:
        """通过 LangGraph 异步驱动 Agentic RAG 双层状态机并实时推送流式事件。"""
        yield AnswerStreamEvent(
            "meta",
            message=prepared.assistant_message,
            user_message=prepared.user_message,
        )

        parts: list[str] = []
        try:
            if prepared.direct_answer is not None:
                parts.append(prepared.direct_answer)
                yield AnswerStreamEvent("delta", delta=prepared.direct_answer)
            else:
                # 1. 组装输入历史
                history = tuple(
                    await self._repository.list_messages(prepared.conversation.id)
                )
                input_messages: list[BaseMessage] = []
                for msg in history:
                    if msg.role == MessageRole.USER:
                        input_messages.append(HumanMessage(content=msg.content))
                    elif msg.role in (MessageRole.ASSISTANT, MessageRole.CLARIFICATION):
                        if msg.content:
                            input_messages.append(AIMessage(content=msg.content))
                # 追加当前用户提问
                input_messages.append(HumanMessage(content=prepared.user_message.content))

                # 2. 构建领域检索工具与 LangGraph 双层图
                tools = create_retrieval_tools(self._retrieval_service)
                graph = create_agentic_rag_graph(self._get_chat_model(), tools)

                # 3. 驱动 LangGraph 异步流式执行
                current_state_messages = input_messages
                thread_config = {"configurable": {"thread_id": str(prepared.conversation.id)}}
                async for update in graph.astream(
                    {"messages": current_state_messages},
                    config=thread_config,
                    stream_mode="updates",
                ):
                    for node_name, node_output in update.items():
                        if node_name == "rewrite_query":
                            if not node_output.get("questionIsClear", True):
                                clarification_msgs = node_output.get("messages", [])
                                for m in clarification_msgs:
                                    if isinstance(m, AIMessage) and m.content:
                                        content_str = str(m.content)
                                        parts.append(content_str)
                                        yield AnswerStreamEvent("delta", delta=content_str)
                        elif node_name == "aggregate_answers":
                            agg_msgs = node_output.get("messages", [])
                            for m in agg_msgs:
                                if isinstance(m, AIMessage) and m.content:
                                    content_str = str(m.content)
                                    parts.append(content_str)
                                    yield AnswerStreamEvent("delta", delta=content_str)

            content = "".join(parts).strip()
            if not content:
                content = "未能从文档中检索到有效回答。"
                yield AnswerStreamEvent("delta", delta=content)

            completed = replace(
                prepared.assistant_message,
                status=MessageStatus.COMPLETE,
                content=content,
                citations=(),
                updated_at=self._clock(),
            )

            await self._remember_completed_turn(prepared)
            if prepared.is_regeneration:
                await self._repository.complete_message(completed, ())
            else:
                await self._repository.commit_turn(
                    prepared.conversation,
                    prepared.user_message,
                    completed,
                    (),
                )

            yield AnswerStreamEvent(
                "done",
                message=completed,
                user_message=prepared.user_message,
                citations=(),
            )
        except asyncio.CancelledError:
            self._logger.info(
                "chat.generation_stopped",
                extra={"message_id": str(prepared.assistant_message.id)},
            )
            raise
        except Exception as error:
            partial_content = "".join(parts).strip()
            failed = replace(
                prepared.assistant_message,
                status=MessageStatus.FAILED,
                content=partial_content,
                error_code=error.code if isinstance(error, ChatError) else "llm_generation_failed",
                error_message=(
                    error.message if isinstance(error, ChatError) else "回答生成失败，请查看日志"
                ),
                citations=(),
                updated_at=self._clock(),
            )
            self._logger.exception(
                "chat.generation_failed",
                extra={"message_id": str(failed.id), "error_code": failed.error_code},
            )
            yield AnswerStreamEvent(
                "error",
                message=failed,
                error_code=failed.error_code,
                error_message=failed.error_message,
            )

    async def save_feedback(
        self,
        conversation_id: UUID,
        message_id: UUID,
        rating: FeedbackRating,
        reason: str | None,
    ) -> None:
        await self.get_conversation(conversation_id)
        message = await self._repository.get_message(message_id)
        if message is None or message.conversation_id != conversation_id:
            raise MessageNotFoundError()
        if message.role is not MessageRole.ASSISTANT:
            raise ChatValidationError("只能评价助手回答")
        normalized_reason = reason.strip() if reason else None
        await self._repository.save_feedback(message_id, rating, normalized_reason)
        self._logger.info(
            "chat.feedback_saved",
            extra={
                "message_id": str(message_id),
                "rating": rating.value,
                "reason": normalized_reason,
            },
        )

    async def _remember_completed_turn(self, prepared: PreparedAnswer) -> None:
        if prepared.memory_content is None or self._memory_service is None:
            return
        remembered = await self._memory_service.remember(
            prepared.memory_content,
            conversation_id=prepared.conversation.id,
            message_id=prepared.user_message.id,
        )
        self._logger.info(
            "memory.explicitly_saved",
            extra={
                "conversation_id": str(prepared.conversation.id),
                "message_id": str(prepared.user_message.id),
                "memory_key": remembered.memory_key,
            },
        )

    def _new_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        status: MessageStatus,
        content: str,
        now: datetime,
        *,
        rewritten_query: str | None = None,
        model: str | None = None,
        rag_enabled: bool = False,
    ) -> ChatMessage:
        return ChatMessage(
            id=self._id_factory(),
            conversation_id=conversation_id,
            role=role,
            status=status,
            content=content,
            rewritten_query=rewritten_query,
            model=model,
            error_code=None,
            error_message=None,
            rag_enabled=rag_enabled,
            citations=(),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _validate_content(content: str) -> str:
        normalized = content.strip()
        if not normalized or len(normalized) > 4000:
            raise ChatValidationError("问题不能为空且不能超过 4000 个字符")
        return normalized

    @staticmethod
    def _title_from_query(query: str) -> str:
        return query if len(query) <= 36 else f"{query[:36]}…"

    @staticmethod
    def _validate_page(limit: int, offset: int) -> None:
        if limit < 1 or limit > 100 or offset < 0:
            raise ChatValidationError("会话分页参数不合法")
