import type {
  ChatGateway,
  ChatMessage,
  ChatMessageList,
  ChatStreamEvent,
  Citation,
  Conversation,
  ConversationPage,
  MessagePageOptions,
} from "../../features/chat/types/chat";

const FIXED_TIME = "2026-08-04T10:00:00.000Z";

export const fakeCitation: Citation = {
  id: "citation-1",
  message_id: "message-assistant-1",
  knowledge_base_id: "kb-1",
  document_id: "document-1",
  parent_id: "parent-1",
  child_id: "child-1",
  citation_number: 1,
  document_name: "架构设计.md",
  heading_path: "检索 / Parent-Child 策略",
  parent_content: "Parent 提供完整上下文，Child 负责精准检索，最终由模型生成回答。",
  child_preview: "Child 负责精准检索",
  child_start_offset: 15,
  child_end_offset: 27,
  score: 0.92,
};

export function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: "conversation-1",
    title: "Parent Child 策略",
    created_at: FIXED_TIME,
    updated_at: FIXED_TIME,
    ...overrides,
  };
}

export function makeMessage(overrides: Partial<ChatMessage>): ChatMessage {
  return {
    id: "message-1",
    conversation_id: "conversation-1",
    role: "assistant",
    status: "complete",
    content: "",
    rag_enabled: false,
    citations: [],
    created_at: FIXED_TIME,
    updated_at: FIXED_TIME,
    ...overrides,
  };
}

/**
 * 会话替身在内存中模拟持久化与流式事件，页面测试无需访问模型、网络或数据库。
 */
export class FakeChatGateway implements ChatGateway {
  conversations: Conversation[];
  messages = new Map<string, ChatMessage[]>();
  feedback: Array<{ messageId: string; rating: "up" | "down"; reason?: string }> = [];
  regenerationCount = 0;
  conversationListCount = 0;
  messagePageOffsets: number[] = [];
  private nextConversation = 2;
  private nextMessage = 1;

  constructor(conversations: Conversation[] = [makeConversation()]) {
    this.conversations = conversations;
    conversations.forEach((conversation) => this.messages.set(conversation.id, []));
  }

  async listConversations(): Promise<ConversationPage> {
    this.conversationListCount += 1;
    return {
      items: [...this.conversations],
      total: this.conversations.length,
      limit: 50,
      offset: 0,
    };
  }

  async createConversation(): Promise<Conversation> {
    const conversation = makeConversation({
      id: `conversation-${this.nextConversation++}`,
      title: "新对话",
    });
    this.conversations = [conversation, ...this.conversations];
    this.messages.set(conversation.id, []);
    return conversation;
  }

  async deleteConversation(conversationId: string): Promise<void> {
    this.conversations = this.conversations.filter((item) => item.id !== conversationId);
    this.messages.delete(conversationId);
  }

  async listMessages(
    conversationId: string,
    options: MessagePageOptions,
  ): Promise<ChatMessageList> {
    this.messagePageOffsets.push(options.offset);
    const allMessages = this.messages.get(conversationId) ?? [];
    const end = Math.max(0, allMessages.length - options.offset);
    const start = Math.max(0, end - options.limit);
    return {
      items: allMessages.slice(start, end),
      total: allMessages.length,
      limit: options.limit,
      offset: options.offset,
      has_more: start > 0,
    };
  }

  async streamMessage(
    conversationId: string,
    content: string,
    onEvent: (event: ChatStreamEvent) => void,
    _signal: AbortSignal,
  ): Promise<void> {
    // 替身复现“寒暄直聊、知识问题走 RAG”的自动路由，不把策略暴露给 UI。
    const useRag = !["你好", "您好", "嗨"].includes(content.trim());
    const user = makeMessage({
      id: `message-user-${this.nextMessage}`,
      conversation_id: conversationId,
      role: "user",
      content,
    });
    const assistant = makeMessage({
      id: `message-assistant-${this.nextMessage++}`,
      conversation_id: conversationId,
      role: "assistant",
      status: "generating",
      rag_enabled: useRag,
      citations: [],
    });
    onEvent({ type: "meta", message: assistant, userMessage: user, citations: [] });
    onEvent({ type: "delta", content: useRag ? "Child 用于精确召回，" : "我是 BiYou，" });
    onEvent({ type: "delta", content: useRag ? "Parent 用于补全上下文。[1]" : "可以直接与你对话。" });
    const completed = {
      ...assistant,
      status: "complete" as const,
      content: useRag
        ? "Child 用于精确召回，Parent 用于补全上下文。[1]"
        : "我是 BiYou，可以直接与你对话。",
      citations: useRag ? [fakeCitation] : [],
    };
    this.messages.set(conversationId, [user, completed]);
    onEvent({ type: "done", message: completed, citations: completed.citations });
  }

