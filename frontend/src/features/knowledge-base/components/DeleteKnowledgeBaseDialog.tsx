import { Dialog } from "../../../components/ui/Dialog";
import type { KnowledgeBase } from "../types/knowledgeBase";
import type { KnowledgeBaseErrorMessage } from "../utils/knowledgeBaseError";
import { KnowledgeBaseErrorNotice } from "./KnowledgeBaseErrorNotice";

interface DeleteKnowledgeBaseDialogProps {
  open: boolean;
  knowledgeBase: KnowledgeBase | null;
  isSubmitting: boolean;
  error: KnowledgeBaseErrorMessage | null;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteKnowledgeBaseDialog({
  open,
  knowledgeBase,
  isSubmitting,
  error,
  onClose,
  onConfirm,
}: DeleteKnowledgeBaseDialogProps) {
  const handleConfirm = async () => {
    try {
      await onConfirm();
    } catch {
      // Mutation Hook 负责保留协议错误；弹窗不关闭，用户可以重试或复制 Trace ID。
    }
  };

  return (
    <Dialog
      open={open}
      title="删除知识库"
      description="此操作只允许删除不包含文档的知识库。"
      tone="danger"
      closeDisabled={isSubmitting}
      onClose={onClose}
      footer={
        <>
          <button className="kb-button kb-button--quiet" type="button" disabled={isSubmitting} onClick={onClose}>取消</button>
          <button
            className="kb-button kb-button--danger"
            type="button"
            disabled={isSubmitting || !knowledgeBase}
            onClick={() => void handleConfirm()}
          >
            {isSubmitting ? "正在删除…" : "删除"}
          </button>
        </>
      }
    >
      <div className="kb-delete-copy">
        <p>确定删除“<strong>{knowledgeBase?.name}</strong>”吗？</p>
        <small>删除成功后，该知识库不会再出现在列表中。</small>
      </div>
      <KnowledgeBaseErrorNotice error={error} />
    </Dialog>
  );
}
