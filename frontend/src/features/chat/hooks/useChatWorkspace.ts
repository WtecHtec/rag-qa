import { useCallback, useEffect, useRef, useState } from "react";

import { knowledgeBaseApi } from "../../knowledge-base/api/knowledgeBaseApi";
import type {
  KnowledgeBase,
  KnowledgeBaseGateway,
} from "../../knowledge-base/types/knowledgeBase";
import { chatApi } from "../api/chatApi";
import type {
  ActiveChatTurn,
  ChatGateway,
  ChatMessage,
  ChatStreamEvent,
  Citation,
  Conversation,
} from "../types/chat";
import { excludeActiveTurnMessages } from "../utils/excludeActiveTurnMessages";
import { mergeChatMessages } from "../utils/mergeChatMessages";
import { RafTextBatcher } from "../utils/rafTextBatcher";

const MESSAGE_PAGE_SIZE = 30;

interface ConversationStreamSession {
  conversationId: string;
  token: string;
  controller: AbortController;
  turn: ActiveChatTurn;
  batcher: RafTextBatcher;
}

const titleFromQuery = (query: string): string => (
  query.length <= 36 ? query : `${query.slice(0, 36)}…`
);

const makeLocalMessage = (
  conversationId: string,
  role: "user" | "assistant",
  content: string,
  ragEnabled = false,
): ChatMessage => ({
  id: `local-${role}-${crypto.randomUUID()}`,
  conversation_id: conversationId,
  role,
  status: role === "assistant" ? "generating" : "complete",
  content,
  rag_enabled: ragEnabled,
  citations: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

export function useChatWorkspace(
  gateway: ChatGateway = chatApi,
  knowledgeBaseGateway: KnowledgeBaseGateway = knowledgeBaseApi,
) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [historyMessages, setHistoryMessages] = useState<ChatMessage[]>([]);
  const [activeTurn, setActiveTurn] = useState<ActiveChatTurn | null>(null);
  const [generatingConversationIds, setGeneratingConversationIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [hasOlderMessages, setHasOlderMessages] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const activeConversationRef = useRef<string | null>(null);
  const conversationsRef = useRef<Conversation[]>([]);
  const streamSessionsRef = useRef(new Map<string, ConversationStreamSession>());
  const messageLoadSequenceRef = useRef(0);

  useEffect(() => {
    conversationsRef.current = conversations;
  }, [conversations]);

  const updateGeneratingState = useCallback((conversationId: string, active: boolean) => {
    setGeneratingConversationIds((current) => {
      const next = new Set(current);
      if (active) next.add(conversationId);
      else next.delete(conversationId);
      return next;
    });
  }, []);

  const publishTurn = useCallback((session: ConversationStreamSession) => {
    if (activeConversationRef.current === session.conversationId) {
      setActiveTurn(session.turn);
    }
  }, []);

  const removeStreamSession = useCallback((conversationId: string, token?: string) => {
    const session = streamSessionsRef.current.get(conversationId);
    if (!session || (token && session.token !== token)) return null;
    streamSessionsRef.current.delete(conversationId);
    session.batcher.clear();
    updateGeneratingState(conversationId, false);
    if (activeConversationRef.current === conversationId) setActiveTurn(null);
    return session;
  }, [updateGeneratingState]);

  const cancelStreamSession = useCallback((conversationId: string) => {
    const session = removeStreamSession(conversationId);
    session?.controller.abort();
  }, [removeStreamSession]);

  useEffect(() => () => {
    // 页面卸载时终止所有本地连接；会话间切换不会触发这一清理。
    for (const session of streamSessionsRef.current.values()) {
      session.batcher.clear();
      session.controller.abort();
    }
    streamSessionsRef.current.clear();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    Promise.all([
      gateway.listConversations(controller.signal),
      knowledgeBaseGateway.list({ limit: 100, signal: controller.signal }),
    ]).then(([conversationPage, knowledgeBasePage]) => {
      const firstConversation = conversationPage.items[0];
      conversationsRef.current = conversationPage.items;
      setConversations(conversationPage.items);
      setKnowledgeBases(knowledgeBasePage.items);
      activeConversationRef.current = firstConversation?.id ?? null;
      setActiveConversationId(firstConversation?.id ?? null);
      setError(null);
      if (!firstConversation) setIsLoading(false);
    }).catch((caught: unknown) => {
      if (controller.signal.aborted) return;
      setError(caught instanceof Error ? caught : new Error("会话加载失败"));
      setIsLoading(false);
    });
    return () => controller.abort();
  }, [gateway, knowledgeBaseGateway]);

  useEffect(() => {
    const sequence = ++messageLoadSequenceRef.current;
    const session = activeConversationId
      ? streamSessionsRef.current.get(activeConversationId)
      : undefined;
    setActiveTurn(session?.turn ?? null);
    if (!activeConversationId) {
      setHistoryMessages([]);
      setHasOlderMessages(false);
      setIsLoading(false);
      return;
    }
    const controller = new AbortController();
    setIsLoading(true);
    gateway.listMessages(
      activeConversationId,
      { limit: MESSAGE_PAGE_SIZE, offset: 0 },
      controller.signal,
    ).then((page) => {
      if (
        activeConversationRef.current !== activeConversationId
        || messageLoadSequenceRef.current !== sequence
      ) return;
      const liveTurn = streamSessionsRef.current.get(activeConversationId)?.turn;
      setHistoryMessages(excludeActiveTurnMessages(page.items, liveTurn));
      setHasOlderMessages(page.has_more);
      setError(null);
      setIsLoading(false);
    }).catch((caught: unknown) => {
      if (controller.signal.aborted) return;
      setError(caught instanceof Error ? caught : new Error("消息加载失败"));
      setIsLoading(false);
    });
    return () => controller.abort();
  }, [activeConversationId, gateway]);

  const startNewConversation = useCallback(async () => {
    const conversation = await gateway.createConversation();
    setConversations((current) => [conversation, ...current]);
    activeConversationRef.current = conversation.id;
    setActiveConversationId(conversation.id);
    setHistoryMessages([]);
    setActiveTurn(null);
    setHasOlderMessages(false);
    setSelectedCitation(null);
    return conversation;
  }, [gateway]);

  const selectConversation = useCallback((conversation: Conversation) => {
    activeConversationRef.current = conversation.id;
    setActiveConversationId(conversation.id);
    setSelectedCitation(null);
    setActiveTurn(streamSessionsRef.current.get(conversation.id)?.turn ?? null);
  }, []);

  const finishStreamSession = useCallback((
    conversationId: string,
    token: string,
    message: ChatMessage,
    citations?: Citation[],
  ) => {
    const session = streamSessionsRef.current.get(conversationId);
    if (!session || session.token !== token) return;
    const completedAssistant = {
      ...message,
      citations: citations ?? message.citations,
    };
    const completedMessages = session.turn.userMessage
      ? [session.turn.userMessage, completedAssistant]
      : [completedAssistant];
    // 使进行中的消息分页请求失效，避免旧快照覆盖 done 的增量结果。
    messageLoadSequenceRef.current += 1;
    if (activeConversationRef.current === conversationId) {
      setHistoryMessages((history) => mergeChatMessages(history, completedMessages));
    }
    setConversations((items) => {
      const conversation = items.find((item) => item.id === conversationId);
      if (!conversation) return items;
      const updated = {
        ...conversation,
        title: conversation.title === "新对话" && session.turn.userMessage
          ? titleFromQuery(session.turn.userMessage.content)
          : conversation.title,
        updated_at: message.updated_at,
      };
      return [updated, ...items.filter((item) => item.id !== updated.id)];
    });
    removeStreamSession(conversationId, token);
  }, [removeStreamSession]);

  const applyStreamEvent = useCallback((
    conversationId: string,
    token: string,
    event: ChatStreamEvent,
  ) => {
    const session = streamSessionsRef.current.get(conversationId);
    // 删除、终止或被新请求替代后，迟到的 SSE 事件必须完全失效。
    if (!session || session.token !== token) return;
    if (event.type === "meta") {
      session.turn = {
        ...session.turn,
        // 重新生成没有临时用户消息，不能把原问题再次追加到历史末尾。
        userMessage: session.turn.userMessage
          ? (event.userMessage ?? session.turn.userMessage)
          : undefined,
        assistantMessage: {
          ...event.message,
          content: session.turn.assistantMessage.content,
          citations: [],
        },
      };
      publishTurn(session);
    } else if (event.type === "delta") {
      session.batcher.push(event.content);
    } else if (event.type === "done") {
      finishStreamSession(conversationId, token, event.message, event.citations);
    } else if (event.type === "error") {
      if (activeConversationRef.current === conversationId) {
        setError(new Error(event.errorMessage ?? "回答生成失败"));
      }
      if (event.message) finishStreamSession(conversationId, token, event.message);
    }
  }, [finishStreamSession, publishTurn]);

  const createStreamSession = useCallback((
    conversationId: string,
    turn: ActiveChatTurn,
  ) => {
    if (streamSessionsRef.current.has(conversationId)) return null;
    const token = crypto.randomUUID();
    const session = {
      conversationId,
      token,
      controller: new AbortController(),
      turn,
      batcher: null as unknown as RafTextBatcher,
    };
    session.batcher = new RafTextBatcher((delta) => {
      const liveSession = streamSessionsRef.current.get(conversationId);
      if (!liveSession || liveSession.token !== token) return;
      liveSession.turn = {
        ...liveSession.turn,
        assistantMessage: {
          ...liveSession.turn.assistantMessage,
          content: liveSession.turn.assistantMessage.content + delta,
        },
      };
      publishTurn(liveSession);
    });
    streamSessionsRef.current.set(conversationId, session);
    updateGeneratingState(conversationId, true);
    publishTurn(session);
    return session;
  }, [publishTurn, updateGeneratingState]);

  const reconcileLatestPage = useCallback(async (conversationId: string) => {
    const page = await gateway.listMessages(
      conversationId,
      { limit: MESSAGE_PAGE_SIZE, offset: 0 },
    ).catch(() => null);
    if (!page || activeConversationRef.current !== conversationId) return;
    setHistoryMessages(page.items);
    setHasOlderMessages(page.has_more);
  }, [gateway]);

  const runStream = useCallback(async (
    session: ConversationStreamSession,
    operation: (onEvent: (event: ChatStreamEvent) => void, signal: AbortSignal) => Promise<void>,
    fallbackError: string,
  ) => {
    try {
      await operation(
        (event) => applyStreamEvent(session.conversationId, session.token, event),
        session.controller.signal,
      );
    } catch (caught: unknown) {
      if (
        !(caught instanceof DOMException && caught.name === "AbortError")
        && activeConversationRef.current === session.conversationId
      ) {
        setError(caught instanceof Error ? caught : new Error(fallbackError));
      }
    } finally {
      const liveSession = streamSessionsRef.current.get(session.conversationId);
      if (!liveSession || liveSession.token !== session.token) return;
      liveSession.batcher.flush();
      removeStreamSession(session.conversationId, session.token);
      await reconcileLatestPage(session.conversationId);
    }
  }, [applyStreamEvent, reconcileLatestPage, removeStreamSession]);

  const sendMessage = useCallback(async (content: string) => {
    const normalized = content.trim();
    if (!normalized) return;
    setError(null);
    let conversationId = activeConversationRef.current;
    if (!conversationId) conversationId = (await startNewConversation()).id;
    if (streamSessionsRef.current.has(conversationId)) return;
    const userMessage = makeLocalMessage(conversationId, "user", normalized);
    const assistantMessage = makeLocalMessage(conversationId, "assistant", "");
    const session = createStreamSession(conversationId, { userMessage, assistantMessage });
    if (!session) return;
    await runStream(
      session,
      (onEvent, signal) => gateway.streamMessage(
        conversationId,
        normalized,
        onEvent,
        signal,
      ),
      "回答生成失败",
    );
  }, [createStreamSession, gateway, runStream, startNewConversation]);

  const regenerate = useCallback(async (messageId: string) => {
    const conversationId = activeConversationRef.current;
    if (!conversationId || streamSessionsRef.current.has(conversationId)) return;
    const target = historyMessages.find((message) => message.id === messageId);
    if (!target) return;
    setHistoryMessages((current) => current.filter((message) => message.id !== messageId));
    const session = createStreamSession(conversationId, {
      assistantMessage: {
        ...target,
        status: "generating",
        content: "",
        citations: [],
        error_code: null,
        error_message: null,
      },
    });
    if (!session) return;
    await runStream(
      session,
      (onEvent, signal) => gateway.regenerate(
        conversationId,
        messageId,
        onEvent,
        signal,
      ),
      "重新生成失败",
    );
  }, [createStreamSession, gateway, historyMessages, runStream]);

  const deleteConversation = useCallback(async (conversationId: string) => {
    cancelStreamSession(conversationId);
    messageLoadSequenceRef.current += 1;
    try {
      await gateway.deleteConversation(conversationId);
      const remaining = conversationsRef.current.filter((item) => item.id !== conversationId);
      conversationsRef.current = remaining;
      setConversations(remaining);
      if (activeConversationRef.current === conversationId) {
        const nextConversation = remaining[0] ?? null;
        activeConversationRef.current = nextConversation?.id ?? null;
        setActiveConversationId(nextConversation?.id ?? null);
        setHistoryMessages([]);
        setActiveTurn(
          nextConversation
            ? (streamSessionsRef.current.get(nextConversation.id)?.turn ?? null)
            : null,
        );
        setHasOlderMessages(false);
        setSelectedCitation(null);
      }
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught : new Error("删除会话失败"));
      await reconcileLatestPage(conversationId);
      throw caught;
    }
  }, [cancelStreamSession, gateway, reconcileLatestPage]);

  const loadOlderMessages = useCallback(async () => {
    const conversationId = activeConversationRef.current;
    if (
      !conversationId
      || isLoadingOlder
      || !hasOlderMessages
      || streamSessionsRef.current.has(conversationId)
    ) return;
    setIsLoadingOlder(true);
    try {
      const page = await gateway.listMessages(conversationId, {
        limit: MESSAGE_PAGE_SIZE,
        offset: historyMessages.length,
      });
      if (activeConversationRef.current !== conversationId) return;
      setHistoryMessages((current) => {
        const knownIds = new Set(current.map((message) => message.id));
        return [...page.items.filter((message) => !knownIds.has(message.id)), ...current];
      });
      setHasOlderMessages(page.has_more);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught : new Error("更早消息加载失败"));
    } finally {
      setIsLoadingOlder(false);
    }
  }, [gateway, hasOlderMessages, historyMessages.length, isLoadingOlder]);

  const stopGeneration = useCallback(() => {
    const conversationId = activeConversationRef.current;
    if (!conversationId) return;
    const session = streamSessionsRef.current.get(conversationId);
    if (session) {
      session.controller.abort();
    }
  }, []);

  const saveFeedback = useCallback(async (
    messageId: string,
    rating: "up" | "down",
    reason?: string,
  ) => {
    const conversationId = activeConversationRef.current;
    if (!conversationId) return;
    await gateway.saveFeedback(conversationId, messageId, rating, reason);
  }, [gateway]);

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  ) ?? null;
  const isGenerating = activeConversationId
    ? generatingConversationIds.has(activeConversationId)
    : false;

  return {
    conversations,
    knowledgeBases,
    activeConversation,
    historyMessages,
    activeTurn,
    generatingConversationIds,
    hasOlderMessages,
    selectedCitation,
    isLoading,
    isLoadingOlder,
    isGenerating,
    error,
    setSelectedCitation,
    selectConversation,
    startNewConversation,
    deleteConversation,
    loadOlderMessages,
    sendMessage,
    regenerate,
    stopGeneration,
    saveFeedback,
  };
}

export type ChatWorkspace = ReturnType<typeof useChatWorkspace>;
