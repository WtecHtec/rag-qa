import { useContext } from "react";

import { ChatWorkspaceContext } from "../context/ChatWorkspaceContext";

export function useChatWorkspaceContext() {
  const workspace = useContext(ChatWorkspaceContext);
  if (!workspace) throw new Error("ChatPage 必须位于 ChatWorkspaceProvider 内");
  return workspace;
}
