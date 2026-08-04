import { Icon } from "../../../components/ui/Icon";
import type { KnowledgeDocument } from "../types/document";
import { formatFileSize, getDocumentStatusLabel, isDocumentProcessing } from "../utils/documentFormat";

interface DocumentListProps {
  items: KnowledgeDocument[];
  isLoading: boolean;
  onInspect: (document: KnowledgeDocument) => void;
  onDelete: (document: KnowledgeDocument) => void;
  onReprocess: (document: KnowledgeDocument) => void;
}

export function DocumentList({
  items, isLoading, onInspect, onDelete, onReprocess,
}: DocumentListProps) {
  if (isLoading && items.length === 0) {
    return <div className="doc-list-skeleton" aria-label="正在加载文档"><span /><span /><span /></div>;
  }
  if (items.length === 0) {
    return (
      <div className="kb-documents-empty doc-empty">
        <span><Icon name="document" size={24} /></span>
        <strong>暂无文档</strong>
        <p>导入 TXT 或 Markdown 后，系统会在本机解析并生成父子文本块。</p>
      </div>
    );
  }
  return (
    <div className="doc-list" role="list">
      {items.map((document) => (
        <article className="doc-row" role="listitem" key={document.id}>
          <span className="doc-file-icon">{document.filename.toLocaleLowerCase().endsWith(".md") ? "MD" : "TXT"}</span>
          <div className="doc-row-copy">
            <strong title={document.filename}>{document.filename}</strong>
            <small>{formatFileSize(document.size_bytes)} · {document.parent_chunk_count} Parent · {document.child_chunk_count} Child</small>
            {isDocumentProcessing(document.status) ? <i><b style={{ width: `${document.progress}%` }} /></i> : null}
            {document.error_message ? <em>{document.error_message}</em> : null}
          </div>
          <span className={`doc-status doc-status--${document.status}`}>
            {getDocumentStatusLabel(document.status)}
          </span>
          <div className="doc-row-actions">
            {document.status === "chunked" || document.status === "ready" ? (
              <button type="button" aria-label={`检查 ${document.filename} 的文本块`} onClick={() => onInspect(document)}><Icon name="layers" size={15} />文本块</button>
            ) : null}
            {document.status === "failed" ? (
              <button type="button" onClick={() => onReprocess(document)}><Icon name="refresh" size={14} />重试</button>
            ) : null}
            <button className="is-danger" type="button" aria-label={`删除 ${document.filename}`} onClick={() => onDelete(document)}><Icon name="trash" size={14} /></button>
          </div>
        </article>
      ))}
    </div>
  );
}