  async regenerate(
    conversationId: string,
    messageId: string,
    onEvent: (event: ChatStreamEvent) => void,
  ): Promise<void> {
    this.regenerationCount += 1;
    const current = (this.messages.get(conversationId) ?? []).find((item) => item.id === messageId);
    if (!current) throw new Error("消息不存在");
    onEvent({ type: "meta", message: { ...current, status: "generating", content: "" } });
    onEvent({ type: "delta", content: "重新生成的回答。[1]" });
    const completed = { ...current, status: "complete" as const, content: "重新生成的回答。[1]" };
    this.messages.set(
      conversationId,
      (this.messages.get(conversationId) ?? []).map((item) => item.id === messageId ? completed : item),
    );
    onEvent({ type: "done", message: completed, citations: completed.citations });
  }

  async saveFeedback(
    _conversationId: string,
    messageId: string,
    rating: "up" | "down",
    reason?: string,
  ): Promise<void> {
    this.feedback.push({ messageId, rating, ...(reason ? { reason } : {}) });
  }
}

interface ControlledStream {
  user: ChatMessage;
  assistant: ChatMessage;
  onEvent: (event: ChatStreamEvent) => void;
  resolve: () => void;
  reject: (reason: unknown) => void;
}

/**
 * 可控流替身让测试精确停在生成中间态，覆盖切换、终止、删除和迟到事件边界。
 */
export class ControlledChatGateway extends FakeChatGateway {
  pendingStreams = new Map<string, ControlledStream>();
  abortedConversationIds = new Set<string>();

  override async streamMessage(
    conversationId: string,
    content: string,
    onEvent: (event: ChatStreamEvent) => void,
    signal: AbortSignal,
  ): Promise<void> {
    const user = makeMessage({
      id: `controlled-user-${conversationId}`,
      conversation_id: conversationId,
      role: "user",
      content,
    });
    const assistant = makeMessage({
      id: `controlled-assistant-${conversationId}`,
      conversation_id: conversationId,
      role: "assistant",
      status: "generating",
    });
    onEvent({ type: "meta", message: assistant, userMessage: user });
    await new Promise<void>((resolve, reject) => {
      this.pendingStreams.set(conversationId, {
        user,
        assistant,
        onEvent,
        resolve,
        reject,
      });
      signal.addEventListener("abort", () => {
        this.abortedConversationIds.add(conversationId);
        reject(new DOMException("请求已终止", "AbortError"));
      }, { once: true });
    });
  }

  emitDelta(conversationId: string, content: string): void {
    this.pendingStreams.get(conversationId)?.onEvent({ type: "delta", content });
  }

  complete(conversationId: string, content = "后台回答已完成"): void {
    const stream = this.pendingStreams.get(conversationId);
    if (!stream) return;
    const completed = {
      ...stream.assistant,
      status: "complete" as const,
      content,
    };
    this.messages.set(conversationId, [stream.user, completed]);
    stream.onEvent({ type: "done", message: completed });
    stream.resolve();
    this.pendingStreams.delete(conversationId);
  }

  emitLateDone(conversationId: string, content = "不应出现的迟到回答"): void {
    const stream = this.pendingStreams.get(conversationId);
    if (!stream) return;
    stream.onEvent({
      type: "done",
      message: {
        ...stream.assistant,
        status: "complete",
        content,
      },
    });
  }
}
