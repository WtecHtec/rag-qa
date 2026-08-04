import type { MouseEvent, ReactNode } from "react";

interface AppNavLinkProps {
  to: string;
  active: boolean;
  children: ReactNode;
  ariaLabel?: string;
  onNavigate: (path: string) => void;
}

export function AppNavLink({
  to,
  active,
  children,
  ariaLabel,
  onNavigate,
}: AppNavLinkProps) {
  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    // 保留新标签页和复制链接等浏览器原生行为，只接管普通左键导航。
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onNavigate(to);
  };

  return (
    <a
      href={to}
      className={active ? "active" : undefined}
      aria-current={active ? "page" : undefined}
      aria-label={ariaLabel}
      onClick={handleClick}
    >
      {children}
    </a>
  );
}
