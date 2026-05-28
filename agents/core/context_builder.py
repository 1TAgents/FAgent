"""
LLM context construction helpers.

This module keeps persisted transcript messages separate from the temporary
API messages sent to a model. Callers provide already-loaded history and the
builder returns a fresh OpenAI-compatible message list.

增强版：加入 token 预算管理、工具 schema 注入、上下文裁剪。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .token_counter import count_messages_tokens, trim_messages_to_budget


Message = Dict[str, Any]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouterHistoryFormat:
    """Formatting policy for the compact history block used by the router."""

    recent_limit: int = 6
    max_content_chars: int = 100
    user_label: str = "用户"
    assistant_label: str = "AI"


class AgentContextBuilder:
    """Build temporary model messages for chat and routing calls."""

    def build_chat_messages(
        self,
        *,
        system_prompt: Optional[str],
        history: Optional[Sequence[Message]],
        user_message: str,
    ) -> List[Message]:
        """Build the full chat context without mutating stored history."""
        messages: List[Message] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            messages.extend(self._copy_messages(history))

        messages.append({"role": "user", "content": user_message})
        return messages

    def build_router_messages(
        self,
        *,
        system_prompt: str,
        history: Optional[Sequence[Message]],
        user_message: str,
        history_format: RouterHistoryFormat = RouterHistoryFormat(),
    ) -> List[Message]:
        """Build a compact routing prompt from history plus current message."""
        messages: List[Message] = [
            {"role": "system", "content": system_prompt},
        ]

        history_block = self._format_router_history(history or [], history_format)
        if history_block:
            user_content = f"【对话历史】\n{history_block}\n\n【当前问题】\n{user_message}"
        else:
            user_content = f"【当前问题】\n{user_message}"

        messages.append({"role": "user", "content": user_content})
        return messages

    def _format_router_history(
        self,
        history: Sequence[Message],
        history_format: RouterHistoryFormat,
    ) -> str:
        """Return a short human-readable history block for route decisions."""
        if not history:
            return ""

        lines: List[str] = []
        for message in history[-history_format.recent_limit :]:
            role = str(message.get("role", "assistant"))
            label = (
                history_format.user_label
                if role == "user"
                else history_format.assistant_label
            )
            content = self._stringify_content(message.get("content", ""))
            lines.append(f"{label}: {self._truncate(content, history_format.max_content_chars)}")

        return "\n".join(lines)

    @staticmethod
    def _copy_messages(history: Sequence[Message]) -> List[Message]:
        """Copy message dicts so downstream adapters cannot mutate storage rows."""
        return [dict(message) for message in history]

    @staticmethod
    def _truncate(content: str, max_chars: int) -> str:
        if max_chars <= 0 or len(content) <= max_chars:
            return content
        return f"{content[:max_chars]}..."

    @staticmethod
    def _stringify_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        return str(content)


@dataclass(frozen=True)
class ContextBudget:
    """Token 预算分配。

    默认值适配主流模型 128k 上下文窗口：
    - system: 2000 tokens（system prompt + memory + skill context）
    - tools: 3000 tokens（tool schemas，最多 15 个工具）
    - history: 8000 tokens（对话历史）
    - reserve: 2000 tokens（模型输出的预留空间）
    """
    max_total: int = 32000       # 总 token 上限
    system: int = 2000           # system prompt 预算
    tools: int = 3000            # tool schemas 预算
    history: int = 8000          # 对话历史预算
    reserve: int = 2000          # 模型输出预留
    preserve_head: int = 1       # 始终保留开头 N 条消息
    preserve_tail: int = 2       # 始终保留末尾 N 条消息


class ContextBuilderWithBudget(AgentContextBuilder):
    """带 token 预算管理的上下文构建器。

    在 AgentContextBuilder 基础上增加：
    - token 计数和预算检查
    - 自动历史裁剪
    - tool schema 注入
    """

    def build_with_tools(
        self,
        *,
        system_prompt: str,
        history: Optional[Sequence[Message]],
        user_message: str,
        tool_schemas: Optional[List[dict]] = None,
        budget: Optional[ContextBudget] = None,
    ) -> tuple[List[Message], dict]:
        """构建带工具 schema 的完整上下文。

        Args:
            system_prompt: 系统提示词
            history: 对话历史
            user_message: 当前用户消息
            tool_schemas: 工具 schema 列表（LLM tool use 格式）
            budget: token 预算配置

        Returns:
            (messages, metadata): 消息列表和元数据（含 token 统计）
        """
        budget = budget or ContextBudget()
        messages: List[Message] = []
        metadata_compaction: dict = {"summary_applied": False}

        # 1. System prompt
        system_tokens = count_messages_tokens([{"role": "system", "content": system_prompt}])
        if system_tokens > budget.system:
            logger.warning(f"system prompt 超出预算: {system_tokens} > {budget.system}")
        messages.append({"role": "system", "content": system_prompt})

        # 2. Tool schemas 作为 system 消息注入
        if tool_schemas:
            tools_desc = _format_tool_schemas_for_context(tool_schemas)
            tools_msg = {"role": "system", "content": f"可用工具:\n{tools_desc}"}
            messages.append(tools_msg)

        # 3. 历史消息（先压缩，再裁剪）
        if history:
            history_msg = [dict(m) for m in history]
            compacted, summary = _compact_or_trim(history_msg, budget.history)
            messages.extend(compacted)
            if summary:
                metadata_compaction["summary_applied"] = True
                metadata_compaction["summary_preview"] = summary[:200]

        # 4. 当前用户消息
        messages.append({"role": "user", "content": user_message})

        # 5. 检查总 token 数
        total_tokens = count_messages_tokens(messages)
        available_for_output = budget.max_total - total_tokens

        metadata = {
            "total_tokens": total_tokens,
            "available_for_output": available_for_output,
            "over_budget": total_tokens > (budget.max_total - budget.reserve),
            "history_count": len([m for m in messages if m["role"] in ("user", "assistant")]),
            "compaction": metadata_compaction,
        }

        if metadata["over_budget"]:
            logger.warning(
                f"上下文接近 token 上限: {total_tokens}/{budget.max_total}, "
                f"可用输出空间: {available_for_output}"
            )

        return messages, metadata


def _format_tool_schemas_for_context(schemas: List[dict]) -> str:
    """将工具 schema 格式化为 LLM 可读的描述文本。"""
    lines = []
    for s in schemas:
        name = s.get("name", "unknown")
        desc = s.get("description", "")
        params = s.get("parameters", {}).get("properties", {})
        param_descs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "string")
            pdesc = pinfo.get("description", "")
            required = pname in s.get("parameters", {}).get("required", [])
            param_descs.append(f"  - {pname}({ptype}){'*' if required else ''}: {pdesc}")
        lines.append(f"【{name}】{desc}")
        if param_descs:
            lines.extend(param_descs)
    return "\n".join(lines)


def _compact_or_trim(
    messages: List[dict],
    max_tokens: int,
) -> tuple[List[dict], Optional[str]]:
    """先尝试压缩摘要，不够则回退到裁剪。

    Args:
        messages: 历史消息列表
        max_tokens: 历史 token 预算

    Returns:
        (消息列表, 摘要文本或None)
    """
    from .compaction import compaction

    # 先尝试压缩（保留最近 4 条消息）
    keep_recent = 4
    compacted, summary = compaction.compact(messages, max_tokens, keep_recent)

    if summary:
        return compacted, summary

    # 压缩未触发（说明 token 够），但还是要检查是否需要裁剪
    return trim_messages_to_budget(
        messages,
        max_tokens,
        preserve_head=1,
        preserve_tail=keep_recent,
    ), None


context_builder = AgentContextBuilder()
context_builder_with_budget = ContextBuilderWithBudget()
