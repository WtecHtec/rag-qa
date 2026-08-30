"""向量嵌入模型领域抽象协议。"""

from collections.abc import Sequence
from typing import Protocol

from app.modules.retrieval.domain.models import Embedding


class EmbeddingProvider(Protocol):
    """Embedding Provider 端口协议。"""

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> Sequence[Embedding]: ...

    async def embed_query(self, text: str) -> Embedding: ...
