/**
 * LLM 模型配置与连通性测试表单组件。
 */

import { useState } from "react";

import type { LlmConfig, ProviderTestResponse } from "../types/settings";
import { LLM_PROVIDER_PRESETS } from "../utils/settingsUtils";

interface LlmConfigFormProps {
  config: LlmConfig;
  onChange: (field: keyof LlmConfig, value: unknown) => void;
  onTestConnection: () => void;
  isTesting: boolean;
  testResult: ProviderTestResponse | null;
}

export function LlmConfigForm({
  config,
  onChange,
  onTestConnection,
  isTesting,
  testResult,
}: LlmConfigFormProps) {
  const [showApiKey, setShowApiKey] = useState(false);

  const handleProviderSelect = (providerId: string) => {
    const preset = LLM_PROVIDER_PRESETS.find((p) => p.id === providerId);
    onChange("provider", providerId);
    if (preset) {
      onChange("base_url", preset.defaultBaseUrl);
      onChange("model", preset.defaultModel);
    }
  };

  return (
    <div className="settings-form-card">
      <div className="settings-form-head">
        <h3>LLM 大语言模型服务配置</h3>
        <p>配置问答推理依赖的 LLM Provider、API 密钥、接口 Endpoint 及模型生成参数</p>
      </div>

      <div className="settings-grid">
        {/* Provider 预设切换 */}
        <div className="settings-field is-full">
          <label>模型 Provider 服务提供商</label>
          <select
            value={config.provider}
            onChange={(e) => handleProviderSelect(e.target.value)}
          >
            {LLM_PROVIDER_PRESETS.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name}
              </option>
            ))}
          </select>
        </div>

        {/* API Key */}
        <div className="settings-field is-full">
          <label>API 密钥 (API Key)</label>
          <div className="settings-field-input-group">
            <input
              type={showApiKey ? "text" : "password"}
              placeholder={
                config.api_key_masked
                  ? `当前 Key: ${config.api_key_masked} (置空保持不变)`
                  : "输入 API 密钥 (如 sk-...)"
              }
              value={config.api_key ?? ""}
              onChange={(e) => onChange("api_key", e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className="settings-btn-toggle"
            >
              {showApiKey ? "隐藏" : "明文"}
            </button>
          </div>
        </div>

        {/* Base URL */}
        <div className="settings-field">
          <label>接口 Endpoint (Base URL)</label>
          <input
            type="text"
            value={config.base_url}
            onChange={(e) => onChange("base_url", e.target.value)}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Model Name */}
        <div className="settings-field">
          <label>模型 Identifier</label>
          <input
            type="text"
            value={config.model}
            onChange={(e) => onChange("model", e.target.value)}
            style={{ fontFamily: "monospace" }}
          />
        </div>

        {/* Temperature */}
        <div className="settings-field">
          <div className="settings-range-meta">
            <span>采样温度 (Temperature)</span>
            <span>{config.temperature}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={config.temperature}
            onChange={(e) => onChange("temperature", parseFloat(e.target.value))}
          />
        </div>

        {/* Max Tokens */}
        <div className="settings-field">
          <label>单次最大 Token 数 (Max Tokens)</label>
          <input
            type="number"
            value={config.max_tokens}
            onChange={(e) => onChange("max_tokens", parseInt(e.target.value, 10))}
            style={{ fontFamily: "monospace" }}
          />
        </div>
      </div>

      {/* 测试连通性按钮与反馈 */}
      <div className="settings-form-actions">
        <button
          type="button"
          onClick={onTestConnection}
          disabled={isTesting}
          className="settings-btn-test"
        >
          {isTesting ? "测试中..." : "测试 Provider 连通性"}
        </button>

        {testResult && (
          <div
            className={`settings-test-msg ${
              testResult.success ? "is-success" : "is-error"
            }`}
          >
            {testResult.message}
            {testResult.latency_ms && ` (${testResult.latency_ms} ms)`}
          </div>
        )}
      </div>
    </div>
  );
}
