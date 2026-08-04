import { ApiError } from "../../../shared/api/client";

export interface KnowledgeBaseErrorMessage {
  message: string;
  traceId?: string;
}

export function toKnowledgeBaseErrorMessage(error: Error | null): KnowledgeBaseErrorMessage | null {
  if (error === null) return null;
  if (error instanceof ApiError) {
    return { message: error.message, traceId: error.traceId };
  }
  return { message: error.message || "发生未知错误" };
}

