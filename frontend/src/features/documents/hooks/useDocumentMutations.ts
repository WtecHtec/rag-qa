import { useCallback, useState } from "react";

import { documentApi } from "../api/documentApi";
import type { DocumentGateway } from "../types/document";

export function useDocumentMutations(gateway: DocumentGateway = documentApi) {
  const [pending, setPending] = useState<"upload" | "delete" | "reprocess" | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const run = useCallback(async <T,>(kind: typeof pending, operation: () => Promise<T>) => {
    setPending(kind);
    setError(null);
    try { return await operation(); }
    catch (caught) {
      const nextError = caught instanceof Error ? caught : new Error("文档操作失败");
      setError(nextError);
      throw nextError;
    } finally { setPending(null); }
  }, []);

  return {
    pending,
    uploadProgress,
    error,
    clearError: useCallback(() => setError(null), []),
    upload: useCallback((knowledgeBaseId: string, file: File) => {
      setUploadProgress(0);
      return run("upload", () => gateway.upload(knowledgeBaseId, file, setUploadProgress));
    }, [gateway, run]),
    remove: useCallback((knowledgeBaseId: string, documentId: string) =>
      run("delete", () => gateway.remove(knowledgeBaseId, documentId)), [gateway, run]),
    reprocess: useCallback((knowledgeBaseId: string, documentId: string) =>
      run("reprocess", () => gateway.reprocess(knowledgeBaseId, documentId)), [gateway, run]),
  };
}
