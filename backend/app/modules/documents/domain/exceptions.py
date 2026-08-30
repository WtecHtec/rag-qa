"""文档领域异常定义。"""


class DocumentError(Exception):
    """文档模块异常基类。"""

    code = "document_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentValidationError(DocumentError):
    code = "document_validation_error"


class DocumentNotFoundError(DocumentError):
    code = "document_not_found"

    def __init__(self) -> None:
        super().__init__("文档不存在或已被删除")


class DocumentTooLargeError(DocumentError):
    code = "document_too_large"

    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(f"文档超过大小限制，最大允许 {max_size_bytes // 1024 // 1024} MB")


class DocumentDuplicateError(DocumentError):
    code = "document_duplicate"

    def __init__(self) -> None:
        super().__init__("当前知识库已经上传过相同内容的文档")


class TextChunkNotFoundError(DocumentError):
    code = "text_chunk_not_found"

    def __init__(self) -> None:
        super().__init__("文本块不存在或已被重新生成")


class DocumentDecodeError(DocumentError):
    code = "document_decode_error"

    def __init__(self) -> None:
        super().__init__("文档不是有效的 UTF-8 文本")
