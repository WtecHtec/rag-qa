import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "BIYOU_");
  const frontendPort = Number(env.BIYOU_FRONTEND_PORT || 4173);
  const backendPort = Number(env.BIYOU_BACKEND_PORT || 8001);

  return {
    plugins: [react()],
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      css: true,
      // React Portal 与定时轮询共用浏览器全局，串行文件可避免环境销毁时仍有调度任务。
      fileParallelism: false,
    },
    server: {
      host: "127.0.0.1",
      port: frontendPort,
      strictPort: true,
      proxy: {
        "/api": {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});
