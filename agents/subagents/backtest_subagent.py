"""
Backtest SubAgent - 回测子智能体

第一阶段目标：
1. 接通内置回测能力
2. 返回确定性结果摘要
3. 暴露 report_id 和 artifact 目录，便于后续比较/审计
"""
import os
import time
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, Optional

from .base import BaseSubAgent
from ..core.context import get_context
from ..core.logging import log_chain_event, log_subagent
from ..mcp.client import MCPClient, MCPError
from ..router.models import TaskContext, TaskType
from ..backtest.strategy_catalog import STRATEGY_CATALOG


STRATEGY_ALIASES: Dict[str, Dict[str, Any]] = STRATEGY_CATALOG


SYMBOL_NAME_MAP = {
    "600519": "贵州茅台",
    "000001": "平安银行",
    "300750": "宁德时代",
}


class BacktestSubAgent(BaseSubAgent):
    """回测相关子智能体。"""

    name = "backtest"

    def __init__(self, mcp_base_url: Optional[str] = None):
        super().__init__()
        resolved_mcp_base_url = mcp_base_url or os.getenv("MCP_BASE_URL", "http://localhost:8002")
        self.mcp = MCPClient(base_url=resolved_mcp_base_url)

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        start_time = time.time()
        log_subagent.start("BacktestSubAgent", context.task_type.value, context)

        try:
            if context.task_type == TaskType.RUN_BACKTEST:
                content = await self._run_backtest(context)
            elif context.task_type == TaskType.OPTIMIZE_BACKTEST:
                content = await self._run_optimization(context)
            else:
                content = self._build_placeholder_response(context)

            yield content
            log_subagent.done("BacktestSubAgent", time.time() - start_time)
        except Exception as e:
            log_subagent.done("BacktestSubAgent", time.time() - start_time, success=False)
            yield f"抱歉，回测执行失败：{e}"

    async def process(self, context: TaskContext) -> str:
        result = []
        async for chunk in self.process_stream(context):
            result.append(chunk)
        return "".join(result)

    async def _run_backtest(self, context: TaskContext) -> str:
        spec = self._normalize_backtest_spec(context)
        log_chain_event(
            layer="subagent",
            event="spec_normalized",
            name="BacktestSubAgent",
            params=spec,
        )

        tool_name = "mcp.backtest_run"
        tool_params = {
            "strategy_name": spec["strategy_id"],
            "symbol": spec["symbol"],
            "start_date": spec["start_date"],
            "end_date": spec["end_date"],
            "initial_capital": spec["initial_capital"],
            "params": spec["params"],
            "metadata": spec["metadata"],
        }
        log_subagent.tool_call(tool_name, tool_params)

        start = time.time()
        try:
            result = await self.mcp.run_backtest(**tool_params)
        except MCPError as e:
            log_subagent.tool_result(tool_name, False, error=str(e), duration=time.time() - start)
            raise

        summary = result.get("summary") or "回测完成"
        log_subagent.tool_result(
            tool_name,
            True,
            data=summary,
            duration=time.time() - start,
        )

        report = result.get("report") or {}
        report_id = result.get("report_id")
        artifacts_dir = result.get("artifacts_dir")
        if report_id and artifacts_dir:
            log_chain_event(
                layer="subagent",
                event="artifact_persisted",
                name="backtest_run",
                params={
                    "report_id": report_id,
                    "artifacts_dir": artifacts_dir,
                },
            )

        return self._format_backtest_response(spec, result, report)

    async def _run_optimization(self, context: TaskContext) -> str:
        spec = self._normalize_backtest_spec(context)
        param_grid = self._resolve_param_grid(spec["strategy_id"], context.params or {}, context.query)
        fixed_params = {
            key: value
            for key, value in spec["params"].items()
            if key not in param_grid
        }

        tool_name = "mcp.backtest_grid_search"
        tool_params = {
            "strategy_name": spec["strategy_id"],
            "symbol": spec["symbol"],
            "start_date": spec["start_date"],
            "end_date": spec["end_date"],
            "param_grid": param_grid,
            "initial_capital": spec["initial_capital"],
            "fixed_params": fixed_params,
        }
        log_subagent.tool_call(tool_name, tool_params)

        start = time.time()
        try:
            result = await self.mcp.grid_search(**tool_params)
        except MCPError as e:
            log_subagent.tool_result(tool_name, False, error=str(e), duration=time.time() - start)
            raise

        log_subagent.tool_result(
            tool_name,
            True,
            data={
                "best_params": result.get("best_params"),
                "total_combinations": result.get("total_combinations"),
            },
            duration=time.time() - start,
        )

        log_chain_event(
            layer="subagent",
            event="optimization_completed",
            name="BacktestSubAgent",
            params={
                "strategy_name": spec["strategy_id"],
                "symbol": spec["symbol"],
                "best_params": result.get("best_params"),
                "total_combinations": result.get("total_combinations"),
            },
        )

        return self._format_optimization_response(spec, param_grid, result)

    def _normalize_backtest_spec(self, context: TaskContext) -> Dict[str, Any]:
        params = context.params or {}
        strategy_id, strategy_display = self._resolve_strategy(params.get("strategy_name"), context.query)
        start_date, end_date = self._resolve_date_range(params)

        default_params = dict(STRATEGY_ALIASES.get(strategy_id, {}).get("default_params", {}))
        merged_params = default_params
        merged_params.update(params.get("params", {}))

        initial_capital = float(params.get("initial_capital") or 100000.0)
        symbol = params.get("symbol") or "600519"

        trace_ctx = get_context()
        metadata = {
            "route_task": context.task_type.value,
            "query": context.query,
            "original_message": context.original_message,
            "cid": context.cid,
            "rid": trace_ctx.get("rid"),
            "mid": trace_ctx.get("mid"),
        }

        return {
            "strategy_id": strategy_id,
            "strategy_display_name": strategy_display,
            "symbol": symbol,
            "symbol_name": SYMBOL_NAME_MAP.get(symbol, symbol),
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "params": merged_params,
            "metadata": metadata,
        }

    def _resolve_strategy(self, strategy_name: Optional[str], query: str) -> tuple[str, str]:
        candidates = []
        if strategy_name:
            candidates.append(strategy_name)
        if query:
            candidates.append(query)

        normalized_candidates = [item.lower() for item in candidates if item]

        for strategy_id, config in STRATEGY_ALIASES.items():
            aliases = [alias.lower() for alias in config["aliases"]]
            if any(any(alias in candidate for alias in aliases) for candidate in normalized_candidates):
                return strategy_id, config["display_name"]

        return "dual_ma", STRATEGY_ALIASES["dual_ma"]["display_name"]

    def _resolve_date_range(self, params: Dict[str, Any]) -> tuple[str, str]:
        end_date = params.get("end_date")
        start_date = params.get("start_date")

        if end_date and start_date:
            return str(start_date), str(end_date)

        end = datetime.now().date()
        start = end - timedelta(days=365)
        return str(start), str(end)

    def _resolve_param_grid(
        self,
        strategy_id: str,
        params: Dict[str, Any],
        query: str,
    ) -> Dict[str, list[Any]]:
        explicit_grid = params.get("param_grid")
        if isinstance(explicit_grid, dict) and explicit_grid:
            return {
                str(key): value if isinstance(value, list) else [value]
                for key, value in explicit_grid.items()
            }

        if strategy_id == "dual_ma":
            inferred = self._infer_dual_ma_grid(query)
            if inferred:
                return inferred
            return {
                "short_period": [3, 5, 8, 10, 15],
                "long_period": [20, 30, 50, 80],
            }

        if strategy_id == "rsi":
            return {
                "period": [6, 14, 21],
                "oversold": [20, 30, 35],
                "overbought": [65, 70, 80],
            }

        if strategy_id == "rsi2":
            return {
                "buy_below": [5, 10],
                "sell_above": [50, 65, 70],
                "trend_ma": [120, 200],
            }

        if strategy_id == "bollinger":
            return {
                "period": [10, 20, 30],
                "std_dev": [1.5, 2.0, 2.5],
            }

        if strategy_id == "macd":
            return {
                "fast": [8, 12],
                "slow": [21, 26, 34],
                "signal": [7, 9],
            }

        if strategy_id == "donchian_breakout":
            return {
                "entry_window": [20, 55],
                "exit_window": [10, 20],
            }

        if strategy_id == "sma_trend":
            return {
                "ma_period": [120, 200, 250],
            }

        return {
            key: [value]
            for key, value in STRATEGY_ALIASES.get(strategy_id, {}).get("default_params", {}).items()
        }

    def _infer_dual_ma_grid(self, query: str) -> Dict[str, list[int]]:
        if not query:
            return {}

        short_grid = None
        long_grid = None

        import re

        patterns = [
            (r"短均线\s*(\d+)\s*(?:到|-|~|至)\s*(\d+)", "short"),
            (r"长均线\s*(\d+)\s*(?:到|-|~|至)\s*(\d+)", "long"),
            (r"短期\s*(\d+)\s*(?:到|-|~|至)\s*(\d+)", "short"),
            (r"长期\s*(\d+)\s*(?:到|-|~|至)\s*(\d+)", "long"),
        ]
        for pattern, target in patterns:
            match = re.search(pattern, query)
            if not match:
                continue
            start = int(match.group(1))
            end = int(match.group(2))
            values = self._build_period_grid(start, end)
            if target == "short":
                short_grid = values
            else:
                long_grid = values

        grid = {}
        if short_grid:
            grid["short_period"] = short_grid
        if long_grid:
            grid["long_period"] = long_grid
        return grid

    def _build_period_grid(self, start: int, end: int, max_points: int = 8) -> list[int]:
        if start > end:
            start, end = end, start
        if start == end:
            return [start]

        span = end - start
        step = max(1, round(span / max(1, max_points - 1)))
        values = list(range(start, end + 1, step))
        if values[-1] != end:
            values.append(end)
        return sorted(set(values))

    def _format_backtest_response(
        self,
        spec: Dict[str, Any],
        result: Dict[str, Any],
        report: Dict[str, Any],
    ) -> str:
        metrics = report.get("metrics", {})
        report_id = result.get("report_id") or "N/A"
        artifacts_dir = result.get("artifacts_dir") or "N/A"
        engine = result.get("engine") or "unknown"

        params_text = ", ".join(f"{key}={value}" for key, value in spec["params"].items()) or "默认参数"

        lines = [
            f"已完成 `{spec['strategy_display_name']}` 在 `{spec['symbol_name']}({spec['symbol']})` 上的内置回测。",
            "",
            f"- 回测 ID：`{report_id}`",
            f"- 引擎：`{engine}`",
            f"- 区间：`{spec['start_date']}` 到 `{spec['end_date']}`",
            f"- 初始资金：`{spec['initial_capital']:.2f}`",
            f"- 参数：`{params_text}`",
            "",
            "**结果**",
            f"- 总收益率：`{metrics.get('total_return', 0):+.2f}%`",
            f"- 年化收益：`{metrics.get('annual_return', 0):+.2f}%`",
            f"- 夏普比率：`{metrics.get('sharpe_ratio', 0):.2f}`",
            f"- 最大回撤：`{metrics.get('max_drawdown', 0):.2f}%`",
            f"- 交易次数：`{metrics.get('total_trades', 0)}`",
            f"- 最终资金：`{metrics.get('final_capital', 0):.2f}`",
            "",
            f"- 产物目录：`{artifacts_dir}`",
        ]

        if result.get("summary"):
            lines.extend(["", "**摘要**", result["summary"]])

        return "\n".join(lines)

    def _format_optimization_response(
        self,
        spec: Dict[str, Any],
        param_grid: Dict[str, list[Any]],
        result: Dict[str, Any],
    ) -> str:
        if not result.get("success", True):
            return f"参数优化失败：{result.get('error', '未知错误')}"

        best_performance = result.get("best_performance") or {}
        top_results = result.get("top_results") or []
        grid_text = ", ".join(f"{key}={value}" for key, value in param_grid.items())
        best_params = result.get("best_params") or {}
        best_params_text = ", ".join(f"{key}={value}" for key, value in best_params.items()) or "N/A"

        lines = [
            f"已完成 `{spec['strategy_display_name']}` 在 `{spec['symbol_name']}({spec['symbol']})` 上的参数优化。",
            "",
            f"- 区间：`{spec['start_date']}` 到 `{spec['end_date']}`",
            f"- 初始资金：`{spec['initial_capital']:.2f}`",
            f"- 参数网格：`{grid_text}`",
            f"- 组合数量：`{result.get('total_combinations', 0)}`",
            f"- 耗时：`{result.get('elapsed_seconds', 0):.2f}s`",
            "",
            "**最优结果**",
            f"- 最优参数：`{best_params_text}`",
            f"- 夏普比率：`{best_performance.get('sharpe_ratio', 0):.2f}`",
            f"- 总收益率：`{best_performance.get('total_returns', 'N/A')}`",
            f"- 最大回撤：`{best_performance.get('max_drawdown', 'N/A')}`",
        ]

        if top_results:
            lines.extend(["", "**Top 参数组合**"])
            for idx, item in enumerate(top_results[:5], start=1):
                params_text = ", ".join(f"{key}={value}" for key, value in item.get("params", {}).items())
                returns = item.get("returns", 0)
                drawdown = item.get("max_drawdown", 0)
                lines.append(
                    f"{idx}. `{params_text}` | Sharpe `{item.get('sharpe', 0):.2f}` | "
                    f"收益 `{returns:+.2%}` | 回撤 `{drawdown:.2%}`"
                )

        lines.extend([
            "",
            "**风险提示**",
            "当前优化基于单段历史区间排序，仍可能过拟合。下一步应补样本内/样本外切分和 walk-forward validation，再用于模拟交易。",
        ])

        return "\n".join(lines)

    def _build_placeholder_response(self, context: TaskContext) -> str:
        return (
            "BacktestSubAgent 已接入主聊天链路。"
            " 当前已支持标准内置回测，回测问答和更复杂的优化/沙盒策略生成功能会继续补齐。"
        )


backtest_subagent = BacktestSubAgent()
