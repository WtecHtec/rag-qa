from __future__ import annotations

from typing import Any

from app.modules.chat.domain.state import ConversationState


def request_clarification(state: ConversationState) -> dict[str, Any]:
    """澄清提问中断节点（配合 interrupt_before 实现等待用户输入）。"""
    return {}
