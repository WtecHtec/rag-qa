from collections.abc import Sequence
from typing import Protocol

from app.modules.retrieval.models import Embedding


class EmbeddingProvider(Protocol):
    """Embedding Provider 端口，文档与查询必须使用同一模型和维度。"""

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> Sequence[Embedding]: ...

    async def embed_query(self, text: str) -> Embedding: ...
