import asyncio
import threading
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from fastembed import TextEmbedding

from app.modules.retrieval.exceptions import EmbeddingProviderError
from app.modules.retrieval.models import Embedding


class FastEmbedEmbeddingProvider:
    """使用量化 ONNX 中文模型在本机生成真实语义向量。"""

    def __init__(
        self,
        *,
        model_name: str,
        dimensions: int,
        cache_dir: Path,
        batch_size: int = 64,
    ) -> None:
        if dimensions < 1 or batch_size < 1:
            raise ValueError("Embedding 维度和批次必须大于 0")
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._model_name = model_name
        self._dimensions = dimensions
        self._batch_size = batch_size
        # lazy_load 避免应用启动就阻塞；首次索引时下载一次，随后复用本地缓存。
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_dir),
            lazy_load=True,
        )
        # ONNX Session 与生成器共用同一实例，串行入口可避免并发初始化和线程争用。
        self._inference_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: Sequence[str]) -> Sequence[Embedding]:
        if not texts:
            return ()
        return await self._run_inference(
            lambda: self._model.embed(texts, batch_size=self._batch_size)
        )

    async def embed_query(self, text: str) -> Embedding:
        vectors = await self._run_inference(lambda: self._model.query_embed([text]))
        if len(vectors) != 1:
            raise EmbeddingProviderError("本地 Embedding 模型未返回查询向量")
        return vectors[0]

    async def _run_inference(self, operation: "EmbeddingOperation") -> Sequence[Embedding]:
        try:
            return await asyncio.to_thread(self._collect, operation)
        except EmbeddingProviderError:
            raise
        except Exception as error:
            raise EmbeddingProviderError(
                "本地 Embedding 模型加载或推理失败，请检查模型缓存与日志"
            ) from error

    def _collect(self, operation: "EmbeddingOperation") -> Sequence[Embedding]:
        with self._inference_lock:
            vectors = tuple(tuple(float(value) for value in vector) for vector in operation())
        if any(len(vector) != self._dimensions for vector in vectors):
            raise EmbeddingProviderError("本地 Embedding 模型维度与配置不一致")
        return vectors


EmbeddingOperation = Callable[[], Iterable[Sequence[float]]]
