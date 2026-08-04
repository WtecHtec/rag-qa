/**
 * 诊断与系统 Analytics API 客户端请求模块。
 */

import type {
  FeedbackStatsResponse,
  LogEventListResponse,
  RetrievalTraceListResponse,
  SystemHealthResponse,
  SystemMetricsResponse,
} from "../types/diagnostics";

const API_BASE = "/api/v1/diagnostics";

/**
 * 诊断 API 请求网关对象。
 */
export const diagnosticsApi = {
  /**
   * 获取系统核心组件健康状态探针。
   */
  async getHealth(): Promise<SystemHealthResponse> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) {
      throw new Error(`获取健康度失败: ${res.statusText}`);
    }
    return res.json() as Promise<SystemHealthResponse>;
  },

  /**
   * 获取系统数据容量与资源指标。
   */
  async getMetrics(): Promise<SystemMetricsResponse> {
    const res = await fetch(`${API_BASE}/metrics`);
    if (!res.ok) {
      throw new Error(`获取系统指标失败: ${res.statusText}`);
    }
    return res.json() as Promise<SystemMetricsResponse>;
  },

  /**
   * 获取 AI 回复点赞、点踩（原因分布）与重新生成统计。
   */
  async getFeedbackStats(): Promise<FeedbackStatsResponse> {
    const res = await fetch(`${API_BASE}/feedback-stats`);
    if (!res.ok) {
      throw new Error(`获取反馈统计失败: ${res.statusText}`);
    }
    return res.json() as Promise<FeedbackStatsResponse>;
  },

  /**
   * 获取最近 RAG 检索 Trace 记录。
   */
  async getTraces(limit = 20): Promise<RetrievalTraceListResponse> {
    const res = await fetch(`${API_BASE}/traces?limit=${limit}`);
    if (!res.ok) {
      throw new Error(`获取检索 Trace 失败: ${res.statusText}`);
    }
    return res.json() as Promise<RetrievalTraceListResponse>;
  },

  /**
   * 获取控制台审计日志列表。
   */
  async getLogs(level?: string, limit = 50): Promise<LogEventListResponse> {
    const params = new URLSearchParams();
    if (level) params.append("level", level);
    params.append("limit", String(limit));

    const res = await fetch(`${API_BASE}/logs?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`获取系统日志失败: ${res.statusText}`);
    }
    return res.json() as Promise<LogEventListResponse>;
  },
};
