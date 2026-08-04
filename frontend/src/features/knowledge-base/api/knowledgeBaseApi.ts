import { apiRequest } from "../../../shared/api/client";
import type {
  CreateKnowledgeBaseInput,
  KnowledgeBase,
  KnowledgeBaseGateway,
  KnowledgeBasePage,
  ListKnowledgeBasesInput,
  UpdateKnowledgeBaseInput,
} from "../types/knowledgeBase";

function buildListQuery(input: ListKnowledgeBasesInput = {}): string {
  const searchParams = new URLSearchParams();
  if (input.query?.trim()) searchParams.set("q", input.query.trim());
  searchParams.set("limit", String(input.limit ?? 50));
  searchParams.set("offset", String(input.offset ?? 0));
  return searchParams.toString();
}

export const knowledgeBaseApi: KnowledgeBaseGateway = {
  list(input = {}) {
    return apiRequest<KnowledgeBasePage>(`/knowledge-bases?${buildListQuery(input)}`, {
      signal: input.signal,
    });
  },

  create(input: CreateKnowledgeBaseInput) {
    return apiRequest<KnowledgeBase>("/knowledge-bases", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  update(id: string, input: UpdateKnowledgeBaseInput) {
    return apiRequest<KnowledgeBase>(`/knowledge-bases/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },

  remove(id: string) {
    return apiRequest<void>(`/knowledge-bases/${id}`, { method: "DELETE" });
  },
};

