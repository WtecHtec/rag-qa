import { useEffect, useRef, useState, type ReactNode } from "react";

import { Icon } from "../../../components/ui/Icon";
import type { KnowledgeBase } from "../types/knowledgeBase";
import { formatKnowledgeBaseDate } from "../utils/formatKnowledgeBaseDate";

interface KnowledgeBaseDetailProps {
  knowledgeBase: KnowledgeBase | null;
  onEdit: () => void;
  onDelete: () => void;
  documentsContent?: ReactNode;
}

export function KnowledgeBaseDetail({
  knowledgeBase,
  onEdit,
  onDelete,
  documentsContent,
}: KnowledgeBaseDetailProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const closeMenu = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, [menuOpen]);

  if (!knowledgeBase) {
    return (
      <section className="kb-detail kb-detail--empty">
        <span><Icon name="library" size={28} /></span>
        <h2>选择一个知识库</h2>
        <p>创建或选择知识库后，可以在这里查看详情。</p>
      </section>
    );
  }

  return (
    <section className="kb-detail">
      <header className="kb-detail-header">
        <span className="kb-detail-icon"><Icon name="library" size={24} /></span>
        <div className="kb-detail-title">
          <h2>{knowledgeBase.name}</h2>
          <p>{knowledgeBase.description || "尚未添加描述"}</p>
        </div>
        <div className="kb-more-menu" ref={menuRef}>
          <button
            className="ui-icon-button"
            type="button"
            aria-label="更多操作"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Icon name="more" />
          </button>
          {menuOpen ? (
            <div className="kb-more-popover">
              <button type="button" onClick={() => { setMenuOpen(false); onEdit(); }}>
                <Icon name="edit" size={15} />编辑知识库
              </button>
              <button className="is-danger" type="button" onClick={() => { setMenuOpen(false); onDelete(); }}>
                <Icon name="trash" size={15} />删除知识库
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <div className="kb-metrics" aria-label="知识库统计">
        <span><strong>{knowledgeBase.document_count}</strong> 文档</span>
        <span><strong>{knowledgeBase.chunk_count}</strong> 文本块</span>
        <span><strong>{knowledgeBase.ready_document_count}</strong> 可检索</span>
        <span><strong>{formatKnowledgeBaseDate(knowledgeBase.updated_at)}</strong> 最近更新</span>
      </div>

      {documentsContent ?? (
        <div className="kb-documents-empty">
          <span><Icon name="document" size={24} /></span>
          <strong>暂无文档</strong>
        </div>
      )}
    </section>
  );
}
