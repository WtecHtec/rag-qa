from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel

from app.container import AppContainer
from app.infrastructure.repositories.sqlite_conversation_repository import (
    SqliteConversationRepository,
)
from app.infrastructure.repositories.sqlite_knowledge_base_repository import (
    SqliteKnowledgeBaseRepository,
)
from app.infrastructure.repositories.sqlite_memory_repository import SqliteMemoryRepository
from app.main import create_app
from app.modules.chat.domain.state import QueryAnalysis
from app.modules.chat.exceptions import LlmProviderError
from app.modules.chat.llm import LlmMessage
from app.modules.chat.service import ChatService
from app.modules.documents.models import Document, DocumentStatus
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.memory.service import MemoryService
from app.modules.retrieval.models import (
    ChildChunkItem,
    ParentChunkDetail,
)
from tests.fakes.knowledge_bases import FakeKnowledgeBaseMetricsReader

NOW = datetime(2026, 8, 4, tzinfo=UTC)
DOCUMENT_ID = UUID(int=100)
PARENT_ID = UUID(int=101)
CHILD_ID = UUID(int=102)


class FakeDocumentReader:
    async def get(self, document_id: UUID) -> Document | None:
        if document_id != DOCUMENT_ID:
            return None
        return Document(
            id=DOCUMENT_ID,
            knowledge_base_id=UUID(int=0),
            filename="架构设计.md",
            extension=".md",
            media_type="text/markdown",
            storage_key="architecture.md",
            size_bytes=100,
            sha256="hash",
            status=DocumentStatus.READY,
            progress=100,
            parent_chunk_count=1,
            child_chunk_count=1,
            error_code=None,
            error_message=None,
            created_at=NOW,
            updated_at=NOW,
        )


class FakeRetrievalService:
    def __init__(self, *, has_matches: bool = True) -> None:
        self.queries: list[str] = []
        self.has_matches = has_matches

    async def search_child_chunks(
        self,
        query: str,
        *,
        limit: int = 5,
        knowledge_base_id: UUID | None = None,
        score_threshold: float = 0.0,
    ) -> Sequence[ChildChunkItem]:
        self.queries.append(query)
        if not self.has_matches:
            return ()
        return (
            ChildChunkItem(
                parent_id=PARENT_ID,
                child_id=CHILD_ID,
                document_id=DOCUMENT_ID,
                heading_path="Chunk 策略",
                content="Parent 提供完整上下文，Child 负责精准检索。",
                score=0.92,
            ),
        )

    async def get_parent_chunk(self, parent_id: UUID) -> ParentChunkDetail | None:
        if not self.has_matches or parent_id != PARENT_ID:
            return None
        return ParentChunkDetail(
            parent_id=PARENT_ID,
            document_id=DOCUMENT_ID,
            heading_path="Chunk 策略",
            content="Parent 提供完整上下文，Child 负责精准检索。",
            char_count=50,
        )


class FakeStructuredRunner:
    def __init__(self, schema: type[BaseModel]) -> None:
        self.schema = schema

    async def ainvoke(self, messages: list[Any]) -> Any:
        return self.invoke(messages)

    def invoke(self, messages: list[Any]) -> Any:
        last_msg = messages[-1]
        content = str(last_msg.content)
        if "用户提问：" in content:
            q = content.split("用户提问：")[-1].strip()
        elif "User Query:" in content:
            q = content.split("User Query:")[-1].strip()
        else:
            q = content
        return QueryAnalysis(
            is_clear=True,
            questions=[q or "默认测试问题"],
            clarification_needed=None,
        )


