import type { Citation } from "../types/chat";

export interface HighlightedCitationContent {
  before: string;
  match: string;
  after: string;
}

/**
 * 优先使用切块阶段保存的真实区间；旧数据没有区间时才回退到文本查找。
 * 不能只用 indexOf，因为重复句子和 Child overlap 会把标记错误地移到首次出现处。
 */
export function splitCitationContent(
  citation: Citation,
): HighlightedCitationContent | null {
  const parent = citation.parent_content;
  const start = citation.child_start_offset;
  const end = citation.child_end_offset;
  const preview = citation.child_preview.trim();
  const offsetMatch = parent.slice(start, end);
  if (
    start >= 0
    && end > start
    && end <= parent.length
    && (!preview || offsetMatch.startsWith(preview))
  ) {
    return {
      before: parent.slice(0, start),
      match: parent.slice(start, end),
      after: parent.slice(end),
    };
  }

  if (!preview) return null;
  const fallbackStart = parent.indexOf(preview);
  if (fallbackStart < 0) return null;
  return {
    before: parent.slice(0, fallbackStart),
    match: preview,
    after: parent.slice(fallbackStart + preview.length),
  };
}
