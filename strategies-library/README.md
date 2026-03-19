# FAgent 策略库

> 策略以 OpenClaw Skill 形式存储，累积成可复用的策略知识库

## 📚 可用策略

### 股票策略

| 策略 | 类型 | 描述 | 复杂度 |
|------|------|------|--------|
| [stock-dual-ma](./stock-dual-ma/) | 趋势跟踪 | 双均线交叉策略，金叉买入死叉卖出 | ⭐ |
| [stock-rsi](./stock-rsi/) | 均值回归 | RSI 超买超卖策略 | ⭐ |

### 期货策略

| 策略 | 类型 | 描述 | 复杂度 |
|------|------|------|--------|
| [future-dual-ma](./future-dual-ma/) | 趋势跟踪 | 双均线交叉，支持做多做空双向交易 | ⭐⭐ |
| [future-rsi](./future-rsi/) | 均值回归 | RSI 超买超卖，支持做多做空 | ⭐⭐ |

## 📖 策略文档结构

每个策略目录包含：

```
strategy-name/
├── SKILL.md      # 策略文档（参数、用法、逻辑说明）
└── strategy.py   # 策略实现代码
```

## 🔧 使用方式

### 1. 回测调用

```python
from modules.stock.strategies.registry import get_strategy

# 获取策略
strategy = get_strategy('dual_ma', {
    'short_period': 5,
    'long_period': 20
})

# 或使用期货策略
from modules.future.strategies.registry import get_strategy as get_future_strategy
strategy = get_future_strategy('rsi', {
    'rsi_period': 14,
    'oversold': 30,
    'overbought': 70
})
```

### 2. MCP 工具调用

```
/backtest/run?strategy=stock-dual-ma&symbol=000001&start=2024-01-01&end=2024-12-31
```

## 📊 策略开发流程

1. **探索阶段** - 用 Codex/Claude Code 探索新策略思路
2. **实现阶段** - 编写策略代码，继承 `BaseStrategy`
3. **文档阶段** - 创建 SKILL.md，记录参数和使用方法
4. **回测阶段** - 运行历史回测，记录表现
5. **入库阶段** - 将策略加入策略库，累积知识库

## 🎯 策略分类

### 按市场
- 股票（只做多）
- 期货（做多 + 做空）

### 按逻辑
- 趋势跟踪（均线、MACD、布林带等）
- 均值回归（RSI、KDJ、随机指标等）
- 动量策略（涨跌幅、成交量等）
- 套利策略（跨期、跨品种、期现套利）

### 按频率
- 日内策略
- 短线策略（1-5 天）
- 中线策略（5-20 天）
- 长线策略（20 天以上）

## 📝 添加新策略

1. 在 `strategies-library/` 创建新目录
2. 复制 `strategy.py` 模板
3. 编写 `SKILL.md` 文档
4. 在 `modules/{stock|future}/strategies/registry.py` 注册
5. 运行回测验证
6. Commit 并更新此 README

---

_策略库持续积累中，每次探索都是知识库的成长_
