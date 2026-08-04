from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge_bases import router as knowledge_bases_router
from app.api.v1.retrieval import router as retrieval_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(knowledge_bases_router, tags=["knowledge-bases"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(retrieval_router, tags=["retrieval"])
api_router.include_router(chat_router, tags=["chat"])
