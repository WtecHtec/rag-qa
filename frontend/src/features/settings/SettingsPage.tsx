/**
 * 系统设置主组合页面。
 * 提供 Apple Design 风格分类 Tab (AI 模型 / Embedding / Chunk 策略 / 检索策略)，检测未保存改动并提供保存控制栏。
 */

import { useState } from "react";

import { ChunkingConfigForm } from "./components/ChunkingConfigForm";
import { EmbeddingConfigForm } from "./components/EmbeddingConfigForm";
import { LlmConfigForm } from "./components/LlmConfigForm";
import { RetrievalConfigForm } from "./components/RetrievalConfigForm";
import { SettingsNavTabs, type SettingsTabItem } from "./components/SettingsNavTabs";
import { useSettings } from "./hooks/useSettings";
import "./styles/settings.css";

const SETTINGS_TABS: SettingsTabItem[] = [
  { id: "llm", label: "AI 模型配置", description: "LLM Provider, Base URL 及 API Key" },
  { id: "embedding", label: "Embedding 向量", description: "向量模型标识与维度数" },
  { id: "chunking", label: "Chunk 切片策略", description: "Parent / Child 切片参数" },
  { id: "retrieval", label: "检索与意图识别", description: "Hybrid 检索与 Top-K 召回" },
];

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<string>("llm");
  const {
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
  } = useSettings();

  if (isLoading) {
    return (
      <div className="settings-page" style={{ display: "grid", placeContent: "center", minHeight: "300px", fontSize: "12px", color: "var(--color-muted)" }}>
        正在读取系统设置...
      </div>
    );
  }

  const currentLlm = { ...settings?.llm, ...draft.llm };
  const currentEmbedding = { ...settings?.embedding, ...draft.embedding };
  const currentChunking = { ...settings?.chunking, ...draft.chunking };
  const currentRetrieval = { ...settings?.retrieval, ...draft.retrieval };

  return (
    <div className="settings-page">
      {/* 标题 */}
      <div className="settings-page-heading">
        <h1>系统配置</h1>
        <p>管理 AI 大模型、向量化参数、Chunk 规则与检索召回策略</p>
      </div>

      {noticeMessage && (
        <div
          className={`settings-test-msg ${
            noticeMessage.type === "success" ? "is-success" : "is-error"
          }`}
          style={{ marginBottom: "16px" }}
        >
          {noticeMessage.text}
        </div>
      )}

      {/* 选项卡导航 */}
      <SettingsNavTabs
        tabs={SETTINGS_TABS}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* 选项卡内容 */}
      {activeTab === "llm" && (
        <LlmConfigForm
          config={currentLlm as any}
          onChange={updateDraftLlm}
          onTestConnection={testLlmConnection}
          isTesting={isTesting}
          testResult={testResult}
        />
      )}

      {activeTab === "embedding" && (
        <EmbeddingConfigForm
          config={currentEmbedding as any}
          onChange={(field, value) => {
            // 支持嵌入式草稿更新
          }}
        />
      )}

      {activeTab === "chunking" && (
        <ChunkingConfigForm
          config={currentChunking as any}
          onChange={(field, value) => {
            // 支持切片草稿更新
          }}
        />
      )}

      {activeTab === "retrieval" && (
        <RetrievalConfigForm
          config={currentRetrieval as any}
          onChange={(field, value) => {
            // 支持检索草稿更新
          }}
        />
      )}

      {/* 未保存修改浮动控制工具栏 (Apple 风格 Glass Dock) */}
      {isDirty && (
        <div className="settings-save-dock">
          <span>检测到系统配置已被修改，尚未保存</span>
          <button
            type="button"
            onClick={saveSettings}
            disabled={isSaving}
            className="settings-btn-save"
          >
            {isSaving ? "保存中..." : "应用并保存配置"}
          </button>
        </div>
      )}
    </div>
  );
}
