import { Icon } from "../../../components/ui/Icon";
import type { TextChunk } from "../types/document";

interface ParentChunkEditorProps {
  chunk: TextChunk | null;
  draft: string;
  isBusy: boolean;
  onDraftChange: (content: string) => void;
  onSave: () => void;
  onDelete: () => void;
}

export function ParentChunkEditor({
  chunk,
  draft,
  isBusy,
  onDraftChange,
  onSave,
  onDelete,
}: ParentChunkEditorProps) {
  if (!chunk) return <p className="chunk-loading">正在读取 Parent…</p>;

  return (
    <section className="chunk-parent-editor" aria-label="Parent 编辑器">
      <header className="chunk-section-heading">
        <div>
          <strong>Parent #{chunk.ordinal + 1}</strong>
          <small>{chunk.heading_path || "无标题层级"} · {chunk.char_count} 字符</small>
        </div>
        {chunk.manually_edited ? <em>已人工编辑</em> : null}
      </header>
      <textarea
        value={draft}
        maxLength={20_000}
        aria-label="Parent 文本内容"
        onChange={(event) => onDraftChange(event.target.value)}
      />
      <div className="chunk-inline-actions">
        <span>保存 Parent 会按最新内容重新生成所属 Child</span>
        <button
          className="kb-button kb-button--danger"
          type="button"
          disabled={isBusy}
          onClick={onDelete}
        >
          <Icon name="trash" size={14} />删除 Parent
        </button>
        <button
          className="kb-button kb-button--primary"
          type="button"
          disabled={isBusy || !draft.trim()}
          onClick={onSave}
        >
          {isBusy ? "保存中…" : "保存 Parent"}
        </button>
      </div>
    </section>
  );
}
