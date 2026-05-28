"""
ReAct Agent Loop - LLM 驱动的工具调用循环

替代 subagent 中硬编码的工具调用，让 LLM 自主决定调用哪些工具。

核心流程：
1. 构建消息（system + history + user + tool schemas）
2. 调用 LLM（带 tool 配置）
3. 如果 LLM 返回 tool_calls，执行工具，回写结果
4. 重复 2-3 直到 LLM 返回最终回复（无 tool_calls）
5. 返回最终回复和完整执行轨迹

设计参考：
- claude-code-rev: ReAct loop with tool execution and result formatting
- Vibe-Trading: ReAct agent with event-driven callbacks
- OpenManus: step-based execution with stuck detection
"""
from __future__ import annotations

import asyncio
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

from ..core.logging import log_subagent, log_chain_event
from ..core.tracing import ExecutionTrace, TurnTrace, trace_store
from ..core.session_state import session_state
from ..tools.registry import ToolRegistry, tool_registry
from ..tools.result import ToolResult
from ..tools.permissions import ToolPermissions
from ..services.memory_bridge import memory_bridge, MemoryEntry

logger = logging.getLogger(__name__)


@dataclass
class ReActTurn:
    """ReAct 循环的单步记录。"""
    turn_id: int
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: List[dict] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    latency_ms: float = 0.0
    final_response: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "turn_id": self.turn_id,
            "model": self.model,
            "latency_ms": round(self.latency_ms, 2),
        }
        if self.tool_calls:
            d["tool_calls"] = [tc.get("name", "") for tc in self.tool_calls]
        if self.final_response:
            d["final_response"] = self.final_response
        return d


@dataclass
class ReActResult:
    """ReAct Loop 的最终输出。"""
    content: str = ""                              # LLM 最终回复
    turns: List[ReActTurn] = field(default_factory=list)  # 执行轨迹
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    error: Optional[str] = None