class FakeChatModel:
    def __init__(self, parent_provider: "FakeLlmProvider | None" = None) -> None:
        self._parent = parent_provider
        self._tools: list[Any] = []

    def bind_tools(self, tools: Sequence[Any]) -> "FakeChatModel":
        new_model = FakeChatModel(self._parent)
        new_model._tools = list(tools)
        return new_model

    def with_structured_output(self, schema: type[BaseModel]) -> FakeStructuredRunner:
        return FakeStructuredRunner(schema)

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        return self.invoke(messages)

    def invoke(self, messages: list[Any]) -> AIMessage:
        if self._parent:
            self._parent.requests.append(messages)

        # 判断是否是在子图 orchestrator 且有工具绑定
        if self._tools:
            has_tool_message = any(isinstance(m, ToolMessage) for m in messages)
            if not has_tool_message:
                # 触发 search_child_chunks
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_child_chunks",
                            "args": {"query": "测试查询", "limit": 5},
                            "id": "tc_1",
                        }
                    ],
                )

        return AIMessage(content="因为 Child 提高召回精度，Parent 保留完整上下文。[1]")

    async def astream(self, messages: list[Any]) -> AsyncIterator[AIMessage]:
        yield AIMessage(content="因为 Child 提高召回精度，")
        yield AIMessage(content="Parent 保留完整上下文。[1]")


class FakeLlmProvider:
    model_name = "fake-chat-model"

    def __init__(self) -> None:
        self.requests: list[Sequence[Any]] = []
        self._chat_model = FakeChatModel(self)

    @property
    def chat_model(self) -> FakeChatModel:
        return self._chat_model

    async def stream(self, messages: Sequence[LlmMessage]) -> AsyncIterator[str]:
        self.requests.append(messages)
        yield "因为 Child 提高召回精度，"
        yield "Parent 保留完整上下文。[1]"


class FailingChatModel:
    def bind_tools(self, tools: Sequence[Any]) -> "FailingChatModel":
        return self

    def with_structured_output(self, schema: type[BaseModel]) -> "FailingChatModel":
        return self

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        raise LlmProviderError("上游模型暂时不可用")

    def invoke(self, messages: list[Any]) -> AIMessage:
        raise LlmProviderError("上游模型暂时不可用")


class FailingLlmProvider:
    model_name = "failing-chat-model"

    def __init__(self) -> None:
        self._chat_model = FailingChatModel()

    @property
    def chat_model(self) -> FailingChatModel:
        return self._chat_model

    async def stream(self, _: Sequence[LlmMessage]) -> AsyncIterator[str]:
        yield "已生成的部分内容"
        raise LlmProviderError("上游模型暂时不可用")


def build_chat_test_app(
    tmp_path: Path,
    llm_provider: FakeLlmProvider | FailingLlmProvider | None = None,
    *,
    retrieval_has_matches: bool = True,
):
    database_path = tmp_path / "chat.db"
    knowledge_repository = SqliteKnowledgeBaseRepository(database_path)
    conversation_repository = SqliteConversationRepository(database_path)
    memory_repository = SqliteMemoryRepository(database_path)
    retrieval = FakeRetrievalService(has_matches=retrieval_has_matches)
    llm = llm_provider or FakeLlmProvider()
    chat_service = ChatService(
        conversation_repository,
        FakeDocumentReader(),  # type: ignore[arg-type]
        retrieval,  # type: ignore[arg-type]
        llm,
        memory_service=MemoryService(memory_repository),
    )
    application = create_app(
        AppContainer(
            knowledge_base_service=KnowledgeBaseService(
                knowledge_repository,
                FakeKnowledgeBaseMetricsReader(),
            ),
            chat_service=chat_service,
            startup_hooks=(
                knowledge_repository.initialize,
                conversation_repository.initialize,
                memory_repository.initialize,
            ),
        )
    )
    return application, retrieval, llm


def test_interrupted_stream_does_not_persist_partial_turn(tmp_path: Path) -> None:
    application, _, _ = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        service = application.state.container.chat_service
        assert service is not None
        assert client.portal is not None

        async def interrupt_after_first_delta() -> None:
            prepared = await service.prepare_answer(
                UUID(conversation["id"]),
                "这条回答会在生成中被取消",
            )
            events = service.stream_answer(prepared)
            await anext(events)
            await anext(events)
            await events.aclose()

        client.portal.call(interrupt_after_first_delta)
        messages = client.get(
            f"/api/v1/conversations/{conversation['id']}/messages"
        ).json()["items"]

    assert messages == []


