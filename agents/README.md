# Agents 模块

Agents 服务负责 LLM 调用、Router 路由决策、行情/策略/回测工具编排与标题生成。它本身不做会话持久化，持久化由 Backend 负责。

## 当前职责

- 处理纯 LLM 对话接口
- 通过 `MainRouter` 在 `chat`、`market`、`strategy`、`backtest`、`trade` 之间路由
- 提供行情接口：报价、K 线、搜索、趋势分析
- 提供策略说明能力：策略列表、策略逻辑、参数模板
- 提供回测能力：标准回测、参数优化、回测产物落盘
- 提供本地模拟交易能力：模拟下单、撤单、持仓和账户快照
- 提供会话标题自动生成接口
- 暴露模型列表给前端和 Backend
- 在缺少真实 API Key 时切到 Mock 模式

## 目录

```text
agents/
├── api/
│   ├── main.py
│   ├── chat.py
│   ├── market.py
│   └── summary.py
├── router/
│   ├── main_router.py
│   └── models.py
├── subagents/
│   ├── backtest_subagent.py
│   ├── chat_subagent.py
│   ├── market_agent.py
│   ├── strategy_subagent.py
│   └── trade_subagent.py
├── backtest/
│   ├── api.py
│   ├── run_store.py
│   └── vectorized_strategies.py
├── trading/
│   └── paper.py
├── common/market/
│   ├── cache.py
│   ├── client.py
│   ├── dataset_manager.py
│   ├── models.py
│   ├── offline_provider.py
│   └── service.py
└── services/
    ├── llm.py
    └── summary.py
```

## 启动

```bash
uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001
```

如果你是从非项目根目录启动，请确保 `PYTHONPATH` 包含仓库根目录。

## 关键环境变量

- `OPENROUTER_API_KEY`：真实模型调用必需
- `OPENROUTER_BASE_URL`：默认 `https://openrouter.ai/api/v1`
- `LLM_MODEL`：默认模型
- `RQDATAC_CONF`：可选，用于部分 RQData 数据脚本/能力
- `FAGENT_MARKET_DATA_MODE`：行情数据模式，支持 `live` / `offline` / `hybrid`，默认 `hybrid`
- `FAGENT_MARKET_AS_OF_DATE`：离线模式固定查询日期，例如 `2026-04-24`
- `FAGENT_MARKET_DB_PATH`：本地行情库路径，默认 `data/stock_data.db`
- `QUANTMIND_DATA_DIR`：QuantMInd 原始数据目录，导入脚本默认优先读取 `data/QuantMInd`
- `BACKTEST_QUANTMIND_DATA_DIR`：可选，指向 QuantMInd 根目录或 `feature_snapshots` 目录，用于回测本地 parquet 数据源

## 路由模式

`/agent/chat/router/stream` 是当前主链路使用的接口：

1. 从 Backend 传入 `cid`、`message_id`、`user_message`
2. `MainRouter` 读取历史消息并调用 LLM 做意图判断
3. 将请求分发到对应的 SubAgent
4. 直接把子 Agent 的输出流式透传回 Backend

当前主要路由方向：

- `chat`：问候、闲聊、通用问答
- `market`：行情、K 线、趋势、股票搜索
- `strategy`：策略列表、策略说明、参数模板
- `backtest`：标准回测、参数优化
- `trade`：本地模拟交易入口，支持模拟下单、撤单、持仓查询；不会执行真实交易

## 主要接口

### 聊天

- `POST /agent/chat/completion`
- `POST /agent/chat/stream`
- `POST /agent/chat/router/stream`
- `POST /agent/chat/router/completion`
- `GET /agent/chat/models`

### 标题生成

- `POST /agent/summary/generate`

### 回测

- `POST /backtest/run`
- `POST /backtest/grid_search`
- `GET /backtest/strategies`
- `GET /backtest/report/{report_id}`

### 模拟交易

当前模拟交易只通过 `MainRouter` / `TradeSubAgent` 在对话链路中使用，不暴露独立 HTTP API。
数据默认保存到 `data/paper_trading.db`，可用 `PAPER_TRADING_DB_PATH` 覆盖。
支持示例：

- `模拟买入 600519 100股 价格 1688`
- `模拟卖出 600519 100股 价格 1700`
- `查看持仓`
- `撤销 po_xxx`

### 行情

- `GET /market/quote/{symbol}`
- `GET /market/kline/{symbol}`
- `GET /market/search`
- `GET /market/analysis/{symbol}`
- `GET /market/quick/quote/{symbol}`
- `GET /market/quick/analysis/{symbol}`
- `GET /market/cache/stats`
- `GET /market/cache/keys`
- `DELETE /market/cache/clear`
- `POST /market/cache/cleanup`

## Mock 模式

如果 `OPENROUTER_API_KEY` 未配置或被设置为占位值，`agents/services/llm.py` 会自动进入 Mock 模式：

- `/health` 仍然可用
- 聊天和标题接口仍然可以联调
- 返回内容为固定/模拟文本，不会调用真实模型

这对本地联调有用，但不适合真实结果验证。

## 数据说明

- 行情能力默认走 `agents/common/market/` 下的服务和缓存；`hybrid` 模式会在线数据失败后回退到项目本地 SQLite 行情库
- 本地行情库通过 `scripts/import_quantmind_to_stock_db.py` 从 QuantMInd qlib 日线数据生成，默认路径为 `data/stock_data.db`
- `data/` 下的原始数据和数据库不进入 git；本机当前 QuantMInd 日线数据截止到 `2026-04-24`
- 回测数据加载顺序为本地数据库、QuantMInd parquet 快照、RQData、AKShare；本机默认会自动发现 `~/Learning/quant_repos/data/QuantMInd/feature_snapshots`
- 独立的数据预热能力请看 [data_sync/README.md](data_sync/README.md)
- 如果需要更细的接口示例，优先查看 `/docs` 自动生成文档
