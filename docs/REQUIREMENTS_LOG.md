# FAgent 需求与开发日志

> 说明：记录用户提出的需求、提出时间与内容；如出现前后矛盾将标注并待确认。
> 排序规则：时间倒序，最新需求在最上面。

---

## 2026-04-08 - Memory 系统设计

- 时间：2026-04-08 08:23-11:58
  内容：FAgent Memory 系统完整设计与开发计划
  - [ ] **第一阶段：Message Memory（13 天）**
    - [ ] Phase 1: ID 体系 + 数据模型 + 数据库（2 天）
    - [ ] Phase 2: 原始消息存储 + 检索 API（1 天）
    - [ ] Phase 3: 消息提取器 + 记忆保存（2 天）
    - [ ] Phase 4: 摘要生成 + 双向链接（2 天）
    - [ ] Phase 5: 工具响应处理 + 分级存储（2 天）
    - [ ] Phase 6: 逐渐披露 API（L1-L5）（2 天）
    - [ ] Phase 7: L1/L2/L3 三层记忆集成（2 天）
  - [ ] **第二阶段：LLM 工具与经验进化（11 天）**
    - [ ] Phase 8: Context Builder + LLM 集成（2 天）
    - [ ] Phase 9: Memory Query Tools（LLM 主动调用）（2 天）
    - [ ] Phase 10: Experience Memory（经验记忆）（3 天）
    - [ ] Phase 11: 经验自动提取器（2 天）
    - [ ] Phase 12: 经验检索与应用（2 天）
    - [ ] Phase 13: 测试 + 文档 + 示例（2 天）
  - [ ] **CLI 工具开发（1.5 天）**
    - [ ] CLI 框架（click + rich）
    - [ ] 会话管理命令
    - [ ] 消息操作命令
    - [ ] 记忆查询命令
    - [ ] 测试命令
  - 核心设计原则:
    1. 原始数据永不丢失 - 所有消息完整存储到 SQLite
    2. 摘要是索引不是替代 - 摘要必须能追溯到原始数据
    3. 双向链接 - 摘要↔原始消息可互相导航
    4. 逐渐披露 - L1 概览→L2 列表→L3 详情→L4 工具→L5 展开
    5. 精确寻址 - 通过 cid:mid:sid:rid 精确定位任意数据
    6. LLM 主动调用 Memory 工具 - 动态扩展上下文
    7. 任务完成时自动提取经验 - Agent 自我进化
  - 文档:
    - docs/memory/DESIGN.md - 主设计文档（v1.1）
    - docs/memory/API.md - API 文档
    - docs/memory/EXAMPLES.md - 使用示例
    - docs/memory/EXPERIENCE_DESIGN.md - 经验记忆设计
  - 工具：OpenClaw（PM 设计，后续实施）
  - commit: 1d4fe41

---

## 2026-03-27

- 时间：2026-03-27 16:51
  内容：批量下载 A 股小时 K 线数据到本地
  - [x] 创建下载脚本 `scripts/download_all_stocks_hourly.py`
  - [x] 使用 AKShare 数据源（stock_zh_a_hist_min_em，period='60'）
  - [x] 支持断点续传、失败重试、限流保护
  - [x] 存储到 SQLite 数据库（bar_data_hourly 表）
  - [x] 详细下载日志记录
  - [ ] 执行下载任务（待用户确认运行）
  - 工具：OpenClaw（PM 直接实现）
  - commit: pending

---

## 2026-03-20

- 时间：2026-03-19 06:36
  内容：策略库以 Skill 形式存储，累积策略知识库
  - [x] 创建 strategies-library/ 目录结构
  - [x] 股票策略入库：stock-dual-ma、stock-rsi
  - [x] 期货策略入库：future-dual-ma、future-rsi
  - [x] 每个策略包含 SKILL.md 文档（参数、用法、逻辑、风险）和 strategy.py 实现
  - [x] 创建 README.md 策略索引和使用指南
  - [x] 支持策略累积和复用，避免每次重新探索
  - 工具：OpenClaw（PM 直接实现）
  - commit: eaace33

- 时间：2026-03-19 06:47-06:56
  内容：股票和期货模块独立开发，前端路由切换
  - [x] 模块化架构：modules/stock/ 和 modules/future/ 独立目录
  - [x] 每个模块包含：api.py、data/、strategies/、backtest/
  - [x] 服务层：strategy_backtest_service、unified_query_interface
  - [x] 工具层：enhanced_logging 日志增强
  - [x] 路由层：router/main_router.py 支持模块切换
  - [x] 前端集成：MarketSwitcher 组件、useMarketMode hook
  - [x] 数据下载脚本：股票全量、期货 5 分钟、补充数据
  - [x] 测试框架：自动化测试运行器、场景测试
  - 工具：OpenClaw（PM 直接实现）
  - commit: aef32bf

