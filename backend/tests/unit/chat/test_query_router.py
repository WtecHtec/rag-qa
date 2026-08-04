import asyncio

import pytest

from app.modules.chat.intent import ClassifiedIntent, IntentDecision
from app.modules.chat.query_router import QueryRouter
from app.modules.chat.query_strategy import QueryIntent


class FakeIntentClassifier:
    def __init__(self, decision: IntentDecision) -> None:
        self.decision = decision
        self.queries: list[str] = []

    async def classify(
        self,
        query: str,
        previous_user_query: str | None,
        previous_rag_enabled: bool,
    ) -> IntentDecision:
        self.queries.append(query)
        return self.decision


class FailingIntentClassifier:
    async def classify(
        self,
        query: str,
        previous_user_query: str | None,
        previous_rag_enabled: bool,
    ) -> IntentDecision:
        raise RuntimeError("分类器不可用")


class SlowIntentClassifier:
    async def classify(
        self,
        query: str,
        previous_user_query: str | None,
        previous_rag_enabled: bool,
    ) -> IntentDecision:
        await asyncio.sleep(0.02)
        return IntentDecision(ClassifiedIntent.GENERAL, 0.99)


@pytest.mark.asyncio
async def test_deterministic_greeting_skips_classifier() -> None:
    classifier = FakeIntentClassifier(IntentDecision(ClassifiedIntent.KNOWLEDGE, 0.99))
    router = QueryRouter(classifier)

    plan = await router.route("你好", None, False)

    assert plan.intent is QueryIntent.GENERAL
    assert classifier.queries == []


@pytest.mark.asyncio
async def test_llm_routes_general_and_knowledge_queries() -> None:
    general = QueryRouter(
        FakeIntentClassifier(IntentDecision(ClassifiedIntent.GENERAL, 0.91))
    )
    knowledge = QueryRouter(
        FakeIntentClassifier(
            IntentDecision(
                ClassifiedIntent.KNOWLEDGE,
                0.93,
                "Parent Child 分块策略的缺点",
            )
        )
    )

    general_plan = await general.route("帮我写一段欢迎词", None, False)
    knowledge_plan = await knowledge.route("它有什么缺点？", "分块策略是什么？", True)

    assert general_plan.intent is QueryIntent.GENERAL
    assert knowledge_plan.intent is QueryIntent.KNOWLEDGE
    assert knowledge_plan.retrieval_query == "Parent Child 分块策略的缺点"


@pytest.mark.asyncio
async def test_memory_candidate_requires_explicit_confirmation() -> None:
    router = QueryRouter(
        FakeIntentClassifier(IntentDecision(ClassifiedIntent.MEMORY_WRITE, 0.96))
    )

    plan = await router.route("以后回答尽量简洁", None, False)

    assert plan.intent is QueryIntent.MEMORY_CONFIRMATION
    assert plan.use_rag is False


@pytest.mark.asyncio
async def test_low_confidence_error_and_timeout_fall_back_to_rag() -> None:
    low_confidence = QueryRouter(
        FakeIntentClassifier(IntentDecision(ClassifiedIntent.GENERAL, 0.4)),
        confidence_threshold=0.65,
    )
    failing = QueryRouter(FailingIntentClassifier())
    slow = QueryRouter(SlowIntentClassifier(), timeout_seconds=0.001)

    plans = [
        await low_confidence.route("量子纠缠是什么？", None, False),
        await failing.route("量子纠缠是什么？", None, False),
        await slow.route("量子纠缠是什么？", None, False),
    ]

    assert all(plan.intent is QueryIntent.KNOWLEDGE for plan in plans)
