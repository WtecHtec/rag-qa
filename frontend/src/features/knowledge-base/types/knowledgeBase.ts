export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  document_count: number;
  ready_document_count: number;
  failed_document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBasePage {
  items: KnowledgeBase[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateKnowledgeBaseInput {
  name: string;
  description: string;
}

export interface UpdateKnowledgeBaseInput {
  name?: string;
  description?: string;
}

export interface ListKnowledgeBasesInput {
  query?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

export interface KnowledgeBaseGateway {
  list(input?: ListKnowledgeBasesInput): Promise<KnowledgeBasePage>;
  create(input: CreateKnowledgeBaseInput): Promise<KnowledgeBase>;
  update(id: string, input: UpdateKnowledgeBaseInput): Promise<KnowledgeBase>;
  remove(id: string): Promise<void>;
}

