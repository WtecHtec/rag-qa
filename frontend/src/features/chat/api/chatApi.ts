import { API_BASE_URL, ApiError, apiRequest } from "../../../shared/api/client";
import type {
  ChatGateway,
  ChatMessage,
  ChatMessageList,
  ChatStreamEvent,
  Citation,
  Conversation,
  ConversationPage,
} from "../types/chat";

interface StreamPayload {
  message?: ChatMessage;
  user_message?: ChatMessage;
  citations?: Citation[];
  content?: string;
  code?: string;
  error_message?: string;
  error?: { message?: string; code?: string; trace_id?: string };
}

export const chatApi: ChatGateway = {
  listConversations(signal) {
    return apiRequest<ConversationPage>("/conversations?limit=50&offset=0", { signal });
  },

  createConversation() {
    return apiRequest<Conversation>("/conversations", {
      method: "POST",
    });
  },

  deleteConversation(conversationId) {
    return apiRequest<void>(`/conversations/${conversationId}`, { method: "DELETE" });
  },

  listMessages(conversationId, options, signal) {
    const query = new URLSearchParams({
      limit: String(options.limit),
      offset: String(options.offset),
    });
    return apiRequest<ChatMessageList>(
      `/conversations/${conversationId}/messages?${query.toString()}`,
      { signal },
    );
  },

  streamMessage(conversationId, content, onEvent, signal) {
    return streamRequest(
      `/conversations/${conversationId}/messages/stream`,
      { content },
      onEvent,
      signal,
    );
  },

  regenerate(conversationId, messageId, onEvent, signal) {
    return streamRequest(
      `/conversations/${conversationId}/messages/${messageId}/regenerate`,
      undefined,
      onEvent,
      signal,
    );
  },

  saveFeedback(conversationId, messageId, rating, reason) {
    return apiRequest<void>(
      `/conversations/${conversationId}/messages/${messageId}/feedback`,
      {
        method: "PUT",
        body: JSON.stringify({ rating, reason }),
      },
    );
  },
};

async function streamRequest(
  path: string,
  body: object | undefined,
  onEvent: (event: ChatStreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    signal,
    headers: {
      Accept: "text/event-stream",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const payload = await readError(response);
    throw new ApiError(
      payload.error?.message ?? `请求失败，状态码 ${response.status}`,
      response.status,
      payload.error?.trace_id,
      payload.error?.code,
    );
  }
  if (!response.body) throw new ApiError("浏览器不支持流式响应", 500);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    frames.forEach((frame) => emitFrame(frame, onEvent));
    if (done) break;
  }
  if (buffer.trim()) emitFrame(buffer, onEvent);
}

function emitFrame(frame: string, onEvent: (event: ChatStreamEvent) => void): void {
  const lines = frame.split("\n");
  const type = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n");
  if (!type || !data) return;
  const payload = JSON.parse(data) as StreamPayload;
  if (type === "meta" && payload.message) {
    onEvent({
      type,
      message: payload.message,
      userMessage: payload.user_message,
      citations: payload.citations,
    });
  } else if (type === "delta" && typeof payload.content === "string") {
    onEvent({ type, content: payload.content });
  } else if (type === "done" && payload.message) {
    onEvent({ type, message: payload.message, citations: payload.citations });
  } else if (type === "error") {
    onEvent({
      type,
      message: payload.message,
      code: payload.code,
      errorMessage: payload.error_message ?? payload.error?.message,
    });
  }
}

async function readError(response: Response): Promise<StreamPayload> {
  try {
    return (await response.json()) as StreamPayload;
  } catch {
    return {};
  }
}
