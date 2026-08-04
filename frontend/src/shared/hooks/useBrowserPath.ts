import { useCallback, useEffect, useState } from "react";

function readBrowserPath(fallbackPath: string): string {
  return window.location.pathname === "/" ? fallbackPath : window.location.pathname;
}

export function useBrowserPath(fallbackPath: string) {
  const [pathname, setPathname] = useState(() => readBrowserPath(fallbackPath));

  useEffect(() => {
    if (window.location.pathname === "/") window.history.replaceState(null, "", fallbackPath);
    const handlePopState = () => setPathname(readBrowserPath(fallbackPath));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [fallbackPath]);

  const navigate = useCallback((nextPath: string) => {
    if (window.location.pathname !== nextPath) window.history.pushState(null, "", nextPath);
    setPathname(nextPath);
  }, []);

  return { pathname, navigate };
}
