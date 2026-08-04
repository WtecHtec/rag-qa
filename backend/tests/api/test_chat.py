from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from app.container import AppContainer
from app.infrastructure.repositories.sqlite_conversation_repository import (
    SqliteConversationRepository,
)
from app.infrastructure.repositories.sqlite_knowledge_base_repository import (
    SqliteKnowledgeBaseRepository,
)
from app.infrastructure.repositories.sqlite_memory_repository import SqliteMemoryRepository
from app.main import create_app
from app.modules.chat.exceptions import LlmProviderError
from app.modules.chat.intent import ClassifiedIntent, IntentDecision
from app.modules.chat.llm import LlmMessage
from app.modules.chat.query_router import QueryRouter
from app.modules.chat.service import ChatService
from app.modules.documents.models import Document, DocumentStatus
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.memory.service import MemoryService
from app.modules.retrieval.models import (
    MatchedChild,
    ParentSearchMatch,
    VectorSearchResult,
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

    async def search_all(self, query: str, *, top_k: int) -> VectorSearchResult:
        self.queries.append(query)
        assert top_k == 5
        return VectorSearchResult(
            query=query,
            embedding_model="fake-embedding",
            matches=(
                ParentSearchMatch(
                    parent_id=PARENT_ID,
                    document_id=DOCUMENT_ID,
                    heading_path="Chunk 策略",
                    content="Parent 提供完整上下文，Child 负责精准检索。",
                    score=0.92,
                    matched_children=(
                        MatchedChild(
                            child_id=CHILD_ID,
                            ordinal=0,
                            preview="Child 负责精准检索。",
                            start_offset=12,
                            end_offset=25,
                            score=0.92,
                        ),
                    ),
                ),
            ) if self.has_matches else (),
        )


class FakeLlmProvider:
    model_name = "fake-chat-model"

    def __init__(self) -> None:
        self.requests: list[Sequence[LlmMessage]] = []

    async def stream(self, messages: Sequence[LlmMessage]) -> AsyncIterator[str]:
        self.requests.append(messages)
        yield "因为 Child 提高召回精度，"
        yield "Parent 保留完整上下文。[1]"


class FailingLlmProvider:
    model_name = "failing-chat-model"

    async def stream(self, _: Sequence[LlmMessage]) -> AsyncIterator[str]:
        yield "已生成的部分内容"
        raise LlmProviderError("上游模型暂时不可用")


class FakeIntentClassifier:
    def __init__(self, decision: IntentDecision) -> None:
        self.decision = decision
        self.queries: list[str] = []

    async def classify(
        self,
        query: str,
        previous_user_query: str | None,
        previous_rag_enabled: bool,
    ) -> IntentDecision:
        self.queries.append(query)
        return self.decision


def build_chat_test_app(
    tmp_path: Path,
    llm_provider: FakeLlmProvider | FailingLlmProvider | None = None,
    *,
    retrieval_has_matches: bool = True,
    intent_classifier: FakeIntentClassifier | None = None,
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
        query_router=QueryRouter(intent_classifier),
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


def test_llm_intent_result_controls_chat_service_routing(tmp_path: Path) -> None:
    classifier = FakeIntentClassifier(IntentDecision(ClassifiedIntent.GENERAL, 0.96))
    application, retrieval, llm = build_chat_test_app(
        tmp_path,
        intent_classifier=classifier,
    )

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        streamed = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "帮我写一句简短的欢迎语"},
        )
        messages = client.get(
            f"/api/v1/conversations/{conversation['id']}/messages"
        ).json()["items"]

    assert streamed.status_code == 200
    assert classifier.queries == ["帮我写一句简短的欢迎语"]
    assert retrieval.queries == []
    assert len(llm.requests) == 1
    assert messages[-1]["rag_enabled"] is False


