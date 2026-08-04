import type { ReactNode } from "react";

import { AppShell } from "../components/layout/AppShell";
import { AnalyticsPage } from "../features/analytics/AnalyticsPage";
import { ChatPage } from "../features/chat/ChatPage";
import type { ChatGateway } from "../features/chat/types/chat";
import { DiagnosticsPage } from "../features/diagnostics/DiagnosticsPage";
import { KnowledgeBasePage } from "../features/knowledge-base/pages/KnowledgeBasePage";
import type { KnowledgeBaseGateway } from "../features/knowledge-base/types/knowledgeBase";
import { OverviewPage } from "../features/overview/OverviewPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { useBrowserPath } from "../shared/hooks/useBrowserPath";

const routes: Record<string, ReactNode> = {
  "/overview": <OverviewPage />,
  "/knowledge-bases": <KnowledgeBasePage />,
  "/analytics": <AnalyticsPage />,
  "/diagnostics": <DiagnosticsPage />,
  "/settings": <SettingsPage />,
};

interface AppRouterProps {
  chatGateway?: ChatGateway;
  knowledgeBaseGateway?: KnowledgeBaseGateway;
}

export function resolveAppRoute(
  pathname: string,
  { chatGateway, knowledgeBaseGateway }: AppRouterProps = {},
): ReactNode {
  if (pathname === "/chat") {
    return (
      <ChatPage
        gateway={chatGateway}
        knowledgeBaseGateway={knowledgeBaseGateway}
      />
    );
  }
  return routes[pathname] ?? routes["/overview"];
}

export function AppRouter(props: AppRouterProps) {
  const { pathname, navigate } = useBrowserPath("/overview");
  return (
    <AppShell currentPath={pathname} onNavigate={navigate}>
      {resolveAppRoute(pathname, props)}
    </AppShell>
  );
}
