# FAgent 回测策略研究基线

日期：2026-05-28

目标：按短线、中线、长线整理经典量化策略，并筛选出当前单标的日线回测框架可以直接验证的一批策略。本文档不构成投资建议，只作为 FAgent 回测模块的工程实现依据。

## 筛选原则

- 优先选择规则清晰、参数少、能用 OHLCV 日线数据验证的策略。
- 优先选择在量化机构研究、著名交易书籍或主流开源回测项目中反复出现的策略。
- 当前回测器是单标的、只做多、日线级别，所以跨资产配置、横截面多因子、市场中性组合先作为后续方向。
- 所有信号必须避免未来函数：突破类指标使用前一日通道，均线和 RSI 使用当前或历史收盘，不读取未来价格。

## 来源摘要

- AQR 的 Hurst、Ooi、Pedersen 在 [A Century of Evidence on Trend-Following Investing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026) 中研究了跨市场长期趋势跟踪/时间序列动量，结论支持趋势跟踪作为一个长期有效的系统化风格。
- Man AHL 在 [The Need for Speed in Trend-Following Strategies](https://www.man.com/insights/need-for-speed-trend-following) 中强调趋势存在于不同速度和周期，从几天/几周到数月不等，实践中会组合不同速度的趋势模型。
- Larry Connors 的 RSI(2) 短线均值回归规则在交易者社区和技术分析资料中非常常见，StockCharts 的 [RSI(2)](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2) 总结了 200 日均线过滤、2 日 RSI 极端值入场的核心思路。
- Turtle/Donchian 突破来自 Richard Dennis / Turtle Traders 传统。Backtrader 示例文档中的 [Donchian Channel Breakout](https://backtrader.readthedocs.io/en/latest/tutorials/examples/strategies.html) 使用 N 日高低点突破作为趋势交易样例。
- Meb Faber 的 [A Quantitative Approach to Tactical Asset Allocation](https://quantpedia.com/strategies/asset-class-trend-following) 将 10 个月均线过滤用于资产配置，思想可以简化成单标的 200 日均线趋势过滤。
- GitHub/开源生态里，QuantConnect [LEAN](https://github.com/quantconnect/lean) 和 [backtesting.py](https://github.com/kernc/backtesting.py) 都强调可重复回测、参数优化和清晰的策略接口，FAgent 当前向量化回测接口应继续向这些方向靠拢。

## 短线策略

### RSI2 均值回归

- 来源：Larry Connors 的短线交易体系，常见规则是价格高于 200 日均线时，只做多短线超跌。
- 周期：1 到 5 个交易日。
- 核心规则：
  - 计算 2 日 RSI。
  - 价格高于 200 日均线时，RSI 跌到 5 或 10 以下买入。
  - RSI 回到 50、65、70 以上，或价格站上短期均线后退出。
- 优点：规则简单，交易频率较高，适合验证交易成本、滑点、手数等执行假设。
- 风险：单边下跌时会过早抄底；不适合没有风控或仓位控制的实盘。
- FAgent 落地：新增 `rsi2` 向量化策略，默认 `period=2, trend_ma=200, buy_below=10, sell_above=65`。

### 布林带/RSI 短线反转

- 来源：常见短线均值回归模板，GitHub 和 Backtrader/backtesting.py 示例里经常作为入门策略。
- 周期：数日到两周。
- 核心规则：价格跌破布林下轨或 RSI 超卖买入，回到中轨/上轨或 RSI 超买退出。
- FAgent 状态：已有 `bollinger` 和 `rsi`，后续可做组合过滤，但第一批不新增，避免策略过拟合。

## 中线策略

### Donchian / Turtle 突破

- 来源：Turtle Trading，开源回测框架中常见的趋势样例。
- 周期：几周到数月。
- 核心规则：
  - 买入：收盘价突破前 N 日最高价。
  - 卖出：收盘价跌破前 M 日最低价。
  - 常见参数：20/10 或 55/20。
- 优点：趋势强时能抓住大行情，规则明确，不需要预测。
- 风险：震荡市假突破多，胜率可能低，依赖少数大盈利。
- FAgent 落地：新增 `donchian_breakout` 向量化策略，默认 `entry_window=20, exit_window=10`，使用 `shift(1)` 避免未来函数。

### 双均线 / MACD 趋势

- 来源：趋势跟踪最常见形式，Man AHL 文章也提到移动均线交叉类模型在趋势跟踪中长期使用。
- 周期：几周到数月。
- FAgent 状态：已有 `dual_ma` 和 `macd`，后续重点是参数验证和样本外测试。

## 长线策略

### 200 日均线趋势过滤

- 来源：Meb Faber 的 10 个月均线资产配置思想可映射到日线 200 日均线。
- 周期：数月到一年以上。
- 核心规则：
  - 收盘价高于长期均线时持有。
  - 收盘价低于长期均线时退出到现金。
- 优点：非常简单，主要目标是降低长期回撤，而不是提高每笔交易胜率。
- 风险：拐点附近会反复进出；个股长期停牌/退市等数据问题需要单独处理。
- FAgent 落地：新增 `sma_trend` 向量化策略，默认 `ma_period=200`。

### 12-1 月动量 / 横截面因子

- 来源：Jegadeesh/Titman 动量、AQR value/momentum、Research Affiliates value-quality-momentum 等。
- 周期：数月到一年。
- 当前限制：需要多标的横截面排序、组合权重、定期调仓，超过当前单标的回测器能力。
- 后续方向：先把回测器升级到多标的组合，再实现 `cross_sectional_momentum` 和 value-quality-momentum 组合。

## 第一批实现清单

| 分类 | 策略 ID | 默认参数 | 实现理由 |
| --- | --- | --- | --- |
| 短线 | `rsi2` | `period=2, trend_ma=200, buy_below=10, sell_above=65` | 经典短线均值回归，能测试交易频率和成本 |
| 中线 | `donchian_breakout` | `entry_window=20, exit_window=10` | Turtle/Donchian 经典突破，能测试趋势捕捉 |
| 长线 | `sma_trend` | `ma_period=200` | Faber/TAA 思想的单标的版本，能测试回撤控制 |

## 回测模块优化建议

1. 策略目录应统一来源：API、Tool、SubAgent、文档都应能看到同一批策略，避免某些向量化策略无法从 `/backtest/strategies` 查到。
2. 参数应继续分成策略参数和执行参数，执行参数包括 `lot_size`、`max_position`、`slippage`。
3. 趋势/突破策略必须显式使用 `shift(1)`，避免把当天最高/最低价用于当天信号。
4. 网格搜索需要支持固定执行参数，例如 `lot_size=1`，否则高复权价格标的可能无法建仓。
5. 下一阶段应增加样本内/样本外、walk-forward、参数稳定性汇总，降低过拟合风险。

