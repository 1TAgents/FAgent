"""
Strategy SubAgent - 策略子智能体

职责：
1. 列出当前可用策略
2. 解释策略逻辑和参数模板
3. 将策略类问题收口成可回测的结构化建议
"""
import os
import time
from typing import Any, AsyncIterator, Dict, Optional

from .base import BaseSubAgent
from ..core.logging import log_subagent
from ..mcp.client import MCPClient, MCPError
from ..router.models import TaskContext, TaskType


STRATEGY_CATALOG: Dict[str, Dict[str, Any]] = {
    "dual_ma": {
        "display_name": "双均线策略",
        "aliases": ["dual_ma", "双均线", "均线策略", "moving average", "ma"],
        "category": "趋势跟踪",
        "description": "用短期均线上穿/下穿长期均线生成买卖信号。",
        "default_params": {"short_period": 5, "long_period": 20},
        "param_schema": {
            "short_period": "短期均线周期，常用 3/5/10/15",
            "long_period": "长期均线周期，常用 20/30/50/80",
        },
        "entry": "短期均线上穿长期均线时买入。",
        "exit": "短期均线下穿长期均线时卖出。",
        "suitable": "更适合趋势清晰、波动连续的标的。",
        "risks": "震荡市容易频繁假突破，参数优化必须做样本外验证。",
    },
    "rsi": {
        "display_name": "RSI 策略",
        "aliases": ["rsi", "rsi策略", "相对强弱指标"],
        "category": "均值回归",
        "description": "用 RSI 超买超卖区间生成反转交易信号。",
        "default_params": {"period": 14, "oversold": 30, "overbought": 70},
        "param_schema": {
            "period": "RSI 计算周期，常用 6/14/21",
            "oversold": "超卖阈值，低于该值考虑买入",
            "overbought": "超买阈值，高于该值考虑卖出",
        },
        "entry": "RSI 低于超卖阈值时买入。",
        "exit": "RSI 高于超买阈值时卖出。",
        "suitable": "更适合震荡或均值回归特征明显的标的。",
        "risks": "单边趋势中可能持续超买或超卖，容易过早反向交易。",
    },
    "bollinger": {
        "display_name": "布林带策略",
        "aliases": ["bollinger", "boll", "布林带", "布林带策略"],
        "category": "波动率/均值回归",
        "description": "用价格相对布林带上下轨的位置生成交易信号。",
        "default_params": {"period": 20, "std_dev": 2.0},
        "param_schema": {
            "period": "均线和标准差计算周期，常用 10/20/30",
            "std_dev": "标准差倍数，常用 1.5/2.0/2.5",
        },
        "entry": "价格跌破下轨时买入。",
        "exit": "价格突破上轨时卖出。",
        "suitable": "更适合有均值回归特征、波动区间较稳定的标的。",
        "risks": "趋势行情中价格可能长期贴轨运行，逆势信号风险较高。",
    },
    "macd": {
        "display_name": "MACD 策略",
        "aliases": ["macd", "macd策略"],
        "category": "趋势跟踪",
        "description": "用 MACD 线和信号线交叉识别趋势动量变化。",
        "default_params": {"fast": 12, "slow": 26, "signal": 9},
        "param_schema": {
            "fast": "快线 EMA 周期",
            "slow": "慢线 EMA 周期",
            "signal": "信号线 EMA 周期",
        },
        "entry": "MACD 线上穿信号线时买入。",
        "exit": "MACD 线下穿信号线时卖出。",
        "suitable": "更适合中短期趋势和动量延续场景。",
        "risks": "滞后性较强，快速反转时可能回撤较大。",
    },
    "kdj": {
        "display_name": "KDJ 策略",
        "aliases": ["kdj", "kdj策略", "随机指标"],
        "category": "震荡指标",
        "description": "用 K/D/J 的交叉和超买超卖区域生成交易信号。",
        "default_params": {"n": 9, "m1": 3, "m2": 3},
        "param_schema": {
            "n": "RSV 计算周期",
            "m1": "K 值平滑周期",
            "m2": "D 值平滑周期",
        },
        "entry": "K 上穿 D 或进入超卖区域时买入。",
        "exit": "K 下穿 D 或进入超买区域时卖出。",
        "suitable": "更适合震荡市和短周期择时。",
        "risks": "信号敏感，噪音较多，需要控制交易成本和频率。",
    },
    "momentum": {
        "display_name": "动量策略",
        "aliases": ["momentum", "动量", "动量策略"],
        "category": "动量/趋势",
        "description": "用过去一段时间的收益率判断趋势延续。",
        "default_params": {"lookback": 20, "threshold": 0.05},
        "param_schema": {
            "lookback": "回看周期，常用 10/20/60",
            "threshold": "动量阈值，例如 0.05 表示 5%",
        },
        "entry": "回看收益率高于正阈值时买入。",
        "exit": "回看收益率低于负阈值时卖出。",
        "suitable": "更适合强趋势、强相对表现延续的标的。",
        "risks": "趋势反转时容易回吐收益，需配合止损或仓位控制。",
    },
}


