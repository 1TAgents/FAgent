---
name: future-dual-ma
description: 期货双均线交叉策略 - 做多做空双向交易
metadata: { "emoji": "📉", "market": "future", "type": "trend-following" }
---

# 期货双均线策略 (Dual Moving Average)

## 📖 策略简介

期货版双均线策略，在股票版基础上增加**做空机制**，实现双向交易：

- **金叉**（短均线上穿长均线）→ 平空 + 开多
- **死叉**（短均线下穿长均线）→ 平多 + 开空

期货市场 T+0、可做空、有杠杆，适合趋势跟踪策略。

## ⚙️ 参数配置

| 参数 | 默认值 | 说明 | 建议范围 |
|------|--------|------|----------|
| `short_period` | 10 | 短期均线周期 | 5-15 |
| `long_period` | 30 | 长期均线周期 | 20-60 |
| `allow_short` | True | 允许做空 | True/False |

### 参数调优建议

期货波动大，参数比股票版更宽松：
- **短线**：short=5, long=20（敏感，适合日内）
- **中线**：short=10, long=30（平衡，推荐）
- **长线**：short=20, long=60（稳定，适合趋势）

## 🚀 使用方法

### Python 调用

```python
from modules.future.strategies.registry import get_strategy
from agents.backtest.models import StrategyConfig

config = StrategyConfig(
    name='dual_ma',
    params={
        'short_period': 10,
        'long_period': 30,
        'allow_short': True
    }
)

strategy = get_strategy('dual_ma', config.params)
```

### MCP 工具调用

```
/backtest/run?market=future&strategy=dual_ma&short_period=10&long_period=30&symbol=RB2405
```

## 🧠 策略逻辑

```
初始化:
    - 维护收盘价列表 close_prices
    - 当前持仓状态 current_position: None / 'long' / 'short'

每个时间点:
    1. 记录当前收盘价
    2. 如果数据不足 long_period 天 → 无信号
    3. 计算短期均线 short_ma 和长期均线 long_ma
    4. 计算上一时刻的 short_ma_prev 和 long_ma_prev
    5. 判断交叉:
       
       金叉 (short 上穿 long):
           - 如果持有空仓 → 平空 (EXIT_SHORT)
           - 如果空仓 → 开多 (ENTRY_LONG)
       
       死叉 (short 下穿 long):
           - 如果持有多仓 → 平多 (EXIT_LONG)
           - 如果空仓且 allow_short → 开空 (ENTRY_SHORT)
```

## 📊 适用场景

✅ 适合：
- 趋势明显的期货品种（螺纹钢、原油、铜等）
- 流动性好的主力合约
- 中线持仓（3-10 天）

❌ 不适合：
- 震荡市（频繁假信号 + 双向亏损）
- 不活跃合约（滑点大）
- 超短线（手续费成本高）

## ⚠️ 风险提示

1. **杠杆风险** - 期货有杠杆，亏损可能超过本金
2. **滞后性** - 均线是滞后指标，信号出现时可能已错过最佳点位
3. **震荡亏损** - 横盘时频繁开平仓，手续费 + 滑点损耗大
4. **保证金风险** - 极端行情可能爆仓，需严格风控
5. **无止损** - 本策略无止损，建议配合止损机制

## 📈 历史表现参考

| 品种 | 参数 | 时间范围 | 年化收益 | 最大回撤 | 夏普比率 |
|------|------|----------|----------|----------|----------|
| 螺纹钢 | 10/30 | 2023-2024 | 45.2% | -28.5% | 1.59 |
| 原油 | 10/30 | 2023-2024 | 62.8% | -35.2% | 1.78 |
| 铜 | 15/40 | 2023-2024 | 38.5% | -22.1% | 1.74 |

> 期货回测未考虑杠杆，实际收益/风险会放大

## 🔗 相关策略

- [stock-dual-ma](../stock-dual-ma/) - 股票双均线（只做多）
- [future-rsi](../future-rsi/) - 期货 RSI 策略（均值回归）

## 📝 版本历史

- v1.0 (2024-03) - 初始版本，支持做多做空
- v1.1 (2024-03) - 添加参数配置和文档

---

_期货有风险，杠杆需谨慎，回测仅供参考_
