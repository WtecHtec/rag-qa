import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../../../components/ui/Icon";
import { DocumentWorkspace } from "../../documents/components/DocumentWorkspace";
import { documentApi } from "../../documents/api/documentApi";
import type { DocumentGateway } from "../../documents/types/document";
import { useDebouncedValue } from "../../../shared/hooks/useDebouncedValue";
import { knowledgeBaseApi } from "../api/knowledgeBaseApi";
import { DeleteKnowledgeBaseDialog } from "../components/DeleteKnowledgeBaseDialog";
import { KnowledgeBaseDetail } from "../components/KnowledgeBaseDetail";
import { KnowledgeBaseErrorNotice } from "../components/KnowledgeBaseErrorNotice";
import { KnowledgeBaseFormDialog } from "../components/KnowledgeBaseFormDialog";
import { KnowledgeBaseList } from "../components/KnowledgeBaseList";
import { useKnowledgeBaseMutations } from "../hooks/useKnowledgeBaseMutations";
import { useKnowledgeBases } from "../hooks/useKnowledgeBases";
import type { KnowledgeBaseGateway } from "../types/knowledgeBase";
import { toKnowledgeBaseErrorMessage } from "../utils/knowledgeBaseError";
import type { KnowledgeBaseFormValues } from "../utils/knowledgeBaseForm";
import "../styles/knowledge-base.css";

interface KnowledgeBasePageProps {
  gateway?: KnowledgeBaseGateway;
  documentGateway?: DocumentGateway;
}

export function KnowledgeBasePage({
  gateway = knowledgeBaseApi,
  documentGateway = documentApi,
}: KnowledgeBasePageProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 240);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const preferredSelectionId = useRef<string | null>(null);
  const [formMode, setFormMode] = useState<"create" | "edit" | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const { items, total, isLoading, error: listError, refresh } = useKnowledgeBases(
    debouncedQuery,
    gateway,
  );
  const mutations = useKnowledgeBaseMutations(gateway);
  const selectedKnowledgeBase = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  useEffect(() => {
    if (preferredSelectionId.current) {
      if (items.some((item) => item.id === preferredSelectionId.current)) {
        setSelectedId(preferredSelectionId.current);
        preferredSelectionId.current = null;
      }
      return;
    }
    if (items.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!items.some((item) => item.id === selectedId)) setSelectedId(items[0].id);
  }, [items, selectedId]);

  const closeForm = () => {
    setFormMode(null);
    mutations.clearError();
  };

  const handleFormSubmit = async (values: KnowledgeBaseFormValues) => {
    if (formMode === "edit" && selectedKnowledgeBase) {
      const updated = await mutations.update(selectedKnowledgeBase.id, values);
      setSelectedId(updated.id);
    } else {
      const created = await mutations.create(values);
      // 刷新完成前旧列表仍会短暂存在，记录期望项可避免选择被重置。
      preferredSelectionId.current = created.id;
      setSelectedId(created.id);
    }
    setFormMode(null);
    refresh();
  };

  const handleDelete = async () => {
    if (!selectedKnowledgeBase) return;
    await mutations.remove(selectedKnowledgeBase.id);
    setDeleteOpen(false);
    setSelectedId(null);
    refresh();
  };

  const mutationError = toKnowledgeBaseErrorMessage(mutations.error);

  return (
    <section className="kb-page">
      <header className="kb-page-heading">
        <div><h1>知识库</h1><p>组织文档，并保持不同主题之间相互独立。</p></div>
        <button
          className="kb-button kb-button--secondary"
          type="button"
          onClick={() => { mutations.clearError(); setFormMode("create"); }}
        >
          <Icon name="plus" size={16} />新建知识库
        </button>
      </header>

      <KnowledgeBaseErrorNotice
        error={toKnowledgeBaseErrorMessage(listError)}
        onRetry={refresh}
      />

      <div className="kb-workspace">
        <KnowledgeBaseList
          items={items}
          selectedId={selectedId}
          query={query}
          isLoading={isLoading}
          onQueryChange={setQuery}
          onSelect={setSelectedId}
        />
        <KnowledgeBaseDetail
          knowledgeBase={selectedKnowledgeBase}
          onEdit={() => { mutations.clearError(); setFormMode("edit"); }}
          onDelete={() => { mutations.clearError(); setDeleteOpen(true); }}
          documentsContent={selectedKnowledgeBase ? (
            <DocumentWorkspace
              knowledgeBaseId={selectedKnowledgeBase.id}
              gateway={documentGateway}
              onMetricsChanged={refresh}
            />
          ) : null}
        />
      </div>

      <p className="kb-result-count" aria-live="polite">共 {total} 个知识库</p>

      <KnowledgeBaseFormDialog
        open={formMode !== null}
        mode={formMode ?? "create"}
        knowledgeBase={selectedKnowledgeBase}
        isSubmitting={mutations.pendingMutation === "create" || mutations.pendingMutation === "update"}
        error={mutationError}
        onClose={closeForm}
        onSubmit={handleFormSubmit}
      />
      <DeleteKnowledgeBaseDialog
        open={deleteOpen}
        knowledgeBase={selectedKnowledgeBase}
        isSubmitting={mutations.pendingMutation === "delete"}
        error={mutationError}
        onClose={() => { setDeleteOpen(false); mutations.clearError(); }}
        onConfirm={handleDelete}
      />
    </section>
  );
}
