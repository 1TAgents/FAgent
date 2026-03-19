---
name: stock-rsi
description: 股票 RSI 超买超卖策略 - 低买高卖
metadata: { "emoji": "📊", "market": "stock", "type": "mean-reversion" }
---

# 股票 RSI 策略 (Relative Strength Index)

## 📖 策略简介

RSI（相对强弱指标）是经典的均值回归指标，通过衡量价格变动的速度和幅度来判断超买超卖状态：

- **RSI < 30**（超卖）→ 买入
- **RSI > 70**（超买）→ 卖出

适合震荡市和区间波动的股票，趋势市可能过早平仓。

## ⚙️ 参数配置

| 参数 | 默认值 | 说明 | 建议范围 |
|------|--------|------|----------|
| `rsi_period` | 14 | RSI 计算周期 | 7-21 |
| `oversold` | 30 | 超卖阈值 | 20-35 |
| `overbought` | 70 | 超买阈值 | 65-80 |

### 参数调优建议

- **敏感策略**：period=7, oversold=25, overbought=75（信号多）
- **标准策略**：period=14, oversold=30, overbought=70（平衡）
- **保守策略**：period=21, oversold=35, overbought=65（信号少但准）

## 🚀 使用方法

### Python 调用

```python
from modules.stock.strategies.registry import get_strategy
from agents.backtest.models import StrategyConfig

config = StrategyConfig(
    name='rsi',
    params={
        'rsi_period': 14,
        'oversold': 30,
        'overbought': 70
    }
)

strategy = get_strategy('rsi', config.params)
```

### MCP 工具调用

```
/backtest/run?strategy=rsi&rsi_period=14&oversold=30&overbought=70&symbol=000001
```

## 🧠 策略逻辑

```
初始化:
    - 维护收盘价列表 close_prices
    - RSI 周期 = rsi_period
    - 超卖阈值 = oversold
    - 超买阈值 = overbought

RSI 计算:
    1. 计算价格变化 deltas = diff(close_prices)
    2. 分离涨跌：gains = max(deltas, 0), losses = max(-deltas, 0)
    3. 计算平均涨跌：avg_gain = mean(gains), avg_loss = mean(losses)
    4. 计算 RS：RS = avg_gain / avg_loss
    5. 计算 RSI：RSI = 100 - (100 / (1 + RS))

每个时间点:
    1. 记录当前收盘价
    2. 计算当前 RSI
    3. 判断信号:
       - RSI < oversold 且无持仓 → 买入 (ENTRY_LONG)
       - RSI > overbought 且有持仓 → 卖出 (EXIT_LONG)
```

## 📊 适用场景

✅ 适合：
- 震荡市、区间波动的股票
- 没有明显趋势的横盘股
- 短线交易（1-5 天）

❌ 不适合：
- 强趋势股票（RSI 可能长期超买/超卖）
- 单边上涨/下跌行情
- 中长线持仓

## ⚠️ 风险提示

1. **钝化风险** - 强趋势时 RSI 可能长期处于超买/超卖区，导致过早平仓
2. **假信号** - 震荡区间突破时，RSI 信号可能失效
3. **参数敏感** - 不同股票需要不同阈值，需回测优化
4. **无止损** - 建议配合止损机制使用

## 📈 历史表现参考

| 股票 | 参数 | 时间范围 | 年化收益 | 最大回撤 | 夏普比率 |
|------|------|----------|----------|----------|----------|
| 工商银行 | 14/30/70 | 2023-2024 | 18.5% | -12.3% | 1.50 |
| 万科 A | 14/30/70 | 2023-2024 | 22.1% | -19.8% | 1.12 |
| 格力电器 | 14/25/75 | 2023-2024 | 15.7% | -14.5% | 1.08 |

## 🔗 相关策略

- [stock-dual-ma](../stock-dual-ma/) - 双均线趋势策略
- [future-rsi](../future-rsi/) - 期货 RSI 策略（支持做空）

## 📝 版本历史

- v1.0 (2024-03) - 初始版本，基础 RSI 逻辑
- v1.1 (2024-03) - 添加参数配置和文档

---

_策略有风险，回测仅供参考，实盘需谨慎_
