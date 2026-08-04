import { useEffect, useLayoutEffect, useRef } from "react";

import { Icon } from "../../../components/ui/Icon";
import type { ActiveChatTurn, ChatMessage, Citation } from "../types/chat";
import { MessageList } from "./MessageList";
import { StreamingTurn } from "./StreamingTurn";

interface ChatTranscriptProps {
  conversationId?: string;
  historyMessages: ChatMessage[];
  activeTurn: ActiveChatTurn | null;
  isLoading: boolean;
  isLoadingOlder: boolean;
  hasOlderMessages: boolean;
  onLoadOlder: () => Promise<void>;
  onCitationSelect: (citation: Citation) => void;
  onRegenerate: (messageId: string) => void;
  onFeedback: (messageId: string, rating: "up" | "down", reason?: string) => void;
}

export function ChatTranscript({
  conversationId,
  historyMessages,
  activeTurn,
  isLoading,
  isLoadingOlder,
  hasOlderMessages,
  onLoadOlder,
  onCitationSelect,
  onRegenerate,
  onFeedback,
}: ChatTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pinnedToBottomRef = useRef(true);
  const initialScrollDoneRef = useRef(false);
  const loadingRequestRef = useRef(false);

  useEffect(() => {
    initialScrollDoneRef.current = false;
    pinnedToBottomRef.current = true;
  }, [conversationId]);

  useLayoutEffect(() => {
    const region = scrollRef.current;
    if (!region || isLoading || initialScrollDoneRef.current) return;
    region.scrollTop = region.scrollHeight;
    initialScrollDoneRef.current = true;
  }, [conversationId, historyMessages.length, isLoading]);

  useEffect(() => {
    const region = scrollRef.current;
    if (!region || !pinnedToBottomRef.current) return;
    const frameId = window.requestAnimationFrame(() => {
      region.scrollTop = region.scrollHeight;
    });
    return () => window.cancelAnimationFrame(frameId);
  }, [activeTurn?.assistantMessage.content, activeTurn?.assistantMessage.status]);

  const handleScroll = () => {
    const region = scrollRef.current;
    if (!region) return;
    pinnedToBottomRef.current = (
      region.scrollHeight - region.scrollTop - region.clientHeight < 96
    );
    if (
      region.scrollTop > 48
      || !hasOlderMessages
      || isLoadingOlder
      || loadingRequestRef.current
    ) return;

    loadingRequestRef.current = true;
    const previousHeight = region.scrollHeight;
    void onLoadOlder().finally(() => {
      window.requestAnimationFrame(() => {
        const currentRegion = scrollRef.current;
        if (currentRegion) {
          currentRegion.scrollTop += currentRegion.scrollHeight - previousHeight;
        }
        loadingRequestRef.current = false;
      });
    });
  };

  const isEmpty = historyMessages.length === 0 && !activeTurn;

  return (
    <div ref={scrollRef} className="chat-scroll-region" onScroll={handleScroll}>
      {isLoading && isEmpty ? (
        <div className="chat-message-loading" aria-label="正在加载消息"><i /><i /><i /></div>
      ) : isEmpty ? (
        <div className="chat-empty-state">
          <span><Icon name="spark" size={22} /></span>
          <h2>开始一个本地会话</h2>
          <p>可以直接交流；知识型问题会优先检索本地文档，没有命中时再使用通用能力回答。</p>
        </div>
      ) : (
        <div className="chat-message-list">
          {hasOlderMessages || isLoadingOlder ? (
            <div className="chat-older-status" aria-live="polite">
              {isLoadingOlder ? "正在加载更早消息…" : "向上滚动加载更早消息"}
            </div>
          ) : historyMessages.length > 0 ? (
            <div className="chat-older-status">已到达本次会话开头</div>
          ) : null}
          <MessageList
            messages={historyMessages}
            allowRegenerate={!activeTurn}
            onCitationSelect={onCitationSelect}
            onRegenerate={onRegenerate}
            onFeedback={onFeedback}
          />
          <StreamingTurn
            turn={activeTurn}
            onCitationSelect={onCitationSelect}
            onRegenerate={onRegenerate}
            onFeedback={onFeedback}
          />
        </div>
      )}
    </div>
  );
}
