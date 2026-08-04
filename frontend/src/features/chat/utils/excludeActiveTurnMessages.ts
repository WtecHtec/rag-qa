import type { ActiveChatTurn, ChatMessage } from "../types/chat";

/**
 * 分页结果可能在 meta 事件到达前已经包含服务端生成占位消息。
 * 优先按真实 ID 排除；ID 尚未对齐时，仅回退排除最新的 generating 问答轮次。
 */
export function excludeActiveTurnMessages(
  messages: ChatMessage[],
  turn: ActiveChatTurn | undefined,
): ChatMessage[] {
  if (!turn) return messages;
  const hiddenIds = new Set([
    turn.assistantMessage.id,
    ...(turn.userMessage ? [turn.userMessage.id] : []),
  ]);
  const exactMatches = messages.filter((message) => hiddenIds.has(message.id));
  if (exactMatches.length > 0) {
    return messages.filter((message) => !hiddenIds.has(message.id));
  }

  let assistantIndex = -1;
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role === "assistant" && message.status === "generating") {
      assistantIndex = index;
      break;
    }
  }
  if (assistantIndex < 0) return messages;
  const userIndex = assistantIndex > 0 && messages[assistantIndex - 1]?.role === "user"
    ? assistantIndex - 1
    : -1;
  return messages.filter((_, index) => index !== assistantIndex && index !== userIndex);
}
