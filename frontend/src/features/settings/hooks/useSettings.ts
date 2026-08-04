/**
 * 系统设置表单状态管理、未保存变动检测、连通性测试与保存 Hook。
 */

import { useCallback, useEffect, useState } from "react";

import { settingsApi } from "../api/settingsApi";
import type {
  LlmConfig,
  ProviderTestResponse,
  SystemSettingsRead,
  SystemSettingsUpdate,
} from "../types/settings";

export function useSettings() {
  const [settings, setSettings] = useState<SystemSettingsRead | null>(null);
  const [draft, setDraft] = useState<SystemSettingsUpdate>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<ProviderTestResponse | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchSettings = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await settingsApi.getSettings();
      setSettings(data);
      setDraft({});
    } catch (err) {
      setNoticeMessage({
        type: "error",
        text: err instanceof Error ? err.message : "读取设置失败",
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchSettings();
  }, [fetchSettings]);

  const updateDraftLlm = (field: keyof LlmConfig, value: unknown) => {
    setDraft((prev) => ({
      ...prev,
      llm: { ...prev.llm, [field]: value },
    }));
  };

  const saveSettings = async () => {
    if (!draft || Object.keys(draft).length === 0) return;
    try {
      setIsSaving(true);
      setNoticeMessage(null);
      const updated = await settingsApi.updateSettings(draft);
      setSettings(updated);
      setDraft({});
      setNoticeMessage({ type: "success", text: "设置已成功保存并同步生效！" });
    } catch (err) {
      setNoticeMessage({
        type: "error",
        text: err instanceof Error ? err.message : "保存设置失败",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const testLlmConnection = async () => {
    const currentLlm = {
      ...settings?.llm,
      ...draft.llm,
    };
    if (!currentLlm.provider || !currentLlm.base_url || !currentLlm.model) return;

    try {
      setIsTesting(true);
      setTestResult(null);
      const result = await settingsApi.testLlmConnection({
        provider: currentLlm.provider,
        api_key: currentLlm.api_key || null,
        base_url: currentLlm.base_url,
        model: currentLlm.model,
      });
      setTestResult(result);
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : "测试发生异常",
        latency_ms: null,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const isDirty = Object.keys(draft).length > 0;

  return {
    settings,
    draft,
    isDirty,
    isLoading,
    isSaving,
    isTesting,
    testResult,
    noticeMessage,
    updateDraftLlm,
    saveSettings,
    testLlmConnection,
    reload: fetchSettings,
  };
}
