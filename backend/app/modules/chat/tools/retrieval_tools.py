"""两阶段检索领域工具：包含子块初筛搜索与父块完整上下文调取。"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from langchain_core.tools import BaseTool, tool

from app.modules.retrieval.service import RetrievalService

CHILD_CHUNK_SEPARATOR = "\n\n---\n\n"
logger = logging.getLogger(__name__)


def _parse_uuid(id_str: str) -> UUID | None:
    """尝试将字符串解析为合法 UUID，失败时返回 None。"""
    try:
        return UUID(id_str.strip())
    except (ValueError, AttributeError):
        return None


def create_retrieval_tools(
    retrieval_service: RetrievalService,
    *,
    knowledge_base_id: UUID | None = None,
    recalled_sink: list[Any] | None = None,
) -> Sequence[BaseTool]:
    """构建两阶段检索工具集合（纯函数构造，扁平易读）。

    1. search_child_chunks: 第一阶段精细子块初筛，返回真实文件名、Chunk ID 与 Parent ID
    2. retrieve_parent_chunks: 第二阶段按需获取父块大上下文
    """

    @tool("search_child_chunks")
    async def search_child_chunks(query: str, limit: int = 5) -> str:
        """在向量知识库中搜索与问题相关的文档片段（第一阶段初筛）。

        返回值包含文档文件名、Parent ID、Chunk ID、标题路径和子块内容。如果内容相关但上下文不够完整，
        请使用返回的 Parent ID 调用 retrieve_parent_chunks 获取完整段落。

        Args:
            query: 精炼的搜索关键词或核心短句。
            limit: 最大返回的片段数量，默认 5 条。
        """
        logger.info("tool.search_child_chunks.start", extra={"query": query, "limit": limit})
        try:
            items = await retrieval_service.search_child_chunks(
                query,
                limit=limit,
                knowledge_base_id=knowledge_base_id,
            )
            if not items:
                output = "NO_RELEVANT_CHUNKS"
                logger.info("tool.search_child_chunks.end", extra={"result": output})
                return output

            if recalled_sink is not None:
                recalled_sink.extend(items)

            formatted_chunks = [
                f"Document: {item.document_name or '未知文档'}\n"
                f"Heading: {item.heading_path or 'General'}\n"
                f"Chunk ID: {item.child_id}\n"
                f"Parent ID: {item.parent_id}\n"
                f"Score: {item.score:.2f}\n"
                f"Content: {item.content.strip()}"
                for item in items
            ]
            output = CHILD_CHUNK_SEPARATOR.join(formatted_chunks)
            logger.info("tool.search_child_chunks.end", extra={"hit_count": len(items)})
            return output
        except Exception as e:
            logger.exception("tool.search_child_chunks.failed", extra={"query": query})
            return f"RETRIEVAL_ERROR: {e!s}"

    @tool("retrieve_parent_chunks")
    async def retrieve_parent_chunks(parent_id: str) -> str:
        """根据 Parent ID 提取完整的父块大上下文段落（第二阶段深入阅读）。

        仅在 search_child_chunks 找到相关线索且需要完整章节背景时调用。
        不要重复调用已经获取过的 Parent ID。

        Args:
            parent_id: search_child_chunks 返回的 Parent ID。
        """
        logger.info("tool.retrieve_parent_chunks.start", extra={"parent_id": parent_id})
        parsed_id = _parse_uuid(parent_id)
        if parsed_id is None:
            return "PARENT_RETRIEVAL_ERROR: Invalid parent_id UUID format."

        try:
            parent = await retrieval_service.get_parent_chunk(parsed_id)
            if not parent:
                output = "NO_PARENT_DOCUMENT"
                logger.info("tool.retrieve_parent_chunks.end", extra={"result": output})
                return output

            output = (
                f"Document: {parent.document_name or '未知文档'}\n"
                f"Parent ID: {parent.parent_id}\n"
                f"Heading: {parent.heading_path or 'General'}\n"
                f"Content: {parent.content.strip()}"
            )
            logger.info(
                "tool.retrieve_parent_chunks.end",
                extra={"parent_id": str(parent.parent_id), "char_count": parent.char_count},
            )
            return output
        except Exception as e:
            logger.exception("tool.retrieve_parent_chunks.failed", extra={"parent_id": parent_id})
            return f"PARENT_RETRIEVAL_ERROR: {e!s}"

    return [search_child_chunks, retrieve_parent_chunks]


# 兼容过渡别名
class RetrievalToolFactory:
    """工具构建器兼容包装。"""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        *,
        knowledge_base_id: UUID | None = None,
    ) -> None:
        self._tools = create_retrieval_tools(
            retrieval_service, knowledge_base_id=knowledge_base_id
        )

    def create_tools(self) -> Sequence[BaseTool]:
        return self._tools
