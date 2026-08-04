import { useEffect, useState } from "react";

import { Dialog } from "../../../components/ui/Dialog";
import { useChunkInspector } from "../hooks/useChunkInspector";
import type { DocumentGateway, KnowledgeDocument } from "../types/document";
import { ChildChunkPanel } from "./ChildChunkPanel";
import { ParentChunkEditor } from "./ParentChunkEditor";

interface ChunkInspectorDialogProps {
  knowledgeBaseId: string;
  document: KnowledgeDocument | null;
  gateway: DocumentGateway;
  onClose: () => void;
  onChanged: () => void;
}

export function ChunkInspectorDialog({
  knowledgeBaseId,
  document,
  gateway,
  onClose,
  onChanged,
}: ChunkInspectorDialogProps) {
  const inspector = useChunkInspector(knowledgeBaseId, document, gateway);
  const [parentDraft, setParentDraft] = useState("");
  const [childDraft, setChildDraft] = useState("");

  useEffect(() => {
    setParentDraft(inspector.selectedParent?.content ?? "");
  }, [inspector.selectedParent]);

  useEffect(() => {
    setChildDraft(inspector.selectedChild?.content ?? "");
  }, [inspector.selectedChild]);

  const saveParent = async () => {
    try {
      await inspector.saveParent(parentDraft);
      onChanged();
    } catch {
      // Hook 已保留可展示错误，组件不再制造未处理的 Promise 拒绝。
    }
  };
  const saveChild = async () => {
    try {
      await inspector.saveChild(childDraft);
      onChanged();
    } catch {
      // Hook 已保留可展示错误，组件不再制造未处理的 Promise 拒绝。
    }
  };
  const deleteParent = async () => {
    await inspector.deleteParent();
    onChanged();
  };
  const deleteChild = async () => {
    await inspector.deleteChild();
    onChanged();
  };

  return (
    <Dialog
      open={document !== null}
      title={document ? `文本块 · ${document.filename}` : "文本块"}
      description="Child 用于向量检索；命中后通过 parent_id 回取上方 Parent 上下文。"
      size="wide"
      closeDisabled={inspector.isSaving}
      onClose={onClose}
      footer={(
        <>
          <span className="chunk-footer-note">每个 Parent 至少包含一个 Child；删除 Parent 会级联删除所属 Child</span>
          <button className="kb-button kb-button--secondary" type="button" onClick={onClose}>完成</button>
        </>
      )}
    >
      <div className="chunk-inspector">
        <aside className="chunk-parent-list">
          <header><strong>Parent</strong><small>{inspector.parentTotal} 个</small></header>
          {inspector.parents.map((parent) => (
            <button
              key={parent.id}
              className={inspector.selectedParent?.id === parent.id ? "is-selected" : ""}
              type="button"
              aria-pressed={inspector.selectedParent?.id === parent.id}
              onClick={() => void inspector.loadParent(parent)}
            >
              <span>#{parent.ordinal + 1}</span>
              <strong>{parent.heading_path || "无标题段落"}</strong>
              <small>{parent.char_count} 字符</small>
            </button>
          ))}
          <nav className="doc-pagination" aria-label="Parent 分页">
            <button
              type="button"
              disabled={inspector.parentOffset === 0}
              onClick={() => inspector.setParentOffset(
                Math.max(0, inspector.parentOffset - inspector.parentPageSize),
              )}
            >上一页</button>
            <button
              type="button"
              disabled={inspector.parentOffset + inspector.parentPageSize >= inspector.parentTotal}
              onClick={() => inspector.setParentOffset(
                inspector.parentOffset + inspector.parentPageSize,
              )}
            >下一页</button>
          </nav>
        </aside>
        <div className="chunk-detail">
          <ParentChunkEditor
            chunk={inspector.selectedParent}
            draft={parentDraft}
            isBusy={inspector.isSaving}
            onDraftChange={setParentDraft}
            onSave={() => void saveParent()}
            onDelete={() => void deleteParent()}
          />
          <ChildChunkPanel
            parentOrdinal={inspector.selectedParent?.ordinal ?? null}
            children={inspector.children}
            selectedChild={inspector.selectedChild}
            draft={childDraft}
            isBusy={inspector.isSaving || inspector.isLoading}
            onSelect={(child) => void inspector.loadChild(child)}
            onDraftChange={setChildDraft}
            onSave={() => void saveChild()}
            onDelete={() => void deleteChild()}
          />
        </div>
      </div>
    </Dialog>
  );
}
