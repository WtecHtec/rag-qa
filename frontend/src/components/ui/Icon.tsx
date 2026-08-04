import type { ReactNode } from "react";

export type IconName =
  | "alert"
  | "arrow"
  | "chat"
  | "check"
  | "chevron"
  | "close"
  | "copy"
  | "diagnostics"
  | "document"
  | "edit"
  | "home"
  | "library"
  | "layers"
  | "more"
  | "plus"
  | "refresh"
  | "search"
  | "send"
  | "settings"
  | "spark"
  | "stop"
  | "thumbDown"
  | "thumbUp"
  | "trash"
  | "upload";

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
}

const paths: Record<IconName, ReactNode> = {
  alert: <><path d="M12 4 3.5 19h17L12 4Z"/><path d="M12 9v4M12 16h.01"/></>,
  arrow: <path d="m9 18 6-6-6-6" />,
  chat: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-5 4v-4.8A2.5 2.5 0 0 1 4 13.2Z"/><path d="M8 8h8M8 12h5"/></>,
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  copy: <><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></>,
  diagnostics: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/><path d="m3 7 6-4 6 7 6-5"/></>,
  document: <><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h4M9 12h6M9 16h6"/></>,
  edit: <><path d="m4 16-.8 4 4-.8L18 8.4 14.6 5 4 16Z"/><path d="m12.8 6.8 3.4 3.4"/></>,
  home: <><path d="m3 11 9-7 9 7"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></>,
  library: <><path d="M4 19.5V5.8A1.8 1.8 0 0 1 5.8 4H18a2 2 0 0 1 2 2v14H5.5A1.5 1.5 0 0 1 4 18.5 1.5 1.5 0 0 1 5.5 17H20"/><path d="M8 8h8M8 12h6"/></>,
  layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
  more: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
  plus: <path d="M12 5v14M5 12h14" />,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9m2 6a7 7 0 0 0 12 2.5L20 15"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  send: <><path d="m3 3 18 9-18 9 4-9-4-9Z"/><path d="M7 12h14"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></>,
  spark: <><path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.4L12 3Z"/><path d="m18.5 14 .8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z"/></>,
  stop: <rect x="6" y="6" width="12" height="12" rx="2" />,
  thumbDown: <><path d="M7 3v11M3 4h4v10H3zM7 13l4 8 2-1v-5h5a2 2 0 0 0 2-2l-1-7a2 2 0 0 0-2-2H7"/></>,
  thumbUp: <><path d="M7 21V10M3 20h4V10H3zM7 11l4-8 2 1v5h5a2 2 0 0 1 2 2l-1 7a2 2 0 0 1-2 2H7"/></>,
  trash: <><path d="M4 7h16M9 3h6l1 4H8l1-4ZM7 7l1 14h8l1-14M10 11v6M14 11v6"/></>,
  upload: <><path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 14v6h14v-6"/></>,
};

export function Icon({ name, size = 18, className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}
