import type {
  CreateKnowledgeBaseInput,
  KnowledgeBase,
  KnowledgeBaseGateway,
  KnowledgeBasePage,
  ListKnowledgeBasesInput,
  UpdateKnowledgeBaseInput,
} from "../../features/knowledge-base/types/knowledgeBase";

const FIXED_TIME = "2026-08-03T10:00:00.000Z";

export function makeKnowledgeBase(
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase {
  return {
    id: "kb-1",
    name: "产品文档",
    description: "产品需求与调研资料",
    document_count: 0,
    ready_document_count: 0,
    failed_document_count: 0,
    chunk_count: 0,
    created_at: FIXED_TIME,
    updated_at: FIXED_TIME,
    ...overrides,
  };
}

/**
 * 内存网关只模拟前端依赖的业务契约，组件测试因此无需启动 HTTP 服务。
 */
export class FakeKnowledgeBaseGateway implements KnowledgeBaseGateway {
  private nextId = 2;

  constructor(public items: KnowledgeBase[] = []) {}

  async list(input: ListKnowledgeBasesInput = {}): Promise<KnowledgeBasePage> {
    const normalizedQuery = input.query?.trim().toLocaleLowerCase() ?? "";
    const filtered = this.items.filter((item) =>
      `${item.name} ${item.description}`.toLocaleLowerCase().includes(normalizedQuery),
    );
    return { items: [...filtered], total: filtered.length, limit: 50, offset: 0 };
  }

  async create(input: CreateKnowledgeBaseInput): Promise<KnowledgeBase> {
    const created = makeKnowledgeBase({ id: `kb-${this.nextId++}`, ...input });
    this.items = [created, ...this.items];
    return created;
  }

  async update(id: string, input: UpdateKnowledgeBaseInput): Promise<KnowledgeBase> {
    const current = this.items.find((item) => item.id === id);
    if (!current) throw new Error("知识库不存在");
    const updated = { ...current, ...input, updated_at: FIXED_TIME };
    this.items = this.items.map((item) => (item.id === id ? updated : item));
    return updated;
  }

  async remove(id: string): Promise<void> {
    this.items = this.items.filter((item) => item.id !== id);
  }
}
