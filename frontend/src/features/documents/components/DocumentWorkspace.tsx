import { useState } from "react";

import { Icon } from "../../../components/ui/Icon";
import { documentApi } from "../api/documentApi";
import { useDocumentMutations } from "../hooks/useDocumentMutations";
import { useDocuments } from "../hooks/useDocuments";
import type { DocumentGateway, KnowledgeDocument } from "../types/document";
import { toDocumentErrorMessage } from "../utils/documentError";
import { ChunkInspectorDialog } from "./ChunkInspectorDialog";
import { DeleteDocumentDialog } from "./DeleteDocumentDialog";
import { DocumentErrorNotice } from "./DocumentErrorNotice";
import { DocumentList } from "./DocumentList";
import { UploadDocumentDialog } from "./UploadDocumentDialog";
import "../styles/documents.css";

interface DocumentWorkspaceProps {
  knowledgeBaseId: string;
  gateway?: DocumentGateway;
  onMetricsChanged: () => void;
}

export function DocumentWorkspace({
  knowledgeBaseId, gateway = documentApi, onMetricsChanged,
}: DocumentWorkspaceProps) {
  const documents = useDocuments(knowledgeBaseId, gateway);
  const mutations = useDocumentMutations(gateway);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null);
  const [inspectTarget, setInspectTarget] = useState<KnowledgeDocument | null>(null);

  const refreshAll = () => { documents.refresh(); onMetricsChanged(); };
  const upload = async (file: File) => {
    await mutations.upload(knowledgeBaseId, file);
    setUploadOpen(false);
    refreshAll();
  };
  const remove = async () => {
    if (!deleteTarget) return;
    await mutations.remove(knowledgeBaseId, deleteTarget.id);
    setDeleteTarget(null);
    refreshAll();
  };
  const reprocess = async (document: KnowledgeDocument) => {
    try { await mutations.reprocess(knowledgeBaseId, document.id); refreshAll(); } catch { /* 行内显示协议错误。 */ }
  };

  const error = toDocumentErrorMessage(mutations.error ?? documents.error);
  return (
    <div className="doc-workspace">
      <div className="kb-documents-heading doc-heading">
        <div><h3>文档</h3><p>分页展示源文件；文本块正文按需读取</p></div>
        <button className="kb-button kb-button--secondary" type="button" onClick={() => { mutations.clearError(); setUploadOpen(true); }}><Icon name="upload" size={15} />导入文档</button>
      </div>
      <DocumentErrorNotice error={error} />
      <DocumentList items={documents.items} isLoading={documents.isLoading} onInspect={setInspectTarget} onDelete={setDeleteTarget} onReprocess={(item) => void reprocess(item)} />
      {documents.total > documents.pageSize ? (
        <nav className="doc-pagination" aria-label="文档分页">
          <span>{documents.offset + 1}–{Math.min(documents.offset + documents.pageSize, documents.total)} / {documents.total}</span>
          <button type="button" disabled={documents.offset === 0} onClick={() => documents.setOffset(Math.max(0, documents.offset - documents.pageSize))}>上一页</button>
          <button type="button" disabled={documents.offset + documents.pageSize >= documents.total} onClick={() => documents.setOffset(documents.offset + documents.pageSize)}>下一页</button>
        </nav>
      ) : null}
      <UploadDocumentDialog open={uploadOpen} isUploading={mutations.pending === "upload"} progress={mutations.uploadProgress} error={toDocumentErrorMessage(mutations.error)} onClose={() => setUploadOpen(false)} onUpload={upload} />
      <DeleteDocumentDialog document={deleteTarget} isDeleting={mutations.pending === "delete"} error={toDocumentErrorMessage(mutations.error)} onClose={() => setDeleteTarget(null)} onConfirm={remove} />
      <ChunkInspectorDialog knowledgeBaseId={knowledgeBaseId} document={inspectTarget} gateway={gateway} onClose={() => setInspectTarget(null)} onChanged={refreshAll} />
    </div>
  );
}
