from collections.abc import AsyncIterator, Sequence

import pytest

from app.modules.chat.intent import ClassifiedIntent
from app.modules.chat.llm import LlmMessage
from app.providers.intent.llm_intent_classifier import LlmIntentClassifier


class FakeLlmProvider:
    model_name = "fake-intent-model"

    def __init__(self, chunks: Sequence[str]) -> None:
        self._chunks = chunks
        self.requests: list[Sequence[LlmMessage]] = []

    async def stream(self, messages: Sequence[LlmMessage]) -> AsyncIterator[str]:
        self.requests.append(messages)
        for chunk in self._chunks:
            yield chunk


@pytest.mark.asyncio
async def test_classifier_parses_streamed_json_and_passes_context() -> None:
    llm = FakeLlmProvider(
        (
            '```json\n{"intent":"knowledge","confidence":0.94,',
            '"rewritten_query":"Parent Child 的边界"}\n```',
        )
    )
    classifier = LlmIntentClassifier(llm)

    decision = await classifier.classify("它的边界呢？", "分块策略是什么？", True)

    assert decision.intent is ClassifiedIntent.KNOWLEDGE
    assert decision.confidence == 0.94
    assert decision.rewritten_query == "Parent Child 的边界"
    assert '"previous_answer_used_rag": true' in llm.requests[0][1].content


@pytest.mark.asyncio
async def test_classifier_rejects_invalid_confidence_without_network() -> None:
    classifier = LlmIntentClassifier(
        FakeLlmProvider(
            ('{"intent":"general","confidence":"高","rewritten_query":null}',)
        )
    )

    with pytest.raises(ValueError, match="置信度"):
        await classifier.classify("随便聊聊", None, False)
