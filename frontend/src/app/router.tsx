import type { ReactNode } from "react";

import { AppShell } from "../components/layout/AppShell";
import { ChatPage } from "../features/chat/ChatPage";
import { DiagnosticsPage } from "../features/diagnostics/DiagnosticsPage";
import { KnowledgeBasePage } from "../features/knowledge-base/pages/KnowledgeBasePage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { useBrowserPath } from "../shared/hooks/useBrowserPath";

const routes: Record<string, ReactNode> = {
  "/overview": <OverviewPage />,
  "/knowledge-bases": <KnowledgeBasePage />,
  "/chat": <ChatPage />,
  "/diagnostics": <DiagnosticsPage />,
  "/settings": <SettingsPage />,
};

export function resolveAppRoute(pathname: string): ReactNode {
  return routes[pathname] ?? routes["/overview"];
}

export function AppRouter() {
  const { pathname, navigate } = useBrowserPath("/overview");
  return (
    <AppShell currentPath={pathname} onNavigate={navigate}>
      {resolveAppRoute(pathname)}
    </AppShell>
  );
}
