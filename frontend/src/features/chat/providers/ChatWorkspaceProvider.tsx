import type { ReactNode } from "react";

import { knowledgeBaseApi } from "../../knowledge-base/api/knowledgeBaseApi";
import type { KnowledgeBaseGateway } from "../../knowledge-base/types/knowledgeBase";
import { chatApi } from "../api/chatApi";
import { ChatWorkspaceContext } from "../context/ChatWorkspaceContext";
import { useChatWorkspace } from "../hooks/useChatWorkspace";
import type { ChatGateway } from "../types/chat";

interface ChatWorkspaceProviderProps {
  children: ReactNode;
  gateway?: ChatGateway;
  knowledgeBaseGateway?: KnowledgeBaseGateway;
}

/**
 * Provider 与问答页同生命周期，离开页面时 Hook 会取消尚未完成的 SSE。
 */
export function ChatWorkspaceProvider({
  children,
  gateway = chatApi,
  knowledgeBaseGateway = knowledgeBaseApi,
}: ChatWorkspaceProviderProps) {
  const workspace = useChatWorkspace(gateway, knowledgeBaseGateway);
  return (
    <ChatWorkspaceContext.Provider value={workspace}>
      {children}
    </ChatWorkspaceContext.Provider>
  );
}
