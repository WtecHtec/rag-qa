import type {
  ChunkKind,
  DocumentGateway,
  DocumentPage,
  KnowledgeDocument,
  TextChunk,
  TextChunkPage,
} from "../../features/documents/types/document";

const FIXED_TIME = "2026-08-04T08:00:00.000Z";

export function makeDocument(overrides: Partial<KnowledgeDocument> = {}): KnowledgeDocument {
  return {
    id: "doc-1",
    knowledge_base_id: "kb-1",
    filename: "架构设计.md",
    media_type: "text/markdown",
    size_bytes: 2048,
    status: "ready",
    progress: 100,
    parent_chunk_count: 2,
    child_chunk_count: 4,
    error_code: null,
    error_message: null,
    created_at: FIXED_TIME,
    updated_at: FIXED_TIME,
    ...overrides,
  };
}

export class FakeDocumentGateway implements DocumentGateway {
  constructor(public items: KnowledgeDocument[] = []) {}

  async list(_: string, limit: number, offset: number): Promise<DocumentPage> {
    return { items: this.items.slice(offset, offset + limit), total: this.items.length, limit, offset };
  }

  async upload(knowledgeBaseId: string, file: File, onProgress: (value: number) => void) {
    onProgress(100);
    const document = makeDocument({
      id: `doc-${this.items.length + 1}`,
      knowledge_base_id: knowledgeBaseId,
      filename: file.name,
      size_bytes: file.size,
    });
    this.items = [document, ...this.items];
    return document;
  }

  async remove(_: string, documentId: string): Promise<void> {
    this.items = this.items.filter((item) => item.id !== documentId);
  }

  async reprocess(_: string, documentId: string): Promise<KnowledgeDocument> {
    const document = this.items.find((item) => item.id === documentId);
    if (!document) throw new Error("文档不存在");
    return document;
  }

  async listChunks(
    _: string, documentId: string, kind: ChunkKind, parentId: string | null,
    limit: number, offset: number,
  ): Promise<TextChunkPage> {
    const isParent = kind === "parent";
    const item = {
      id: kind === "parent" ? "parent-1" : "child-1",
      document_id: documentId,
      parent_id: parentId,
      kind,
      ordinal: 0,
      heading_path: "架构",
      preview: isParent ? "父块完整内容：包含背景、约束和实现说明。" : "子块局部内容：只包含实现说明。",
      char_count: isParent ? 20 : 16,
      start_offset: 0,
      end_offset: isParent ? 20 : 16,
      manually_edited: false,
    };
    return { items: offset === 0 ? [item] : [], total: 1, limit, offset };
  }

  async getChunk(_: string, documentId: string, chunkId: string): Promise<TextChunk> {
    const isChild = chunkId.startsWith("child");
    const content = isChild
      ? "子块局部内容：只包含实现说明。"
      : "父块完整内容：包含背景、约束和实现说明。";
    return {
      id: chunkId,
      document_id: documentId,
      parent_id: isChild ? "parent-1" : null,
      kind: isChild ? "child" : "parent",
      ordinal: 0,
      heading_path: "架构",
      content,
      char_count: content.length,
      start_offset: 0,
      end_offset: content.length,
      manually_edited: false,
      created_at: FIXED_TIME,
      updated_at: FIXED_TIME,
    };
  }

  async updateChunk(
    knowledgeBaseId: string, documentId: string, chunkId: string, content: string,
  ): Promise<TextChunk> {
    const current = await this.getChunk(knowledgeBaseId, documentId, chunkId);
    return { ...current, content, char_count: content.length, manually_edited: true };
  }

  async removeChunk(): Promise<void> {}
}
