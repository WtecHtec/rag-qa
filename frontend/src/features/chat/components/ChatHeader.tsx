interface ChatHeaderProps {
  title: string;
  readyKnowledgeBaseCount: number;
  readyDocumentCount: number;
}

export function ChatHeader({
  title,
  readyKnowledgeBaseCount,
  readyDocumentCount,
}: ChatHeaderProps) {
  return (
    <header className="chat-header">
      <div>
        <h1>{title}</h1>
        <div className="chat-global-scope" aria-label="回答策略：自动路由">
          <span aria-hidden="true" />
          <strong>智能路由</strong>
          <small>{readyKnowledgeBaseCount} 个空间 · {readyDocumentCount} 篇文档已接入</small>
        </div>
      </div>
    </header>
  );
}
