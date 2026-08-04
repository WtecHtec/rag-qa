import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// JSDOM 没有原生动画帧调度，测试替身保持与浏览器异步帧边界一致。
globalThis.requestAnimationFrame = (callback: FrameRequestCallback) => (
  window.setTimeout(() => callback(performance.now()), 0)
);
globalThis.cancelAnimationFrame = (frameId: number) => window.clearTimeout(frameId);

// Vitest 当前关闭全局 API，显式清理可避免不同组件测试共享残留 DOM。
afterEach(() => cleanup());
