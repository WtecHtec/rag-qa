export interface KnowledgeBaseFormValues {
  name: string;
  description: string;
}

export interface KnowledgeBaseFormErrors {
  name?: string;
  description?: string;
}

export function validateKnowledgeBaseForm(
  values: KnowledgeBaseFormValues,
): KnowledgeBaseFormErrors {
  const errors: KnowledgeBaseFormErrors = {};
  const normalizedName = values.name.replace(/\s+/g, " ").trim();
  if (!normalizedName) errors.name = "请输入知识库名称";
  else if (normalizedName.length > 80) errors.name = "名称不能超过 80 个字符";
  if (values.description.trim().length > 500) errors.description = "描述不能超过 500 个字符";
  return errors;
}

export function normalizeKnowledgeBaseForm(
  values: KnowledgeBaseFormValues,
): KnowledgeBaseFormValues {
  return {
    name: values.name.replace(/\s+/g, " ").trim(),
    description: values.description.trim(),
  };
}

