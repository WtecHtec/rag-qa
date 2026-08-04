import { memo } from "react";

import type { ChatMessage, Citation } from "../types/chat";
import { MessageItem } from "./MessageItem";

interface MessageListProps {
  messages: ChatMessage[];
  allowRegenerate: boolean;
  onCitationSelect: (citation: Citation) => void;
  onRegenerate: (messageId: string) => void;
  onFeedback: (messageId: string, rating: "up" | "down", reason?: string) => void;
}

/** 已完成历史与流式状态隔离；token 到达时该组件的 Props 不发生变化。 */
export const MessageList = memo(function MessageList({
  messages,
  allowRegenerate,
  onCitationSelect,
  onRegenerate,
  onFeedback,
}: MessageListProps) {
  const visibleMessages = messages.filter((message) => message.role !== "system");
  const latestAnswerId = [...visibleMessages].reverse().find(
    (message) => message.role === "assistant" || message.role === "clarification",
  )?.id;

  return (
    <div className="chat-history-list" aria-label="历史消息">
      {visibleMessages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          canRegenerate={allowRegenerate && message.id === latestAnswerId}
          onCitationSelect={onCitationSelect}
          onRegenerate={onRegenerate}
          onFeedback={onFeedback}
        />
      ))}
    </div>
  );
});