class StrategySubAgent(BaseSubAgent):
    """策略相关子智能体。"""

    name = "strategy"

    def __init__(self, mcp_base_url: Optional[str] = None):
        super().__init__()
        resolved_mcp_base_url = mcp_base_url or os.getenv("MCP_BASE_URL", "http://localhost:8002")
        self.mcp = MCPClient(base_url=resolved_mcp_base_url)

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        start_time = time.time()
        log_subagent.start("StrategySubAgent", context.task_type.value, context)

        try:
            if context.task_type == TaskType.LIST_STRATEGIES:
                content = await self._list_strategies(context)
            elif context.task_type == TaskType.STRATEGY_QA:
                content = await self._explain_strategy(context)
            else:
                content = self._build_general_response(context)

            yield content
            log_subagent.done("StrategySubAgent", time.time() - start_time)
        except Exception as e:
            log_subagent.done("StrategySubAgent", time.time() - start_time, success=False)
            yield f"抱歉，策略任务处理失败：{e}"

    async def process(self, context: TaskContext) -> str:
        result = []
        async for chunk in self.process_stream(context):
            result.append(chunk)
        return "".join(result)

    async def _list_strategies(self, context: TaskContext) -> str:
        strategies = await self._load_strategy_catalog()
        category = (context.params or {}).get("category")

        rows = []
        for strategy_id, item in strategies.items():
            if category and category not in item.get("category", "") and category not in item.get("display_name", ""):
                continue
            rows.append((strategy_id, item))

        if not rows:
            return f"当前没有匹配 `{category}` 的策略。可以先查看全部策略，或指定趋势、均值回归、波动率等类别。"

        lines = [
            "当前可用策略如下：",
            "",
        ]
        for strategy_id, item in rows:
            params_text = ", ".join(f"{key}={value}" for key, value in item.get("default_params", {}).items())
            lines.extend([
                f"- `{strategy_id}`：{item['display_name']}（{item.get('category', '未分类')}）",
                f"  - 逻辑：{item.get('description', '')}",
                f"  - 默认参数：`{params_text}`",
            ])

        lines.extend([
            "",
            "可以继续说：",
            "- `解释一下 dual_ma`",
            "- `用 5/20 双均线回测贵州茅台`",
            "- `帮我优化双均线参数`",
        ])
        return "\n".join(lines)

    async def _explain_strategy(self, context: TaskContext) -> str:
        strategies = await self._load_strategy_catalog()
        strategy_id = self._resolve_strategy_id((context.params or {}).get("strategy_name"), context.query, strategies)

        if not strategy_id:
            return (
                "我还不能确定你想了解哪一个策略。当前可用策略包括："
                + "、".join(f"`{key}`" for key in strategies.keys())
                + "。"
            )

        item = strategies[strategy_id]
        params_text = "\n".join(
            f"- `{key}`：{desc}；默认 `{item.get('default_params', {}).get(key)}`"
            for key, desc in item.get("param_schema", {}).items()
        )
        default_params = ", ".join(f"{key}={value}" for key, value in item.get("default_params", {}).items())

        return "\n".join([
            f"**{item['display_name']} (`{strategy_id}`)**",
            "",
            f"- 类别：{item.get('category', '未分类')}",
            f"- 核心逻辑：{item.get('description', '')}",
            f"- 入场：{item.get('entry', '')}",
            f"- 出场：{item.get('exit', '')}",
            f"- 适用场景：{item.get('suitable', '')}",
            f"- 主要风险：{item.get('risks', '')}",
            "",
            "**参数模板**",
            params_text,
            "",
            "**可回测配置**",
            f"- strategy_name：`{strategy_id}`",
            f"- 默认 params：`{default_params}`",
            "",
            "下一步可以直接说："
            f"`用 {item['display_name']} 回测 600519 过去一年`，"
            "或者指定参数后再回测/优化。",
        ])

    async def _load_strategy_catalog(self) -> Dict[str, Dict[str, Any]]:
        catalog = {key: dict(value) for key, value in STRATEGY_CATALOG.items()}

        try:
            result = await self.mcp.list_backtest_strategies()
        except MCPError:
            return catalog
        except Exception:
            return catalog

        for strategy_id, item in (result.get("strategies") or {}).items():
            if strategy_id not in catalog:
                catalog[strategy_id] = {
                    "display_name": item.get("name", strategy_id),
                    "aliases": [strategy_id, item.get("name", "")],
                    "category": "回测策略",
                    "description": item.get("description", ""),
                    "default_params": {},
                    "param_schema": {},
                    "entry": "请查看策略源码或回测结果。",
                    "exit": "请查看策略源码或回测结果。",
                    "suitable": "需要通过回测验证适用场景。",
                    "risks": "需要通过样本外验证控制过拟合。",
                }
            elif item.get("description"):
                catalog[strategy_id]["description"] = item["description"]

        return catalog

    def _resolve_strategy_id(
        self,
        strategy_name: Optional[str],
        query: str,
        strategies: Dict[str, Dict[str, Any]],
    ) -> Optional[str]:
        candidates = [strategy_name or "", query or ""]
        normalized_candidates = [item.lower() for item in candidates if item]

        for strategy_id, item in strategies.items():
            aliases = [strategy_id, item.get("display_name", ""), *item.get("aliases", [])]
            normalized_aliases = [alias.lower() for alias in aliases if alias]
            if any(any(alias in candidate for alias in normalized_aliases) for candidate in normalized_candidates):
                return strategy_id

        return None

    def _build_general_response(self, context: TaskContext) -> str:
        return (
            "StrategySubAgent 当前支持策略列表和策略说明。"
            "可以问 `有哪些策略`、`解释一下双均线策略`，"
            "或继续让 BacktestSubAgent 执行回测和参数优化。"
        )


strategy_subagent = StrategySubAgent()
