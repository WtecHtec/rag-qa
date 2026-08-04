/**
 * 诊断与系统 Analytics 数据结构 TypeScript 定义。
 */

export interface ComponentStatus {
  /** 组件名称 Identifier */
  name: string;
  /** 组件状态 */
  status: "healthy" | "degraded" | "unhealthy";
  /** 描述文字或诊断堆栈 */
  details: string;
  /** 探针延迟 (ms) */
  latency_ms: number | null;
}

export interface SystemHealthResponse {
  /** 总体健康度 */
  overall_status: "healthy" | "degraded" | "unhealthy";
  /** 检查时间 */
  checked_at: string;
  /** 组件列表 */
  components: ComponentStatus[];
}

export interface SystemMetricsResponse {
  /** 知识库总数量 */
  knowledge_base_count: number;
  /** 文档总数 */
  document_count: number;
  /** 就绪文档数 */
  ready_document_count: number;
  /** Chunk 总向量数 */
  total_chunks_count: number;
  /** 会话数 */
  conversation_count: number;
  /** 消息数 */
  message_count: number;
  /** 存储总字节数 */
  storage_size_bytes: number;
}

export interface FeedbackReasonStat {
  /** 点踩原因描述 */
  reason: string;
  /** 频次 count */
  count: number;
  /** 占比 (0-100) */
  percentage: number;
}

export interface FeedbackStatsResponse {
  /** 收到反馈的总消息数 */
  total_feedbacks: number;
  /** 点赞总数 */
  up_count: number;
  /** 点踩总数 */
  down_count: number;
  /** 好评率 (0-100) */
  up_rate: number;
  /** 重新生成总次数 */
  regeneration_count: number;
  /** 点踩原因分布统计 */
  reason_stats: FeedbackReasonStat[];
}

export interface RecalledChunkDetail {
  /** 所属文档名称 */
  document_name: string;
  /** 标题层级路径 */
  heading_path: string;
  /** 匹配得分 */
  score: number;
  /** Child Chunk 预览 */
  child_preview: string;
  /** Parent Chunk 完整上下文 */
  parent_content: string;
}

export interface RetrievalTraceItem {
  /** Trace ID */
  trace_id: string;
  /** 原始 Query */
  query: string;
  /** 改写 Query */
  rewritten_query: string | null;
  /** 意图类型 */
  intent_category: string | null;
  /** 候选 Chunk 条数 */
  retrieved_chunks_count: number;
  /** 最高相似度得分 */
  top_score: number | null;
  /** 检索耗时 (ms) */
  retrieval_latency_ms: number;
  /** LLM 生成耗时 (ms) */
  llm_latency_ms: number | null;
  /** 发生时间 */
  timestamp: string;
  /** AI 最终生成回复 */
  ai_response: string | null;
  /** 召回的 Chunk 细节列表 */
  recalled_chunks: RecalledChunkDetail[];
}

export interface RetrievalTraceListResponse {
  items: RetrievalTraceItem[];
  total: number;
}

export interface LogEventItem {
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR";
  event: string;
  message: string;
  trace_id: string | null;
}

export interface LogEventListResponse {
  items: LogEventItem[];
  total: number;
}
