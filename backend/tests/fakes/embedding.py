from collections.abc import Sequence

from app.modules.retrieval.models import Embedding


class FakeEmbeddingProvider:
    """API 测试使用确定性向量，不加载真实模型或访问网络。"""

    model_name = "fake-chinese-embedding"
    dimensions = 3

    async def embed_documents(self, texts: Sequence[str]) -> Sequence[Embedding]:
        return [self._embedding(text) for text in texts]

    async def embed_query(self, text: str) -> Embedding:
        return self._embedding(text)

    @staticmethod
    def _embedding(text: str) -> Embedding:
        if "蓝鲸协议" in text:
            return (1.0, 0.0, 0.0)
        return (0.0, 1.0, 0.0)
