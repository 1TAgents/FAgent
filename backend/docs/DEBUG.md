# 调试指南

本文档涵盖 Backend 和 Agents 两个服务的调试配置。

## 1. 环境准备

### 虚拟环境
```bash
# 激活项目虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt
```

### 环境变量
在项目根目录创建 `.env` 文件：
```bash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
openrounter_p=your_api_key
LLM_MODEL=xiaomi/mimo-v2-flash:free
LOG_LEVEL=DEBUG
```

## 2. VSCode/Cursor 调试配置

配置文件位置：`{workspace}/.vscode/launch.json`（workspace 为项目根目录）

### Backend 服务（端口 8000）

```json
{
    "name": "Python: FAgent Backend",
    "type": "debugpy",
    "request": "launch",
    "module": "uvicorn",
    "cwd": "${workspaceFolder}/FAgent",
    "python": "${workspaceFolder}/FAgent/.venv/bin/python",
    "args": [
        "backend.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ],
    "env": {
        "PYTHONPATH": "${workspaceFolder}/FAgent"
    },
    "console": "integratedTerminal",
    "justMyCode": false
}
```

### Agents 服务（端口 8001）

```json
{
    "name": "Python: FAgent Agents",
    "type": "debugpy",
    "request": "launch",
    "module": "uvicorn",
    "cwd": "${workspaceFolder}/FAgent",
    "python": "${workspaceFolder}/FAgent/.venv/bin/python",
    "args": [
        "agents.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8001"
    ],
    "env": {
        "PYTHONPATH": "${workspaceFolder}/FAgent"
    },
    "console": "integratedTerminal",
    "justMyCode": false
}
```

**配置说明：**
- `justMyCode: false` - 允许调试第三方库代码
- `--reload` - 代码修改后自动重载
- Backend 端口：8000，Agents 端口：8001
- 调试时需要同时启动两个服务

## 3. 启动调试

### 方式一：VSCode/Cursor Debug

1. 按 `F5` 或点击左侧 Debug 图标
2. 下拉菜单选择 `Python: FAgent Backend` 或 `Python: FAgent Agents`
3. 点击绿色播放按钮
4. **注意**：需要同时启动两个服务才能完整测试

### 方式二：终端启动

```bash
# 终端 1：Backend 服务
source .venv/bin/activate
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：Agents 服务
source .venv/bin/activate
uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001
```

启动成功日志：
```
# Backend
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

# Agents
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

## 4. 常用断点位置

### Backend 服务

| 文件 | 函数 | 用途 |
|------|------|------|
| `backend/api/chat.py` | `chat_send_stream()` | 流式对话入口 |
| `backend/api/chat.py` | `create_session()` | 会话创建 |
| `backend/services/storage.py` | `add_message()` | 消息落库 |
| `backend/services/session.py` | `get_messages_for_llm()` | 历史消息获取 |

### Agents 服务

| 文件 | 函数 | 用途 |
|------|------|------|
| `agents/api/chat.py` | `agent_chat_stream()` | LLM 流式调用入口 |
| `agents/api/chat.py` | `agent_chat_completion()` | LLM 非流式调用 |
| `agents/services/llm.py` | `chat_completion_stream()` | OpenAI SDK 调用 |
| `agents/core/prompts.py` | - | System Prompt 配置 |

## 5. 测试请求

### 健康检查
```bash
# Backend
curl http://localhost:8000/health

# Agents
curl http://localhost:8001/health
```

### 创建会话
```bash
curl -X POST http://localhost:8000/api/chat/session/create
```

### 发送消息（流式）
```bash
# cid 为上一步创建会话返回的会话 ID
curl -X POST http://localhost:8000/api/chat/send/stream \
  -H "Content-Type: application/json" \
  -d '{"cid": <创建会话返回的cid>, "user_message": "你好", "temperature": 0.7}'
```

### 发送消息（非流式）
```bash
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"cid": <创建会话返回的cid>, "user_message": "你好"}'
```

### 获取会话记录
```bash
curl http://localhost:8000/api/chat/conversation/1
```

### 获取会话列表
```bash
curl http://localhost:8000/api/chat/conversations
```

## 6. 常见问题

### 端口被占用
```bash
# 查找占用进程
lsof -i :8000

# 终止进程
kill -9 <PID>
```

### 虚拟环境未激活
确保 VSCode/Cursor 选择了正确的 Python 解释器：
`FAgent/.venv/bin/python`

### 断点不生效
检查 `justMyCode` 是否设置为 `false`

## 7. API 文档

服务运行后访问：http://localhost:8000/docs

