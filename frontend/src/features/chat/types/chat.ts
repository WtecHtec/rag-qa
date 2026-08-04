export type MessageRole = "user" | "assistant" | "clarification" | "system";
export type MessageStatus = "complete" | "generating" | "failed" | "stopped";

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationPage {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export interface Citation {
  id: string;
  message_id: string;
  knowledge_base_id: string;
  document_id: string;
  parent_id: string;
  child_id: string;
  citation_number: number;
  document_name: string;
  heading_path: string;
  parent_content: string;
  child_preview: string;
  child_start_offset: number;
  child_end_offset: number;
  score: number;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  status: MessageStatus;
  content: string;
  rewritten_query?: string | null;
  model?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  rag_enabled: boolean;
  citations: Citation[];
  created_at: string;
  updated_at: string;
}

export interface ChatMessageList {
  items: ChatMessage[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface MessagePageOptions {
  limit: number;
  offset: number;
}

export interface ActiveChatTurn {
  userMessage?: ChatMessage;
  assistantMessage: ChatMessage;
}

export type ChatStreamEvent =
  | {
    type: "meta";
    message: ChatMessage;
    userMessage?: ChatMessage;
    citations?: Citation[];
  }
  | { type: "delta"; content: string }
  | { type: "done"; message: ChatMessage; citations?: Citation[] }
  | { type: "error"; message?: ChatMessage; code?: string; errorMessage?: string };

export interface ChatGateway {
  listConversations(signal?: AbortSignal): Promise<ConversationPage>;
  createConversation(): Promise<Conversation>;
  deleteConversation(conversationId: string): Promise<void>;
  listMessages(
    conversationId: string,
    options: MessagePageOptions,
    signal?: AbortSignal,
  ): Promise<ChatMessageList>;
  streamMessage(
    conversationId: string,
    content: string,
    onEvent: (event: ChatStreamEvent) => void,
    signal: AbortSignal,
  ): Promise<void>;
  regenerate(
    conversationId: string,
    messageId: string,
    onEvent: (event: ChatStreamEvent) => void,
    signal: AbortSignal,
  ): Promise<void>;
  saveFeedback(
    conversationId: string,
    messageId: string,
    rating: "up" | "down",
    reason?: string,
  ): Promise<void>;
}
