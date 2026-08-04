import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Icon } from "../../../components/ui/Icon";

interface ChatComposerProps {
  isGenerating: boolean;
  onSend: (content: string) => void;
  onStop: () => void;
}

export function ChatComposer({
  isGenerating,
  onSend,
  onStop,
}: ChatComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const normalized = value.trim();
    if (!normalized || isGenerating) return;
    onSend(normalized);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form className="chat-composer" onSubmit={submit}>
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        maxLength={4000}
        disabled={isGenerating}
        placeholder={isGenerating ? "当前对话正在回复，停止后可继续输入" : "输入问题…"}
        onKeyDown={handleKeyDown}
        onChange={(event) => {
          setValue(event.target.value);
          event.target.style.height = "auto";
          event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`;
        }}
      />
      <div className="chat-composer-footer">
        <span className="chat-auto-route"><Icon name="spark" size={12} />自动选择回答方式</span>
        <span className="chat-send-hint"><kbd>⌘</kbd><kbd>↵</kbd> 发送</span>
        {isGenerating ? (
          <button className="chat-stop-button" type="button" aria-label="停止生成" onClick={onStop}>
            <Icon name="stop" size={13} />
          </button>
        ) : (
          <button type="submit" aria-label="发送问题" disabled={!value.trim()}>
            <Icon name="send" size={15} />
          </button>
        )}
      </div>
    </form>
  );
}
