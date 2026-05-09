"""
Token Counter - 近似 token 计数

提供快速的 token 估算，避免每次计数都调用 tiktoken。
当 tiktoken 可用时使用精确计数，否则使用启发式估算。

设计参考：hermes-agent 的 trajectory_compressor，claude-code-rev 的 token budget。
"""
from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_has_tiktoken = False
_tiktoken_enc = None

try:
    import tiktoken
    _tiktoken_enc = tiktoken.encoding_for_model("gpt-4o")
    _has_tiktoken = True
except ImportError:
    pass

# 中文 token 估算系数：1 个中文字符 ≈ 1.5 tokens
# 英文：1 个单词 ≈ 1.3 tokens
ZH_RATIO = 1.5
EN_RATIO = 1.3


def count_tokens(text: str) -> int:
    """估算文本的 token 数量。"""
    if not text:
        return 0
    if _has_tiktoken:
        return len(_tiktoken_enc.encode(text))
    # 启发式估算：分离中英文字符
    zh_chars = sum(1 for c in text if '一' <= c <= '鿿')
    en_words = len(text.split())
    other = len(text) - zh_chars - sum(len(w) for w in text.split())
    return int(zh_chars * ZH_RATIO + en_words * EN_RATIO + other * 0.3)


def count_messages_tokens(messages: List[dict]) -> int:
    """估算一组消息的 token 总数（包含 role 和 content 开销）。"""
    total = 0
    for msg in messages:
        # 每条消息有固定开销：role + 格式标记 ≈ 4 tokens
        total += 4
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += count_tokens(part["text"])
                else:
                    total += 1
        # tool calls 额外开销
        if "tool_calls" in msg:
            total += 10  # 格式开销
            for tc in msg["tool_calls"]:
                total += count_tokens(str(tc.get("function", {})))
    return total


def trim_messages_to_budget(
    messages: List[dict],
    max_tokens: int,
    preserve_head: int = 1,
    preserve_tail: int = 2,
) -> List[dict]:
    """裁剪消息列表以符合 token 预算。

    策略：
    - 保留最开头的 preserve_head 条消息（通常是 system prompt）
    - 保留最末尾的 preserve_tail 条消息（最近的对话）
    - 中间的按时间顺序从旧到新裁剪

    Args:
        messages: 原始消息列表
        max_tokens: 最大 token 数
        preserve_head: 保留开头消息数
        preserve_tail: 保留末尾消息数

    Returns:
        裁剪后的消息列表
    """
    if not messages:
        return []

    total = count_messages_tokens(messages)
    if total <= max_tokens:
        return list(messages)

    head = messages[:preserve_head]
    tail = messages[-preserve_tail:] if len(messages) > preserve_tail else []
    middle = messages[preserve_head:len(messages) - preserve_tail] if len(messages) > preserve_head + preserve_tail else []

    # 从中间消息开始裁剪（从最旧的开始）
    result = list(head) + list(tail)
    result_tokens = count_messages_tokens(result)

    if result_tokens > max_tokens:
        # 即使只保留头和尾也超限，只能保留最后一条
        logger.warning(f"token 预算严重超限 ({result_tokens} > {max_tokens})，仅保留最新消息")
        return [messages[-1]]

    return result


def estimate_context_size(messages: List[dict]) -> dict:
    """返回上下文大小的详细分析。"""
    total = count_messages_tokens(messages)
    breakdown = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        tokens = count_tokens(content) if isinstance(content, str) else 4
        breakdown.append({"idx": i, "role": role, "tokens": tokens})

    return {
        "total_tokens": total,
        "message_count": len(messages),
        "breakdown": breakdown,
        "uses_tiktoken": _has_tiktoken,
    }
