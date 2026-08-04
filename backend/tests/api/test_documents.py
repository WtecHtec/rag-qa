from pathlib import Path

from fastapi.testclient import TestClient

from app.container import AppContainer
from app.infrastructure.repositories.sqlite_document_repository import SqliteDocumentRepository
from app.infrastructure.repositories.sqlite_knowledge_base_repository import (
    SqliteKnowledgeBaseRepository,
)
from app.infrastructure.storage.local_document_storage import LocalDocumentStorage
from app.infrastructure.vector_stores.lancedb_vector_store import LanceDbVectorStore
from app.main import create_app
from app.modules.documents.service import DocumentService
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.retrieval.service import RetrievalService
from app.providers.chunking.text_chunker import ParentChildTextChunker
from tests.fakes.embedding import FakeEmbeddingProvider


def build_document_test_app(
    tmp_path: Path,
    *,
    max_size_bytes: int = 1024 * 1024,
    with_retrieval: bool = False,
):
    database_path = tmp_path / "test.db"
    knowledge_repository = SqliteKnowledgeBaseRepository(database_path)
    document_repository = SqliteDocumentRepository(database_path, write_batch_size=3)
    vector_store = LanceDbVectorStore(tmp_path / "vectors", dimensions=3)
    retrieval_service = (
        RetrievalService(
            document_repository,
            knowledge_repository,
            FakeEmbeddingProvider(),
            vector_store,
            embedding_batch_size=2,
        )
        if with_retrieval
        else None
    )
    document_service = DocumentService(
        document_repository,
        knowledge_repository,
        LocalDocumentStorage(tmp_path / "files"),
        ParentChildTextChunker(parent_chars=80, child_chars=30, child_overlap_chars=5),
        max_size_bytes=max_size_bytes,
        indexer=retrieval_service,
    )
    return create_app(
        AppContainer(
            knowledge_base_service=KnowledgeBaseService(knowledge_repository, document_repository),
            document_service=document_service,
            retrieval_service=retrieval_service,
            startup_hooks=(
                knowledge_repository.initialize,
                document_repository.initialize,
                *((vector_store.initialize,) if with_retrieval else ()),
            ),
        )
    )


def test_upload_process_paginate_and_delete_document(tmp_path: Path) -> None:
    application = build_document_test_app(tmp_path)
    markdown = "# 上传设计\n" + "大文件需要流式处理。" * 30

    with TestClient(application) as client:
        knowledge_base = client.post("/api/v1/knowledge-bases", json={"name": "产品文档"}).json()
        base_url = f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents"
        uploaded = client.post(
            base_url,
            params={"filename": "upload.md"},
            content=markdown.encode(),
            headers={"Content-Type": "text/markdown"},
        )
        listed = client.get(base_url).json()
        parents = client.get(
            f"{base_url}/{uploaded.json()['id']}/chunks",
            params={"kind": "parent", "limit": 2},
        ).json()
        first_parent = parents["items"][0]
        detail = client.get(
            f"{base_url}/{uploaded.json()['id']}/chunks/{first_parent['id']}"
        ).json()
        edited = client.patch(
            f"{base_url}/{uploaded.json()['id']}/chunks/{first_parent['id']}",
            json={"content": "人工修订后的父块。" * 6},
        ).json()
        regenerated_children = client.get(
            f"{base_url}/{uploaded.json()['id']}/chunks",
            params={"kind": "child", "parent_id": first_parent["id"]},
        ).json()
        deleted = client.delete(f"{base_url}/{uploaded.json()['id']}")

    assert uploaded.status_code == 201
    assert listed["items"][0]["status"] == "chunked"
    assert listed["items"][0]["parent_chunk_count"] > 1
    assert parents["limit"] == 2
    assert len(first_parent["preview"]) <= 240
    assert detail["content"].startswith("# 上传设计")
    assert edited["manually_edited"] is True
    assert regenerated_children["total"] > 0
    assert regenerated_children["items"][0]["ordinal"] == 0
    assert regenerated_children["items"][0]["preview"].startswith("人工修订")
    assert deleted.status_code == 204
    assert not list((tmp_path / "files").glob("*.md"))


