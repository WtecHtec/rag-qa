from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

from app.providers.embedding import fastembed_embedding


class FakeTextEmbedding:
    """替代真实 ONNX 模型，确保单测不下载模型。"""

    init_arguments: dict[str, object] = {}

    def __init__(self, **kwargs: object) -> None:
        self.init_arguments = kwargs
        FakeTextEmbedding.init_arguments = kwargs

    def embed(self, documents: Sequence[str], *, batch_size: int) -> Iterable[Sequence[float]]:
        assert batch_size == 2
        return ([float(len(document)), 0.0] for document in documents)

    def query_embed(self, queries: Sequence[str]) -> Iterable[Sequence[float]]:
        return ([0.0, float(len(query))] for query in queries)


@pytest.mark.asyncio
async def test_fastembed_provider_lazily_uses_local_cache_and_separates_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fastembed_embedding, "TextEmbedding", FakeTextEmbedding)
    provider = fastembed_embedding.FastEmbedEmbeddingProvider(
        model_name="fake/model",
        dimensions=2,
        cache_dir=tmp_path / "models",
        batch_size=2,
    )
    documents = await provider.embed_documents(["知识", "检索"])
    query = await provider.embed_query("问题")

    assert FakeTextEmbedding.init_arguments["model_name"] == "fake/model"
    assert FakeTextEmbedding.init_arguments["lazy_load"] is True
    assert documents == ((2.0, 0.0), (2.0, 0.0))
    assert query == (0.0, 2.0)
