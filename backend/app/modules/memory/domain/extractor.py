"""显式记忆提取与键派生领域纯函数。"""

import re

PREFIX_PATTERN = re.compile(
    r"^(?:请)?记住(?:这个|这点|以下内容)?[：:\s]*(?P<content>.+?)[。！!]*$",
    re.IGNORECASE,
)
SUFFIX_PATTERN = re.compile(
    r"^(?P<content>.+?)[，,。；;！!\s]*(?:请)?记住(?:这个|这点|它)?[。！!]*$",
    re.IGNORECASE,
)
KEY_SEPARATORS = re.compile(r"现在修改为|修改为|改为|调整为|切换为")


def extract_explicit_memory(message: str) -> str | None:
    """提取用户明确要求保存的记忆内容。"""
    normalized = message.strip()
    for pattern in (PREFIX_PATTERN, SUFFIX_PATTERN):
        matched = pattern.fullmatch(normalized)
        if matched:
            content = matched.group("content").strip(" \t\r\n，,。；;：:！!")
            return content if content else None
    return None


def derive_memory_key(content: str) -> str:
    """从内容主体派生去重索引键。"""
    normalized = " ".join(content.casefold().split())
    subject = KEY_SEPARATORS.split(normalized, maxsplit=1)[0].strip(" ，,。；;：:")
    return (subject or normalized)[:80]
