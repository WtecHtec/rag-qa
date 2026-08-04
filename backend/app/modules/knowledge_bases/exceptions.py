class KnowledgeBaseError(Exception):
    """知识库模块可预期异常的基类。"""

    code = "knowledge_base_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class KnowledgeBaseValidationError(KnowledgeBaseError):
    """输入不满足知识库领域规则。"""

    code = "knowledge_base_validation_error"


class KnowledgeBaseNotFoundError(KnowledgeBaseError):
    """指定的知识库不存在。"""

    code = "knowledge_base_not_found"

    def __init__(self) -> None:
        super().__init__("知识库不存在或已被删除")


class KnowledgeBaseNameConflictError(KnowledgeBaseError):
    """知识库名称与已有记录冲突。"""

    code = "knowledge_base_name_conflict"

    def __init__(self, name: str) -> None:
        super().__init__(f"知识库名称“{name}”已存在")


class KnowledgeBaseNotEmptyError(KnowledgeBaseError):
    """知识库仍包含文档，不能由知识库模块直接删除。"""

    code = "knowledge_base_not_empty"

    def __init__(self, document_count: int) -> None:
        super().__init__(f"知识库仍包含 {document_count} 个文档，请先处理关联文档")
        self.document_count = document_count
