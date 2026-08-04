/**
 * 系统设置纯工具函数模块。
 * 包含 Provider 预设选项列举、校验与格式化无副作用纯函数。
 */

export interface ProviderPreset {
  id: string;
  name: string;
  defaultBaseUrl: string;
  defaultModel: string;
}

export const LLM_PROVIDER_PRESETS: ProviderPreset[] = [
  {
    id: "openai_compatible",
    name: "OpenAI Compatible (SiliconFlow / DeepSeek / vLLM)",
    defaultBaseUrl: "https://api.siliconflow.cn/v1",
    defaultModel: "Pro/zai-org/GLM-4.7",
  },
  {
    id: "openai",
    name: "OpenAI 官方 API",
    defaultBaseUrl: "https://api.openai.com/v1",
    defaultModel: "gpt-4o-mini",
  },
  {
    id: "claude",
    name: "Anthropic Claude",
    defaultBaseUrl: "https://api.anthropic.com/v1",
    defaultModel: "claude-3-5-sonnet-20241022",
  },
  {
    id: "gemini",
    name: "Google Gemini",
    defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta",
    defaultModel: "gemini-1.5-flash",
  },
  {
    id: "ollama",
    name: "Ollama (本地运行)",
    defaultBaseUrl: "http://localhost:11434/v1",
    defaultModel: "qwen2.5:7b",
  },
];

/**
 * 根据 Provider ID 获取预设信息。
 */
export function getProviderPreset(providerId: string): ProviderPreset | undefined {
  return LLM_PROVIDER_PRESETS.find((p) => p.id === providerId);
}

/**
 * 校验 Base URL 简单格式。
 */
export function isValidBaseUrl(url: string): boolean {
  if (!url || typeof url !== "string") return false;
  return url.startsWith("http://") || url.startsWith("https://");
}
