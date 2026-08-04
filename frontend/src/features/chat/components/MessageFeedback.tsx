import { useId, useState } from "react";
import { createPortal } from "react-dom";

import { Icon } from "../../../components/ui/Icon";
import { useFeedbackMenu } from "../hooks/useFeedbackMenu";

const DOWN_REASONS = ["回答错误", "内容不完整", "引用错误", "没解决问题", "其他"] as const;

interface MessageFeedbackProps {
  messageId: string;
  onFeedback: (messageId: string, rating: "up" | "down", reason?: string) => void;
}

export function MessageFeedback({ messageId, onFeedback }: MessageFeedbackProps) {
  const [selected, setSelected] = useState<"up" | "down" | null>(null);
  const menuId = useId();
  const menu = useFeedbackMenu();

  const saveUp = () => {
    setSelected("up");
    menu.close();
    onFeedback(messageId, "up");
  };

  const saveDown = (reason: string) => {
    setSelected("down");
    menu.close();
    onFeedback(messageId, "down", reason);
  };

  return (
    <div className="chat-feedback">
      <button
        className={selected === "up" ? "is-selected" : ""}
        type="button"
        aria-label="回答有帮助"
        onClick={saveUp}
      >
        <Icon name="thumbUp" size={14} />
      </button>
      <button
        className={selected === "down" ? "is-selected" : ""}
        type="button"
        aria-label="回答需改进"
        aria-controls={menuId}
        aria-expanded={menu.isOpen}
        ref={menu.triggerRef}
        onClick={menu.toggle}
      >
        <Icon name="thumbDown" size={14} />
      </button>
      {menu.isOpen ? createPortal(
        <div
          className="chat-feedback-menu"
          id={menuId}
          ref={menu.menuRef}
          role="menu"
          aria-label="选择改进原因"
          style={menu.position}
          onKeyDown={(event) => {
            if (event.key !== "Escape") return;
            menu.close();
            menu.triggerRef.current?.focus();
          }}
        >
          {DOWN_REASONS.map((reason) => (
            <button type="button" role="menuitem" key={reason} onClick={() => saveDown(reason)}>
              {reason}
            </button>
          ))}
        </div>,
        document.body,
      ) : null}
    </div>
  );
}
