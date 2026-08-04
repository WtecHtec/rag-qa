/**
 * RAG 检索策略配置表单组件。
 */

import type { RetrievalConfig } from "../types/settings";

interface RetrievalConfigFormProps {
  config: RetrievalConfig;
  onChange: (field: keyof RetrievalConfig, value: unknown) => void;
}

export function RetrievalConfigForm({ config, onChange }: RetrievalConfigFormProps) {
  return (
    <div className="settings-form-card">
      <div className="settings-form-head">
        <h3>RAG 检索策略与意图分类配置</h3>
        <p>配置 Hybrid 混合检索模式、Top-K 候选召回数量及 Query 理解 Intent 分类器开关</p>
      </div>

      <div className="settings-grid">
        {/* Mode Selector */}
        <div className="settings-field">
          <label>检索模式 (Retrieval Mode)</label>
          <select
            value={config.mode}
            onChange={(e) => onChange("mode", e.target.value)}
          >
            <option value="hybrid">Hybrid 混合检索 (向量 + 关键字关键词融合)</option>
            <option value="vector">Vector 纯向量语义检索</option>
          </select>
        </div>

        {/* Top-K Slider */}
        <div className="settings-field">
          <div className="settings-range-meta">
            <span>召回 Context 数量 (Top-K)</span>
            <span>{config.rag_top_k} 条</span>
          </div>
          <input
            type="range"
            min="1"
            max="20"
            step="1"
            value={config.rag_top_k}
            onChange={(e) => onChange("rag_top_k", parseInt(e.target.value, 10))}
          />
        </div>

        {/* Intent Classifier Switch */}
        <div className="settings-field is-full" style={{ paddingTop: "12px", borderTop: "1px solid var(--color-line)" }}>
          <div style={{ display: "flex", itemsCenter: "center", justifyContent: "space-between" }}>
            <div>
              <span style={{ fontSize: "11px", fontWeight: 600 }}>
                启用意图识别管线 (Intent Classifier Pipeline)
              </span>
              <p style={{ margin: "2px 0 0", color: "var(--color-muted)", fontSize: "10px" }}>
                开启后系统在检索前自动识别 Detail/Summary/General 类别，精准适配检索策略
              </p>
            </div>
            <input
              type="checkbox"
              checked={config.intent_classifier_enabled}
              onChange={(e) => onChange("intent_classifier_enabled", e.target.checked)}
              style={{ width: "18px", height: "18px", cursor: "pointer" }}
            />
          </div>
        </div>

        {/* Intent Threshold */}
        {config.intent_classifier_enabled && (
          <div className="settings-field is-full">
            <div className="settings-range-meta">
              <span>意图置信度阈值 (Confidence Threshold)</span>
              <span>{config.intent_confidence_threshold}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={config.intent_confidence_threshold}
              onChange={(e) =>
                onChange("intent_confidence_threshold", parseFloat(e.target.value))
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
