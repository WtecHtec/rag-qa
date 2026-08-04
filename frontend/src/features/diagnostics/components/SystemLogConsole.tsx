/**
 * 系统结构化控制台日志组件。
 * 支持按日志级别 (INFO / WARNING / ERROR) 进行卡片筛选。
 */

import { useState } from "react";

import type { LogEventItem } from "../types/diagnostics";

interface SystemLogConsoleProps {
  logs: LogEventItem[];
}

export function SystemLogConsole({ logs }: SystemLogConsoleProps) {
  const [filterLevel, setFilterLevel] = useState<string>("ALL");

  const filteredLogs = logs.filter((log) => {
    if (filterLevel === "ALL") return true;
    return log.level === filterLevel;
  });

  return (
    <div className="diag-card">
      <div className="diag-card-header">
        <div>
          <h3>控制台审计日志</h3>
          <p>系统运行关键逻辑与报错审计事件</p>
        </div>

        <div style={{ display: "flex", gap: "4px", background: "var(--color-line)", padding: "3px", borderRadius: "8px" }}>
          {["ALL", "INFO", "WARNING", "ERROR"].map((lvl) => (
            <button
              key={lvl}
              type="button"
              onClick={() => setFilterLevel(lvl)}
              className={`kb-button ${filterLevel === lvl ? "kb-button--secondary" : "kb-button--quiet"}`}
              style={{ minHeight: "26px", padding: "0 8px", fontSize: "10px" }}
            >
              {lvl === "ALL" ? "全部" : lvl}
            </button>
          ))}
        </div>
      </div>

      <div className="diag-log-console">
        {filteredLogs.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#6b7280" }}>
            未检索到指定级别的日志事件
          </div>
        ) : (
          filteredLogs.map((log, i) => (
            <div key={i} className="diag-log-row">
              <span style={{ color: "#6b7280" }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
              <span className={`diag-log-level-${log.level}`}>[{log.level}]</span>
              <span style={{ color: "#818cf8" }}>[{log.event}]</span>
              <span style={{ flex: 1, color: "#f3f4f6" }}>{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
