"""知识库领域异常定义。"""


class KnowledgeBaseError(Exception):
    code = "knowledge_base_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class KnowledgeBaseNotFoundError(KnowledgeBaseError):
    code = "knowledge_base_not_found"

    def __init__(self) -> None:
        super().__init__("知识库不存在或已被删除")


class KnowledgeBaseConflictError(KnowledgeBaseError):
    code = "knowledge_base_conflict"

    def __init__(self, name: str) -> None:
        super().__init__(f"知识库名称 '{name}' 已存在")
        self.name = name


class KnowledgeBaseNameConflictError(KnowledgeBaseError):
    code = "knowledge_base_name_conflict"

    def __init__(self, name: str) -> None:
        super().__init__(f"知识库名称 '{name}' 已存在")
        self.name = name


class KnowledgeBaseNotEmptyError(KnowledgeBaseError):
    code = "knowledge_base_not_empty"

    def __init__(self, document_count: int = 0) -> None:
        super().__init__(f"知识库下仍包含 {document_count} 篇文档，请先清空或确认强制删除")
        self.document_count = document_count


class KnowledgeBaseValidationError(KnowledgeBaseError):
    code = "knowledge_base_validation_error"
