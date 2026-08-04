import { Icon } from "../../../components/ui/Icon";
import type { TextChunk, TextChunkSummary } from "../types/document";

interface ChildChunkPanelProps {
  parentOrdinal: number | null;
  children: TextChunkSummary[];
  selectedChild: TextChunk | null;
  draft: string;
  isBusy: boolean;
  onSelect: (child: TextChunkSummary) => void;
  onDraftChange: (content: string) => void;
  onSave: () => void;
  onDelete: () => void;
}

export function ChildChunkPanel({
  parentOrdinal,
  children,
  selectedChild,
  draft,
  isBusy,
  onSelect,
  onDraftChange,
  onSave,
  onDelete,
}: ChildChunkPanelProps) {
  return (
    <section className="chunk-child-panel" aria-label="Child 文本块">
      <header className="chunk-section-heading">
        <div>
          <strong>Child</strong>
          <small>{children.length > 0 ? `${children.length} 个局部检索块` : "无需拆分"}</small>
        </div>
      </header>

      {children.length === 0 ? (
        <div className="chunk-child-empty" role="status">
          <strong>当前 Parent 缺少 Child</strong>
          <p>每个 Parent 至少应有一个用于 Embedding 的 Child，请重新处理该文档。</p>
        </div>
      ) : (
        <div className="chunk-child-rail" aria-label="Child 列表">
          {children.map((child) => (
            <button
              key={child.id}
              type="button"
              className={selectedChild?.id === child.id ? "is-selected" : ""}
              aria-pressed={selectedChild?.id === child.id}
              onClick={() => onSelect(child)}
            >
              <span>Child #{child.ordinal + 1}</span>
              <p>{child.preview}</p>
              <small>{child.char_count} 字符</small>
            </button>
          ))}
        </div>
      )}

      {children.length > 0 && !selectedChild ? (
        <p className="chunk-child-hint">选择一个 Child 后，会在这里打开独立编辑区；Parent 内容始终保留在上方。</p>
      ) : null}

      {selectedChild ? (
        <div className="chunk-child-editor">
          <header>
            <div>
              <strong>Child #{selectedChild.ordinal + 1} 详情</strong>
              <small>所属 Parent #{parentOrdinal === null ? "-" : parentOrdinal + 1} · {selectedChild.char_count} 字符</small>
            </div>
            {selectedChild.manually_edited ? <em>已人工编辑</em> : null}
          </header>
          <textarea
            value={draft}
            maxLength={20_000}
            aria-label="Child 文本内容"
            onChange={(event) => onDraftChange(event.target.value)}
          />
          <div className="chunk-inline-actions">
            <span>只修改当前 Child，不影响上方 Parent</span>
            <button
              className="kb-button kb-button--danger"
              type="button"
              disabled={isBusy}
              onClick={onDelete}
            >
              <Icon name="trash" size={14} />删除 Child
            </button>
            <button
              className="kb-button kb-button--primary"
              type="button"
              disabled={isBusy || !draft.trim()}
              onClick={onSave}
            >
              {isBusy ? "保存中…" : "保存 Child"}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
