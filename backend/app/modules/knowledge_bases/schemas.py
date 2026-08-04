from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.knowledge_bases.models import KnowledgeBaseDetail, KnowledgeBasePage


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)


class KnowledgeBaseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def ensure_at_least_one_field(self) -> "KnowledgeBaseUpdateRequest":
        if self.name is None and self.description is None:
            raise ValueError("至少需要提供一个要修改的字段")
        return self


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    document_count: int
    ready_document_count: int
    failed_document_count: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_detail(cls, detail: KnowledgeBaseDetail) -> "KnowledgeBaseResponse":
        knowledge_base = detail.knowledge_base
        metrics = detail.metrics
        return cls(
            id=knowledge_base.id,
            name=knowledge_base.name,
            description=knowledge_base.description,
            document_count=metrics.document_count,
            ready_document_count=metrics.ready_document_count,
            failed_document_count=metrics.failed_document_count,
            chunk_count=metrics.chunk_count,
            created_at=knowledge_base.created_at,
            updated_at=knowledge_base.updated_at,
        )


class KnowledgeBasePageResponse(BaseModel):
    items: list[KnowledgeBaseResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: KnowledgeBasePage) -> "KnowledgeBasePageResponse":
        return cls(
            items=[KnowledgeBaseResponse.from_detail(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )
