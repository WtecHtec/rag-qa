import type { DocumentStatus } from "../types/document";

const STATUS_LABELS: Record<DocumentStatus, string> = {
  pending: "等待处理",
  parsing: "正在解析",
  chunking: "正在切块",
  chunked: "切块完成",
  embedding: "正在向量化",
  indexing: "正在写入索引",
  ready: "可检索",
  failed: "处理失败",
};

export function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`;
}

export function getDocumentStatusLabel(status: DocumentStatus): string {
  return STATUS_LABELS[status];
}

export function isDocumentProcessing(status: DocumentStatus): boolean {
  return ["pending", "parsing", "chunking", "embedding", "indexing"].includes(status);
}

export function validateUploadFile(file: File, maxSizeBytes: number): string | null {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLocaleLowerCase();
  if (extension !== ".txt" && extension !== ".md") return "目前只支持 TXT 和 Markdown 文档";
  if (file.size === 0) return "不能上传空文档";
  if (file.size > maxSizeBytes) return `单个文件不能超过 ${formatFileSize(maxSizeBytes)}`;
  return null;
}
