"""
Memory Extractor - 对话后自动抽取记忆

在每轮对话结束后，用 LLM 分析用户消息和助手回复，
从中提取值得长期记住的信息。

设计参考：hermes-agent 的 memory plugin lifecycle (sync_turn)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .llm import llm_service
from .memory_bridge import memory_bridge, MemoryEntry
from ..core.logging import logger

EXTRACT_PROMPT = """分析以下对话，从中提取值得长期记住的信息。

只提取对后续对话有帮助的、持久的信息，例如：
- 用户的投资偏好（风险偏好、关注的股票、偏好的策略）
- 用户明确表达的事实或需求
- 用户在对话中确认的交易历史或决策

不要提取：
- 一次性问题或临时性信息
- 助手回复中的技术细节
- 寒暄或礼貌用语

输出 JSON 数组，每项包含：
[
  {"category": "user_preference", "content": "偏好低风险投资"},
  {"category": "fact", "content": "用户持有贵州茅台600519"},
  {"category": "trade_history", "content": "用户于2024年初买入600519"}
]

category 只能是：user_preference, fact, trade_history, project_context

对话：
用户：{user_message}
助手：{assistant_message}

输出 JSON："""


class MemoryExtractor:
    """对话记忆抽取器。"""

    def __init__(self):
        self._recent_pairs: List[tuple] = []  # 最近对话对，限制抽取频率

    async def extract_and_store(
        self,
        user_message: str,
        assistant_message: str,
        cid: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """从对话中提取并存储记忆。

        Args:
            user_message: 用户消息
            assistant_message: 助手回复
            cid: 会话 ID（用于来源标记）

        Returns:
            抽取到的记忆条目
        """
        # 简单的去重：如果和最近一次完全一样，跳过
        pair_key = (user_message.strip()[:200], assistant_message.strip()[:200])
        if pair_key in self._recent_pairs:
            return []
        self._recent_pairs.append(pair_key)
        # 只保留最近 10 条
        if len(self._recent_pairs) > 10:
            self._recent_pairs = self._recent_pairs[-10:]

        try:
            response = await llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": EXTRACT_PROMPT.format(
                        user_message=user_message[:500],
                        assistant_message=assistant_message[:500],
                    )},
                    {"role": "user", "content": "提取对话中的记忆信息。"},
                ],
                temperature=0.3,
                max_tokens=300,
            )

            content = response.choices[0].message.content
            memories = self._parse_extraction(content, cid)

            if memories:
                ids = memory_bridge.store_many(memories)
                logger.info(f"Memory extracted: {len(memories)} entries for cid={cid}")
                return memories

        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")

        return []

    def _parse_extraction(
        self,
        content: str,
        cid: Optional[int],
    ) -> List[MemoryEntry]:
        """解析 LLM 输出的 JSON 数组。"""
        try:
            # 提取 JSON
            json_match = re.search(r'\[[\s\S]*\]', content)
            if not json_match:
                return []

            items = json.loads(json_match.group())
            if not isinstance(items, list):
                return []

            valid_categories = {"user_preference", "fact", "trade_history", "project_context"}
            entries = []
            for item in items:
                category = item.get("category", "").strip()
                mem_content = item.get("content", "").strip()
                if category not in valid_categories or not mem_content:
                    continue

                entry = MemoryEntry(
                    id="",
                    category=category,
                    content=mem_content,
                    source_cid=str(cid) if cid else None,
                )
                entries.append(entry)

            return entries

        except Exception as e:
            logger.debug(f"Memory parse error: {e}")
            return []


# 全局单例
memory_extractor = MemoryExtractor()
