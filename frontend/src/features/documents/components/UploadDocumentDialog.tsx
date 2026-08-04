import { useEffect, useRef, useState, type DragEvent } from "react";

import { Dialog } from "../../../components/ui/Dialog";
import { Icon } from "../../../components/ui/Icon";
import type { DocumentErrorMessage } from "../utils/documentError";
import { formatFileSize, validateUploadFile } from "../utils/documentFormat";
import { DocumentErrorNotice } from "./DocumentErrorNotice";

const MAX_FILE_SIZE = 100 * 1024 * 1024;

interface UploadDocumentDialogProps {
  open: boolean;
  isUploading: boolean;
  progress: number;
  error: DocumentErrorMessage | null;
  onClose: () => void;
  onUpload: (file: File) => Promise<void>;
}

export function UploadDocumentDialog({
  open, isUploading, progress, error, onClose, onUpload,
}: UploadDocumentDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (open) { setFile(null); setValidationError(null); }
  }, [open]);

  const selectFile = (nextFile: File | undefined) => {
    if (!nextFile) return;
    const nextError = validateUploadFile(nextFile, MAX_FILE_SIZE);
    setValidationError(nextError);
    setFile(nextError ? null : nextFile);
  };

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    try { await onUpload(file); } catch { /* 错误由 Mutation Hook 保留在弹窗内。 */ }
  };

  return (
    <Dialog
      open={open}
      title="导入本地文档"
      description="文件会流式传输并仅保存在本机，支持 TXT 与 Markdown。"
      closeDisabled={isUploading}
      onClose={onClose}
      footer={<>
        <button className="kb-button kb-button--quiet" type="button" disabled={isUploading} onClick={onClose}>取消</button>
        <button className="kb-button kb-button--primary" type="button" disabled={!file || isUploading} onClick={() => void handleUpload()}>
          {isUploading ? `上传中 ${progress}%` : "开始上传"}
        </button>
      </>}
    >
      <input ref={inputRef} className="sr-only" type="file" accept=".txt,.md,text/plain,text/markdown" onChange={(event) => selectFile(event.target.files?.[0])} />
      <button
        className={`doc-drop-zone ${file ? "has-file" : ""}`}
        type="button"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <span><Icon name={file ? "check" : "upload"} size={23} /></span>
        <strong>{file ? file.name : "拖入文件，或点按选择"}</strong>
        <small>{file ? formatFileSize(file.size) : "单个文件最大 100 MB；上传不会把整份文件读入页面内存"}</small>
      </button>
      {isUploading ? <div className="doc-upload-progress"><i style={{ width: `${progress}%` }} /></div> : null}
      <DocumentErrorNotice error={validationError ? { message: validationError } : error} />
    </Dialog>
  );
}
