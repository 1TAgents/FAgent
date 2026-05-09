"""
Tool Permissions - 工具权限控制

根据 10-dimensions 文档：
"高危能力不要靠模型自觉不用。应该在 runtime / toolset / sandbox 层做硬限制。"

核心概念：
- ToolPermissions: 定义允许的最大危险等级和特定工具的 allow/deny 列表
- 权限检查在 ToolRegistry.execute() 和 ReActLoop 执行前进行

设计参考：
- claude-code-rev: tool approval with always-allow / always-deny / per-request
- Vibe-Trading: trade confirmation gate before real order execution
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Set

from .base import DangerLevel

logger = logging.getLogger(__name__)


@dataclass
class ToolPermissions:
    """工具权限策略。

    通过组合最大危险等级 + 显式 allow/deny 列表，
    实现对工具执行权限的精细控制。
    """

    max_danger_level: DangerLevel = DangerLevel.EXECUTE  # 允许的最大危险等级
    allowed: Set[str] = field(default_factory=set)  # 显式允许的工具名（白名单）
    denied: Set[str] = field(default_factory=set)  # 显式拒绝的工具名（黑名单）

    def is_allowed(self, tool_name: str, danger_level: DangerLevel) -> bool:
        """检查工具是否被允许执行。

        规则：
        1. 黑名单优先 — 显式 deny 的工具一律拒绝
        2. 白名单覆盖 — 显式 allow 的工具可以超过 max_danger_level
        3. 默认按 max_danger_level 判断
        """
        # 黑名单优先
        if tool_name in self.denied:
            return False

        # 白名单覆盖
        if tool_name in self.allowed:
            return True

        # 按危险等级判断
        return danger_level <= self.max_danger_level

    def deny_reason(self, tool_name: str, danger_level: DangerLevel) -> str:
        """返回拒绝原因。"""
        if tool_name in self.denied:
            return f"工具 {tool_name} 被管理员拒绝"
        if danger_level > self.max_danger_level:
            return (
                f"工具 {tool_name} 危险等级为 {danger_level.name}，"
                f"超过允许的最大等级 {self.max_danger_level.name}"
            )
        return "权限不足"

    def clone(self) -> ToolPermissions:
        return ToolPermissions(
            max_danger_level=self.max_danger_level,
            allowed=set(self.allowed),
            denied=set(self.denied),
        )


# 预设策略
def permissions_for_route(route: str) -> ToolPermissions:
    """根据路由类型返回默认权限策略。

    金融交易系统中，不同路由的风险容忍度不同：
    - chat: 仅允许只读工具
    - market: 允许只读和执行（如回测），但不允许交易
    - strategy: 允许只读和写入
    - backtest: 允许执行（回测本身无风险）
    - trade: 允许所有等级（包括交易）
    """
    if route == "chat":
        return ToolPermissions(max_danger_level=DangerLevel.READ_ONLY)
    elif route == "market":
        return ToolPermissions(max_danger_level=DangerLevel.EXECUTE)
    elif route == "strategy":
        return ToolPermissions(max_danger_level=DangerLevel.WRITE)
    elif route == "backtest":
        return ToolPermissions(max_danger_level=DangerLevel.EXECUTE)
    elif route == "trade":
        return ToolPermissions(max_danger_level=DangerLevel.TRADE)
    else:
        return ToolPermissions(max_danger_level=DangerLevel.READ_ONLY)


# 全局默认
default_permissions = ToolPermissions(max_danger_level=DangerLevel.EXECUTE)
