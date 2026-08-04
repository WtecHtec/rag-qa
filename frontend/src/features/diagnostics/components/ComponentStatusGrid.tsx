/**
 * 组件探针细节网格卡片组件。
 * 展示数据库、向量库、Embedding、LLM 各引擎的运行状态与延迟。
 */

import type { ComponentStatus } from "../types/diagnostics";
import { formatLatency, getComponentNameInChinese, getStatusBadgeInfo } from "../utils/diagnosticsUtils";

interface ComponentStatusGridProps {
  components: ComponentStatus[];
}

export function ComponentStatusGrid({ components }: ComponentStatusGridProps) {
  if (!components.length) {
    return null;
  }

  return (
    <div className="diag-comp-grid">
      {components.map((comp) => {
        const info = getStatusBadgeInfo(comp.status);
        const isDegraded = comp.status === "degraded";
        const isUnhealthy = comp.status === "unhealthy";

        return (
          <div key={comp.name} className="diag-comp-card">
            <div>
              <div className="diag-comp-header">
                <h4>{getComponentNameInChinese(comp.name)}</h4>
                <span
                  className={`diag-badge${
                    isUnhealthy
                      ? " is-unhealthy"
                      : isDegraded
                      ? " is-degraded"
                      : " is-healthy"
                  }`}
                >
                  {info.label}
                </span>
              </div>
              <p>{comp.details}</p>
            </div>

            <div className="diag-comp-footer">
              <span>探针响应时间</span>
              <span style={{ fontFamily: "monospace", fontWeight: 600 }}>
                {formatLatency(comp.latency_ms)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
