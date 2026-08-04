/**
 * RAG 检索链路 Trace 日志观察卡片组件。
 * 展现历史问题的检索耗时、最高 Score 以及查询改写记录。
 */

import type { RetrievalTraceItem } from "../types/diagnostics";
import { formatLatency } from "../utils/diagnosticsUtils";

interface RetrievalTraceViewerProps {
  traces: RetrievalTraceItem[];
}

export function RetrievalTraceViewer({ traces }: RetrievalTraceViewerProps) {
  return (
    <div className="diag-card">
      <div className="diag-card-header">
        <div>
          <h3>RAG 检索链路 Trace 追踪</h3>
          <p>监控问答查询的检索耗时、改写词与最高匹配得分 Top Score</p>
        </div>
        <span style={{ fontSize: "11px", color: "var(--color-muted)", fontFamily: "monospace" }}>
          共 {traces.length} 条
        </span>
      </div>

      <div className="diag-trace-list">
        {traces.length === 0 ? (
          <div style={{ padding: "30px", textAlign: "center", fontSize: "11px", color: "var(--color-muted)" }}>
            尚无检索 Trace 追踪数据
          </div>
        ) : (
          traces.map((trace) => (
            <div key={trace.trace_id} className="diag-trace-item">
              <div className="diag-trace-head">
                <span>{trace.trace_id}</span>
                <span>{new Date(trace.timestamp).toLocaleTimeString()}</span>
              </div>

              <div className="diag-trace-query">问: {trace.query}</div>

              {trace.rewritten_query && (
                <div className="diag-trace-rewrite">改写: {trace.rewritten_query}</div>
              )}

              <div className="diag-trace-meta">
                <span style={{ background: "var(--color-line)", padding: "2px 6px", borderRadius: "4px" }}>
                  Score: {trace.top_score ?? "--"}
                </span>
                <span>候选 Chunk: {trace.retrieved_chunks_count} 条</span>
                <span>检索耗时: {formatLatency(trace.retrieval_latency_ms)}</span>
                {trace.llm_latency_ms && (
                  <span>LLM 耗时: {formatLatency(trace.llm_latency_ms)}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
