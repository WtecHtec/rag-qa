import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { Icon } from "./Icon";
import "./dialog.css";

interface DialogProps {
  open: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  footer: ReactNode;
  onClose: () => void;
  closeDisabled?: boolean;
  tone?: "default" | "danger";
  size?: "default" | "wide";
}

export function Dialog({
  open,
  title,
  description,
  children,
  footer,
  onClose,
  closeDisabled = false,
  tone = "default",
  size = "default",
}: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    // 使用同步 effect 聚焦，避免延迟回调打断用户已经开始的键盘输入。
    const focusTarget = dialogRef.current?.querySelector<HTMLElement>(
      "[autofocus], input, textarea, button:not([disabled])",
    );
    (focusTarget ?? dialogRef.current)?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="ui-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !closeDisabled) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={`ui-dialog ui-dialog--${tone} ui-dialog--${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="ui-dialog-title"
        tabIndex={-1}
        onKeyDown={(event) => {
          if (event.key === "Escape" && !closeDisabled) onClose();
        }}
      >
        <header className="ui-dialog__header">
          <div>
            <h2 id="ui-dialog-title">{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          <button
            className="ui-icon-button"
            type="button"
            aria-label="关闭"
            disabled={closeDisabled}
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </header>
        <div className="ui-dialog__body">{children}</div>
        <footer className="ui-dialog__footer">{footer}</footer>
      </div>
    </div>,
    document.body,
  );
}
