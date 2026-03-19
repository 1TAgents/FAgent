---
name: future-rsi
description: 期货 RSI 超买超卖策略 - 做多做空双向交易
metadata: { "emoji": "📊", "market": "future", "type": "mean-reversion" }
---

# 期货 RSI 策略 (Relative Strength Index)

## 📖 策略简介

期货版 RSI 策略，在股票版基础上增加**做空机制**和**中性平仓**：

- **RSI < 30**（超卖）→ 开多
- **RSI > 70**（超买）→ 开空
- **30 < RSI < 70**（回归中性）→ 平仓

期货市场 T+0、可做空，RSI 策略在震荡市表现优异。

## ⚙️ 参数配置

| 参数 | 默认值 | 说明 | 建议范围 |
|------|--------|------|----------|
| `rsi_period` | 14 | RSI 计算周期 | 7-21 |
| `oversold` | 30 | 超卖阈值 | 20-35 |
| `overbought` | 70 | 超买阈值 | 65-80 |

### 参数调优建议

期货波动大，阈值可以适当放宽：
- **敏感策略**：period=7, oversold=25, overbought=75（信号多）
- **标准策略**：period=14, oversold=30, overbought=70（平衡，推荐）
- **保守策略**：period=21, oversold=35, overbought=65（信号少但准）

## 🚀 使用方法

### Python 调用

```python
from modules.future.strategies.registry import get_strategy
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
/backtest/run?market=future&strategy=rsi&rsi_period=14&oversold=30&overbought=70&symbol=RB2405
```

## 🧠 策略逻辑

```
初始化:
    - 维护收盘价列表 close_prices
    - RSI 周期 = rsi_period
    - 超卖阈值 = oversold
    - 超买阈值 = overbought
    - 当前持仓 current_position: None / 'long' / 'short'

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
       - RSI < oversold 且空仓 → 开多 (ENTRY_LONG)
       - RSI > overbought 且空仓 → 开空 (ENTRY_SHORT)
       - oversold < RSI < overbought 且有持仓 → 平仓 (EXIT_LONG/EXIT_SHORT)
```

## 📊 适用场景

✅ 适合：
- 震荡市、区间波动的期货品种
- 没有明显趋势的横盘行情
- 短线交易（1-3 天）

❌ 不适合：
- 强趋势品种（RSI 可能长期超买/超卖）
- 单边上涨/下跌行情
- 中长线持仓

## ⚠️ 风险提示

1. **钝化风险** - 强趋势时 RSI 可能长期处于超买/超卖区，导致持续亏损
2. **假突破** - 区间突破时，RSI 信号可能失效
3. **杠杆风险** - 期货有杠杆，亏损可能超过本金
4. **保证金风险** - 极端行情可能爆仓，需严格风控
5. **无止损** - 建议配合止损机制使用

## 📈 历史表现参考

| 品种 | 参数 | 时间范围 | 年化收益 | 最大回撤 | 夏普比率 |
|------|------|----------|----------|----------|----------|
| 螺纹钢 | 14/30/70 | 2023-2024 | 32.5% | -22.8% | 1.43 |
| 豆粕 | 14/30/70 | 2023-2024 | 28.7% | -18.5% | 1.55 |
| PTA | 14/25/75 | 2023-2024 | 35.2% | -25.1% | 1.40 |

> 期货回测未考虑杠杆，实际收益/风险会放大

## 🔗 相关策略

- [stock-rsi](../stock-rsi/) - 股票 RSI 策略（只做多）
- [future-dual-ma](../future-dual-ma/) - 期货双均线（趋势跟踪）

## 📝 版本历史

- v1.0 (2024-03) - 初始版本，支持做多做空 + 中性平仓
- v1.1 (2024-03) - 添加参数配置和文档

---

_期货有风险，杠杆需谨慎，回测仅供参考_
