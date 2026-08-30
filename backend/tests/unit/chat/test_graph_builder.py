from unittest.mock import MagicMock

from langchain_core.tools import tool

from app.modules.chat.graph_builder import create_agentic_rag_graph


@tool
def dummy_tool(query: str) -> str:
    """测试用虚拟工具。"""
    return f"result for {query}"


def test_create_agentic_rag_graph_compiles_successfully() -> None:
    fake_llm = MagicMock()
    fake_llm.bind_tools.return_value = fake_llm

    graph = create_agentic_rag_graph(fake_llm, [dummy_tool])
    assert graph is not None

    # 验证主图的节点与中断配置
    assert "summarize_history" in graph.nodes
    assert "rewrite_query" in graph.nodes
    assert "request_clarification" in graph.nodes
    assert "agent" in graph.nodes
    assert "aggregate_answers" in graph.nodes
