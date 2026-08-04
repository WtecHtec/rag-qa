import { useCallback, useState } from "react";

import { knowledgeBaseApi } from "../api/knowledgeBaseApi";
import type {
  CreateKnowledgeBaseInput,
  KnowledgeBaseGateway,
  UpdateKnowledgeBaseInput,
} from "../types/knowledgeBase";

export type KnowledgeBaseMutation = "create" | "update" | "delete";

export function useKnowledgeBaseMutations(
  gateway: KnowledgeBaseGateway = knowledgeBaseApi,
) {
  const [pendingMutation, setPendingMutation] = useState<KnowledgeBaseMutation | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useCallback(
    async <T,>(mutation: KnowledgeBaseMutation, operation: () => Promise<T>): Promise<T> => {
      setPendingMutation(mutation);
      setError(null);
      try {
        return await operation();
      } catch (caughtError) {
        const normalizedError =
          caughtError instanceof Error ? caughtError : new Error("知识库操作失败");
        setError(normalizedError);
        throw normalizedError;
      } finally {
        setPendingMutation(null);
      }
    },
    [],
  );

  const create = useCallback(
    (input: CreateKnowledgeBaseInput) =>
      runMutation("create", () => gateway.create(input)),
    [gateway, runMutation],
  );

  const update = useCallback(
    (id: string, input: UpdateKnowledgeBaseInput) =>
      runMutation("update", () => gateway.update(id, input)),
    [gateway, runMutation],
  );

  const remove = useCallback(
    (id: string) => runMutation("delete", () => gateway.remove(id)),
    [gateway, runMutation],
  );

  return {
    create,
    update,
    remove,
    pendingMutation,
    error,
    clearError: useCallback(() => setError(null), []),
  };
}