---

## 2026-03-18

- 时间：2026-03-18 07:12
  内容：实现回测验证器模块（支持不同策略类型的验证方式）
  - [x] 验证器基类设计（BacktestValidator）
  - [x] HoldoutValidator（固定分割，适合长期策略）
  - [x] WalkForwardValidator（滚动窗口，适合中短期策略）
  - [x] ExpandingWindowValidator（扩展窗口，适合参数稳定策略）
  - [x] 过拟合检测机制（参数敏感度、样本外一致性检查）
  - [x] 与现有 engine.py 集成（ValidatorEngine）
  - [x] API 端点（/backtest/validate, /backtest/validators）
  - [x] 单元测试（tests/test_validators.py）
  - [x] 使用示例（examples/validator_example.py）
  - [x] 设计文档（docs/VALIDATOR_DESIGN.md）
  - 工具：OpenClaw（PM 设计 + 直接实现）
  - commit: 04bcdb4

- 时间：2026-03-18 19:30
  内容：多股票组合策略测试（选股 + 择时，最多 5 只）
  - [x] 创建组合策略回测引擎（支持多股票、定期调仓）
  - [x] 实现选股策略（动量、RSI 超卖、RSI 趋势）
  - [x] 实现仓位管理（等权重、最多 5 只）
  - [x] 实现调仓逻辑（定期卖出 + 重新选股）
  - [x] 测试 5 种策略组合
  - [x] 找到 3 个年化 20%+ 策略
  - [x] 最佳策略：动量选股 (20 日，20 天调仓) - 年化 68.4%
  - [x] 生成测试报告（docs/PORTFOLIO_STRATEGY_TEST_REPORT.md）
  - 工具：OpenClaw（直接实现）
  - commit: pending

---

## 2026-03-17

- 时间：2026-03-17 08:50
  内容：实现回测引擎和更多行情 API
  - [x] 新增 `stock_bill` 工具 - 龙虎榜数据
  - [x] 新增 `stock_limit_up` 工具 - 涨跌停统计
  - [x] 新增 `stock_block_trade` 工具 - 大宗交易
  - [x] 新增 `stock_margin` 工具 - 融资融券
  - [x] 创建回测模块 `agents/backtest/`
  - [x] 实现回测引擎 `BacktestEngine`（数据加载→信号生成→订单执行→绩效计算）
  - [x] 实现 3 个示例策略：双均线/RSI/布林带
  - [x] 新增 `backtest_run` 工具 - 执行策略回测
  - [x] 新增 `backtest_strategies` 工具 - 列出可用策略
  - [x] 绩效指标：总收益/年化/夏普比率/最大回撤/胜率/盈亏比等
  - [x] 更新文档：`docs/MCP.md` 添加回测工具说明
  - 工具：OpenClaw（直接编辑代码）
  - commit: pending

- 时间：2026-03-17 08:35
  内容：新增行业数据和主流指数行情支持
  - [x] 新增 `index_quote` 工具 - 主流指数实时行情（沪深 300/中证 500/上证 50/科创 50/创业板指等）
  - [x] 新增 `index_kline` 工具 - 指数 K 线数据
  - [x] 新增 `industry_quote` 工具 - 行业板块行情（单个行业或全行业涨幅榜）
  - [x] 新增 `industry_kline` 工具 - 行业 K 线数据
  - [x] 新增 `industry_detail` 工具 - 行业成分股列表
  - [x] 新增数据模型：`IndexQuote`, `IndustryQuote`, `IndustryDetail`
  - [x] 新增缓存方法：指数/行业相关缓存支持
  - [x] 更新文档：`docs/MCP.md` 添加新工具使用说明
  - 工具：OpenClaw（直接编辑代码）
  - commit: f5b20c6

---

## 2026-03-15

- 时间：2026-03-15 18:35
  内容：实现 MCP（Model Context Protocol）金融服务
  - [x] Phase 1: 基础 MCP Server（6 个工具：stock_quote/stock_kline/stock_search/stock_fund_flow/stock_rank/stock_financial）
  - [x] Phase 2: Agent 集成（MarketSubAgent 改造为 MCP Client 调用）
  - [x] Phase 3: Redis 缓存层（行情 60s/K 线 5min/搜索 1h）
  - [x] Phase 4: 新增工具（资金流向/股票排行/财务指标）
  - [x] Phase 5: 限流鉴权（60 次/分钟，API Key 可选）
  - [x] 文档：docs/MCP.md 完整开发文档
  - 工具：OpenClaw subagent（5 个 Phase 全部自动化实现）
  - commit: 79f56eb

