import type { ChatMessage } from "../types/chat";

/**
 * 按服务端 ID 增量合并消息；未变化的历史对象保留原引用，让 memo 子项跳过渲染。
 */
export function mergeChatMessages(
  current: ChatMessage[],
  incoming: ChatMessage[],
): ChatMessage[] {
  if (incoming.length === 0) return current;
  const pending = new Map(incoming.map((message) => [message.id, message]));
  let changed = false;
  const merged = current.map((message) => {
    const replacement = pending.get(message.id);
    if (!replacement) return message;
    pending.delete(message.id);
    if (replacement === message) return message;
    changed = true;
    return replacement;
  });
  if (pending.size > 0) {
    changed = true;
    merged.push(...pending.values());
  }
  return changed ? merged : current;
}
