import { createContext } from "react";

import type { ChatWorkspace } from "../hooks/useChatWorkspace";

/** 工作区上下文仅负责页面内依赖传递，不承担业务逻辑。 */
export const ChatWorkspaceContext = createContext<ChatWorkspace | null>(null);
