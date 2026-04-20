# Agents 模块

Agents 服务负责三类事情：LLM 调用、Router 路由决策、行情工具与标题生成。它本身不做会话持久化，持久化由 Backend 负责。

## 当前职责

- 处理纯 LLM 对话接口
- 通过 `MainRouter` 在 `chat` 和 `market` 之间路由
- 提供行情接口：报价、K 线、搜索、趋势分析
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
│   ├── chat_subagent.py
│   └── market_agent.py
├── common/market/
│   ├── cache.py
│   ├── client.py
│   ├── dataset_manager.py
│   ├── models.py
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

## 路由模式

`/agent/chat/router/stream` 是当前主链路使用的接口：

1. 从 Backend 传入 `cid`、`message_id`、`user_message`
2. `MainRouter` 读取历史消息并调用 LLM 做意图判断
3. 将请求分发到 `ChatSubAgent` 或 `MarketSubAgent`
4. 直接把子 Agent 的输出流式透传回 Backend

当前主要路由方向：

- `chat`：问候、闲聊、通用问答
- `market`：行情、K 线、趋势、股票搜索

## 主要接口

### 聊天

- `POST /agent/chat/completion`
- `POST /agent/chat/stream`
- `POST /agent/chat/router/stream`
- `POST /agent/chat/router/completion`
- `GET /agent/chat/models`

### 标题生成

- `POST /agent/summary/generate`

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

- 行情能力默认走 `agents/common/market/` 下的服务和缓存
- 独立的数据预热能力请看 [data_sync/README.md](data_sync/README.md)
- 如果需要更细的接口示例，优先查看 `/docs` 自动生成文档
