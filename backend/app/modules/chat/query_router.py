import asyncio
import logging
from collections.abc import Callable
from time import perf_counter

from app.modules.chat.intent import ClassifiedIntent, IntentClassifier, IntentDecision
from app.modules.chat.query_strategy import (
    QueryIntent,
    QueryPlan,
    plan_query,
    plan_query_deterministic,
)

MonotonicClock = Callable[[], float]


class QueryRouter:
    """先应用高精度规则，再用 LLM 分类，并在任何异常时安全降级。"""

    def __init__(
        self,
        classifier: IntentClassifier | None = None,
        *,
        timeout_seconds: float = 8,
        confidence_threshold: float = 0.65,
        clock: MonotonicClock = perf_counter,
        logger: logging.Logger | None = None,
    ) -> None:
        self._classifier = classifier
        self._timeout_seconds = timeout_seconds
        self._confidence_threshold = confidence_threshold
        self._clock = clock
        self._logger = logger or logging.getLogger(__name__)

    async def route(
        self,
        query: str,
        previous_user_query: str | None,
        previous_rag_enabled: bool,
    ) -> QueryPlan:
        started_at = self._clock()
        deterministic = plan_query_deterministic(
            query,
            previous_user_query,
            previous_rag_enabled,
        )
        if deterministic is not None:
            self._log_result(deterministic, "rule", None, started_at)
            return deterministic
        if self._classifier is None:
            fallback = plan_query(query, previous_user_query, previous_rag_enabled)
            self._log_result(fallback, "fallback_disabled", None, started_at)
            return fallback

        try:
            decision = await asyncio.wait_for(
                self._classifier.classify(
                    query,
                    previous_user_query,
                    previous_rag_enabled,
                ),
                timeout=self._timeout_seconds,
            )
            if decision.confidence < self._confidence_threshold:
                fallback = plan_query(query, previous_user_query, previous_rag_enabled)
                self._log_result(
                    fallback,
                    "fallback_low_confidence",
                    decision.confidence,
                    started_at,
                )
                return fallback
            plan = self._to_query_plan(query, decision)
            self._log_result(plan, "llm", decision.confidence, started_at)
            return plan
        except Exception as error:
            # 分类器是增强能力，不能因为超时、配置或格式问题阻断正常问答。
            fallback = plan_query(query, previous_user_query, previous_rag_enabled)
            self._logger.warning(
                "chat.intent_classifier_fallback",
                extra={
                    "error_type": type(error).__name__,
                    "fallback_intent": fallback.intent.value,
                },
            )
            self._log_result(fallback, "fallback_error", None, started_at)
            return fallback

    @staticmethod
    def _to_query_plan(query: str, decision: IntentDecision) -> QueryPlan:
        normalized = query.strip()
        if decision.intent is ClassifiedIntent.KNOWLEDGE:
            rewritten = (decision.rewritten_query or "").strip() or normalized
            return QueryPlan(QueryIntent.KNOWLEDGE, rewritten)
        if decision.intent is ClassifiedIntent.CLARIFICATION:
            return QueryPlan(QueryIntent.CLARIFICATION, normalized)
        if decision.intent is ClassifiedIntent.MEMORY_WRITE:
            # LLM 只能提出记忆候选；真正写入仍要求用户使用明确授权语句。
            return QueryPlan(QueryIntent.MEMORY_CONFIRMATION, normalized)
        return QueryPlan(QueryIntent.GENERAL, normalized)

    def _log_result(
        self,
        plan: QueryPlan,
        source: str,
        confidence: float | None,
        started_at: float,
    ) -> None:
        self._logger.info(
            "chat.intent_routed",
            extra={
                "intent": plan.intent.value,
                "intent_source": source,
                "intent_confidence": confidence,
                "rag_enabled": plan.use_rag,
                "intent_latency_ms": round((self._clock() - started_at) * 1000, 2),
            },
        )
