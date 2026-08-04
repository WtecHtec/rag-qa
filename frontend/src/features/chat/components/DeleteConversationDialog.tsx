import { Dialog } from "../../../components/ui/Dialog";
import type { Conversation } from "../types/chat";

interface DeleteConversationDialogProps {
  conversation: Conversation | null;
  isDeleting: boolean;
  isGenerating: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteConversationDialog({
  conversation,
  isDeleting,
  isGenerating,
  onClose,
  onConfirm,
}: DeleteConversationDialogProps) {
  const confirm = async () => {
    try {
      await onConfirm();
    } catch {
      // Workspace 保留删除错误；失败时弹窗继续打开，便于用户重试。
    }
  };

  return (
    <Dialog
      open={conversation !== null}
      title="删除对话"
      description={isGenerating ? "该对话正在回复，删除会先终止当前生成。" : "对话及其全部消息将从本机删除。"}
      tone="danger"
      closeDisabled={isDeleting}
      onClose={onClose}
      footer={<>
        <button className="chat-dialog-button" type="button" disabled={isDeleting} onClick={onClose}>取消</button>
        <button
          className="chat-dialog-button chat-dialog-button--danger"
          type="button"
          disabled={isDeleting || !conversation}
          onClick={() => void confirm()}
        >
          {isDeleting ? "正在删除…" : "删除"}
        </button>
      </>}
    >
      <div className="chat-delete-copy">
        <p>确定删除“<strong>{conversation?.title}</strong>”吗？</p>
        <small>{isGenerating ? "正在传输的 SSE 连接会立即终止，迟到事件不会重新写入页面。" : "删除后无法恢复。"}</small>
      </div>
    </Dialog>
  );
}
