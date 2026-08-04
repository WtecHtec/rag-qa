/**
 * 诊断与系统状态页面组装组件。
 * 组合系统基础设施健康度探针、AI 问答反馈与重新生成统计分析，以及系统控制台日志。
 */

import { ComponentStatusGrid } from "./components/ComponentStatusGrid";
import { FeedbackMetricsCard } from "./components/FeedbackMetricsCard";
import { HealthOverviewCard } from "./components/HealthOverviewCard";
import { SystemLogConsole } from "./components/SystemLogConsole";
import { useDiagnostics } from "./hooks/useDiagnostics";
import "./styles/diagnostics.css";

export function DiagnosticsPage() {
  const { health, metrics, feedbackStats, logs, isLoading, error, refresh } =
    useDiagnostics(15000);

  return (
    <div className="diag-page">
      {/* 顶部标题与说明 */}
      <div className="diag-page-heading">
        <h1>系统诊断</h1>
        <p>实时监测基础设施联通性、问答满意度反馈与控制台审计日志</p>
      </div>

      {error && (
        <div className="kb-error-notice">
          <div>
            <strong>发生诊断异常</strong>
            <small>{error}</small>
          </div>
        </div>
      )}

      {/* 1. 整体运行状态与资源统计 */}
      <HealthOverviewCard
        health={health}
        metrics={metrics}
        onRefresh={refresh}
        isLoading={isLoading}
      />

      {/* 2. 组件探针网格 */}
      {health?.components && <ComponentStatusGrid components={health.components} />}

      {/* 3. AI 反馈与重新生成统计卡片 */}
      <div style={{ marginTop: "20px" }}>
        <FeedbackMetricsCard stats={feedbackStats} />
      </div>

      {/* 4. 控制台审计日志 */}
      <div style={{ marginTop: "20px" }}>
        <SystemLogConsole logs={logs} />
      </div>
    </div>
  );
}
