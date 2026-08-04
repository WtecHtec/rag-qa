import { Icon } from "../../../components/ui/Icon";
import type { Conversation } from "../types/chat";
import { formatChatTime } from "../utils/formatChatTime";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId?: string;
  generatingIds: ReadonlySet<string>;
  onNew: () => void;
  onSelect: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
}

export function ConversationSidebar({
  conversations,
  activeId,
  generatingIds,
  onNew,
  onSelect,
  onDelete,
}: ConversationSidebarProps) {
  return (
    <aside className="chat-conversations" aria-label="历史会话">
      <button className="chat-new-button" type="button" onClick={onNew}>
        <Icon name="plus" size={14} />新对话
      </button>
      <p className="chat-list-label">最近会话</p>
      <div className="chat-conversation-scroll">
        {conversations.length === 0 ? (
          <p className="chat-conversation-empty">还没有历史会话</p>
        ) : conversations.map((conversation) => {
          const isGenerating = generatingIds.has(conversation.id);
          return (
            <div className="chat-conversation-row" key={conversation.id}>
              <button
                className={`chat-conversation${conversation.id === activeId ? " is-active" : ""}`}
                type="button"
                onClick={() => onSelect(conversation)}
              >
                <strong>{conversation.title}</strong>
                <small>
                  {isGenerating ? <i aria-hidden="true" /> : null}
                  {isGenerating ? "正在回复" : formatChatTime(conversation.updated_at)}
                </small>
              </button>
              <button
                className="chat-conversation-delete"
                type="button"
                aria-label={`删除会话 ${conversation.title}`}
                onClick={() => onDelete(conversation)}
              >
                <Icon name="trash" size={13} />
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