def test_interrupted_regeneration_keeps_previous_answer(tmp_path: Path) -> None:
    application, _, _ = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "保留原回答"},
        )
        original = client.get(
            f"/api/v1/conversations/{conversation['id']}/messages"
        ).json()["items"][-1]
        service = application.state.container.chat_service
        assert service is not None
        assert client.portal is not None

        async def interrupt_after_first_delta() -> None:
            prepared = await service.prepare_regeneration(
                UUID(conversation["id"]),
                UUID(original["id"]),
            )
            events = service.stream_answer(prepared)
            await anext(events)
            await anext(events)
            await events.aclose()

        client.portal.call(interrupt_after_first_delta)
        refreshed = client.get(
            f"/api/v1/conversations/{conversation['id']}/messages"
        ).json()["items"][-1]

    assert refreshed == original


def test_stream_chat_persists_messages_citations_feedback_and_regeneration(
    tmp_path: Path,
) -> None:
    application, retrieval, llm = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        conversation = client.post(
            "/api/v1/conversations",
        ).json()
        streamed = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "为什么使用 Parent Child？"},
        )
        messages = client.get(f"/api/v1/conversations/{conversation['id']}/messages").json()[
            "items"
        ]
        assistant = messages[-1]
        feedback = client.put(
            f"/api/v1/conversations/{conversation['id']}/messages/{assistant['id']}/feedback",
            json={"rating": "up"},
        )
        regenerated = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/{assistant['id']}/regenerate"
        )
        refreshed = client.get(f"/api/v1/conversations/{conversation['id']}/messages").json()[
            "items"
        ]

    assert streamed.status_code == 200
    assert "event: delta" in streamed.text
    assert "Parent 保留完整上下文" in streamed.text
    meta_frame = streamed.text.split("\n\n", maxsplit=1)[0]
    assert '"user_message"' in meta_frame
    assert '"role": "user"' in meta_frame
    assert messages[0]["role"] == "user"
    assert assistant["status"] == "complete"
    assert feedback.status_code == 204
    assert regenerated.status_code == 200
    assert refreshed[-1]["id"] == assistant["id"]
    assert len(retrieval.queries) == 2


def test_explicit_memory_is_saved_and_recalled_across_conversations(tmp_path: Path) -> None:
    application, retrieval, llm = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        first_conversation = client.post("/api/v1/conversations").json()
        remembered = client.post(
            f"/api/v1/conversations/{first_conversation['id']}/messages/stream",
            json={"content": "chunk 策略现在修改为分层策略模式，记住这个"},
        )
        second_conversation = client.post("/api/v1/conversations").json()
        streamed = client.post(
            f"/api/v1/conversations/{second_conversation['id']}/messages/stream",
            json={"content": "chunk 策略现在是什么模式？"},
        )

    assert "好的，已记住" in remembered.text
    assert streamed.status_code == 200


def test_stream_error_is_reported_but_incomplete_turn_is_not_persisted(
    tmp_path: Path,
) -> None:
    application, _, _ = build_chat_test_app(tmp_path, FailingLlmProvider())

    with TestClient(application) as client:
        conversation = client.post(
            "/api/v1/conversations",
        ).json()
        streamed = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "触发上游错误"},
        )
        messages = client.get(f"/api/v1/conversations/{conversation['id']}/messages").json()[
            "items"
        ]

    assert "event: error" in streamed.text
    assert '"error_message": "上游模型暂时不可用"' in streamed.text
    assert '"message": {' in streamed.text
    assert messages == []


def test_only_latest_assistant_answer_can_be_regenerated(tmp_path: Path) -> None:
    application, _, llm = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        for content in ("第一个知识问题", "第二个知识问题"):
            client.post(
                f"/api/v1/conversations/{conversation['id']}/messages/stream",
                json={"content": content},
            )
        messages = client.get(
            f"/api/v1/conversations/{conversation['id']}/messages"
        ).json()["items"]
        assistant_ids = [item["id"] for item in messages if item["role"] == "assistant"]
        rejected = client.post(
            f"/api/v1/conversations/{conversation['id']}"
            f"/messages/{assistant_ids[0]}/regenerate"
        )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["message"] == "只能重新生成最新一条助手回答"
