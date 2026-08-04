import { memo } from "react";

import type { ActiveChatTurn, Citation } from "../types/chat";
import { MessageItem } from "./MessageItem";

interface StreamingTurnProps {
  turn: ActiveChatTurn | null;
  onCitationSelect: (citation: Citation) => void;
  onRegenerate: (messageId: string) => void;
  onFeedback: (messageId: string, rating: "up" | "down", reason?: string) => void;
}

/** 当前轮次单独订阅高频流式文本，不把更新传播给历史消息树。 */
export const StreamingTurn = memo(function StreamingTurn({
  turn,
  onCitationSelect,
  onRegenerate,
  onFeedback,
}: StreamingTurnProps) {
  if (!turn) return null;
  return (
    <div className="chat-streaming-turn" aria-live="polite" aria-label="当前回答">
      {turn.userMessage ? (
        <MessageItem
          message={turn.userMessage}
          onCitationSelect={onCitationSelect}
          onRegenerate={onRegenerate}
          onFeedback={onFeedback}
        />
      ) : null}
      <MessageItem
        message={turn.assistantMessage}
        canRegenerate={turn.assistantMessage.status !== "generating"}
        onCitationSelect={onCitationSelect}
        onRegenerate={onRegenerate}
        onFeedback={onFeedback}
      />
    </div>
  );
});