def test_llm_memory_candidate_requests_explicit_authorization(tmp_path: Path) -> None:
    classifier = FakeIntentClassifier(
        IntentDecision(ClassifiedIntent.MEMORY_WRITE, 0.97)
    )
    application, retrieval, llm = build_chat_test_app(
        tmp_path,
        intent_classifier=classifier,
    )

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        streamed = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "以后回答尽量简洁"},
        )

    assert streamed.status_code == 200
    assert "请明确回复" in streamed.text
    assert retrieval.queries == []
    assert llm.requests == []


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
    assert "架构设计.md" not in meta_frame
    assert '"user_message"' in meta_frame
    assert '"role": "user"' in meta_frame
    assert messages[0]["role"] == "user"
    assert assistant["status"] == "complete"
    assert assistant["citations"][0]["parent_id"] == str(PARENT_ID)
    assert assistant["citations"][0]["child_id"] == str(CHILD_ID)
    assert assistant["citations"][0]["child_start_offset"] == 12
    assert assistant["citations"][0]["child_end_offset"] == 25
    assert feedback.status_code == 204
    assert regenerated.status_code == 200
    assert refreshed[-1]["id"] == assistant["id"]
    assert len(retrieval.queries) == 2
    assert len(llm.requests) == 2


def test_greeting_is_normal_chat_from_first_turn_and_skips_retrieval(tmp_path: Path) -> None:
    application, retrieval, llm = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        first_stream = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "你好"},
        )
        second_stream = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "你好"},
        )
        page = client.get(f"/api/v1/conversations/{conversation['id']}/messages").json()

    assert first_stream.status_code == 200
    assert second_stream.status_code == 200
    assert retrieval.queries == []
    assert len(llm.requests) == 2
    assert page["total"] == 4
    assert [item["role"] for item in page["items"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert all(not item["rag_enabled"] for item in page["items"])
    assert "缺少可判断的上下文" not in first_stream.text


def test_explicit_memory_is_saved_and_recalled_across_conversations(tmp_path: Path) -> None:
    application, retrieval, llm = build_chat_test_app(tmp_path)

    with TestClient(application) as client:
        first_conversation = client.post("/api/v1/conversations").json()
        remembered = client.post(
            f"/api/v1/conversations/{first_conversation['id']}/messages/stream",
            json={"content": "chunk 策略现在修改为分层策略模式，记住这个"},
        )
        second_conversation = client.post("/api/v1/conversations").json()
        client.post(
            f"/api/v1/conversations/{second_conversation['id']}/messages/stream",
            json={"content": "chunk 策略现在是什么模式？"},
        )

    assert "好的，已记住" in remembered.text
    assert retrieval.queries == ["chunk 策略现在是什么模式？"]
    assert len(llm.requests) == 1
    assert "chunk 策略现在修改为分层策略模式" in llm.requests[0][0].content


def test_knowledge_query_falls_back_to_general_llm_when_retrieval_is_empty(
    tmp_path: Path,
) -> None:
    application, retrieval, llm = build_chat_test_app(
        tmp_path,
        retrieval_has_matches=False,
    )

    with TestClient(application) as client:
        conversation = client.post("/api/v1/conversations").json()
        streamed = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            json={"content": "量子纠缠是什么？"},
        )
        messages = client.get(
            f"/api/v1/conversations/{conversation['id']}/messages"
        ).json()["items"]

    assert streamed.status_code == 200
    assert retrieval.queries == ["量子纠缠是什么？"]
    assert len(llm.requests) == 1
    assert "没有找到足够相关的内容" in llm.requests[0][0].content
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["rag_enabled"] is True
    assert messages[-1]["citations"] == []


def test_stream_error_keeps_failed_message_snapshot_and_separate_error_text(
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

    assert 'event: error' in streamed.text
    assert '"error_message": "上游模型暂时不可用"' in streamed.text
    assert '"message": {' in streamed.text
    assert messages[-1]["status"] == "failed"
    assert messages[-1]["content"] == "已生成的部分内容"


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
    assert len(llm.requests) == 2
