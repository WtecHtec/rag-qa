import { Icon } from "../../../components/ui/Icon";
import type { DocumentErrorMessage } from "../utils/documentError";

export function DocumentErrorNotice({ error }: { error: DocumentErrorMessage | null }) {
  if (!error) return null;
  return (
    <div className="doc-error" role="alert">
      <Icon name="alert" size={16} />
      <span><strong>{error.message}</strong>{error.traceId ? <small>Trace ID：{error.traceId}</small> : null}</span>
    </div>
  );
}
