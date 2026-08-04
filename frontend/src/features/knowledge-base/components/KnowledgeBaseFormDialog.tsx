import { useEffect, useState, type FormEvent } from "react";

import { Dialog } from "../../../components/ui/Dialog";
import type { KnowledgeBase } from "../types/knowledgeBase";
import type { KnowledgeBaseErrorMessage } from "../utils/knowledgeBaseError";
import {
  normalizeKnowledgeBaseForm,
  validateKnowledgeBaseForm,
  type KnowledgeBaseFormErrors,
  type KnowledgeBaseFormValues,
} from "../utils/knowledgeBaseForm";
import { KnowledgeBaseErrorNotice } from "./KnowledgeBaseErrorNotice";

interface KnowledgeBaseFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  knowledgeBase: KnowledgeBase | null;
  isSubmitting: boolean;
  error: KnowledgeBaseErrorMessage | null;
  onClose: () => void;
  onSubmit: (values: KnowledgeBaseFormValues) => Promise<void>;
}

const EMPTY_FORM: KnowledgeBaseFormValues = { name: "", description: "" };

export function KnowledgeBaseFormDialog({
  open,
  mode,
  knowledgeBase,
  isSubmitting,
  error,
  onClose,
  onSubmit,
}: KnowledgeBaseFormDialogProps) {
  const [values, setValues] = useState<KnowledgeBaseFormValues>(EMPTY_FORM);
  const [errors, setErrors] = useState<KnowledgeBaseFormErrors>({});

  useEffect(() => {
    if (!open) return;
    setValues(
      mode === "edit" && knowledgeBase
        ? { name: knowledgeBase.name, description: knowledgeBase.description }
        : EMPTY_FORM,
    );
    setErrors({});
    // 弹窗打开期间列表刷新不应覆盖用户已经输入的内容。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, open]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const nextErrors = validateKnowledgeBaseForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    try {
      await onSubmit(normalizeKnowledgeBaseForm(values));
    } catch {
      // Mutation Hook 会把协议错误转换为可展示状态，表单保持打开供用户修正。
    }
  };

  return (
    <Dialog
      open={open}
      title={mode === "create" ? "新建知识库" : "编辑知识库"}
      description="知识库用于隔离不同主题的文档和索引。"
      closeDisabled={isSubmitting}
      onClose={onClose}
      footer={
        <>
          <button className="kb-button kb-button--quiet" type="button" disabled={isSubmitting} onClick={onClose}>取消</button>
          <button className="kb-button kb-button--primary" type="submit" form="knowledge-base-form" disabled={isSubmitting}>
            {isSubmitting ? "正在保存…" : mode === "create" ? "创建" : "保存"}
          </button>
        </>
      }
    >
      <form id="knowledge-base-form" className="kb-form" onSubmit={handleSubmit}>
        <label>
          <span>名称</span>
          <input
            autoFocus
            value={values.name}
            maxLength={80}
            aria-invalid={Boolean(errors.name)}
            placeholder="例如：产品文档"
            onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))}
          />
          {errors.name ? <small className="kb-field-error">{errors.name}</small> : null}
        </label>
        <label>
          <span>描述 <small>选填</small></span>
          <textarea
            value={values.description}
            maxLength={500}
            rows={4}
            aria-invalid={Boolean(errors.description)}
            placeholder="说明这个知识库包含哪些资料"
            onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))}
          />
          <small className="kb-field-counter">{values.description.length} / 500</small>
          {errors.description ? <small className="kb-field-error">{errors.description}</small> : null}
        </label>
        <KnowledgeBaseErrorNotice error={error} />
      </form>
    </Dialog>
  );
}
