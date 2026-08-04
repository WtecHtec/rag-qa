/**
 * Embedding 向量模型与维度参数表单组件。
 */

import type { EmbeddingConfig } from "../types/settings";

interface EmbeddingConfigFormProps {
  config: EmbeddingConfig;
  onChange: (field: keyof EmbeddingConfig, value: unknown) => void;
}

export function EmbeddingConfigForm({ config, onChange }: EmbeddingConfigFormProps) {
  return (
    <div className="settings-form-card">
      <div className="settings-form-head">
        <h3>Embedding 文本向量模型配置</h3>
        <p>配置文本 Chunk 向量化编码器模型名称、向量维度数与批处理 Cache</p>
      </div>

      <div className="settings-grid">
        {/* Model Name */}
        <div className="settings-field is-full">
          <label>Embedding 模型标识 (如 BAAI/bge-small-zh-v1.5)</label>
          <input
            type="text"
            value={config.model_name}
            onChange={(e) => onChange("model_name", e.target.value)}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Dimensions */}
        <div className="settings-field">
          <label>向量维度数 (Dimensions)</label>
          <input
            type="number"
            value={config.dimensions}
            onChange={(e) => onChange("dimensions", parseInt(e.target.value, 10))}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Batch Size */}
        <div className="settings-field">
          <label>批处理大小 (Batch Size)</label>
          <input
            type="number"
            value={config.batch_size}
            onChange={(e) => onChange("batch_size", parseInt(e.target.value, 10))}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Cache Path */}
        <div className="settings-field is-full">
          <label>本地模型缓存路径 (Cache Path)</label>
          <input
            type="text"
            readOnly
            value={config.cache_path}
            style={{ fontFamily: "monospace", opacity: 0.6, cursor: "not-allowed" }}
          />
        </div>
      </div>
    </div>
  );
}
