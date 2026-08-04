from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.knowledge_bases.models import KnowledgeBaseMetrics
from tests.fakes.container import build_test_container


def test_knowledge_base_crud_through_http_without_real_database() -> None:
    container, repository, _ = build_test_container()
    application = create_app(container)

    with TestClient(application) as client:
        created = client.post(
            "/api/v1/knowledge-bases",
            json={"name": "产品文档", "description": "产品资料"},
        )
        knowledge_base_id = created.json()["id"]

        listed = client.get("/api/v1/knowledge-bases", params={"q": "产品"})
        updated = client.patch(
            f"/api/v1/knowledge-bases/{knowledge_base_id}",
            json={"description": "新的说明"},
        )
        deleted = client.delete(f"/api/v1/knowledge-bases/{knowledge_base_id}")

    assert created.status_code == 201
    assert created.headers["X-Trace-ID"].startswith("tr_")
    assert listed.json()["total"] == 1
    assert updated.json()["description"] == "新的说明"
    assert deleted.status_code == 204
    assert repository.items == {}


def test_duplicate_name_returns_stable_conflict_response() -> None:
    container, _, _ = build_test_container()
    application = create_app(container)

    with TestClient(application) as client:
        client.post("/api/v1/knowledge-bases", json={"name": "Product Docs"})
        response = client.post("/api/v1/knowledge-bases", json={"name": "product docs"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "knowledge_base_name_conflict"
    assert response.json()["error"]["trace_id"] == response.headers["X-Trace-ID"]


def test_delete_non_empty_knowledge_base_does_not_cross_document_boundary() -> None:
    container, _, metrics_reader = build_test_container()
    application = create_app(container)

    with TestClient(application) as client:
        created = client.post("/api/v1/knowledge-bases", json={"name": "产品文档"})
        knowledge_base_id = created.json()["id"]
        metrics_reader.metrics[UUID(knowledge_base_id)] = KnowledgeBaseMetrics(document_count=4)
        response = client.delete(f"/api/v1/knowledge-bases/{knowledge_base_id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "knowledge_base_not_empty"


def test_empty_name_returns_domain_validation_error() -> None:
    container, _, _ = build_test_container()
    application = create_app(container)

    with TestClient(application) as client:
        response = client.post("/api/v1/knowledge-bases", json={"name": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "knowledge_base_validation_error"
