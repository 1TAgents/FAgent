# 后端架构文档

本文档描述当前仓库里真正跑起来的三层链路，而不是历史上曾经讨论过的所有方案。

## 一、服务边界

```text
Frontend
  |
  v
Backend
  |
  v
Agents
  |
  +--> OpenRouter-compatible LLM
  +--> 行情数据与缓存
```

### Frontend

- 浏览器中的 UI 层
- 只请求 Backend，不直接请求 Agents
- 通过 Vite 代理把 `/api` 转发到 Backend

### Backend

- 面向前端的统一 API
- 管理会话、消息、用户
- 持久化 SQLite 数据
- 调用 Agents 完成聊天与标题生成
- 负责 SSE 透传和最终消息落库

### Agents

- 纯能力层，不直接维护会话数据库
- 提供 Router、行情工具、标题生成、模型列表
- 封装 OpenRouter 兼容 LLM 调用

## 二、为什么拆成 Backend + Agents

当前拆分有三个直接收益：

1. Backend 保持“业务与数据边界”清晰，前端只对接一套 API。
2. Agents 可以独立切换模型、Prompt、Router 和工具，不影响存储结构。
3. 没有真实 API Key 时，Agents 可以单独进入 Mock 模式，便于整条链路联调。

## 三、核心请求流程

### 1. 流式聊天

```text
Browser
  -> POST /api/chat/send/stream
Backend
  -> 用户消息先落库
  -> 构建 cid / message_id / history
  -> POST /agent/chat/router/stream
Agents
  -> MainRouter 做意图判断
  -> 分发给 ChatSubAgent 或 MarketSubAgent
  -> 流式返回文本片段
Backend
  -> 透传 SSE 给前端
  -> 汇总完整回复并落库
  -> 异步触发标题生成
```

### 2. 会话标题生成

```text
Backend
  -> 在首轮对话结束后取最近消息
  -> POST /agent/summary/generate
Agents
  -> 调用 SummaryService 生成短标题
Backend
  -> 更新 conversations.title
```

### 3. 行情工具调用

```text
用户问题 -> Backend -> Agents Router
                     -> MarketSubAgent
                     -> common/market/service.py
                     -> 数据源 / 缓存
```

## 四、Backend 内部分层

### API 层

- `backend/api/main.py`
- `backend/api/chat.py`
- `backend/api/auth.py`
- `backend/api/middleware.py`

职责：

- 参数校验
- 接口编排
- 调用服务层
- 生成 HTTP / SSE 响应

### Core 层

- 请求上下文
- 日志追踪

职责：

- 生成 / 传递 `rid`
- 记录 `cid` / `message_id`
- 输出结构化日志

### Services 层

- `session.py`
- `storage.py`

职责：

- 会话 CRUD
- 消息存储与历史查询
- 用户表读写

## 五、数据模型

### 会话

- `cid`：整数自增
- `title`
- `metadata`
- `user_id`（可选）
- `created_at` / `updated_at`

### 消息

- `message_id`：整数自增
- `cid`
- `role`
- `content`
- `content_type`
- `metadata`
- `created_at`

### 用户

- `id`
- `username`
- `email`
- `password_hash`
- `created_at`

## 六、鉴权策略

- 未登录：允许匿名创建会话和聊天
- 已登录：Backend 根据 `Authorization` 解析 JWT，按 `user_id` 返回会话列表
- Agents 当前不负责鉴权，只接受 Backend 调用后的业务请求

## 七、模型与配置

模型列表由 Agents 维护，Backend 只做代理：

- Frontend 调 `GET /api/chat/models`
- Backend 转发到 `GET /agent/chat/models`
- 如果 Agents 暂时不可用，Backend 返回保底默认模型

## 八、观测与排障

### 追踪字段

- `rid`：请求级追踪 ID
- `cid`：会话 ID
- `mid`：消息 ID

### 关键日志点

- Backend 收到请求
- 用户消息落库
- 调用 Agents
- SSE 完成
- 助手回复落库
- 标题生成成功 / 失败

## 九、当前不是主线的内容

以下内容在仓库中存在，但不是当前 Web 主链路的核心依赖：

- `src/memory/`：实验中的 Memory 系统
- `modules/`：股票 / 期货策略与回测实验模块
- `agents/data_sync/`：独立数据同步服务
- `frontend/ANDROID_IMPLEMENTATION_GUIDE.md`：未来规划文档

## 十、后续演进方向

1. 将 Memory 能力逐步接入 Backend / Agents，而不是停留在独立模块。
2. 为 Frontend / Backend / Agents 增加更稳定的 CI 冒烟测试。
3. 进一步梳理实验模块和主链路之间的边界。
4. 如果 Router 复杂度继续上升，再评估更重的工作流编排方案。

---

最后更新：2026-04-20
