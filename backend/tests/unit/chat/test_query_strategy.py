from app.modules.chat.query_strategy import QueryIntent, plan_query, rewrite_query


def test_greeting_is_general_conversation_in_new_chat() -> None:
    plan = plan_query("你好", None, False)

    assert plan.intent is QueryIntent.GENERAL
    assert plan.use_rag is False


def test_short_knowledge_term_is_not_mistaken_for_missing_context() -> None:
    plan = plan_query("RAG", None, False)

    assert plan.intent is QueryIntent.KNOWLEDGE
    assert plan.use_rag is True


def test_new_conversation_ambiguous_query_requires_clarification() -> None:
    rewritten, needs_clarification = rewrite_query("为什么？", None)

    assert rewritten == "为什么？"
    assert needs_clarification is True


def test_follow_up_query_is_rewritten_only_for_retrieval() -> None:
    rewritten, needs_clarification = rewrite_query("继续", "为什么使用 Parent Child？")

    assert rewritten == "上一问题：为什么使用 Parent Child？\n当前追问：继续"
    assert needs_clarification is False


def test_follow_up_inherits_previous_general_chat_mode() -> None:
    plan = plan_query("继续", "介绍一下你自己", False)

    assert plan.intent is QueryIntent.GENERAL
    assert plan.retrieval_query == "上一问题：介绍一下你自己\n当前追问：继续"


def test_follow_up_inherits_previous_rag_mode() -> None:
    plan = plan_query("然后呢？", "Parent Child 如何工作？", True)

    assert plan.intent is QueryIntent.KNOWLEDGE
    assert plan.retrieval_query == "上一问题：Parent Child 如何工作？\n当前追问：然后呢？"
