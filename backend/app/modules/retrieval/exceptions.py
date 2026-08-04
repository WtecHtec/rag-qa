class RetrievalError(Exception):
    """检索模块可预期异常基类。"""

    code = "retrieval_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RetrievalValidationError(RetrievalError):
    code = "retrieval_validation_error"


class EmbeddingProviderError(RetrievalError):
    code = "embedding_provider_error"


class VectorStoreError(RetrievalError):
    code = "vector_store_error"
