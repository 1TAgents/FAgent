"""
Backtest Tools - 回测与策略工具

将回测引擎和策略库封装为 ReAct Loop 可调用的 Tool。

工具列表：
- list_strategies: 列出所有可用策略及其简介
- get_strategy_info: 获取指定策略的详细说明和参数
- run_backtest: 执行回测并返回绩效摘要
- optimize_backtest: 参数网格搜索优化
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from ..base import BaseTool, DangerLevel
from ..result import ToolResult
from ...backtest.strategy_catalog import STRATEGY_CATALOG, resolve_strategy

logger = logging.getLogger(__name__)

SYMBOL_NAMES = {
    "600519": "贵州茅台",
    "000001": "平安银行",
    "300750": "宁德时代",
}


def _resolve_strategy(query: str) -> Optional[str]:
    """从用户查询中解析策略名称。"""
    return resolve_strategy(query)


# ==================== ListStrategiesTool ====================

class ListStrategiesTool(BaseTool):
    """列出所有可用策略及其简介。"""

    name = "list_strategies"
    description = "列出所有可用的交易策略，包括名称、分类和简介"
    category = "backtest"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "按策略分类过滤，如 '趋势跟踪', '均值回归', '动量'",
                },
            },
            "required": [],
        }

    async def execute(self, category: Optional[str] = None, **kw) -> ToolResult:
        lines = ["可用策略列表：", ""]
        for name, info in STRATEGY_CATALOG.items():
            if category and info["category"] != category:
                continue
            lines.append(f"- **{name}** ({info['display_name']}) — {info['category']}")
            lines.append(f"  {info['description']}")
            lines.append(f"  默认参数: {json.dumps(info['default_params'], ensure_ascii=False)}")
            lines.append("")

        if len(lines) == 2:
            return ToolResult.ok(self.name, text=f"未找到分类为 '{category}' 的策略。")

        return ToolResult.ok(self.name, data={"strategies": list(STRATEGY_CATALOG.keys())}, text="\n".join(lines))


# ==================== GetStrategyInfoTool ====================

class GetStrategyInfoTool(BaseTool):
    """获取指定策略的详细说明。"""

    name = "get_strategy_info"
    description = "获取指定策略的详细说明，包括逻辑、参数、适用场景和风险"
    category = "backtest"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "strategy_name": {
                    "type": "string",
                    "description": f"策略名称或别名，可用: {', '.join(STRATEGY_CATALOG.keys())}",
                },
            },
            "required": ["strategy_name"],
        }

    async def execute(self, strategy_name: str, **kw) -> ToolResult:
        info = STRATEGY_CATALOG.get(strategy_name)
        if not info:
            info = STRATEGY_CATALOG.get(_resolve_strategy(strategy_name) or "")
        if not info:
            return ToolResult.fail(self.name, error=f"未知策略: {strategy_name}。可用: {', '.join(STRATEGY_CATALOG.keys())}")

        lines = [
            f"## {info['display_name']} (`{strategy_name}`)",
            f"**分类**: {info['category']}",
            f"**逻辑**: {info['description']}",
            f"",
            f"**入场**: {info['entry']}",
            f"**出场**: {info['exit']}",
            f"",
            f"**参数**:",
        ]
        for pname, pdesc in info["param_schema"].items():
            default = info["default_params"].get(pname, "N/A")
            lines.append(f"- `{pname}` (默认={default}): {pdesc}")
        lines.append(f"")
        lines.append(f"**适用场景**: {info['suitable']}")
        lines.append(f"**风险**: {info['risks']}")

        return ToolResult.ok(self.name, data=info, text="\n".join(lines))


# ==================== RunBacktestTool ====================

class RunBacktestTool(BaseTool):
    """执行回测。"""

    name = "run_backtest"
    description = "对指定策略和标的执行回测，返回绩效指标摘要"
    category = "backtest"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "strategy_name": {
                    "type": "string",
                    "description": f"策略名称，可用: {', '.join(STRATEGY_CATALOG.keys())}",
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 600519（茅台）、000001（平安银行）",
                },
                "start_date": {
                    "type": "string",
                    "description": "回测开始日期，格式 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "回测结束日期，格式 YYYY-MM-DD",
                },
                "initial_capital": {
                    "type": "number",
                    "description": "初始资金",
                    "default": 100000,
                },
                "params": {
                    "type": "object",
                    "description": "策略参数和执行参数覆盖（可选），如 {\"short_period\": 10, \"long_period\": 30, \"lot_size\": 1, \"max_position\": 0.95, \"slippage\": 0.001}",
                },
            },
            "required": ["strategy_name", "symbol"],
        }

    async def execute(
        self,
        strategy_name: str,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital: float = 100000,
        params: Optional[dict] = None,
        **kw,
    ) -> ToolResult:
        from datetime import datetime, timedelta

        # 解析策略名称
        resolved = _resolve_strategy(strategy_name) or strategy_name
        if resolved not in STRATEGY_CATALOG:
            return ToolResult.fail(
                self.name,
                error=f"未知策略: {strategy_name}。可用: {', '.join(STRATEGY_CATALOG.keys())}",
            )

        # 默认日期：最近一年
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365)
            start_date = start.strftime("%Y-%m-%d")

        # 合并参数
        strategy_params = dict(STRATEGY_CATALOG[resolved]["default_params"])
        if params:
            strategy_params.update(params)

        # 调用回测 API
        try:
            import httpx

            # 尝试调用 agents 服务的回测接口
            agents_url = kw.get("agents_base_url", "http://localhost:8001")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{agents_url}/backtest/run",
                    json={
                        "strategy_name": resolved,
                        "symbol": symbol,
                        "start_date": start_date,
                        "end_date": end_date,
                        "initial_capital": initial_capital,
                        "params": strategy_params,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            if not data.get("success"):
                return ToolResult.fail(self.name, error=data.get("error", "回测失败"))

            report = data.get("report", {})
            metrics = report.get("metrics", {})
            report_id = data.get("report_id", "")
            engine = data.get("engine", "")

            symbol_name = SYMBOL_NAMES.get(symbol, symbol)
            lines = [
                f"## 回测结果: {STRATEGY_CATALOG[resolved]['display_name']} — {symbol_name} ({symbol})",
                f"周期: {start_date} ~ {end_date} | 引擎: {engine}",
                f"",
                f"| 指标 | 值 |",
                f"|------|------|",
                f"| 总收益率 | {metrics.get('total_return', 0):.2f}% |",
                f"| 年化收益 | {metrics.get('annual_return', 0):.2f}% |",
            ]
            if metrics.get("benchmark_return") is not None:
                lines.append(f"| 买入持有基准 | {metrics.get('benchmark_return', 0):.2f}% |")
            if metrics.get("alpha") is not None:
                lines.append(f"| Alpha | {metrics.get('alpha', 0):.2f}% |")
            lines.extend([
                f"| 夏普比率 | {metrics.get('sharpe_ratio', 0):.2f} |",
                f"| 最大回撤 | {metrics.get('max_drawdown', 0):.2f}% |",
                f"| 胜率 | {metrics.get('win_rate', 0):.2f}% |",
                f"| 交易次数 | {metrics.get('total_trades', 0)} |",
                f"| 盈亏比 | {metrics.get('profit_factor', 0):.2f} |",
            ])
            if report_id:
                lines.append(f"")
                lines.append(f"报告 ID: `{report_id}`")

            return ToolResult.ok(
                self.name,
                data={"report": report, "report_id": report_id},
                text="\n".join(lines),
            )

        except Exception as e:
            # 如果 agents 服务不可用，返回友好错误
            logger.warning(f"回测工具调用失败: {e}")
            return ToolResult.fail(
                self.name,
                error=f"回测服务暂时不可用: {e}。请确认 agents 服务正在运行。",
            )


# ==================== OptimizeBacktestTool ====================

class OptimizeBacktestTool(BaseTool):
    """参数网格搜索优化。"""

    name = "optimize_backtest"
    description = "对指定策略执行参数网格搜索优化，返回最优参数和绩效"
    category = "backtest"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "strategy_name": {
                    "type": "string",
                    "description": f"策略名称，可用: {', '.join(STRATEGY_CATALOG.keys())}",
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码",
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD",
                },
                "param_grid": {
                    "type": "object",
                    "description": "参数搜索网格，如 {\"short_period\": [5, 10, 20], \"long_period\": [20, 50, 100]}；可固定或搜索执行参数 lot_size/max_position/slippage",
                },
                "initial_capital": {
                    "type": "number",
                    "description": "初始资金",
                    "default": 100000,
                },
                "fixed_params": {
                    "type": "object",
                    "description": "固定策略/执行参数，不参与搜索，如 {\"lot_size\": 1, \"slippage\": 0}",
                },
            },
            "required": ["strategy_name", "symbol", "param_grid"],
        }

    async def execute(
        self,
        strategy_name: str,
        symbol: str,
        param_grid: dict,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital: float = 100000,
        fixed_params: Optional[dict] = None,
        **kw,
    ) -> ToolResult:
        from datetime import datetime, timedelta

        resolved = _resolve_strategy(strategy_name) or strategy_name
        if resolved not in STRATEGY_CATALOG:
            return ToolResult.fail(
                self.name,
                error=f"未知策略: {strategy_name}。可用: {', '.join(STRATEGY_CATALOG.keys())}",
            )

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365)
            start_date = start.strftime("%Y-%m-%d")

        try:
            import httpx

            agents_url = kw.get("agents_base_url", "http://localhost:8001")
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{agents_url}/backtest/grid_search",
                    json={
                        "strategy_name": resolved,
                        "symbol": symbol,
                        "start_date": start_date,
                        "end_date": end_date,
                        "param_grid": param_grid,
                        "initial_capital": initial_capital,
                        "fixed_params": fixed_params or {},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            if not data.get("success"):
                return ToolResult.fail(self.name, error=data.get("error", "优化失败"))

            best = data.get("best_result", {})
            best_params = data.get("best_params", {})
            total = data.get("total_combinations", 0)
            elapsed = data.get("elapsed_seconds", 0)

            lines = [
                f"## 参数优化结果: {STRATEGY_CATALOG[resolved]['display_name']} — {SYMBOL_NAMES.get(symbol, symbol)}",
                f"搜索组合数: {total} | 耗时: {elapsed:.1f}s",
                f"",
                f"**最优参数**: `{json.dumps(best_params, ensure_ascii=False)}`",
                f"",
                f"| 指标 | 值 |",
                f"|------|------|",
                f"| 总收益率 | {best.get('returns', 0) * 100:.2f}% |",
                f"| 夏普比率 | {best.get('sharpe', 0):.2f} |",
                f"| 最大回撤 | {best.get('max_drawdown', 0) * 100:.2f}% |",
            ]
            # Top 5 参数组合
            all_results = data.get("all_results", [])[:5]
            if all_results:
                lines.append(f"")
                lines.append(f"**Top 5 参数组合**:")
                for i, r in enumerate(all_results, 1):
                    lines.append(f"{i}. {json.dumps(r['params'], ensure_ascii=False)} — 夏普 {r['sharpe']:.2f}, 收益 {r['returns'] * 100:.2f}%")

            return ToolResult.ok(
                self.name,
                data=data,
                text="\n".join(lines),
            )

        except Exception as e:
            logger.warning(f"参数优化失败: {e}")
            return ToolResult.fail(
                self.name,
                error=f"优化服务暂时不可用: {e}",
            )


# ==================== Factory ====================

def get_backtest_tools() -> list[BaseTool]:
    """获取所有回测工具实例。"""
    return [
        ListStrategiesTool(),
        GetStrategyInfoTool(),
        RunBacktestTool(),
        OptimizeBacktestTool(),
    ]
