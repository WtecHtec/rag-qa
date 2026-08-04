import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.chat.citation_selector import select_cited_sources
from app.modules.chat.exceptions import (
    ChatError,
    ChatValidationError,
    ConversationNotFoundError,
    MessageNotFoundError,
)
from app.modules.chat.llm import LlmMessage, LlmProvider
from app.modules.chat.models import (
    ChatMessage,
    ChatMessagePage,
    Citation,
    Conversation,
    ConversationPage,
    FeedbackRating,
    MessageRole,
    MessageStatus,
)
from app.modules.chat.prompt_builder import (
    build_general_chat_messages,
    build_knowledge_fallback_messages,
    build_llm_messages,
)
from app.modules.chat.query_router import QueryRouter
from app.modules.chat.query_strategy import (
    QueryIntent,
    QueryPlan,
    find_latest_answer_rag_mode,
    find_latest_user_query,
)
from app.modules.chat.repository import ConversationRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.memory.service import MemoryService
from app.modules.retrieval.models import VectorSearchResult
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
    """编排会话持久化、查询重写、RAG 检索、上下文构建和 LLM 流式输出。"""

    def __init__(
        self,
        repository: ConversationRepository,
        document_repository: DocumentRepository,
        retrieval_service: RetrievalService,
        llm_provider: LlmProvider,
        *,
        rag_top_k: int = 5,
        memory_service: MemoryService | None = None,
        query_router: QueryRouter | None = None,
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
        self._query_router = query_router or QueryRouter()
        self._clock = clock
        self._id_factory = id_factory
        self._logger = logger or logging.getLogger(__name__)

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
        previous_query = find_latest_user_query(history)
        memory_content = self._memory_service.extract(normalized) if self._memory_service else None
        query_plan = (
            QueryPlan(QueryIntent.GENERAL, normalized)
            if memory_content is not None
            else await self._query_router.route(
                normalized,
                previous_query,
                find_latest_answer_rag_mode(history),
            )
        )
        now = self._clock()
        user_message = self._new_message(
            conversation.id,
            MessageRole.USER,
            MessageStatus.COMPLETE,
            normalized,
            now,
        )
        assistant_role = (
            MessageRole.CLARIFICATION
            if query_plan.intent
            in (QueryIntent.CLARIFICATION, QueryIntent.MEMORY_CONFIRMATION)
            else MessageRole.ASSISTANT
        )
        assistant_message = self._new_message(
            conversation.id,
            assistant_role,
            MessageStatus.GENERATING,
            "",
            now,
            rewritten_query=query_plan.retrieval_query,
            model=self._llm_provider.model_name,
            rag_enabled=query_plan.use_rag,
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
        if assistant_role is MessageRole.CLARIFICATION:
            direct_answer = (
                "如果希望我长期保存这条信息，请明确回复“记住：要保存的内容”。"
                if query_plan.intent is QueryIntent.MEMORY_CONFIRMATION
                else "这个问题缺少可判断的上下文，请补充具体对象或完整问题后再试。"
            )
            return PreparedAnswer(
                conversation,
                user_message,
                assistant_message,
                (),
                (),
                direct_answer,
            )
        if query_plan.intent is QueryIntent.GENERAL:
            memories = await self._prompt_memories()
            return PreparedAnswer(
                conversation,
                user_message,
                assistant_message,
                (),
                build_general_chat_messages(
                    history,
                    user_message.content,
                    memories=memories,
                ),
                None,
            )
        return await self._prepare_with_retrieval(
            conversation,
            user_message,
            assistant_message,
            history,
            query_plan.retrieval_query,
            await self._prompt_memories(),
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
            # 重新生成会覆盖原消息；只允许最新回答可避免改写中间历史导致上下文分叉。
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
        previous_query = find_latest_user_query(messages[:user_index])
        memory_content = (
            self._memory_service.extract(user_message.content)
            if self._memory_service
            else None
        )
        query_plan = (
            QueryPlan(QueryIntent.GENERAL, user_message.content)
            if memory_content is not None
            else await self._query_router.route(
                user_message.content,
                previous_query,
                find_latest_answer_rag_mode(messages[:user_index]),
            )
        )
        generating = replace(
            target,
            role=(
                MessageRole.CLARIFICATION
                if query_plan.intent
                in (QueryIntent.CLARIFICATION, QueryIntent.MEMORY_CONFIRMATION)
                else MessageRole.ASSISTANT
            ),
            status=MessageStatus.GENERATING,
            content="",
            rewritten_query=query_plan.retrieval_query,
            model=self._llm_provider.model_name,
            error_code=None,
            error_message=None,
            rag_enabled=query_plan.use_rag,
            citations=(),
            updated_at=self._clock(),
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
        if query_plan.intent in (
            QueryIntent.CLARIFICATION,
            QueryIntent.MEMORY_CONFIRMATION,
        ):
            direct_answer = (
                "如果希望我长期保存这条信息，请明确回复“记住：要保存的内容”。"
                if query_plan.intent is QueryIntent.MEMORY_CONFIRMATION
                else "这个问题缺少可判断的上下文，请补充具体对象或完整问题后再试。"
            )
            return PreparedAnswer(
                conversation,
                user_message,
                generating,
                (),
                (),
                direct_answer,
                True,
            )
        if query_plan.intent is QueryIntent.GENERAL:
            memories = await self._prompt_memories()
            return PreparedAnswer(
                conversation,
                user_message,
                generating,
                (),
                build_general_chat_messages(
                    messages[:user_index],
                    user_message.content,
                    memories=memories,
                ),
                None,
                True,
            )
        return await self._prepare_with_retrieval(
            conversation,
            user_message,
            generating,
            messages[:user_index],
            query_plan.retrieval_query,
            await self._prompt_memories(),
            is_regeneration=True,
        )

    async def stream_answer(
        self,
        prepared: PreparedAnswer,
    ) -> AsyncIterator[AnswerStreamEvent]:
        # meta 只确认服务端消息身份；检索候选必须等正文实际引用后才能暴露给前端。
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
                async for delta in self._llm_provider.stream(prepared.llm_messages):
                    parts.append(delta)
                    yield AnswerStreamEvent("delta", delta=delta)
            content = "".join(parts).strip()
            cited_sources = select_cited_sources(content, prepared.citations)
            completed = replace(
                prepared.assistant_message,
                status=MessageStatus.COMPLETE,
                content=content,
                citations=cited_sources,
                updated_at=self._clock(),
            )
            await self._remember_completed_turn(prepared)
            if prepared.is_regeneration:
                await self._repository.complete_message(completed, cited_sources)
            else:
                # 首次问答只在完整生成后原子提交，取消请求不会留下半轮消息。
                await self._repository.commit_turn(
                    prepared.conversation,
                    prepared.user_message,
                    completed,
                    cited_sources,
                )
            yield AnswerStreamEvent(
                "done",
                message=completed,
                citations=cited_sources,
            )
        except asyncio.CancelledError:
            # 主动停止、切换路由或刷新都视为放弃本轮，不保存用户问题和部分回答。
            self._logger.info(
                "chat.generation_stopped",
                extra={"message_id": str(prepared.assistant_message.id)},
            )
            raise
        except Exception as error:
            partial_content = "".join(parts).strip()
            cited_sources = select_cited_sources(partial_content, prepared.citations)
            failed = replace(
                prepared.assistant_message,
                status=MessageStatus.FAILED,
                content=partial_content,
                error_code=error.code if isinstance(error, ChatError) else "llm_generation_failed",
                error_message=(
                    error.message if isinstance(error, ChatError) else "回答生成失败，请查看日志"
                ),
                citations=cited_sources,
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

    async def _prepare_with_retrieval(
        self,
        conversation: Conversation,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        history: Sequence[ChatMessage],
        retrieval_query: str,
        memories: Sequence[str],
        *,
        is_regeneration: bool = False,
    ) -> PreparedAnswer:
        import time
        start_time = time.perf_counter()
        result = await self._retrieval_service.search_all(
            retrieval_query,
            top_k=self._rag_top_k,
        )
        retrieval_latency = round((time.perf_counter() - start_time) * 1000, 2)
        citations = await self._build_citations(
            assistant_message.id,
            result,
        )
        top_score = (
            citations[0].score
            if citations
            else (result.matches[0].score if result.matches else None)
        )
        trace_id = f"trc-{str(assistant_message.id)[:8]}"
        try:
            await self._repository.save_retrieval_trace(
                trace_id=trace_id,
                query=user_message.content,
                rewritten_query=(
                    retrieval_query
                    if retrieval_query != user_message.content
                    else None
                ),
                intent_category="Detail" if citations else "General",
                retrieved_chunks_count=len(citations),
                top_score=top_score,
                retrieval_latency_ms=retrieval_latency,
            )
        except Exception as e:
            self._logger.warning("save_retrieval_trace.failed: %s", e)

        if not citations:
            return PreparedAnswer(
                conversation,
                user_message,
                assistant_message,
                (),
                build_knowledge_fallback_messages(
                    history,
                    user_message.content,
                    memories=memories,
                ),
                None,
                is_regeneration,
            )
        llm_messages = build_llm_messages(
            history,
            user_message.content,
            citations,
            memories=memories,
        )
        return PreparedAnswer(
            conversation,
            user_message,
            assistant_message,
            citations,
            llm_messages,
            None,
            is_regeneration,
        )
    async def _build_citations(
        self,
        message_id: UUID,
        result: VectorSearchResult,
    ) -> tuple[Citation, ...]:
        documents = await asyncio.gather(
            *(self._document_repository.get(match.document_id) for match in result.matches)
        )
        citations: list[Citation] = []
        for match, document in zip(result.matches, documents, strict=True):
            if document is None or not match.matched_children:
                continue
            child = match.matched_children[0]
            citations.append(
                Citation(
                    id=self._id_factory(),
                    message_id=message_id,
                    knowledge_base_id=document.knowledge_base_id,
                    document_id=match.document_id,
                    parent_id=match.parent_id,
                    child_id=child.child_id,
                    citation_number=len(citations) + 1,
                    document_name=document.filename,
                    heading_path=match.heading_path,
                    parent_content=match.content,
                    child_preview=child.preview,
                    child_start_offset=child.start_offset,
                    child_end_offset=child.end_offset,
                    score=match.score,
                )
            )
        return tuple(citations)

    async def _prompt_memories(self) -> tuple[str, ...]:
        if self._memory_service is None:
            return ()
        return await self._memory_service.list_prompt_contents()

    async def _remember_completed_turn(self, prepared: PreparedAnswer) -> None:
        """显式记忆也随完整轮次提交，中断回复不能提前产生长期副作用。"""
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
