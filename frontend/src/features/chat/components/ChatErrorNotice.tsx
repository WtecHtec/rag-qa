import { Icon } from "../../../components/ui/Icon";

interface ChatErrorNoticeProps {
  error: Error | null;
}

export function ChatErrorNotice({ error }: ChatErrorNoticeProps) {
  if (!error) return null;
  return (
    <div className="chat-error-notice" role="alert">
      <Icon name="alert" size={15} />
      <span><strong>暂时无法完成操作</strong><small>{error.message}</small></span>
    </div>
  );
}
