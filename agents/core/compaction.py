"""
Context Compaction — 对话历史压缩摘要

当 token 预算不足时，将旧对话压缩为简短摘要，
而非直接丢弃。保留关键信息：用户约束、工具结果、关键决策。

设计参考：
- claude-code-rev: compaction service with summary extraction
- OpenManus: step-based trajectory summarization
"""
from __future__ import annotations

import logging
from typing import List, Optional

from .token_counter import count_messages_tokens, count_tokens

logger = logging.getLogger(__name__)


class ContextCompaction:
    """将旧对话压缩为摘要消息。

    两种策略：
    1. 规则提取（默认）：从旧消息中抽取关键事实，零成本
    2. LLM 摘要（可选）：调用 LLM 生成连贯摘要，成本更高但质量更好
    """

    def __init__(self, llm_service=None):
        self._llm = llm_service

    def compact(
        self,
        messages: List[dict],
        max_tokens: int,
        keep_recent: int = 4,
    ) -> tuple[List[dict], Optional[str]]:
        """压缩消息列表，返回 (压缩后消息, 摘要文本)。

        Args:
            messages: 原始消息列表（不含 system prompt）
            max_tokens: 历史消息的 token 预算
            keep_recent: 保留最近 N 条消息不压缩

        Returns:
            (compressed_messages, summary_text): 压缩后的消息列表和摘要文本。
            如果无需压缩，summary_text 为 None。
        """
        if not messages:
            return [], None

        total = count_messages_tokens(messages)
        if total <= max_tokens:
            return list(messages), None

        # 分离：待压缩的老消息 + 需保留的新消息
        cutoff = max(0, len(messages) - keep_recent)
        old_messages = messages[:cutoff]
        recent_messages = messages[cutoff:]

        if not old_messages:
            return list(messages), None

        # 生成摘要
        summary = self._extract_summary(old_messages)

        # 构建摘要消息
        result = []
        if summary:
            result.append({
                "role": "system",
                "content": f"【历史对话摘要】\n{summary}\n（以上为旧对话的压缩摘要，供参考上下文。）",
            })
        result.extend(recent_messages)

        return result, summary

    def _extract_summary(self, messages: List[dict]) -> str:
        """从旧消息中提取关键信息。

        提取：
        - 用户的问题/约束
        - 工具调用和关键结果
        - assistant 的关键结论
        """
        facts = []
        last_user = ""
        tool_summary = {}  # 统计每个工具的调用次数和关键结果

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""

            if role == "user" and content:
                # 提取用户问题（截取前 100 字符）
                q = content[:100].strip()
                if q:
                    facts.append(f"用户问: {q}")

            elif role == "assistant":
                # 提取 assistant 的关键结论
                if content:
                    # 只保留有意义的结论（跳过简短确认）
                    sentences = content.split("。")
                    for s in sentences:
                        s = s.strip()
                        if 10 < len(s) < 200:
                            facts.append(f"AI说: {s}")
                            if len(facts) > 10:
                                break

            elif role == "tool":
                # 统计工具调用结果
                tool_name = msg.get("name", "unknown")
                if tool_name not in tool_summary:
                    tool_summary[tool_name] = 0
                tool_summary[tool_name] += 1
                # 提取关键数据（截取前 80 字符）
                if content:
                    key_data = content[:80].strip()
                    if key_data and len(key_data) > 5:
                        facts.append(f"工具({tool_name}): {key_data}")

        # 如果事实太多，截取最重要的
        if len(facts) > 8:
            facts = facts[:4] + [f"... (共 {len(facts)} 条关键信息，以上为摘要)"]

        if not facts:
            return ""

        return "\n".join(facts)

    async def llm_summarize(self, messages: List[dict]) -> str:
        """使用 LLM 生成摘要（可选增强路径）。

        比规则提取更连贯，但成本更高。
        """
        if not self._llm:
            return self._extract_summary(messages)

        prompt = (
            "以下是多轮对话历史。请用 2-3 句话总结其中的关键信息：\n"
            "用户的问题和约束、AI 的重要结论、工具调用的关键结果。\n"
            "不要添加新信息，只总结已有内容。\n\n"
        )
        for msg in messages[-10:]:  # 最多总结最近 10 条
            role = msg.get("role", "")
            content = msg.get("content", "") or ""
            if content:
                prompt += f"[{role}] {content[:150]}\n"

        try:
            response = await self._llm.chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"LLM 摘要生成失败，回退到规则提取: {e}")
            return self._extract_summary(messages)


# 全局实例（无 LLM，使用规则提取）
compaction = ContextCompaction()
