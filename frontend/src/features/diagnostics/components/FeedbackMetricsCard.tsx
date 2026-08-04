/**
 * AI 回复反馈与重新生成统计分析卡片组件。
 * 展示点赞数、点踩数（含具体改进原因比例）以及重新生成触发频次。
 */

import type { FeedbackStatsResponse } from "../types/diagnostics";

interface FeedbackMetricsCardProps {
  stats: FeedbackStatsResponse | null;
}

export function FeedbackMetricsCard({ stats }: FeedbackMetricsCardProps) {
  if (!stats) {
    return (
      <div className="diag-card" style={{ fontSize: "12px", color: "var(--color-muted)" }}>
        正在加载反馈数据...
      </div>
    );
  }

  return (
    <div className="diag-card">
      <div className="diag-card-header">
        <div>
          <h3>AI 回复质量与反馈分析</h3>
          <p>收集用户点赞 👍、点踩 👎 原因及重新生成上报数据</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <span style={{ fontSize: "24px", fontWeight: 700, color: "var(--color-success)" }}>
            {stats.up_rate}%
          </span>
          <span style={{ display: "block", fontSize: "10px", color: "var(--color-muted)" }}>
            总体满意度
          </span>
        </div>
      </div>

      <div className="diag-feedback-grid">
        <div className="diag-fb-box is-up">
          <div className="diag-fb-box-head">
            <span>点赞数 (👍)</span>
            <strong>{stats.up_count}</strong>
          </div>
          <div style={{ fontSize: "10px", marginTop: "4px", opacity: 0.8 }}>
            回答准确有帮助
          </div>
        </div>

        <div className="diag-fb-box is-down">
          <div className="diag-fb-box-head">
            <span>点踩数 (👎)</span>
            <strong>{stats.down_count}</strong>
          </div>
          <div style={{ fontSize: "10px", marginTop: "4px", opacity: 0.8 }}>
            需要改进与补充
          </div>
        </div>

        <div className="diag-fb-box is-regen">
          <div className="diag-fb-box-head">
            <span>重新生成次数</span>
            <strong>{stats.regeneration_count}</strong>
          </div>
          <div style={{ fontSize: "10px", marginTop: "4px", opacity: 0.8 }}>
            重新生成事件计数
          </div>
        </div>
      </div>

      {/* 点踩原因占比说明 */}
      <div className="diag-fb-reasons">
        <h4>点踩原因占比分布 ({stats.down_count} 次)</h4>

        {stats.reason_stats.length === 0 ? (
          <p style={{ fontSize: "11px", color: "var(--color-muted)", fontStyle: "italic" }}>
            暂无点踩反馈记录
          </p>
        ) : (
          <div>
            {stats.reason_stats.map((item) => (
              <div key={item.reason} className="diag-reason-row">
                <div className="diag-reason-meta">
                  <span>{item.reason}</span>
                  <span style={{ fontFamily: "monospace" }}>
                    {item.count} 次 ({item.percentage}%)
                  </span>
                </div>
                <div className="diag-progress-track">
                  <div
                    className="diag-progress-bar"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
