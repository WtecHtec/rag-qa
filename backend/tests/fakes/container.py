from app.container import AppContainer
from app.modules.knowledge_bases.service import KnowledgeBaseService
from tests.fakes.knowledge_bases import (
    FakeKnowledgeBaseMetricsReader,
    FakeKnowledgeBaseRepository,
)


def build_test_container() -> tuple[
    AppContainer,
    FakeKnowledgeBaseRepository,
    FakeKnowledgeBaseMetricsReader,
]:
    repository = FakeKnowledgeBaseRepository()
    metrics_reader = FakeKnowledgeBaseMetricsReader()
    service = KnowledgeBaseService(repository, metrics_reader)
    return AppContainer(knowledge_base_service=service), repository, metrics_reader
