from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class ChunkKind(StrEnum):
    PARENT = "parent"
    CHILD = "child"


@dataclass(frozen=True, slots=True)
class Document:
    id: UUID
    knowledge_base_id: UUID
    filename: str
    extension: str
    media_type: str
    storage_key: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    progress: int
    parent_chunk_count: int
    child_chunk_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TextChunk:
    id: UUID
    document_id: UUID
    parent_id: UUID | None
    kind: ChunkKind
    ordinal: int
    heading_path: str
    content: str
    char_count: int
    start_offset: int
    end_offset: int
    manually_edited: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TextChunkSummary:
    id: UUID
    document_id: UUID
    parent_id: UUID | None
    kind: ChunkKind
    ordinal: int
    heading_path: str
    preview: str
    char_count: int
    start_offset: int
    end_offset: int
    manually_edited: bool


@dataclass(frozen=True, slots=True)
class DocumentPage:
    items: tuple[Document, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class TextChunkPage:
    items: tuple[TextChunkSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class StoredDocument:
    storage_key: str
    size_bytes: int
    sha256: str
