import { Icon } from "../../../components/ui/Icon";
import type { KnowledgeBaseErrorMessage } from "../utils/knowledgeBaseError";

interface KnowledgeBaseErrorNoticeProps {
  error: KnowledgeBaseErrorMessage | null;
  onRetry?: () => void;
}

export function KnowledgeBaseErrorNotice({ error, onRetry }: KnowledgeBaseErrorNoticeProps) {
  if (!error) return null;
  return (
    <div className="kb-error-notice" role="alert">
      <Icon name="alert" />
      <div>
        <strong>{error.message}</strong>
        {error.traceId ? <small>Trace ID：{error.traceId}</small> : null}
      </div>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          <Icon name="refresh" size={14} />重新加载
        </button>
      ) : null}
    </div>
  );
}

