import { memo, useState } from "react";

import { Icon } from "../../../components/ui/Icon";
import type { ChatMessage, Citation } from "../types/chat";
import { MessageFeedback } from "./MessageFeedback";

interface MessageItemProps {
  message: ChatMessage;
  canRegenerate?: boolean;
  onCitationSelect: (citation: Citation) => void;
  onRegenerate: (messageId: string) => void;
  onFeedback: (messageId: string, rating: "up" | "down", reason?: string) => void;
}

/** 单条历史消息独立记忆化，复制反馈等局部状态不会让整段历史重新渲染。 */
export const MessageItem = memo(function MessageItem({
  message,
  canRegenerate = false,
  onCitationSelect,
  onRegenerate,
  onFeedback,
}: MessageItemProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copyMessage = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <article className={`chat-message chat-message--${isUser ? "user" : "assistant"}`}>
      {!isUser && <span className="chat-assistant-mark"><Icon name="spark" size={14} /></span>}
      <div className="chat-message-body">
        <div className="chat-message-content">
          {message.content ? message.content.split("\n").map((paragraph, index) => (
            <p key={`${message.id}-${index}`}>{paragraph || "\u00a0"}</p>
          )) : message.status === "generating" ? (
            <span className="chat-typing" aria-label="正在生成"><i /><i /><i /></span>
          ) : null}
          {message.status === "generating" && message.content ? (
            <span className="chat-stream-caret" aria-hidden="true" />
          ) : null}
        </div>

        {!isUser && message.citations.length > 0 ? (
          <div className="chat-citations" aria-label="回答实际引用">
            {message.citations.map((citation) => (
              <button type="button" key={citation.id} onClick={() => onCitationSelect(citation)}>
                <span>{citation.citation_number}</span>
                {citation.document_name}
              </button>
            ))}
          </div>
        ) : null}

        {message.status === "failed" ? (
          <p className="chat-message-error">{message.error_message ?? "回答生成失败，请稍后重试。"}</p>
        ) : null}

        {!isUser && message.status !== "generating" && message.content ? (
          <div className="chat-message-actions">
            <button type="button" aria-label="复制回答" onClick={() => void copyMessage()}>
              {copied ? <Icon name="check" size={14} /> : <Icon name="copy" size={14} />}
            </button>
            {canRegenerate ? (
              <button type="button" aria-label="重新生成" onClick={() => onRegenerate(message.id)}>
                <Icon name="refresh" size={14} />
              </button>
            ) : null}
            <span />
            {message.role === "assistant" ? (
              <MessageFeedback
                messageId={message.id}
                initialRating={message.feedback_rating}
                onFeedback={onFeedback}
              />
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
});
