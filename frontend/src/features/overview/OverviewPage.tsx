import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "../../shared/api/health";

export function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal)
      .then(setHealth)
      .catch(() => setError(true));

    return () => controller.abort();
  }, []);

  return (
    <section className="overview-page">
      <header className="page-header">
        <div>
          <h1>概览</h1>
          <p>前后端分离工程已准备就绪。</p>
        </div>
        <div className={`health-badge ${health ? "is-online" : ""}`}>
          <span aria-hidden="true" />
          {health ? "后端服务正常" : error ? "等待后端启动" : "正在检查服务"}
        </div>
      </header>

      <div className="foundation-grid">
        <article>
          <small>前端</small>
          <strong>React + TypeScript</strong>
          <p>路由、功能模块和共享组件已经分层。</p>
        </article>
        <article>
          <small>后端</small>
          <strong>FastAPI</strong>
          <p>API、日志、Trace ID 和 Provider 目录已经建立。</p>
        </article>
        <article>
          <small>连接状态</small>
          <strong>{health?.trace_id ?? "—"}</strong>
          <p>{health ? "本次健康检查 Trace ID" : "启动后端后自动连接"}</p>
        </article>
      </div>
    </section>
  );
}

