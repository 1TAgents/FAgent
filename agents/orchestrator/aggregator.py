"""
Result Aggregator - 结果聚合器

将多个 SubAgent 的结果综合为一个统一回复。
设计参考：Vibe-Trading 的 Swarm result synthesis。
"""
from __future__ import annotations

import json
from typing import List

from .dispatcher import DispatchResult


class ResultAggregator:
    """结果聚合器。

    策略：
    - merge: 合并所有成功结果
    - best: 选择最长的成功结果
    - llm_synthesis: 用 LLM 综合多个结果（需传入 llm_service）
    """

    def merge(self, results: List[DispatchResult]) -> str:
        """合并所有成功结果。"""
        parts = []
        for r in results:
            if r.success and r.content:
                parts.append(r.content)
            elif not r.success:
                parts.append(f"[{r.agent_name} 失败: {r.error}]")
        return "\n\n".join(parts) if parts else "所有 SubAgent 均未返回有效结果。"

    def best(self, results: List[DispatchResult]) -> str:
        """选择最长的成功结果。"""
        successful = [r for r in results if r.success and r.content]
        if not successful:
            failed = [r for r in results if not r.success]
            if failed:
                return f"处理失败: {'; '.join(f.error for f in failed)}"
            return "无可用结果。"
        return max(successful, key=lambda r: len(r.content)).content

    def structured(self, results: List[DispatchResult]) -> dict:
        """生成结构化结果。"""
        return {
            "total_agents": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [
                {
                    "agent": r.agent_name,
                    "success": r.success,
                    "content_preview": r.preview,
                    "duration_ms": round(r.duration_ms, 2),
                }
                for r in results
            ],
        }
