/**
 * 系统设置与连通性测试 API 客户端封装。
 */

import type {
  ProviderTestRequest,
  ProviderTestResponse,
  SystemSettingsRead,
  SystemSettingsUpdate,
} from "../types/settings";

const API_BASE = "/api/v1/settings";

export const settingsApi = {
  /**
   * 获取当前生效的系统配置。
   */
  async getSettings(): Promise<SystemSettingsRead> {
    const res = await fetch(API_BASE);
    if (!res.ok) {
      throw new Error(`获取设置失败: ${res.statusText}`);
    }
    return res.json() as Promise<SystemSettingsRead>;
  },

  /**
   * 增量保存系统配置。
   */
  async updateSettings(payload: SystemSettingsUpdate): Promise<SystemSettingsRead> {
    const res = await fetch(API_BASE, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`保存设置失败: ${res.statusText}`);
    }
    return res.json() as Promise<SystemSettingsRead>;
  },

  /**
   * 测试指定 LLM Provider 连通性。
   */
  async testLlmConnection(payload: ProviderTestRequest): Promise<ProviderTestResponse> {
    const res = await fetch(`${API_BASE}/test-llm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`测试 LLM 连通性失败: ${res.statusText}`);
    }
    return res.json() as Promise<ProviderTestResponse>;
  },
};