- 时间：2026-03-15 11:19
  内容：实现三级链路追踪日志规范（cid/mid/rid）
  - [x] Backend 层：`context.py` 添加 mid 字段，`logging.py` 更新前缀格式，`chat.py` 注入 mid 并记录关联日志
  - [x] Agents 层：`context.py`/`logging.py` 支持 mid，中间件解析 cid/mid，Router 注入 mid
  - [x] 日志前缀统一为 `[cid=X mid=Y rid=Z]`，子任务标签 `[market]`/`[llm]`/`[router]`
  - [x] 错误日志规范化：`[MODULE] 操作失败 | 输入={xxx} | 原因={error}`
  - [x] 测试验证：Backend 日志输出符合规范，三级 ID 正确传递
  - 工具：OpenClaw subagent（直接执行代码修改）
  - commit: b343116

---

## 2026-03-07

- 时间：2026-03-07 00:40
  内容：【构想】系统自我进化能力（Admin Debug & Auto-Evolution）。
  - 层次一（可观测）：超级管理员前端面板，按 cid 查看完整链路日志（路由决策、LLM 调用、工具调用、报错）
  - 层次二（可诊断）：管理员召唤特殊对话窗口，将 cid 上下文（消息 + 日志 + 报错）喂给 LLM 做根因分析和优化建议
  - 层次三（可进化）：系统自动收集异常/低质量回复 → 生成修复方案 → 自动更新 Prompt 或代码 → 验证效果（需安全审批机制）
  - 状态：构想讨论中，待确定落地优先级

- 时间：2026-03-07 00:35
  内容：LLM 提供商从 OpenRouter 切换到 Qwen Code Plan（DashScope）。
  - 已更新 `.env`、`agents/services/llm.py`、`backend/api/chat.py` 模型配置
  - 7 个模型全部验证通过：qwen3-coder-plus、qwen3.5-plus、qwen3-coder-next、qwen3-max-2026-01-23、glm-5、kimi-k2.5、MiniMax-M2.5
  - 端到端链路验证通过（MiniMax-M2.5 + 茅台行情查询）

- 时间：2026-03-07 00:33
  内容：前端 & Agent 体验问题，两项待修复。
  - [ ] **URL 路由缺少 cid**：浏览器地址栏始终显示 `localhost:5173`，切换会话时 URL 不变，无法通过 URL 直接定位到某个会话。需要实现前端路由（如 `/chat/:cid`）。
  - [ ] **Agent 不知道当前日期**：用户问"今天是哪一天"，Agent 回答"2025年12月17日，星期三"，与实际日期（2026年3月7日，星期五）严重不符。需要在 System Prompt 或上下文中注入当前日期。

---

## 2026-03-06

- 时间：2026-03-06 23:30
  内容：梳理项目待办事项，明确当前开发优先级。
  - Phase 4 多平台扩展（Android/iOS/桌面端）先不做
  - 美股、港股搜索支持先不考虑
  - 聚焦 A 股能力在网页端的完整展现，把预设逻辑和整个框架跑通
  - 具体完成：
    - [x] 前端侧边栏编辑/删除交互（代码审查确认已实现）
    - [x] 前端动态模型列表（从 `/api/chat/models` 获取，替代硬编码，含模型名称和描述展示）
    - [x] Agents 层 user_id 上下文注入（Backend 透传 → Agents 接收 → 日志追踪 `uid=xxx`）
    - [x] Backend 会话总结触发策略优化（按总字符数 1500 截取 + 新增 `POST /conversation/{cid}/regenerate-title` 手动重生成接口）
    - [x] 重构 AKShare 行情数据源：从东财 `stock_zh_a_spot_em`（curl_cffi，受系统代理影响）切换到新浪 `stock_zh_a_daily` + `stock_info_a_code_name`
    - [x] 端到端验证：A 股搜索（茅台→600519）、行情查询（1402 元，+0.21%）、K 线数据均通过
    - [x] 环境搭建：Python venv + 前后端依赖安装 + tsconfig 修复
    - [ ] 端到端 LLM 路由链路验证（需配置 API Key 后测试）

---

