from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.modules.chat.exceptions import (
    ChatError,
    ChatValidationError,
    ConversationNotFoundError,
    LlmConfigurationError,
    LlmProviderError,
    MessageNotFoundError,
)
from app.modules.documents.exceptions import (
    DocumentDuplicateError,
    DocumentError,
    DocumentNotFoundError,
    DocumentTooLargeError,
    DocumentValidationError,
    TextChunkNotFoundError,
)
from app.modules.knowledge_bases.exceptions import (
    KnowledgeBaseError,
    KnowledgeBaseNameConflictError,
    KnowledgeBaseNotEmptyError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseValidationError,
)
from app.modules.retrieval.exceptions import (
    EmbeddingProviderError,
    RetrievalError,
    RetrievalValidationError,
    VectorStoreError,
)


def register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(ChatError)
    async def handle_chat_error(request: Request, error: ChatError) -> JSONResponse:
        if isinstance(error, (ConversationNotFoundError, MessageNotFoundError)):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(error, ChatValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif isinstance(error, LlmConfigurationError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif isinstance(error, LlmProviderError):
            status_code = status.HTTP_502_BAD_GATEWAY
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "trace_id": getattr(request.state, "trace_id", "-"),
                }
            },
        )

    @application.exception_handler(KnowledgeBaseError)
    async def handle_knowledge_base_error(
        request: Request,
        error: KnowledgeBaseError,
    ) -> JSONResponse:
        status_code = _status_code_for(error)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "trace_id": getattr(request.state, "trace_id", "-"),
                }
            },
        )

    @application.exception_handler(DocumentError)
    async def handle_document_error(request: Request, error: DocumentError) -> JSONResponse:
        return JSONResponse(
            status_code=_document_status_code_for(error),
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "trace_id": getattr(request.state, "trace_id", "-"),
                }
            },
        )

    @application.exception_handler(RetrievalError)
    async def handle_retrieval_error(request: Request, error: RetrievalError) -> JSONResponse:
        if isinstance(error, RetrievalValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif isinstance(error, (EmbeddingProviderError, VectorStoreError)):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "trace_id": getattr(request.state, "trace_id", "-"),
                }
            },
        )


def _status_code_for(error: KnowledgeBaseError) -> int:
    if isinstance(error, KnowledgeBaseNotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, (KnowledgeBaseNameConflictError, KnowledgeBaseNotEmptyError)):
        return status.HTTP_409_CONFLICT
    if isinstance(error, KnowledgeBaseValidationError):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _document_status_code_for(error: DocumentError) -> int:
    if isinstance(error, (DocumentNotFoundError, TextChunkNotFoundError)):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, DocumentDuplicateError):
        return status.HTTP_409_CONFLICT
    if isinstance(error, DocumentTooLargeError):
        return status.HTTP_413_CONTENT_TOO_LARGE
    if isinstance(error, DocumentValidationError):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_500_INTERNAL_SERVER_ERROR
