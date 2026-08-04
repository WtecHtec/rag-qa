import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";

const VIEWPORT_PADDING = 8;
const MENU_GAP = 8;
const FALLBACK_MENU_WIDTH = 140;
const FALLBACK_MENU_HEIGHT = 176;

/** 管理反馈浮层定位和关闭边界，组件只负责渲染原因选项。 */
export function useFeedbackMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<CSSProperties>({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((current) => !current), []);

  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const triggerRect = trigger.getBoundingClientRect();
    const menuWidth = menuRef.current?.offsetWidth || FALLBACK_MENU_WIDTH;
    const menuHeight = menuRef.current?.offsetHeight || FALLBACK_MENU_HEIGHT;
    const left = Math.min(
      window.innerWidth - menuWidth - VIEWPORT_PADDING,
      Math.max(VIEWPORT_PADDING, triggerRect.right - menuWidth),
    );
    const spaceAbove = triggerRect.top - MENU_GAP;
    const top = spaceAbove >= menuHeight + VIEWPORT_PADDING
      ? triggerRect.top - menuHeight - MENU_GAP
      : triggerRect.bottom + MENU_GAP;
    setPosition({ top, left });
  }, []);

  useLayoutEffect(() => {
    if (!isOpen) return;
    updatePosition();
    // 打开后把键盘焦点送入菜单，Escape 与方向键交互不会落到页面背景。
    menuRef.current?.querySelector<HTMLButtonElement>("[role='menuitem']")?.focus();
  }, [isOpen, updatePosition]);

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      close();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      close();
      triggerRef.current?.focus();
    };
    const closeOnViewportChange = () => close();

    document.addEventListener("pointerdown", handlePointerDown, true);
    document.addEventListener("keydown", handleKeyDown, true);
    document.addEventListener("scroll", closeOnViewportChange, true);
    window.addEventListener("resize", closeOnViewportChange);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown, true);
      document.removeEventListener("keydown", handleKeyDown, true);
      document.removeEventListener("scroll", closeOnViewportChange, true);
      window.removeEventListener("resize", closeOnViewportChange);
    };
  }, [close, isOpen]);

  return {
    isOpen,
    position,
    triggerRef,
    menuRef,
    close,
    toggle,
  };
}
