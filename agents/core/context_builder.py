"""
LLM context construction helpers.

This module keeps persisted transcript messages separate from the temporary
API messages sent to a model. Callers provide already-loaded history and the
builder returns a fresh OpenAI-compatible message list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


Message = Dict[str, Any]


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


context_builder = AgentContextBuilder()
