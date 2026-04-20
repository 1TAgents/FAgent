# Backend 模块

Backend 是前端的唯一业务入口，负责会话和消息持久化、用户认证、SSE/REST 接口，以及对 Agents 服务的调用编排。

## 负责内容

- 会话创建、列出、重命名、删除、清空
- 用户消息入库与助手回复入库
- SSE 流式接口与普通 REST 接口
- 登录 / 注册 / JWT 校验
- 会话标题自动生成触发
- 可用模型列表代理
- 股票 / 期货实验模块代理接口

## 目录

```text
backend/
├── api/
│   ├── main.py
│   ├── chat.py
│   ├── auth.py
│   └── middleware.py
├── core/
├── services/
└── docs/
```

## 依赖安装

在项目根目录执行：

```bash
pip install -r backend/requirements.txt
```

当前 `backend/requirements.txt` 已覆盖：

- FastAPI / Uvicorn
- httpx
- OpenAI SDK
- PyJWT
- passlib + bcrypt
- email-validator

## 关键环境变量

- `AGENTS_BASE_URL`：Agents 服务地址，默认 `http://localhost:8001`
- `DATABASE_PATH`：SQLite 数据库路径
- `JWT_SECRET`：JWT 密钥
- `LOG_LEVEL`：日志级别
- `OPENROUTER_API_KEY`：真实模型调用由 Agents 读取；Backend 本身不直接调模型

## 启动

```bash
AGENTS_BASE_URL=http://localhost:8001 \
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 主要接口

### 健康检查

- `GET /health`

### 认证

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### 对话与会话

- `POST /api/chat/session/create`
- `POST /api/chat/send`
- `POST /api/chat/send/stream`
- `POST /api/chat/send/router/stream`
- `GET /api/chat/conversation/{cid}`
- `GET /api/chat/conversation/{cid}/messages`
- `GET /api/chat/conversation/{cid}/history`
- `PATCH /api/chat/conversation/{cid}`
- `DELETE /api/chat/conversation/{cid}`
- `POST /api/chat/conversation/{cid}/clear`
- `GET /api/chat/conversations`
- `GET /api/chat/models`

### 实验接口

- `POST /api/chat/market/chat`
- `GET /api/chat/market/modules`

## 运行说明

- 聊天链路依赖 Agents 服务；如果 `AGENTS_BASE_URL` 不可达，聊天接口会返回 `502`
- 首轮对话完成后，Backend 会异步调用 Agents 的总结接口生成标题
- 未登录用户也可以创建匿名会话；已登录用户的会话会按 `user_id` 隔离

## 参考文档

- [API 使用文档](docs/API_USAGE.md)
- [架构文档](docs/ARCHITECTURE.md)
- [调试指南](docs/DEBUG.md)
