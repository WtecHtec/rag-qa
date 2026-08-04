const DATE_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const TIME_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function formatKnowledgeBaseDate(value: string, now = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "未知";

  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDifference = Math.round(
    (startOfToday.getTime() - startOfDate.getTime()) / 86_400_000,
  );
  // 最近两天使用相对日期，既更易扫读，也避免窄面板内的时间换行。
  if (dayDifference === 0) return `今天 ${TIME_FORMATTER.format(date)}`;
  if (dayDifference === 1) return `昨天 ${TIME_FORMATTER.format(date)}`;
  return DATE_FORMATTER.format(date);
}