class ReActAgentLoop:
    """ReAct 主循环。

    Args:
        llm_service: LLM 服务实例
        system_prompt: 系统提示词
        registry: 工具注册中心
        max_turns: 最大循环次数（防无限调用）
        model: 使用的模型
        verbose: 是否输出详细日志
    """

    def __init__(
        self,
        llm_service,
        system_prompt: str,
        registry: Optional[ToolRegistry] = None,
        max_turns: int = 10,
        model: Optional[str] = None,
        verbose: bool = False,
        use_memory: bool = True,
        trace: Optional[ExecutionTrace] = None,
        cid: int = 0,
        permissions: Optional[ToolPermissions] = None,
        allowed_tool_names: Optional[Sequence[str]] = None,
    ):
        self.llm = llm_service
        self.system_prompt = system_prompt
        self.registry = registry or tool_registry
        self.max_turns = max_turns
        self.model = model
        self.verbose = verbose
        self.use_memory = use_memory
        self.trace = trace
        self.cid = cid
        self.permissions = permissions or ToolPermissions()  # 默认允许所有已注册工具
        self.allowed_tool_names = (
            list(dict.fromkeys(allowed_tool_names))
            if allowed_tool_names is not None
            else None
        )
        self._allowed_tool_name_set = (
            set(self.allowed_tool_names) if self.allowed_tool_names is not None else None
        )

    async def run(
        self,
        user_message: str,
        history: Optional[Sequence[dict]] = None,
    ) -> ReActResult:
        """执行 ReAct 循环（非流式）。

        Args:
            user_message: 当前用户消息
            history: 对话历史消息列表

        Returns:
            ReActResult: 最终结果和执行轨迹
        """
        messages = self._build_messages(user_message, history)
        result = ReActResult()
        stuck_counter = 0
        last_tool_signature = ""

        for turn_id in range(1, self.max_turns + 1):
            # 检查取消
            if session_state.is_cancelled(self.cid):
                result.content = "请求已被取消。"
                result.error = "cancelled"
                self._finalize_trace(result, user_message)
                return result

            turn_start = time.monotonic()
            turn = ReActTurn(turn_id=turn_id, model=self.model or "")

            # 1. 调用 LLM（带工具）
            response = await self._call_llm(messages)
            turn.latency_ms = (time.monotonic() - turn_start) * 1000

            # 2. 解析 LLM 响应
            tool_calls = self._extract_tool_calls(response)
            assistant_content = self._extract_assistant_content(response)

            # 2b. 累加 token 使用量
            if hasattr(response, "usage") and response.usage:
                turn.input_tokens = response.usage.prompt_tokens or 0
                turn.output_tokens = response.usage.completion_tokens or 0
                result.total_tokens += turn.input_tokens + turn.output_tokens

            if tool_calls:
                turn.tool_calls = tool_calls
                # 检查是否卡住（重复调用相同工具相同参数）
                sig = self._tool_call_signature(tool_calls)
                if sig == last_tool_signature:
                    stuck_counter += 1
                    if stuck_counter >= 3:
                        logger.warning(f"ReAct 检测到循环调用，强制终止")
                        turn.final_response = "抱歉，处理您的请求时遇到循环，已终止。"
                        result.content = turn.final_response
                        result.turns.append(turn)
                        self._finalize_trace(result, user_message)
                        return result
                else:
                    stuck_counter = 0
                    last_tool_signature = sig

                self._append_assistant_tool_message(messages, assistant_content, tool_calls)

                # 3. 并行执行工具
                tool_results = await self._execute_tools_parallel(tool_calls)
                turn.tool_results = tool_results

                for tc, tr in zip(tool_calls, tool_results):
                    tool_id = tc.get("id", "")
                    log_subagent.tool_result(
                        tr.tool_name,
                        tr.success,
                        data=tr.to_llm_content()[:300],
                        error=tr.error,
                        duration=tr.duration_ms / 1000,
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tr.to_llm_content(),
                    })

                result.turns.append(turn)
                # 继续下一轮循环

            else:
                # LLM 返回最终回复（无 tool_calls）
                turn.final_response = assistant_content
                result.content = assistant_content or "抱歉，我没有得到有效的回复。"
                result.turns.append(turn)
                log_subagent.done("ReActAgent", turn.latency_ms / 1000)
                self._finalize_trace(result, user_message)
                return result

        # 超出最大循环次数
        result.error = f"超出最大工具调用次数 ({self.max_turns})"
        result.content = "抱歉，处理您的请求时超出了最大循环次数。"
        self._finalize_trace(result, user_message)
        return result

    async def run_stream(
        self,
        user_message: str,
        history: Optional[Sequence[dict]] = None,
    ) -> AsyncIterator[str]:
        """执行 ReAct 循环（流式输出最终回复）。

        工具调用阶段不输出中间结果，只在 LLM 返回最终回复时流式输出。
        """
        messages = self._build_messages(user_message, history)
        stuck_counter = 0
        last_tool_signature = ""
        total_tokens = 0
        turns: List[TurnTrace] = []
        finished = False

        for turn_id in range(1, self.max_turns + 1):
            if session_state.is_cancelled(self.cid):
                yield "请求已被取消。"
                self._save_trace_from_stream(turns, total_tokens, user_message, error="cancelled")
                return
            turn_start = time.monotonic()
            response = await self._call_llm(messages)
            latency = (time.monotonic() - turn_start) * 1000
            tool_calls = self._extract_tool_calls(response)
            assistant_content = self._extract_assistant_content(response)

            # 累加 token
            if hasattr(response, "usage") and response.usage:
                total_tokens += (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)

            if tool_calls:
                # 追加 assistant 消息
                self._append_assistant_tool_message(messages, assistant_content, tool_calls)

                # 检查循环
                sig = self._tool_call_signature(tool_calls)
                if sig == last_tool_signature:
                    stuck_counter += 1
                    if stuck_counter >= 3:
                        turns.append(TurnTrace(
                            turn_id=turn_id, model=self.model or "", latency_ms=latency,
                            tool_calls=[tc.get("name", "") for tc in tool_calls],
                        ))
                        yield "抱歉，处理您的请求时遇到循环，已终止。"
                        self._save_trace_from_stream(turns, total_tokens, user_message, error="stuck: repeated tool calls")
                        return
                else:
                    stuck_counter = 0
                    last_tool_signature = sig

                # 并行执行工具
                tool_results = await self._execute_tools_parallel(tool_calls)

                for tc, tr in zip(tool_calls, tool_results):
                    tool_id = tc.get("id", "")
                    log_subagent.tool_result(
                        tr.tool_name,
                        tr.success,
                        data=tr.to_llm_content()[:300],
                        error=tr.error,
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tr.to_llm_content(),
                    })

                turns.append(TurnTrace(
                    turn_id=turn_id, model=self.model or "", latency_ms=latency,
                    tool_calls=[tc.get("name", "") for tc in tool_calls],
                    tool_results=[tr.to_dict() for tr in tool_results],
                ))
                # 继续循环
            else:
                response_text = assistant_content or "抱歉，我没有得到有效的回复。"
                yield response_text

                turns.append(TurnTrace(
                    turn_id=turn_id, model=self.model or "", latency_ms=latency,
                ))
                self._save_trace_from_stream(turns, total_tokens, user_message, final=response_text)
                return

        yield "抱歉，处理您的请求时超出了最大循环次数。"
        self._save_trace_from_stream(turns, total_tokens, user_message, error="exceeded max turns")

    def _save_trace_from_stream(
        self,
        turns: List[TurnTrace],
        total_tokens: int,
        user_message: str,
        *,
        final: str = "",
        error: Optional[str] = None,
    ) -> None:
        """流式模式下保存 trace（无 ReActResult 对象）。"""
        if not self.trace:
            return
        self.trace.turns = turns
        self.trace.total_tokens = total_tokens
        self.trace.total_latency_ms = sum(t.latency_ms for t in turns)
        self.trace.final_response = final
        self.trace.error = error
        self.trace.finished_at = time.time()
        try:
            trace_store.save(self.trace)
        except Exception as e:
            logger.warning(f"Failed to save stream trace: {e}")

    def _build_messages(
        self,
        user_message: str,
        history: Optional[Sequence[dict]] = None,
    ) -> List[dict]:
        """构建完整的 LLM 消息列表。"""
        system_prompt = self.system_prompt

        # 注入记忆上下文（如果 Router 尚未注入）
        if self.use_memory and "已由 Router 注入" not in system_prompt:
            memory_text = memory_bridge.format_for_prompt(max_entries=5)
            if memory_text:
                system_prompt = system_prompt + "\n" + memory_text

        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages.extend([dict(m) for m in history])

        messages.append({"role": "user", "content": user_message})
        return messages

    async def _call_llm(self, messages: List[dict]) -> Any:
        """调用 LLM，带工具配置。"""
        # 上下文压缩：如果消息过多，压缩旧对话
        non_system = [m for m in messages if m["role"] != "system"]
        if len(non_system) > 12:
            self._compact_messages(messages)

        tool_schemas = self._build_tool_schemas_for_llm()

        params = {
            "messages": messages,
            "temperature": 0.7,
            "model": self.model,
        }

        if tool_schemas:
            params["tools"] = tool_schemas

        return await self.llm.chat_completion(**params)

    def _build_tool_schemas_for_llm(self) -> List[dict]:
        """将内部工具 schema 转换为 LLM tool use 格式。"""
        if self.allowed_tool_names is None:
            schemas = self.registry.get_all_schemas()
        else:
            schemas = [
                tool.schema
                for name in self.allowed_tool_names
                if (tool := self.registry.get(name)) is not None
            ]

        result = []
        for s in schemas:
            result.append({
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": s["parameters"],
                },
            })
        return result

    def _extract_tool_calls(self, response) -> List[dict]:
        """从 LLM 响应中提取工具调用。"""
        message = response.choices[0].message if response.choices else None
        if not message:
            return []

        # OpenAI-compatible: message.tool_calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            result = []
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                result.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })
            return result

        return []

    def _extract_assistant_content(self, response) -> Optional[str]:
        """提取 assistant 文本内容。"""
        message = response.choices[0].message if response.choices else None
        if message and hasattr(message, "content"):
            return message.content
        return None

    def _append_assistant_tool_message(
        self,
        messages: List[dict],
        assistant_content: Optional[str],
        tool_calls: List[dict],
    ) -> None:
        """Append assistant tool calls using the provider-facing schema."""
        messages.append({
            "role": "assistant",
            "content": assistant_content or None,
            "tool_calls": self._to_llm_tool_calls(tool_calls),
        })

    @staticmethod
    def _to_llm_tool_calls(tool_calls: List[dict]) -> List[dict]:
        """Convert internal tool-call records to OpenAI-compatible messages."""
        llm_tool_calls: List[dict] = []
        for index, tc in enumerate(tool_calls):
            arguments = tc.get("arguments") or {}
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
            llm_tool_calls.append({
                "id": tc.get("id") or f"call_{index}",
                "type": "function",
                "function": {
                    "name": tc.get("name", ""),
                    "arguments": arguments,
                },
            })
        return llm_tool_calls

    @staticmethod
    def _tool_call_signature(tool_calls: List[dict]) -> str:
        """Return a stable signature for loop detection.

        Provider-generated tool call ids change between turns, so the signature
        only includes the semantic action: tool name and normalized arguments.
        """
        parts = []
        for tc in tool_calls:
            arguments = tc.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass
            parts.append({
                "name": str(tc.get("name", "")),
                "arguments": arguments,
            })
        return json.dumps(
            sorted(
                json.dumps(part, ensure_ascii=False, sort_keys=True, default=str)
                for part in parts
            ),
            ensure_ascii=False,
        )

    async def _execute_tools_parallel(
        self,
        tool_calls: List[dict],
    ) -> List[ToolResult]:
        """并行执行多个工具调用。

        每个工具调用独立执行，失败不影响其他工具。
        返回结果列表（与 tool_calls 顺序一致）。
        """
        coros = []
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            tool_args = tc.get("arguments", {})
            log_subagent.tool_call(tool_name, tool_args)
            coros.append(self._execute_single(tool_name, tool_args))

        results = await asyncio.gather(*coros, return_exceptions=True)

        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_name = tool_calls[i].get("name", "unknown")
                tr = ToolResult.fail(tool_name, error=str(result))
            else:
                tr = result
            processed.append(tr)

        return processed

    async def _execute_single(self, tool_name: str, tool_args: dict) -> ToolResult:
        """执行单个工具，返回 ToolResult。"""
        exec_start = time.monotonic()

        if (
            self._allowed_tool_name_set is not None
            and tool_name not in self._allowed_tool_name_set
        ):
            return ToolResult.fail(tool_name, error=f"工具 {tool_name} 不在当前工具集中")

        # 权限检查
        tool = self.registry.get(tool_name)
        timeout_seconds = 30
        if tool:
            timeout_seconds = tool.timeout_seconds
            if not self.permissions.is_allowed(tool_name, tool.danger_level):
                reason = self.permissions.deny_reason(tool_name, tool.danger_level)
                logger.warning(f"工具权限拒绝: {tool_name} - {reason}")
                return ToolResult.fail(tool_name, error=reason)

        try:
            result = await asyncio.wait_for(
                self.registry.execute(tool_name, **tool_args),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            result = ToolResult.fail(tool_name, error=f"工具执行超时 ({timeout_seconds}s)")
        except Exception as e:
            result = ToolResult.fail(tool_name, error=str(e))
        result.duration_ms = (time.monotonic() - exec_start) * 1000
        return result

    def _finalize_trace(self, result: ReActResult, user_message: str) -> None:
        """从 ReActResult 构建 ExecutionTrace 并持久化。"""
        if not self.trace:
            return
        self.trace.total_tokens = result.total_tokens
        self.trace.total_latency_ms = sum(t.latency_ms for t in result.turns)
        self.trace.error = result.error
        self.trace.finished_at = time.time()

        # 构建 TurnTrace
        for rt in result.turns:
            tt = TurnTrace(
                turn_id=rt.turn_id,
                model=rt.model,
                input_tokens=rt.input_tokens,
                output_tokens=rt.output_tokens,
                latency_ms=rt.latency_ms,
                tool_calls=[tc.get("name", "") for tc in rt.tool_calls],
                tool_results=[tr.to_dict() for tr in rt.tool_results],
            )
            self.trace.turns.append(tt)

        if result.content:
            self.trace.final_response = result.content

        try:
            trace_store.save(self.trace)
            logger.info(f"Trace saved: {self.trace.trace_id} ({len(result.turns)} turns)")
        except Exception as e:
            logger.warning(f"Failed to save trace: {e}")

    def _compact_messages(self, messages: List[dict]) -> None:
        """就地压缩旧消息，保留 system prompt 和最近的消息。"""
        from ..core.compaction import compaction

        # 分离 system prompt
        system_idx = 0 if messages and messages[0]["role"] == "system" else -1
        if system_idx >= 0:
            system_msg = messages[0]
            old_messages = messages[1:]
        else:
            system_msg = None
            old_messages = messages

        compacted, summary = compaction.compact(old_messages, max_tokens=6000, keep_recent=6)

        if not summary:
            return  # 未触发压缩

        # 替换为压缩结果
        new_messages = [system_msg] if system_msg else []
        new_messages.extend(compacted)

        # 就地修改原列表
        messages.clear()
        messages.extend(new_messages)

        logger.info(f"上下文压缩: {len(old_messages)} 条 -> {len(compacted)} 条 | 摘要: {summary[:80]}")
