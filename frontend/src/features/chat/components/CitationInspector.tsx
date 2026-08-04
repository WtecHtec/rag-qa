import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../../../components/ui/Icon";
import type { Citation } from "../types/chat";
import { splitCitationContent } from "../utils/splitCitationContent";

interface CitationInspectorProps {
  citation: Citation | null;
  knowledgeBaseName?: string;
  onClose: () => void;
}

export function CitationInspector({
  citation,
  knowledgeBaseName,
  onClose,
}: CitationInspectorProps) {
  const highlighted = useMemo(
    () => citation ? splitCitationContent(citation) : null,
    [citation],
  );
  const matchedContentRef = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!highlighted) return;
    // 面板展开后把真实命中区间放到视口中央，避免用户误以为顶部正文就是命中点。
    const frameId = window.requestAnimationFrame(() => {
      matchedContentRef.current?.scrollIntoView?.({ block: "start" });
    });
    return () => window.cancelAnimationFrame(frameId);
  }, [citation?.id, highlighted]);

  if (!citation) return null;

  const copySource = async () => {
    await navigator.clipboard.writeText(citation.parent_content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <aside className="chat-source-inspector" aria-label="引用来源">
      <header>
        <div><small>来源 {citation.citation_number}</small><h2>{citation.document_name}</h2></div>
        <button type="button" aria-label="关闭来源" onClick={onClose}><Icon name="close" size={16} /></button>
      </header>
      <div className="chat-source-meta">
        {knowledgeBaseName && <span>{knowledgeBaseName}</span>}
        <span>命中子块</span>
        <span>相似度 {Math.round(citation.score * 100)}%</span>
      </div>
      {citation.heading_path && <p className="chat-source-path">{citation.heading_path}</p>}
      <article>
        {highlighted ? (
          <p>
            {highlighted.before}
            <mark ref={matchedContentRef}>{highlighted.match}</mark>
            {highlighted.after}
          </p>
        ) : (
          <><p>{citation.parent_content}</p><blockquote>{citation.child_preview}</blockquote></>
        )}
      </article>
      <footer>
        <p>检索使用命中子块，回答上下文使用完整父块。</p>
        <button type="button" onClick={() => void copySource()}>
          {copied ? <Icon name="check" size={14} /> : <Icon name="copy" size={14} />}
          {copied ? "已复制" : "复制父块内容"}
        </button>
      </footer>
    </aside>
  );
}
