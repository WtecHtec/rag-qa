import { Icon } from "../../../components/ui/Icon";
import type { KnowledgeBase } from "../types/knowledgeBase";

interface KnowledgeBaseListProps {
  items: KnowledgeBase[];
  selectedId: string | null;
  query: string;
  isLoading: boolean;
  onQueryChange: (value: string) => void;
  onSelect: (id: string) => void;
}

export function KnowledgeBaseList({
  items,
  selectedId,
  query,
  isLoading,
  onQueryChange,
  onSelect,
}: KnowledgeBaseListProps) {
  return (
    <aside className="kb-list-panel" aria-label="知识库列表">
      <label className="kb-search-field">
        <Icon name="search" size={15} />
        <span className="sr-only">搜索知识库</span>
        <input
          value={query}
          placeholder="搜索知识库"
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </label>

      <div className="kb-list" aria-live="polite">
        {isLoading && items.length === 0 ? <KnowledgeBaseListSkeleton /> : null}
        {!isLoading && items.length === 0 ? (
          <div className="kb-list-empty">
            <Icon name="library" size={22} />
            <strong>{query.trim() ? "没有匹配的知识库" : "还没有知识库"}</strong>
            <small>{query.trim() ? "尝试更换搜索关键词" : "创建后即可管理本地资料"}</small>
          </div>
        ) : null}
        {items.map((item, index) => (
          <button
            key={item.id}
            type="button"
            className={`kb-list-item ${selectedId === item.id ? "is-selected" : ""}`}
            aria-pressed={selectedId === item.id}
            onClick={() => onSelect(item.id)}
          >
            <span className={`kb-list-icon kb-list-icon--${(index % 3) + 1}`}>
              <Icon name="library" />
            </span>
            <span className="kb-list-copy">
              <strong>{item.name}</strong>
              <small>{item.document_count} 个文档</small>
            </span>
            <Icon name="chevron" size={14} />
          </button>
        ))}
      </div>
    </aside>
  );
}

function KnowledgeBaseListSkeleton() {
  return (
    <div className="kb-list-skeleton" aria-label="正在加载知识库">
      <span /><span /><span />
    </div>
  );
}

