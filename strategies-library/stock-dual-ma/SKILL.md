---
name: stock-dual-ma
description: 股票双均线交叉策略 - 金叉买入，死叉卖出
metadata: { "emoji": "📈", "market": "stock", "type": "trend-following" }
---

# 股票双均线策略 (Dual Moving Average)

## 📖 策略简介

经典趋势跟踪策略，通过短期均线和长期均线的交叉信号判断买卖时机：

- **金叉**（短均线上穿长均线）→ 买入
- **死叉**（短均线下穿长均线）→ 卖出

适合趋势明显的股票，震荡市容易产生假信号。

## ⚙️ 参数配置

| 参数 | 默认值 | 说明 | 建议范围 |
|------|--------|------|----------|
| `short_period` | 5 | 短期均线周期 | 3-10 |
| `long_period` | 20 | 长期均线周期 | 15-60 |

### 参数调优建议

- **短线交易**：short=5, long=20（敏感，信号多）
- **中线交易**：short=10, long=30（平衡）
- **长线交易**：short=20, long=60（稳定，信号少）

## 🚀 使用方法

### Python 调用

```python
from modules.stock.strategies.registry import get_strategy
from agents.backtest.models import StrategyConfig

# 创建策略配置
config = StrategyConfig(
    name='dual_ma',
    params={
        'short_period': 5,
        'long_period': 20
    }
)

# 获取策略实例
strategy = get_strategy('dual_ma', config.params)
```

### MCP 工具调用

```
/backtest/run?strategy=dual_ma&short_period=5&long_period=20&symbol=000001
```

### 回测示例

```python
from agents.backtest.engine import BacktestEngine

engine = BacktestEngine(
    strategy=strategy,
    initial_capital=100000,
    commission_rate=0.0003
)

result = engine.run(data, start='2024-01-01', end='2024-12-31')
print(result.summary())
```

## 🧠 策略逻辑

```
初始化:
    - 维护收盘价列表 close_prices
    - 维护日期列表 dates

每个时间点:
    1. 记录当前收盘价
    2. 如果数据不足 long_period 天 → 无信号
    3. 计算短期均线 short_ma = mean(close_prices[-short_period:])
    4. 计算长期均线 long_ma = mean(close_prices[-long_period:])
    5. 计算上一时刻的 short_ma_prev 和 long_ma_prev
    6. 判断交叉:
       - 金叉：short_ma_prev <= long_ma_prev 且 short_ma > long_ma
         → 生成买入信号 (ENTRY_LONG)
       - 死叉：short_ma_prev >= long_ma_prev 且 short_ma < long_ma
         → 生成卖出信号 (EXIT_LONG)
```

## 📊 适用场景

✅ 适合：
- 趋势明显的股票（单边上涨或下跌）
- 流动性好的大盘股
- 中长期持仓

❌ 不适合：
- 震荡市（频繁假信号）
- 小盘股（容易被操纵）
- 超短线交易（滞后性）

## ⚠️ 风险提示

1. **滞后性** - 均线是滞后指标，信号出现时可能已错过最佳点位
2. **震荡亏损** - 横盘震荡时频繁金叉死叉，产生连续亏损
3. **参数敏感** - 不同股票需要不同参数，需回测优化
4. **无止损** - 本策略无止损机制，建议配合风控使用

## 📈 历史表现参考

> 以下为示例数据，实际表现因股票和参数而异

| 股票 | 参数 | 时间范围 | 年化收益 | 最大回撤 | 夏普比率 |
|------|------|----------|----------|----------|----------|
| 贵州茅台 | 5/20 | 2023-2024 | 25.3% | -18.2% | 1.39 |
| 宁德时代 | 10/30 | 2023-2024 | 31.7% | -25.4% | 1.25 |
| 平安银行 | 5/20 | 2023-2024 | 12.8% | -15.1% | 0.85 |

## 🔗 相关策略

- [stock-rsi](../stock-rsi/) - RSI 超买超卖策略（均值回归）
- [future-dual-ma](../future-dual-ma/) - 期货双均线（支持做空）

## 📝 版本历史

- v1.0 (2024-03) - 初始版本，基础双均线逻辑
- v1.1 (2024-03) - 添加参数配置和文档

---

_策略有风险，回测仅供参考，实盘需谨慎_
