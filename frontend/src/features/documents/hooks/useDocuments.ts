import { useCallback, useEffect, useState } from "react";

import { documentApi } from "../api/documentApi";
import type { DocumentGateway, KnowledgeDocument } from "../types/document";
import { isDocumentProcessing } from "../utils/documentFormat";

const PAGE_SIZE = 20;

export function useDocuments(
  knowledgeBaseId: string,
  gateway: DocumentGateway = documentApi,
) {
  const [items, setItems] = useState<KnowledgeDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const refresh = useCallback(() => setRefreshVersion((value) => value + 1), []);

  useEffect(() => {
    setOffset(0);
  }, [knowledgeBaseId]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setIsLoading(true);
    gateway.list(knowledgeBaseId, PAGE_SIZE, offset, controller.signal).then((page) => {
      if (!active) return;
      setItems(page.items);
      setTotal(page.total);
      setError(null);
      setIsLoading(false);
    }).catch((caught: unknown) => {
      if (!active || controller.signal.aborted) return;
      setError(caught instanceof Error ? caught : new Error("文档加载失败"));
      setIsLoading(false);
    });
    return () => { active = false; controller.abort(); };
  }, [gateway, knowledgeBaseId, offset, refreshVersion]);

  useEffect(() => {
    if (!items.some((item) => isDocumentProcessing(item.status))) return;
    const timer = window.setInterval(refresh, 1_500);
    return () => window.clearInterval(timer);
  }, [items, refresh]);

  return { items, total, offset, pageSize: PAGE_SIZE, isLoading, error, setOffset, refresh };
}
