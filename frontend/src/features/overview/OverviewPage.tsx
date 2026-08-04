import { useEffect, useState } from "react";

import { Icon } from "../../components/ui/Icon";
import { apiRequest } from "../../shared/api/client";
import { useBrowserPath } from "../../shared/hooks/useBrowserPath";
import type { Conversation } from "../chat/types/chat";
import type { SystemMetricsItem } from "../diagnostics/types/diagnostics";
import type { KnowledgeBaseList } from "../knowledge-base/types/knowledgeBase";
import "./styles/overview.css";

interface RecentDocItem {
  id: string;
  filename: string;
  extension: string;
  knowledgeBaseName: string;
  sizeBytes: number;
  chunkCount: number;
  status: "ready" | "working" | "failed";
  updatedAt: string;
}

interface OverviewPageProps {
  onNavigate?: (path: string) => void;
}

export function OverviewPage({ onNavigate }: OverviewPageProps = {}) {
  const { navigate } = useBrowserPath("/overview");
  const [metrics, setMetrics] = useState<SystemMetricsItem | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [recentDocs, setRecentDocs] = useState<RecentDocItem[]>([]);
  const [loading, setLoading] = useState(true);

  const handleNavigate = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      navigate(path);
    }
  };

  useEffect(() => {
    const controller = new AbortController();

    async function loadOverviewData() {
      try {
        const [metricsRes, kbRes, chatRes] = await Promise.allSettled([
          apiRequest<SystemMetricsItem>("/diagnostics/metrics", { signal: controller.signal }),
          apiRequest<KnowledgeBaseList>("/knowledge-bases?limit=20", { signal: controller.signal }),
          apiRequest<{ items: Conversation[] }>("/conversations?limit=5", { signal: controller.signal }),
        ]);

        if (metricsRes.status === "fulfilled") {
          setMetrics(metricsRes.value);
        }

        if (chatRes.status === "fulfilled" && chatRes.value.items) {
          setConversations(chatRes.value.items.slice(0, 4));
        }

        if (kbRes.status === "fulfilled" && kbRes.value.items) {
          const kbs = kbRes.value.items;
          const docPromises = kbs.slice(0, 3).map((kb) =>
            apiRequest<{ items: any[] }>(`/knowledge-bases/${kb.id}/documents?limit=5`, {
              signal: controller.signal,
            }).then((res) =>
              (res.items || []).map((doc) => ({
                id: doc.id,
                filename: doc.filename,
                extension: doc.filename.split(".").pop()?.toUpperCase() ?? "DOC",
                knowledgeBaseName: kb.name,
                sizeBytes: doc.file_size_bytes ?? 1024 * 1024,
                chunkCount: doc.parent_chunk_count ?? 0,
                status: (doc.status === "ready" ? "ready" : doc.status === "failed" ? "failed" : "working") as "ready" | "working" | "failed",
                updatedAt: doc.updated_at ?? doc.created_at,
              })),
            ).catch(() => []),
          );
          const docsNested = await Promise.all(docPromises);
          const docsFlattened = docsNested.flat().slice(0, 4);
          setRecentDocs(docsFlattened);
        }
      } catch {
        // 网络或降级由界面容错显示
      } finally {
        setLoading(false);
      }
    }

    loadOverviewData();

    return () => controller.abort();
  }, []);

  const formatSize = (bytes: number) => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${Math.round(bytes / 1024)} KB`;
  };

  const formatRelativeTime = (isoString: string) => {
    if (!isoString) return "刚刚";
    const date = new Date(isoString);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - date.getTime()) / 60000);
    if (diffMin < 1) return "刚刚";
    if (diffMin < 60) return `${diffMin} 分钟前`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours} 小时前`;
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  };

  const activeDoc = recentDocs.find((d) => d.status === "working");
  const isPipelineWorking = Boolean(activeDoc);

  return (
    <section className="overview-page">
      <div className="overview-heading">
        <div>
          <h1>概览</h1>
          <p>你的资料已经整理就绪，随时可以开始提问。</p>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={() => handleNavigate("/chat")}
        >
          <Icon name="spark" size={15} />
          开始问答
        </button>
      </div>

      <div className="overview-metric-strip">
        <button
          className="overview-metric"
          type="button"
          onClick={() => handleNavigate("/knowledge-bases")}
        >
          <span>知识库</span>
          <strong>{metrics ? metrics.knowledge_base_count : "—"}</strong>
          <small>彼此独立的资料空间</small>
        </button>

        <button
          className="overview-metric"
          type="button"
          onClick={() => handleNavigate("/knowledge-bases")}
        >
          <span>文档</span>
          <strong>{metrics ? metrics.document_count : "—"}</strong>
          <small>
            {metrics ? `${metrics.document_count} 篇已可检索` : "资料就绪"}
          </small>
        </button>

        <button
          className="overview-metric"
          type="button"
          onClick={() => handleNavigate("/chat")}
        >
          <span>对话</span>
          <strong>{metrics ? metrics.conversation_count : "—"}</strong>
          <small>
            {conversations.length > 0
              ? `最近一次在 ${formatRelativeTime(conversations[0].updated_at)}`
              : "从本地知识库中问答"}
          </small>
        </button>
      </div>

      <div className="overview-dashboard-grid">
        <section className="overview-block">
          <div className="overview-section-heading">
            <div>
              <h2>最近文档</h2>
              <p>最新导入和处理状态</p>
            </div>
            <button
              className="overview-text-button"
              type="button"
              onClick={() => handleNavigate("/knowledge-bases")}
            >
              查看全部
              <Icon name="arrow" size={14} />
            </button>
          </div>

          <div className="overview-document-list">
            {recentDocs.length > 0 ? (
              recentDocs.map((doc) => (
                <button
                  key={doc.id}
                  className="overview-document-row"
                  type="button"
                  onClick={() => handleNavigate("/knowledge-bases")}
                >
                  <div
                    className={`overview-file-icon ${
                      doc.extension === "MD" || doc.extension === "MARKDOWN"
                        ? "markdown"
                        : doc.extension === "PDF"
                        ? "pdf"
                        : "text"
                    }`}
                  >
                    {doc.extension.slice(0, 3)}
                  </div>
                  <div className="overview-document-copy">
                    <strong>{doc.filename}</strong>
                    <small>
                      {doc.knowledgeBaseName} · {formatSize(doc.sizeBytes)}
                    </small>
                  </div>
                  <span
                    className={`overview-state ${
                      doc.status === "ready"
                        ? "ready"
                        : doc.status === "failed"
                        ? "error"
                        : "working"
                    }`}
                  >
                    <i />
                    {doc.status === "ready"
                      ? "可检索"
                      : doc.status === "failed"
                      ? "索引失败"
                      : "生成索引中"}
                  </span>
                  <time>{formatRelativeTime(doc.updatedAt)}</time>
                  <Icon name="arrow" className="overview-row-arrow" size={14} />
                </button>
              ))
            ) : (
              <div style={{ padding: "30px 20px", textAlign: "center", color: "#6d727c" }}>
                {loading ? "正在获取最近文档…" : "暂无文档，请在知识库中导入文档"}
              </div>
            )}
          </div>
        </section>

        <aside className="overview-block">
          <div className="overview-section-heading">
            <div>
              <h2>处理动态</h2>
              <p>文档流水线</p>
            </div>
          </div>

          <div className="overview-pipeline-visual">
            <div className="overview-ring">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" />
                <circle
                  className="ring-value"
                  cx="50"
                  cy="50"
                  r="42"
                  style={{
                    strokeDashoffset: isPipelineWorking ? 84 : 0,
                  }}
                />
              </svg>
              <strong>
                {isPipelineWorking ? "68" : "100"}
                <small>%</small>
              </strong>
            </div>
            <div className="overview-pipeline-info">
              <strong>
                {isPipelineWorking ? "正在建立索引" : "流水线就绪"}
              </strong>
              <p>
                {activeDoc ? activeDoc.filename : "所有文档索引处理就绪"}
              </p>
              <small>
                {isPipelineWorking
                  ? "Embedding · 向量索引生成中"
                  : "支持 Markdown、TXT、PDF 本地解析"}
              </small>
            </div>
          </div>

          <div className="overview-pipeline-steps">
            <span className="done">解析</span>
            <i />
            <span className="done">切片</span>
            <i />
            <span className={isPipelineWorking ? "active" : "done"}>向量化</span>
            <i />
            <span className={isPipelineWorking ? "" : "done"}>索引</span>
          </div>
        </aside>
      </div>

      <section className="overview-block overview-recent-chats">
        <div className="overview-section-heading">
          <div>
            <h2>继续上次对话</h2>
            <p>从你的知识库中接着探索</p>
          </div>
          <button
            className="overview-text-button"
            type="button"
            onClick={() => handleNavigate("/chat")}
          >
            所有对话
            <Icon name="arrow" size={14} />
          </button>
        </div>

        <div className="overview-chat-rail">
          {conversations.length > 0 ? (
            conversations.map((conv, idx) => (
              <button
                key={conv.id}
                className="overview-chat-preview"
                type="button"
                onClick={() => handleNavigate("/chat")}
              >
                <span
                  className={`overview-preview-icon ${
                    idx % 2 === 1 ? "purple" : ""
                  }`}
                >
                  <Icon name="chat" size={16} />
                </span>
                <div>
                  <strong>{conv.title}</strong>
                  <p>基于本地知识库问答上下文</p>
                </div>
                <time>{formatRelativeTime(conv.updated_at)}</time>
              </button>
            ))
          ) : (
            <div style={{ gridColumn: "span 2", padding: "24px", textAlign: "center", color: "#6d727c" }}>
              {loading ? "正在加载问答记录…" : "暂无历史对话，点击「开始问答」发起首个探索"}
            </div>
          )}
        </div>
      </section>
    </section>
  );
}
