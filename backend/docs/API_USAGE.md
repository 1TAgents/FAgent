# API 使用文档

本文档描述当前 Backend 对外暴露的主要接口，以及前端/测试脚本最常用的调用方式。

## 基本约定

### 标识

- `cid`：会话 ID，整数自增
- `message_id`：消息 ID，整数自增

### 可选请求头

- `X-Request-ID`：请求追踪 ID，推荐传 8 位 UUID 片段
- `Authorization: Bearer <token>`：登录后访问用户隔离数据时使用

### 主服务地址

- Backend：`http://localhost:8000`
- Agents：`http://localhost:8001`

## 常用接口

### 1. 创建会话

```bash
curl -X POST http://localhost:8000/api/chat/session/create \
  -H "Content-Type: application/json" \
  -d '{"title":"smoke-test"}'
```

响应示例：

```json
{
  "cid": 1,
  "title": "smoke-test",
  "message": "Session created successfully"
}
```

### 2. 非流式聊天

```bash
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "cid": 1,
    "user_message": "帮我简单介绍一下你自己",
    "temperature": 0.7,
    "model": "qwen3.5-plus"
  }'
```

响应示例：

```json
{
  "content": "这是一个回复示例",
  "cid": 1,
  "user_message_id": 1,
  "assistant_message_id": 2
}
```

### 3. 流式聊天（SSE）

```bash
curl -N -X POST http://localhost:8000/api/chat/send/stream \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: abc12345" \
  -d '{
    "cid": 1,
    "user_message": "帮我做一个流式测试",
    "model": "qwen3.5-plus"
  }'
```

流式事件格式：

```text
data: {"content":"第一个片段"}

data: {"content":"第二个片段"}

data: {"done":true,"cid":1,"user_message_id":3,"assistant_message_id":4}

data: [DONE]
```

### 4. 获取会话和消息

```bash
curl http://localhost:8000/api/chat/conversation/1
curl http://localhost:8000/api/chat/conversation/1/messages
curl "http://localhost:8000/api/chat/conversation/1/history?before_message_id=3&limit=10"
curl http://localhost:8000/api/chat/conversations
```

### 5. 更新 / 删除会话

```bash
curl -X PATCH http://localhost:8000/api/chat/conversation/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"新标题"}'

curl -X DELETE http://localhost:8000/api/chat/conversation/1

curl -X POST http://localhost:8000/api/chat/conversation/1/clear
```

### 6. 获取模型列表

```bash
curl http://localhost:8000/api/chat/models
```

响应来自 Agents 服务，典型格式如下：

```json
{
  "models": [
    {
      "id": "qwen3.5-plus",
      "name": "Qwen 3.5 Plus",
      "description": "通用问答主模型"
    }
  ],
  "default": "qwen3.5-plus"
}
```

### 7. 认证接口

注册：

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username":"demo_user",
    "email":"demo@example.com",
    "password":"secret123"
  }'
```

登录：

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"demo@example.com",
    "password":"secret123"
  }'
```

获取当前用户：

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

### 8. 市场模块实验接口

```bash
curl http://localhost:8000/api/chat/market/modules

curl -X POST http://localhost:8000/api/chat/market/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message":"帮我看看贵州茅台行情",
    "mode":"stock"
  }'
```

## 直接调用 Agents

Backend 的聊天主链路依赖 Agents。需要绕过持久化时，可以直接调用：

- `POST /agent/chat/completion`
- `POST /agent/chat/stream`
- `POST /agent/chat/router/stream`
- `GET /agent/chat/models`

这类接口说明请以 `agents/README.md` 和 `http://localhost:8001/docs` 为准。

## 常见问题

### 1. 聊天接口返回 502

通常表示 Backend 调 Agents 失败。先确认：

- Agents 服务是否已启动
- `AGENTS_BASE_URL` 是否正确

### 2. 返回的是 Mock 内容

说明 Agents 没拿到有效的 `OPENROUTER_API_KEY`。链路联调仍然可用，但不会调用真实模型。

### 3. 登录接口启动即报依赖错误

请确认你安装的是最新的 `backend/requirements.txt`，其中已包含：

- `PyJWT`
- `passlib[bcrypt]`
- `email-validator`
- `httpx`

---

最后更新：2026-04-20
