import { API_BASE_URL, ApiError, apiRequest } from "../../../shared/api/client";
import type {
  DocumentGateway,
  DocumentPage,
  KnowledgeDocument,
  TextChunk,
  TextChunkPage,
} from "../types/document";

function documentBasePath(knowledgeBaseId: string): string {
  return `/knowledge-bases/${knowledgeBaseId}/documents`;
}

export const documentApi: DocumentGateway = {
  list(knowledgeBaseId, limit, offset, signal) {
    return apiRequest<DocumentPage>(
      `${documentBasePath(knowledgeBaseId)}?limit=${limit}&offset=${offset}`,
      { signal },
    );
  },

  upload(knowledgeBaseId, file, onProgress) {
    return uploadRawFile(knowledgeBaseId, file, onProgress);
  },

  remove(knowledgeBaseId, documentId) {
    return apiRequest<void>(`${documentBasePath(knowledgeBaseId)}/${documentId}`, {
      method: "DELETE",
    });
  },

  reprocess(knowledgeBaseId, documentId) {
    return apiRequest<KnowledgeDocument>(
      `${documentBasePath(knowledgeBaseId)}/${documentId}/reprocess`,
      { method: "POST" },
    );
  },

  listChunks(knowledgeBaseId, documentId, kind, parentId, limit, offset) {
    const params = new URLSearchParams({ kind, limit: String(limit), offset: String(offset) });
    if (parentId) params.set("parent_id", parentId);
    return apiRequest<TextChunkPage>(
      `${documentBasePath(knowledgeBaseId)}/${documentId}/chunks?${params}`,
    );
  },

  getChunk(knowledgeBaseId, documentId, chunkId) {
    return apiRequest<TextChunk>(
      `${documentBasePath(knowledgeBaseId)}/${documentId}/chunks/${chunkId}`,
    );
  },

  updateChunk(knowledgeBaseId, documentId, chunkId, content) {
    return apiRequest<TextChunk>(
      `${documentBasePath(knowledgeBaseId)}/${documentId}/chunks/${chunkId}`,
      { method: "PATCH", body: JSON.stringify({ content }) },
    );
  },

  removeChunk(knowledgeBaseId, documentId, chunkId) {
    return apiRequest<void>(
      `${documentBasePath(knowledgeBaseId)}/${documentId}/chunks/${chunkId}`,
      { method: "DELETE" },
    );
  },
};

function uploadRawFile(
  knowledgeBaseId: string,
  file: File,
  onProgress: (progress: number) => void,
): Promise<KnowledgeDocument> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const filename = encodeURIComponent(file.name);
    request.open(
      "POST",
      `${API_BASE_URL}${documentBasePath(knowledgeBaseId)}?filename=${filename}`,
    );
    request.responseType = "json";
    request.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        resolve(request.response as KnowledgeDocument);
        return;
      }
      const error = request.response?.error;
      reject(
        new ApiError(
          error?.message ?? `上传失败，状态码 ${request.status}`,
          request.status,
          error?.trace_id ?? request.getResponseHeader("X-Trace-ID") ?? undefined,
          error?.code,
        ),
      );
    });
    request.addEventListener("error", () => reject(new ApiError("无法连接本地服务", 0)));
    // 直接发送 File 可避免 FileReader 为大文件创建第二份内存副本。
    request.send(file);
  });
}
