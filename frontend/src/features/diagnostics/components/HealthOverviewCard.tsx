/**
 * 整体健康度与系统容量仪表卡片组件。
 * 遵守 Apple Design 材质与平滑过渡规范。
 */

import type { SystemHealthResponse, SystemMetricsResponse } from "../types/diagnostics";
import { formatBytes, getStatusBadgeInfo } from "../utils/diagnosticsUtils";

interface HealthOverviewCardProps {
  health: SystemHealthResponse | null;
  metrics: SystemMetricsResponse | null;
  onRefresh: () => void;
  isLoading: boolean;
}

export function HealthOverviewCard({
  health,
  metrics,
  onRefresh,
  isLoading,
}: HealthOverviewCardProps) {
  const statusInfo = getStatusBadgeInfo(health?.overall_status || "healthy");
  const isDegraded = health?.overall_status === "degraded";
  const isUnhealthy = health?.overall_status === "unhealthy";

  return (
    <div className="diag-card">
      <div className="diag-card-header">
        <div className="diag-card-title">
          <div
            className={`diag-status-dot${
              isUnhealthy ? " is-unhealthy" : isDegraded ? " is-degraded" : ""
            }`}
          >
            <span />
          </div>
          <div>
            <h3>系统运行状态</h3>
            <p>实时探针与整体基础设施状态检测</p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            className={`diag-badge${
              isUnhealthy
                ? " is-unhealthy"
                : isDegraded
                ? " is-degraded"
                : " is-healthy"
            }`}
          >
            {statusInfo.label}
          </span>
          <button
            type="button"
            onClick={onRefresh}
            disabled={isLoading}
            className="diag-btn"
          >
            {isLoading ? "刷新中..." : "刷新探针"}
          </button>
        </div>
      </div>

      {/* 4 维容量/数量数据卡片 */}
      <div className="diag-metrics-grid">
        <div className="diag-metric-item">
          <label>知识库总量</label>
          <strong>{metrics?.knowledge_base_count ?? 0}</strong>
        </div>

        <div className="diag-metric-item">
          <label>已就绪文档 / 总数</label>
          <strong>
            {metrics?.ready_document_count ?? 0} / {metrics?.document_count ?? 0}
          </strong>
        </div>

        <div className="diag-metric-item">
          <label>向量 Chunk 总数</label>
          <strong>{metrics?.total_chunks_count ?? 0}</strong>
        </div>

        <div className="diag-metric-item">
          <label>存储占用总容量</label>
          <strong>{formatBytes(metrics?.storage_size_bytes ?? 0)}</strong>
        </div>
      </div>
    </div>
  );
}
