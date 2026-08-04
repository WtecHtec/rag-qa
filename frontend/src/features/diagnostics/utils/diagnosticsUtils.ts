/**
 * 诊断与 Analytics 格式化纯工具函数。
 * 包含磁盘体积转换、耗时格式化、状态颜色映射等无副作用纯函数，方便单元测试。
 */

/**
 * 将字节数格式化为人类可读的 MB / GB 字符串。
 */
export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = bytes / Math.pow(k, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
}

/**
 * 格式化毫秒耗时显示。
 */
export function formatLatency(ms: number | null): string {
  if (ms === null || ms === undefined) return "--";
  if (ms < 1) return "< 1 ms";
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/**
 * 根据总体健康状态返回 CSS Badge 类别及中文状态名。
 */
export function getStatusBadgeInfo(status: "healthy" | "degraded" | "unhealthy"): {
  label: string;
  badgeClass: string;
  dotColorClass: string;
} {
  switch (status) {
    case "healthy":
      return {
        label: "运行正常",
        badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
        dotColorClass: "bg-emerald-500",
      };
    case "degraded":
      return {
        label: "性能下降 / 部分待索引",
        badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
        dotColorClass: "bg-amber-500",
      };
    case "unhealthy":
    default:
      return {
        label: "存在异常",
        badgeClass: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
        dotColorClass: "bg-rose-500",
      };
  }
}

/**
 * 将组件英文名映射为友好中文显示。
 */
export function getComponentNameInChinese(name: string): string {
  const nameMap: Record<string, string> = {
    sqlite_database: "SQLite 关系型数据库",
    lancedb_vector_store: "LanceDB 向量索引存储",
    embedding_provider: "Embedding 文本向量化引擎",
    llm_provider: "LLM 大语言模型服务",
  };
  return nameMap[name] || name;
}
