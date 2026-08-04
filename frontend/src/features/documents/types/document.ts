export type DocumentStatus =
  | "pending"
  | "parsing"
  | "chunking"
  | "chunked"
  | "embedding"
  | "indexing"
  | "ready"
  | "failed";
export type ChunkKind = "parent" | "child";

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  status: DocumentStatus;
  progress: number;
  parent_chunk_count: number;
  child_chunk_count: number;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentPage {
  items: KnowledgeDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface TextChunkSummary {
  id: string;
  document_id: string;
  parent_id?: string | null;
  kind: ChunkKind;
  ordinal: number;
  heading_path: string;
  preview: string;
  char_count: number;
  start_offset: number;
  end_offset: number;
  manually_edited: boolean;
}

export interface TextChunk extends Omit<TextChunkSummary, "preview"> {
  content: string;
  created_at: string;
  updated_at: string;
}

export interface TextChunkPage {
  items: TextChunkSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentGateway {
  list(knowledgeBaseId: string, limit: number, offset: number, signal?: AbortSignal): Promise<DocumentPage>;
  upload(
    knowledgeBaseId: string,
    file: File,
    onProgress: (progress: number) => void,
  ): Promise<KnowledgeDocument>;
  remove(knowledgeBaseId: string, documentId: string): Promise<void>;
  reprocess(knowledgeBaseId: string, documentId: string): Promise<KnowledgeDocument>;
  listChunks(
    knowledgeBaseId: string,
    documentId: string,
    kind: ChunkKind,
    parentId: string | null,
    limit: number,
    offset: number,
  ): Promise<TextChunkPage>;
  getChunk(knowledgeBaseId: string, documentId: string, chunkId: string): Promise<TextChunk>;
  updateChunk(
    knowledgeBaseId: string,
    documentId: string,
    chunkId: string,
    content: string,
  ): Promise<TextChunk>;
  removeChunk(knowledgeBaseId: string, documentId: string, chunkId: string): Promise<void>;
}
