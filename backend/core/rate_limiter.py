"""
Rate Limiter - 滑动窗口请求限流

防止 API 滥用，按客户端标识（IP 或 User ID）限制请求频率。

设计：
- 滑动窗口计数器
- 按 endpoint 分组配置
- 内存存储（适合单进程部署）
"""
from __future__ import annotations

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """限流规则。"""

    name: str
    max_requests: int      # 窗口内最大请求数
    window_seconds: int    # 滑动窗口大小（秒）
    paths: List[str] = field(default_factory=list)  # 匹配的路径前缀


# 默认规则
DEFAULT_RULES = [
    RateLimitRule(
        name="chat",
        max_requests=30,
        window_seconds=60,
        paths=["/api/chat/send", "/api/chat/send/stream", "/api/chat/send/router/stream"],
    ),
    RateLimitRule(
        name="auth",
        max_requests=10,
        window_seconds=60,
        paths=["/api/auth/login", "/api/auth/register"],
    ),
]


class SlidingWindowLimiter:
    """滑动窗口限流器。"""

    def __init__(self, rules: Optional[List[RateLimitRule]] = None):
        self._rules = rules or DEFAULT_RULES
        # key: (rule_name, client_id) -> [timestamp, ...]
        self._windows: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def _cleanup(self, key: Tuple[str, str], now: float, window: int) -> None:
        """清理过期记录。"""
        cutoff = now - window
        timestamps = self._windows[key]
        # 使用二分查找优化（列表有序）
        idx = 0
        while idx < len(timestamps) and timestamps[idx] < cutoff:
            idx += 1
        if idx > 0:
            self._windows[key] = timestamps[idx:]

    def is_allowed(self, rule_name: str, client_id: str) -> Tuple[bool, dict]:
        """检查是否允许请求。

        Returns:
            (是否允许, 限流元数据)
        """
        rule = next((r for r in self._rules if r.name == rule_name), None)
        if not rule:
            return True, {}

        now = time.monotonic()
        key = (rule_name, client_id)

        self._cleanup(key, now, rule.window_seconds)

        current_count = len(self._windows[key])
        remaining = max(0, rule.max_requests - current_count)
        reset_at = 0
        if self._windows[key]:
            reset_at = int(self._windows[key][0] + rule.window_seconds - now)

        if current_count >= rule.max_requests:
            return False, {
                "limit": rule.max_requests,
                "remaining": 0,
                "reset_seconds": max(1, reset_at),
                "rule": rule_name,
            }

        # 记录本次请求
        self._windows[key].append(now)

        return True, {
            "limit": rule.max_requests,
            "remaining": remaining - 1,
            "reset_seconds": max(0, reset_at),
            "rule": rule_name,
        }

    def match_rule(self, path: str) -> Optional[RateLimitRule]:
        """根据路径匹配限流规则。"""
        for rule in self._rules:
            for prefix in rule.paths:
                if path.startswith(prefix):
                    return rule
        return None

    def register_rule(self, rule: RateLimitRule) -> None:
        """注册新的限流规则。"""
        self._rules.append(rule)


# 全局单例
rate_limiter = SlidingWindowLimiter()
