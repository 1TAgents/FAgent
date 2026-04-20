# 调试指南

本文档覆盖当前最常见的本地调试方式：直接终端启动、Cursor/VS Code 调试、以及链路健康检查。

## 1. 环境准备

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
```

推荐再准备一个 `.env`：

```bash
OPENROUTER_API_KEY=your_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=qwen3.5-plus
AGENTS_BASE_URL=http://localhost:8001
LOG_LEVEL=DEBUG
```

如果暂时没有真实模型 Key，也可以先不填 `OPENROUTER_API_KEY`。Agents 会进入 Mock 模式，适合联调。

## 2. 终端启动

```bash
# 终端 1：Agents
source .venv/bin/activate
uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001

# 终端 2：Backend
source .venv/bin/activate
AGENTS_BASE_URL=http://localhost:8001 \
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

如果端口被占用，可以换端口，但要同步修改：

- Backend 启动端口
- `AGENTS_BASE_URL`
- 前端代理（如你也在调前端）

## 3. Cursor / VS Code 调试配置

如果工作区根目录就是仓库根目录，可直接使用如下 `launch.json` 片段：

### Backend

```json
{
  "name": "Python: FAgent Backend",
  "type": "debugpy",
  "request": "launch",
  "module": "uvicorn",
  "cwd": "${workspaceFolder}",
  "python": "${workspaceFolder}/.venv/bin/python",
  "args": [
    "backend.api.main:app",
    "--reload",
    "--host", "0.0.0.0",
    "--port", "8000"
  ],
  "env": {
    "PYTHONPATH": "${workspaceFolder}",
    "AGENTS_BASE_URL": "http://localhost:8001"
  },
  "console": "integratedTerminal",
  "justMyCode": false
}
```

### Agents

```json
{
  "name": "Python: FAgent Agents",
  "type": "debugpy",
  "request": "launch",
  "module": "uvicorn",
  "cwd": "${workspaceFolder}",
  "python": "${workspaceFolder}/.venv/bin/python",
  "args": [
    "agents.api.main:app",
    "--reload",
    "--host", "0.0.0.0",
    "--port", "8001"
  ],
  "env": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "console": "integratedTerminal",
  "justMyCode": false
}
```

## 4. 推荐断点位置

### Backend

- `backend/api/chat.py::chat_send`
- `backend/api/chat.py::chat_send_stream`
- `backend/api/chat.py::create_session`
- `backend/api/auth.py::register`
- `backend/api/auth.py::login`
- `backend/services/session.py`
- `backend/services/storage.py`

### Agents

- `agents/api/chat.py::router_chat_stream`
- `agents/router/main_router.py::process_stream`
- `agents/services/llm.py::chat_completion`
- `agents/services/summary.py::generate_summary`
- `agents/api/market.py`

## 5. 健康检查

```bash
curl http://localhost:8001/health
curl http://localhost:8000/health
```

预期：

- Agents 返回 `status=healthy`
- Backend 返回 `status=healthy`

## 6. 聊天链路冒烟

```bash
curl -X POST http://localhost:8000/api/chat/session/create \
  -H "Content-Type: application/json" \
  -d '{"title":"debug-smoke"}'
```

假设返回 `cid=1`，再执行：

```bash
curl -N -X POST http://localhost:8000/api/chat/send/stream \
  -H "Content-Type: application/json" \
  -d '{"cid":1,"user_message":"你好，做个链路测试"}'
```

## 7. 常见问题

### 端口占用

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:8001 -sTCP:LISTEN
```

### Backend 启动报认证依赖缺失

确认你安装了最新的 `backend/requirements.txt`。当前必须有：

- `PyJWT`
- `passlib[bcrypt]`
- `email-validator`

### 聊天只返回 Mock 内容

说明 Agents 没拿到有效的 `OPENROUTER_API_KEY`。这不是链路错误，而是模型配置尚未接真实环境。

### 登录能弹窗但后端报错

前端有开发态 mock fallback；如果要验证真实登录，必须确认 Backend 的认证依赖和数据库都初始化成功。

---

最后更新：2026-04-20
