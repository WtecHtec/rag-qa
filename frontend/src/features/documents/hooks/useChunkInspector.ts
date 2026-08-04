import { useCallback, useEffect, useRef, useState } from "react";

import { documentApi } from "../api/documentApi";
import type {
  DocumentGateway,
  KnowledgeDocument,
  TextChunk,
  TextChunkSummary,
} from "../types/document";

const PARENT_PAGE_SIZE = 20;
const CHILD_PAGE_SIZE = 30;

function toSummary(chunk: TextChunk): TextChunkSummary {
  return {
    id: chunk.id,
    document_id: chunk.document_id,
    parent_id: chunk.parent_id,
    kind: chunk.kind,
    ordinal: chunk.ordinal,
    heading_path: chunk.heading_path,
    preview: chunk.content.slice(0, 240),
    char_count: chunk.char_count,
    start_offset: chunk.start_offset,
    end_offset: chunk.end_offset,
    manually_edited: chunk.manually_edited,
  };
}

export function useChunkInspector(
  knowledgeBaseId: string,
  document: KnowledgeDocument | null,
  gateway: DocumentGateway = documentApi,
) {
  const [parents, setParents] = useState<TextChunkSummary[]>([]);
  const [parentTotal, setParentTotal] = useState(0);
  const [parentOffset, setParentOffset] = useState(0);
  const [children, setChildren] = useState<TextChunkSummary[]>([]);
  const [selectedParent, setSelectedParent] = useState<TextChunk | null>(null);
  const [selectedChild, setSelectedChild] = useState<TextChunk | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const selectedParentIdRef = useRef<string | null>(null);

  const loadParent = useCallback(async (summary: TextChunkSummary) => {
    if (!document) return;
    setIsLoading(true);
    setSelectedChild(null);
    try {
      // Parent 正文和 Child 摘要互不依赖，并行读取可避免检查器出现串行等待。
      const [detail, childPage] = await Promise.all([
        gateway.getChunk(knowledgeBaseId, document.id, summary.id),
        gateway.listChunks(
          knowledgeBaseId, document.id, "child", summary.id, CHILD_PAGE_SIZE, 0,
        ),
      ]);
      selectedParentIdRef.current = summary.id;
      setSelectedParent(detail);
      setChildren(childPage.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Parent 加载失败"));
    } finally {
      setIsLoading(false);
    }
  }, [document, gateway, knowledgeBaseId]);

  const loadChild = useCallback(async (summary: TextChunkSummary) => {
    if (!document) return;
    setIsLoading(true);
    try {
      setSelectedChild(await gateway.getChunk(knowledgeBaseId, document.id, summary.id));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Child 加载失败"));
    } finally {
      setIsLoading(false);
    }
  }, [document, gateway, knowledgeBaseId]);

  useEffect(() => {
    if (!document) {
      selectedParentIdRef.current = null;
      setParents([]);
      setSelectedParent(null);
      setSelectedChild(null);
      setChildren([]);
      return;
    }
    let active = true;
    setIsLoading(true);
    gateway.listChunks(
      knowledgeBaseId, document.id, "parent", null, PARENT_PAGE_SIZE, parentOffset,
    ).then(async (page) => {
      if (!active) return;
      setParents(page.items);
      setParentTotal(page.total);
      const preferred = page.items.find(
        (item) => item.id === selectedParentIdRef.current,
      ) ?? page.items[0];
      if (preferred) await loadParent(preferred);
      else {
        setSelectedParent(null);
        setSelectedChild(null);
        setChildren([]);
      }
    }).catch((caught: unknown) => {
      if (active) setError(caught instanceof Error ? caught : new Error("文本块加载失败"));
    }).finally(() => {
      if (active) setIsLoading(false);
    });
    return () => { active = false; };
  }, [document, gateway, knowledgeBaseId, loadParent, parentOffset, refreshVersion]);

  const saveParent = useCallback(async (content: string) => {
    if (!document || !selectedParent) return;
    setIsSaving(true);
    try {
      const updated = await gateway.updateChunk(
        knowledgeBaseId, document.id, selectedParent.id, content,
      );
      const childPage = await gateway.listChunks(
        knowledgeBaseId, document.id, "child", updated.id, CHILD_PAGE_SIZE, 0,
      );
      setSelectedParent(updated);
      setSelectedChild(null);
      setChildren(childPage.items);
      setParents((items) => items.map(
        (item) => item.id === updated.id ? toSummary(updated) : item,
      ));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Parent 保存失败"));
      throw caught;
    } finally {
      setIsSaving(false);
    }
  }, [document, gateway, knowledgeBaseId, selectedParent]);

  const saveChild = useCallback(async (content: string) => {
    if (!document || !selectedChild) return;
    setIsSaving(true);
    try {
      const updated = await gateway.updateChunk(
        knowledgeBaseId, document.id, selectedChild.id, content,
      );
      setSelectedChild(updated);
      setChildren((items) => items.map(
        (item) => item.id === updated.id ? toSummary(updated) : item,
      ));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Child 保存失败"));
      throw caught;
    } finally {
      setIsSaving(false);
    }
  }, [document, gateway, knowledgeBaseId, selectedChild]);

  const deleteParent = useCallback(async () => {
    if (!document || !selectedParent) return;
    setIsSaving(true);
    try {
      await gateway.removeChunk(knowledgeBaseId, document.id, selectedParent.id);
      selectedParentIdRef.current = null;
      setSelectedParent(null);
      setSelectedChild(null);
      setChildren([]);
      setRefreshVersion((value) => value + 1);
    } finally {
      setIsSaving(false);
    }
  }, [document, gateway, knowledgeBaseId, selectedParent]);

  const deleteChild = useCallback(async () => {
    if (!document || !selectedChild || !selectedParent) return;
    setIsSaving(true);
    try {
      await gateway.removeChunk(knowledgeBaseId, document.id, selectedChild.id);
      const childPage = await gateway.listChunks(
        knowledgeBaseId, document.id, "child", selectedParent.id, CHILD_PAGE_SIZE, 0,
      );
      setSelectedChild(null);
      setChildren(childPage.items);
    } finally {
      setIsSaving(false);
    }
  }, [document, gateway, knowledgeBaseId, selectedChild, selectedParent]);

  return {
    parents,
    parentTotal,
    parentOffset,
    parentPageSize: PARENT_PAGE_SIZE,
    children,
    selectedParent,
    selectedChild,
    isLoading,
    isSaving,
    error,
    setParentOffset,
    loadParent,
    loadChild,
    saveParent,
    saveChild,
    deleteParent,
    deleteChild,
  };
}