> 以下为基于 Git 历史记录整理的早期开发日志。

## 2025-12-20 — 项目立项

- 创建仓库，初始化项目
- 编写项目 README 文档，确立产品方向：基于对话的智能股票交易助手

## 2025-12-22 — 文档与规范

- 添加应用开发指南文档
- 优化文档排版风格

## 2025-12-23 — 后端服务初始化

- 初始化后端服务（FastAPI）
- 搭建测试框架

## 2025-12-24 — 消息系统与文档

- 重构消息系统，实现自增 ID 管理
- 更新文档，移除硬编码路径
- 添加前端开发文档

## 2025-12-29 — 后端重构

- 重构 System Prompt 管理：从存储层迁移到配置层，不再落库
- 重组后端文档结构，新增调试指南（DEBUG.md）

## 2025-12-31 — 三层架构拆分

- 重大重构：将单体应用拆分为三层架构
  - **Frontend**（前端展示层）
  - **Backend**（业务存储层）
  - **Agents**（智能体服务层）
- 后端端口 8000，Agents 端口 8001，前后端通过 HTTP/SSE 通信

## 2026-01-06 — 行情服务与子 Agent

- 新增 Market Service（行情数据服务），接入 AKShare
- 实现 SubAgent 基类框架
- 完善测试框架

## 2026-01-07 — 前端初始化 + 对话体验

- 初始化 React 前端项目，接入后端 API
- 使用 shadcn 组件库重构 UI
- 添加 Markdown 渲染支持
- 实现会话历史记录与侧边栏导航
- 增强 Agent Mock 模式响应

## 2026-01-08 — 功能规范文档

- 标准化功能需求规格文档（FEATURE_SPECS.md）
- 添加侧边栏分组逻辑设计

## 2026-01-09 — 会话标题自动生成

- 实现自动会话标题生成功能
- 首轮对话后由 LLM 异步生成会话标题

## 2026-01-10 ~ 01-11 — Multi-Agent 路由架构

- 编写多智能体路由架构设计文档
- **实现 Router-based Multi-Agent 架构（Phase 1）**
  - MainRouter：LLM 驱动意图识别 + 智能路由
  - MarketSubAgent：行情查询、K 线、趋势分析
  - ChatSubAgent：通用对话兜底
- 优化会话摘要 Prompt 与逻辑
- 实现智能侧边栏交互与全链路请求追踪（rid/cid）
- 更新 .gitignore 和项目布局

## 2026-01-13 — 用户认证系统

- 实现前端用户认证 UI（注册、登录）
- 实现动态模型切换前端交互
- 添加邮箱格式校验
- 修复 backend/api/chat.py 误改问题

## 2026-01-14 — 认证与模型切换后端

- 后端实现动态模型切换 API
- 后端实现用户认证（注册、登录、JWT、数据隔离）
- **Phase 1 & Phase 2 基本完成**

---

## 功能里程碑总结

| 阶段 | 时间 | 核心产出 |
|------|------|---------|
| 立项 | 2025-12-20 | 仓库创建、产品方向确立 |
| 后端基础 | 2025-12-23 ~ 12-29 | FastAPI 服务、消息系统、System Prompt 管理 |
| 架构升级 | 2025-12-31 | 三层架构拆分（Frontend → Backend → Agents） |
| 前端上线 | 2026-01-06 ~ 01-08 | React 前端、行情服务、会话管理、UI 组件 |
| 智能体系统 | 2026-01-09 ~ 01-11 | Multi-Agent 路由架构、自动标题、请求追踪 |
| 用户体系 | 2026-01-13 ~ 01-14 | 认证系统、动态模型切换、数据隔离 |


## 技术决策记录

| 决策 | 选择 | 时间 | 原因 |
|------|------|------|------|
| 整体架构 | 三层分离 | 2025-12-31 | 解耦前端/业务/AI，独立部署和扩展 |
| Agent 架构 | 自研 Router + SubAgent | 2026-01-10 | 比 LangChain 更轻量可控 |
| 前端框架 | React + shadcn | 2026-01-07 | 现代化组件 + 快速迭代 |
| 行情数据 | AKShare | 2026-01-06 | 开源免费，覆盖 A 股全量 |
| 通信方式 | SSE 流式 | 2025-12-23 | 实时展示 AI 输出，体验好 |
| 存储 | SQLite | 2025-12-23 | MVP 阶段轻量，无需运维 |
| LLM 接入 | OpenRouter | 2026-01-14 | 多模型切换，灵活控成本 |
sk-sp-fake1234567890abcdef
