/**
 * RAG 检索链路 Trace 独立分析页面。
 * 提供完整的问答 Trace 数据浏览、检索查询词匹配、改写词对比、AI 回复内容与召回 Chunk 明细 Drawer/Modal。
 */

import { useState } from "react";

import { useDiagnostics } from "../diagnostics/hooks/useDiagnostics";
import type { RetrievalTraceItem } from "../diagnostics/types/diagnostics";
import { formatLatency } from "../diagnostics/utils/diagnosticsUtils";
import "./styles/analytics.css";

export function AnalyticsPage() {
  const { traces, isLoading, error, refresh } = useDiagnostics(10000);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTrace, setSelectedTrace] = useState<RetrievalTraceItem | null>(null);

  const filteredTraces = traces.filter((t) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.query.toLowerCase().includes(q) ||
      t.trace_id.toLowerCase().includes(q) ||
      (t.rewritten_query && t.rewritten_query.toLowerCase().includes(q)) ||
      (t.ai_response && t.ai_response.toLowerCase().includes(q))
    );
  });

  return (
    <div className="analytics-page">
      {/* 标题 */}
      <div className="analytics-heading">
        <h1>RAG 检索链路 Trace 追踪</h1>
        <p>独立审计与排查每次问答的核心检索词改写、召回 Chunk 切片、AI 最终回复与全链路耗时</p>
      </div>

      {error && (
        <div className="kb-error-notice">
          <div>
            <strong>读取 Trace 产生异常</strong>
            <small>{error}</small>
          </div>
        </div>
      )}

      <div className="analytics-card">
        {/* 工具栏：搜索框与刷新按钮 */}
        <div className="analytics-toolbar">
          <div className="analytics-search-box">
            <input
              type="text"
              placeholder="搜索 Trace ID / 用户问题 / 改写词 / AI 回复..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <button
            type="button"
            onClick={refresh}
            disabled={isLoading}
            className="diag-btn"
          >
            {isLoading ? "加载中..." : "刷新 Trace 记录"}
          </button>
        </div>

        {/* Trace 列表数据 */}
        {filteredTraces.length === 0 ? (
          <div className="analytics-empty-state">
            <h3>尚未发现检索 Trace 记录</h3>
            <p>去「问答」页面提出针对知识库的问题后，即可在此查看实时生成的 RAG 检索链路 Trace。</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="analytics-trace-table">
              <thead>
                <tr>
                  <th>Trace ID</th>
                  <th>原始用户提问</th>
                  <th>改写检索词 (Rewrite)</th>
                  <th>召回 Chunk 数</th>
                  <th>最高相似度 (Score)</th>
                  <th>检索耗时</th>
                  <th>LLM 生成耗时</th>
                  <th>时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredTraces.map((trace) => (
                  <tr key={trace.trace_id}>
                    <td style={{ fontFamily: "monospace", fontSize: "11px", fontWeight: 600 }}>
                      {trace.trace_id}
                    </td>
                    <td style={{ fontWeight: 600, maxWidth: "180px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {trace.query}
                    </td>
                    <td style={{ color: "var(--color-accent)", maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {trace.rewritten_query ?? "--"}
                    </td>
                    <td>{trace.retrieved_chunks_count} 条</td>
                    <td>
                      <span className="diag-badge is-healthy">
                        {trace.top_score ?? "--"}
                      </span>
                    </td>
                    <td style={{ fontFamily: "monospace" }}>
                      {formatLatency(trace.retrieval_latency_ms)}
                    </td>
                    <td style={{ fontFamily: "monospace" }}>
                      {trace.llm_latency_ms ? formatLatency(trace.llm_latency_ms) : "--"}
                    </td>
                    <td style={{ fontSize: "11px", color: "var(--color-muted)" }}>
                      {new Date(trace.timestamp).toLocaleTimeString()}
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => setSelectedTrace(trace)}
                        className="kb-button kb-button--quiet"
                        style={{ minHeight: "26px", padding: "0 8px", fontSize: "11px" }}
                      >
                        查看明细
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 详细模态弹框 Drawer */}
      {selectedTrace && (
        <div className="analytics-modal-scrim" onClick={() => setSelectedTrace(null)}>
          <div className="analytics-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="analytics-modal-head">
              <div>
                <h3>Trace 追踪明细 ({selectedTrace.trace_id})</h3>
                <p style={{ margin: "4px 0 0", color: "var(--color-muted)", fontSize: "11px" }}>
                  请求时间: {new Date(selectedTrace.timestamp).toLocaleString()}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTrace(null)}
                className="kb-button kb-button--quiet"
                style={{ padding: "4px 8px" }}
              >
                关闭
              </button>
            </div>

            {/* 1. 提问与改写 */}
            <div className="analytics-detail-item">
              <label>原始用户提问 (User Query)</label>
              <div>{selectedTrace.query}</div>
            </div>

            <div className="analytics-detail-item">
              <label>意图管线改写词 (Rewritten Query)</label>
              <div>{selectedTrace.rewritten_query ?? "未触发改写，直接使用原词检索"}</div>
            </div>

            {/* 2. AI 最终回复 */}
            <div className="analytics-detail-item">
              <label>AI 最终回复内容 (AI Response)</label>
              <div style={{ whiteSpace: "pre-wrap", maxHeight: "200px", overflowY: "auto" }}>
                {selectedTrace.ai_response || "(暂无回复内容或生成尚未完成)"}
              </div>
            </div>

            {/* 3. 性能指标 */}
            <div className="analytics-detail-item">
              <label>检索与生成耗时 (Performance)</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                <span>最高相似度: <strong>{selectedTrace.top_score ?? "--"}</strong></span>
                <span>召回 Chunk 数: <strong>{selectedTrace.retrieved_chunks_count} 条</strong></span>
                <span>检索耗时: <strong>{formatLatency(selectedTrace.retrieval_latency_ms)}</strong></span>
                <span>生成耗时: <strong>{selectedTrace.llm_latency_ms ? formatLatency(selectedTrace.llm_latency_ms) : "--"}</strong></span>
              </div>
            </div>

            {/* 4. 召回的 Chunk 内容列表 */}
            <div className="analytics-detail-item">
              <label>召回的 Chunk 节点明细 ({selectedTrace.recalled_chunks?.length ?? 0} 条)</label>
              {selectedTrace.recalled_chunks && selectedTrace.recalled_chunks.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "6px" }}>
                  {selectedTrace.recalled_chunks.map((chunk, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "12px",
                        borderRadius: "var(--radius-small)",
                        border: "1px solid var(--color-line)",
                        background: "var(--color-surface-solid)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "11px", fontWeight: 600 }}>
                        <span style={{ color: "var(--color-accent)" }}>
                          📄 {chunk.document_name} {chunk.heading_path ? `> ${chunk.heading_path}` : ""}
                        </span>
                        <span className="diag-badge is-healthy">
                          匹配得分: {chunk.score.toFixed(3)}
                        </span>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--color-text)", marginBottom: "4px" }}>
                        <strong>Child 预览:</strong> {chunk.child_preview}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--color-muted)", whiteSpace: "pre-wrap", maxHeight: "120px", overflowY: "auto", background: "color-mix(in srgb, var(--color-muted) 5%, transparent)", padding: "6px 8px", borderRadius: "4px" }}>
                        <strong>Parent 上下文:</strong> {chunk.parent_content}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "var(--color-muted)", fontSize: "11px", fontStyle: "italic" }}>
                  本次问答未命中有价值的知识库 Chunk 或未触发 RAG 检索。
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
