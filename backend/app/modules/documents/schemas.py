from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.documents.models import (
    Document,
    DocumentPage,
    TextChunk,
    TextChunkPage,
    TextChunkSummary,
)


class DocumentResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    filename: str
    media_type: str
    size_bytes: int
    status: str
    progress: int
    parent_chunk_count: int
    child_chunk_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: Document) -> "DocumentResponse":
        return cls(**{field: getattr(document, field) for field in cls.model_fields})


class DocumentPageResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: DocumentPage) -> "DocumentPageResponse":
        return cls(
            items=[DocumentResponse.from_document(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class TextChunkSummaryResponse(BaseModel):
    id: UUID
    document_id: UUID
    parent_id: UUID | None
    kind: str
    ordinal: int
    heading_path: str
    preview: str
    char_count: int
    start_offset: int
    end_offset: int
    manually_edited: bool

    @classmethod
    def from_summary(cls, chunk: TextChunkSummary) -> "TextChunkSummaryResponse":
        return cls(**{field: getattr(chunk, field) for field in cls.model_fields})


class TextChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    parent_id: UUID | None
    kind: str
    ordinal: int
    heading_path: str
    content: str
    char_count: int
    start_offset: int
    end_offset: int
    manually_edited: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_chunk(cls, chunk: TextChunk) -> "TextChunkResponse":
        return cls(**{field: getattr(chunk, field) for field in cls.model_fields})


class TextChunkPageResponse(BaseModel):
    items: list[TextChunkSummaryResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: TextChunkPage) -> "TextChunkPageResponse":
        return cls(
            items=[TextChunkSummaryResponse.from_summary(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class TextChunkUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
