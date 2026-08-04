/**
 * 系统设置 TypeScript 数据模型。
 */

export interface LlmConfig {
  provider: string;
  api_key_masked?: string | null;
  api_key?: string | null;
  base_url: string;
  model: string;
  timeout_seconds: number;
  max_tokens: number;
  temperature: number;
}

export interface EmbeddingConfig {
  model_name: string;
  dimensions: number;
  batch_size: number;
  cache_path: string;
}

export interface ChunkingConfig {
  strategy: "parent_child" | "recursive" | "semantic";
  parent_chunk_size: number;
  child_chunk_size: number;
  overlap_size: number;
}

export interface RetrievalConfig {
  mode: "hybrid" | "vector";
  rag_top_k: number;
  intent_classifier_enabled: boolean;
  intent_confidence_threshold: number;
}

export interface SystemSettingsRead {
  llm: LlmConfig;
  embedding: EmbeddingConfig;
  chunking: ChunkingConfig;
  retrieval: RetrievalConfig;
}

export interface SystemSettingsUpdate {
  llm?: Partial<LlmConfig>;
  embedding?: Partial<EmbeddingConfig>;
  chunking?: Partial<ChunkingConfig>;
  retrieval?: Partial<RetrievalConfig>;
}

export interface ProviderTestRequest {
  provider: string;
  api_key?: string | null;
  base_url: string;
  model: string;
}

export interface ProviderTestResponse {
  success: boolean;
  message: string;
  latency_ms: number | null;
}
