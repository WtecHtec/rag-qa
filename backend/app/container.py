from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.core.config import Settings
from app.infrastructure.migrations.sqlite_vectors_to_lancedb import (
    SqliteVectorsToLanceDbMigration,
)
from app.infrastructure.repositories.sqlite_conversation_repository import (
    SqliteConversationRepository,
)
from app.infrastructure.repositories.sqlite_document_repository import SqliteDocumentRepository
from app.infrastructure.repositories.sqlite_knowledge_base_repository import (
    SqliteKnowledgeBaseRepository,
)
from app.infrastructure.repositories.sqlite_memory_repository import SqliteMemoryRepository
from app.infrastructure.storage.local_document_storage import LocalDocumentStorage
from app.infrastructure.vector_stores.lancedb_vector_store import LanceDbVectorStore
from app.modules.chat.query_router import QueryRouter
from app.modules.chat.service import ChatService
from app.modules.diagnostics.service import DiagnosticsService
from app.modules.documents.service import DocumentService
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.memory.service import MemoryService
from app.modules.retrieval.service import RetrievalService
from app.modules.settings.service import SettingsService
from app.providers.chunking.text_chunker import ParentChildTextChunker
from app.providers.embedding.fastembed_embedding import FastEmbedEmbeddingProvider
from app.providers.intent.llm_intent_classifier import LlmIntentClassifier
from app.providers.llm.factory import LlmProviderFactory, LlmRuntimeConfig

StartupHook = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class AppContainer:
    """显式保存应用依赖，测试可以替换边界而无需修改全局变量。"""

    knowledge_base_service: KnowledgeBaseService
    document_service: DocumentService | None = None
    retrieval_service: RetrievalService | None = None
    chat_service: ChatService | None = None
    diagnostics_service: DiagnosticsService | None = None
    settings_service: SettingsService | None = None
    startup_hooks: tuple[StartupHook, ...] = field(default_factory=tuple)

    async def startup(self) -> None:
        for hook in self.startup_hooks:
            await hook()


def build_default_container(settings: Settings) -> AppContainer:
    repository = SqliteKnowledgeBaseRepository(settings.database_path)
    document_repository = SqliteDocumentRepository(settings.database_path)
    conversation_repository = SqliteConversationRepository(settings.database_path)
    memory_repository = SqliteMemoryRepository(settings.database_path)
    vector_store = LanceDbVectorStore(
        settings.vector_database_path,
        dimensions=settings.embedding_dimensions,
        index_threshold=settings.vector_index_threshold,
    )
    vector_migration = SqliteVectorsToLanceDbMigration(
        settings.database_path,
        vector_store,
        target_path=settings.vector_database_path,
        embedding_model=settings.embedding_model_name,
        dimensions=settings.embedding_dimensions,
    )
    retrieval_service = RetrievalService(
        document_repository,
        repository,
        FastEmbedEmbeddingProvider(
            model_name=settings.embedding_model_name,
            dimensions=settings.embedding_dimensions,
            cache_dir=settings.embedding_cache_path,
            batch_size=settings.embedding_batch_size,
        ),
        vector_store,
        embedding_batch_size=settings.embedding_batch_size,
    )
    api_key = (
        settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    )
    llm_factory = LlmProviderFactory()
    llm_provider = llm_factory.create(
        LlmRuntimeConfig(
            provider=settings.llm_provider,
            api_key=api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
    )
    intent_classifier = None
    if settings.intent_classifier_enabled:
        intent_llm_provider = llm_factory.create(
            LlmRuntimeConfig(
                provider=settings.llm_provider,
                api_key=api_key,
                base_url=settings.llm_base_url,
                model=settings.intent_model or settings.llm_model,
                timeout_seconds=settings.intent_timeout_seconds,
                max_tokens=settings.intent_max_tokens,
                temperature=0,
            )
        )
        intent_classifier = LlmIntentClassifier(intent_llm_provider)
    chat_service = ChatService(
        conversation_repository,
        document_repository,
        retrieval_service,
        llm_provider,
        rag_top_k=settings.rag_top_k,
        memory_service=MemoryService(memory_repository),
        query_router=QueryRouter(
            intent_classifier,
            timeout_seconds=settings.intent_timeout_seconds,
            confidence_threshold=settings.intent_confidence_threshold,
        ),
    )
    service = KnowledgeBaseService(repository, document_repository)
    document_service = DocumentService(
        document_repository,
        repository,
        LocalDocumentStorage(settings.document_storage_path),
        ParentChildTextChunker(),
        max_size_bytes=settings.max_document_size_bytes,
        indexer=retrieval_service,
    )
    diagnostics_service = DiagnosticsService(settings)
    settings_service = SettingsService(settings, chat_service=chat_service)

    return AppContainer(
        knowledge_base_service=service,
        document_service=document_service,
        retrieval_service=retrieval_service,
        chat_service=chat_service,
        diagnostics_service=diagnostics_service,
        settings_service=settings_service,
        startup_hooks=(
            repository.initialize,
            document_repository.initialize,
            conversation_repository.initialize,
            memory_repository.initialize,
            vector_store.initialize,
            vector_migration.run,
        ),
    )

