"""Orchestrator 包 - 子智能体编排层。

支持：
- 并行分发到多个 SubAgent
- 结果聚合和综合
- 超时和取消处理
"""
from .dispatcher import SubAgentDispatcher, DispatchResult
from .aggregator import ResultAggregator

__all__ = ["SubAgentDispatcher", "DispatchResult", "ResultAggregator"]
