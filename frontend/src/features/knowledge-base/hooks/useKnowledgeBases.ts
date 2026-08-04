import { useCallback, useEffect, useState } from "react";

import { knowledgeBaseApi } from "../api/knowledgeBaseApi";
import type { KnowledgeBase, KnowledgeBaseGateway } from "../types/knowledgeBase";

interface KnowledgeBaseListState {
  items: KnowledgeBase[];
  total: number;
  isLoading: boolean;
  error: Error | null;
}

const INITIAL_STATE: KnowledgeBaseListState = {
  items: [],
  total: 0,
  isLoading: true,
  error: null,
};

export function useKnowledgeBases(
  query: string,
  gateway: KnowledgeBaseGateway = knowledgeBaseApi,
) {
  const [state, setState] = useState<KnowledgeBaseListState>(INITIAL_STATE);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const refresh = useCallback(() => {
    setRefreshVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let isActive = true;

    setState((current) => ({ ...current, isLoading: true, error: null }));
    gateway
      .list({ query, signal: controller.signal })
      .then((page) => {
        if (!isActive) return;
        setState({ items: page.items, total: page.total, isLoading: false, error: null });
      })
      .catch((error: unknown) => {
        if (!isActive || controller.signal.aborted) return;
        setState((current) => ({
          ...current,
          isLoading: false,
          error: error instanceof Error ? error : new Error("知识库加载失败"),
        }));
      });

    return () => {
      isActive = false;
      controller.abort();
    };
  }, [gateway, query, refreshVersion]);

  return { ...state, refresh };
}

