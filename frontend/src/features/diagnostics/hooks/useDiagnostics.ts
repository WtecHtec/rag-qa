/**
 * 诊断与 Analytics 页面数据加载与自动刷新 Hook。
 */

import { useCallback, useEffect, useState } from "react";

import { diagnosticsApi } from "../api/diagnosticsApi";
import type {
  FeedbackStatsResponse,
  LogEventItem,
  RetrievalTraceItem,
  SystemHealthResponse,
  SystemMetricsResponse,
} from "../types/diagnostics";

export function useDiagnostics(autoRefreshIntervalMs = 15000) {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [metrics, setMetrics] = useState<SystemMetricsResponse | null>(null);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStatsResponse | null>(null);
  const [traces, setTraces] = useState<RetrievalTraceItem[]>([]);
  const [logs, setLogs] = useState<LogEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAllData = useCallback(async () => {
    try {
      setError(null);
      const [hRes, mRes, fRes, tRes, lRes] = await Promise.all([
        diagnosticsApi.getHealth().catch(() => null),
        diagnosticsApi.getMetrics().catch(() => null),
        diagnosticsApi.getFeedbackStats().catch(() => null),
        diagnosticsApi.getTraces(15).catch(() => ({ items: [], total: 0 })),
        diagnosticsApi.getLogs(undefined, 30).catch(() => ({ items: [], total: 0 })),
      ]);

      if (hRes) setHealth(hRes);
      if (mRes) setMetrics(mRes);
      if (fRes) setFeedbackStats(fRes);
      if (tRes) setTraces(tRes.items);
      if (lRes) setLogs(lRes.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "获取诊断数据失败");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAllData();

    if (autoRefreshIntervalMs > 0) {
      const timer = setInterval(() => {
        void fetchAllData();
      }, autoRefreshIntervalMs);
      return () => clearInterval(timer);
    }
  }, [fetchAllData, autoRefreshIntervalMs]);

  return {
    health,
    metrics,
    feedbackStats,
    traces,
    logs,
    isLoading,
    error,
    refresh: fetchAllData,
  };
}