def test_duplicate_and_oversized_upload_return_stable_errors(tmp_path: Path) -> None:
    application = build_document_test_app(tmp_path, max_size_bytes=32)

    with TestClient(application) as client:
        knowledge_base_id = client.post("/api/v1/knowledge-bases", json={"name": "边界"}).json()[
            "id"
        ]
        base_url = f"/api/v1/knowledge-bases/{knowledge_base_id}/documents"
        first = client.post(base_url, params={"filename": "a.txt"}, content=b"same")
        duplicate = client.post(base_url, params={"filename": "b.txt"}, content=b"same")
        oversized = client.post(base_url, params={"filename": "large.txt"}, content=b"x" * 33)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "document_duplicate"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "document_too_large"


def test_invalid_utf8_is_preserved_as_failed_document(tmp_path: Path) -> None:
    application = build_document_test_app(tmp_path)

    with TestClient(application) as client:
        knowledge_base_id = client.post("/api/v1/knowledge-bases", json={"name": "编码"}).json()[
            "id"
        ]
        base_url = f"/api/v1/knowledge-bases/{knowledge_base_id}/documents"
        client.post(base_url, params={"filename": "broken.txt"}, content=b"\xff\xfe\xfa")
        document = client.get(base_url).json()["items"][0]

    assert document["status"] == "failed"
    assert document["error_code"] == "document_decode_error"


def test_short_parent_keeps_child_for_embedding_fallback(tmp_path: Path) -> None:
    application = build_document_test_app(tmp_path)

    with TestClient(application) as client:
        knowledge_base_id = client.post("/api/v1/knowledge-bases", json={"name": "短文档"}).json()[
            "id"
        ]
        base_url = f"/api/v1/knowledge-bases/{knowledge_base_id}/documents"
        uploaded = client.post(
            base_url,
            params={"filename": "short.md"},
            content="# 提示\n一句足够短的说明。".encode(),
        ).json()
        children = client.get(
            f"{base_url}/{uploaded['id']}/chunks", params={"kind": "child"}
        ).json()
        rejected_oversized_child = client.patch(
            f"{base_url}/{uploaded['id']}/chunks/{children['items'][0]['id']}",
            json={"content": "过长" * 20},
        )
        rejected_delete = client.delete(
            f"{base_url}/{uploaded['id']}/chunks/{children['items'][0]['id']}"
        )
        document = client.get(base_url).json()["items"][0]

    assert document["parent_chunk_count"] == 1
    assert document["child_chunk_count"] == 1
    assert children["total"] == 1
    assert children["items"][0]["parent_id"] is not None
    assert rejected_oversized_child.status_code == 422
    assert rejected_delete.status_code == 422


def test_child_vector_search_returns_parent_context_and_child_evidence(tmp_path: Path) -> None:
    application = build_document_test_app(tmp_path, with_retrieval=True)

    with TestClient(application) as client:
        knowledge_base_id = client.post(
            "/api/v1/knowledge-bases", json={"name": "检索测试"}
        ).json()["id"]
        base_url = f"/api/v1/knowledge-bases/{knowledge_base_id}/documents"
        uploaded = client.post(
            base_url,
            params={"filename": "whale.md"},
            content=("# 蓝鲸协议\n蓝鲸协议要求所有节点进行离线校验。" * 8).encode(),
        ).json()
        document = client.get(f"{base_url}/{uploaded['id']}").json()
        searched = client.post(
            f"/api/v1/knowledge-bases/{knowledge_base_id}/search",
            json={"query": "蓝鲸协议", "top_k": 3},
        )

    result = searched.json()
    assert document["status"] == "ready"
    assert searched.status_code == 200
    assert result["embedding_model"] == "fake-chinese-embedding"
    assert "蓝鲸协议" in result["matches"][0]["content"]
    assert result["matches"][0]["matched_children"]
    assert result["matches"][0]["matched_children"][0]["child_id"]
