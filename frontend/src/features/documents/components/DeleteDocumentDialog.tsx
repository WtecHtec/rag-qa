import { Dialog } from "../../../components/ui/Dialog";
import type { KnowledgeDocument } from "../types/document";
import type { DocumentErrorMessage } from "../utils/documentError";
import { DocumentErrorNotice } from "./DocumentErrorNotice";

interface DeleteDocumentDialogProps {
  document: KnowledgeDocument | null;
  isDeleting: boolean;
  error: DocumentErrorMessage | null;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteDocumentDialog({
  document, isDeleting, error, onClose, onConfirm,
}: DeleteDocumentDialogProps) {
  const confirm = async () => { try { await onConfirm(); } catch { /* 保留错误并保持弹窗。 */ } };
  return (
    <Dialog
      open={document !== null}
      title="删除文档"
      description="原始文件及其全部父子文本块会一起删除。"
      tone="danger"
      closeDisabled={isDeleting}
      onClose={onClose}
      footer={<>
        <button className="kb-button kb-button--quiet" type="button" disabled={isDeleting} onClick={onClose}>取消</button>
        <button className="kb-button kb-button--danger" type="button" disabled={isDeleting} onClick={() => void confirm()}>{isDeleting ? "正在删除…" : "删除"}</button>
      </>}
    >
      <div className="kb-delete-copy"><p>确定删除“<strong>{document?.filename}</strong>”吗？</p><small>这不会影响知识库中的其他文档。</small></div>
      <DocumentErrorNotice error={error} />
    </Dialog>
  );
}
