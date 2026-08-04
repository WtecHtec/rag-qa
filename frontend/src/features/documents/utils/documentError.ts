import { ApiError } from "../../../shared/api/client";

export interface DocumentErrorMessage {
  message: string;
  traceId?: string;
}

export function toDocumentErrorMessage(error: Error | null): DocumentErrorMessage | null {
  if (!error) return null;
  return { message: error.message, traceId: error instanceof ApiError ? error.traceId : undefined };
}
