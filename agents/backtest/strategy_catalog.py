"""Shared backtest strategy catalog."""
from __future__ import annotations

from typing import Any, Dict, Optional


STRATEGY_CATALOG: Dict[str, Dict[str, Any]] = {
    "dual_ma": {
        "display_name": "双均线策略",
        "aliases": ["dual_ma", "双均线", "双均线策略", "均线策略", "moving average", "ma"],
        "category": "趋势跟踪",
        "horizon": "中线",
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
        "horizon": "短线",
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
    "rsi2": {
        "display_name": "RSI2 短线均值回归",
        "aliases": ["rsi2", "rsi 2", "2日rsi", "connors rsi", "connors"],
        "category": "短线均值回归",
        "horizon": "短线",
        "description": "在长期趋势向上时，用 2 日 RSI 极端超跌捕捉短线反弹。",
        "default_params": {"period": 2, "trend_ma": 200, "buy_below": 10, "sell_above": 65},
        "param_schema": {
            "period": "RSI 周期，经典值为 2",
            "trend_ma": "长期趋势过滤均线，经典值为 200",
            "buy_below": "RSI 低于该值买入，常用 5/10",
            "sell_above": "RSI 高于该值卖出，常用 50/65/70",
        },
        "entry": "收盘价高于长期均线且 RSI2 低于买入阈值时买入。",
        "exit": "RSI2 高于卖出阈值时卖出。",
        "suitable": "更适合上升趋势中的短线回撤。",
        "risks": "单边下跌时可能连续抄底失败，必须控制仓位和成本。",
    },
    "bollinger": {
        "display_name": "布林带策略",
        "aliases": ["bollinger", "boll", "布林带", "布林带策略"],
        "category": "波动率/均值回归",
        "horizon": "短线",
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
        "horizon": "中线",
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
    "donchian_breakout": {
        "display_name": "Donchian/Turtle 突破",
        "aliases": ["donchian", "donchian_breakout", "turtle", "海龟", "唐奇安", "突破策略"],
        "category": "突破/趋势跟踪",
        "horizon": "中线",
        "description": "价格突破前 N 日高点买入，跌破前 M 日低点卖出。",
        "default_params": {"entry_window": 20, "exit_window": 10},
        "param_schema": {
            "entry_window": "入场通道周期，Turtle System 1 常用 20",
            "exit_window": "出场通道周期，Turtle System 1 常用 10",
        },
        "entry": "收盘价突破前 entry_window 日最高价时买入。",
        "exit": "收盘价跌破前 exit_window 日最低价时卖出。",
        "suitable": "更适合趋势突破后有延续性的标的。",
        "risks": "震荡市假突破多，胜率可能偏低，收益依赖少数大趋势。",
    },
    "kdj": {
        "display_name": "KDJ 策略",
        "aliases": ["kdj", "kdj策略"],
        "category": "超买超卖/动量",
        "horizon": "短线",
        "description": "用 KDJ 指标的极端位置和交叉识别短线买卖点。",
        "default_params": {"n": 9, "m1": 3, "m2": 3},
        "param_schema": {
            "n": "RSV 计算周期",
            "m1": "K 值平滑周期",
            "m2": "D 值平滑周期",
        },
        "entry": "K 上穿 D 或 K 进入超卖区域时买入。",
        "exit": "K 下穿 D 或 K 进入超买区域时卖出。",
        "suitable": "更适合短线交易和波动较大的标的。",
        "risks": "信号频繁，交易成本高，需要配合止损。",
    },
    "momentum": {
        "display_name": "动量策略",
        "aliases": ["momentum", "动量", "动量策略"],
        "category": "动量/趋势",
        "horizon": "中线",
        "description": "用过去一段时间的涨幅识别趋势延续。",
        "default_params": {"lookback": 20, "threshold": 0.05},
        "param_schema": {
            "lookback": "回看天数",
            "threshold": "动量阈值，超过该值认为有趋势",
        },
        "entry": "过去 lookback 天涨幅超过 threshold 时买入。",
        "exit": "涨幅低于负 threshold 时卖出。",
        "suitable": "更适合有持续动量延续的标的。",
        "risks": "追高风险，涨幅可能已接近尾声。",
    },
    "sma_trend": {
        "display_name": "长期均线趋势过滤",
        "aliases": ["sma_trend", "200日均线", "长期均线", "faber", "taa", "趋势过滤"],
        "category": "长期趋势/风控",
        "horizon": "长线",
        "description": "收盘价高于长期均线时持有，低于长期均线时退出到现金。",
        "default_params": {"ma_period": 200},
        "param_schema": {
            "ma_period": "长期均线周期，日线常用 200，对应约 10 个月",
        },
        "entry": "收盘价高于 ma_period 日均线时买入或继续持有。",
        "exit": "收盘价低于 ma_period 日均线时卖出。",
        "suitable": "更适合长线趋势过滤和降低回撤。",
        "risks": "拐点附近会反复进出，可能错过 V 型反转。",
    },
}


def resolve_strategy(query: Optional[str]) -> Optional[str]:
    """Resolve a strategy id from a user query, alias, or exact strategy id."""
    if not query:
        return None

    q = query.lower()
    for name, info in STRATEGY_CATALOG.items():
        if name in q:
            return name
        for alias in info["aliases"]:
            if alias.lower() in q:
                return name
    return None


def default_params(strategy_id: str) -> Dict[str, Any]:
    """Return a copy of default params for a strategy."""
    return dict(STRATEGY_CATALOG.get(strategy_id, {}).get("default_params", {}))

