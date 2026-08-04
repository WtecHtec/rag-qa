import type { ReactNode } from "react";

import { AppNavLink } from "../navigation/AppNavLink";
import { Icon, type IconName } from "../ui/Icon";

const navigation: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/overview", label: "概览", icon: "home" },
  { to: "/knowledge-bases", label: "知识库", icon: "library" },
  { to: "/chat", label: "问答", icon: "chat" },
  { to: "/analytics", label: "链路追踪", icon: "layers" },
  { to: "/diagnostics", label: "诊断", icon: "diagnostics" },
];

interface AppShellProps {
  currentPath: string;
  children: ReactNode;
  onNavigate: (path: string) => void;
}

export function AppShell({ currentPath, children, onNavigate }: AppShellProps) {
  const currentPage = navigation.find((item) => currentPath.startsWith(item.to))?.label ?? "设置";

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BiYou</strong>
            <small>本地知识库</small>
          </span>
        </div>

        <nav className="navigation">
          {navigation.map((item) => (
            <AppNavLink
              key={item.to}
              to={item.to}
              active={currentPath === item.to}
              ariaLabel={item.label}
              onNavigate={onNavigate}
            >
              <Icon name={item.icon} size={17} />
              <span>{item.label}</span>
            </AppNavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="service-dot" aria-hidden="true" />
          <span>本地服务</span>
          <AppNavLink to="/settings" active={currentPath === "/settings"} onNavigate={onNavigate}>
            <Icon name="settings" size={16} /><span>设置</span>
          </AppNavLink>
        </div>
      </aside>

      <div className="workspace-shell">
        <header className="app-topbar">
          <span>BiYou</span><Icon name="chevron" size={12} /><strong>{currentPage}</strong>
          <em><i aria-hidden="true" />仅存储在本机</em>
        </header>
        <main className="workspace">
          {children}
        </main>
      </div>
    </div>
  );
}
