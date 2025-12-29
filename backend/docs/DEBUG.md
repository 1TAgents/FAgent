# Backend 调试指南

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

**配置说明：**
- `justMyCode: false` - 允许调试第三方库代码
- `--reload` - 代码修改后自动重载
- 端口：8000

## 3. 启动调试

1. 按 `F5` 或点击左侧 Debug 图标
2. 下拉菜单选择 `Python: FAgent Backend`
3. 点击绿色播放按钮

启动成功日志：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

## 4. 常用断点位置

| 文件 | 函数 | 用途 |
|------|------|------|
| `api/chat.py` | `stream_chat()` | 流式对话入口 |
| `api/chat.py` | `create_session()` | 会话创建 |
| `services/llm.py` | `stream_chat()` | LLM 调用 |
| `services/storage.py` | `save_message()` | 消息落库 |
| `api/middleware.py` | `dispatch()` | 请求上下文 |

## 5. 测试请求

### 健康检查
```bash
curl http://localhost:8000/health
```

### 创建会话
```bash
curl -X POST http://localhost:8000/api/chat/session/create
```

### 发送消息（流式）
```bash
# cid 为上一步创建会话返回的会话 ID
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"cid": <创建会话返回的cid>, "user_message": "你好", "temperature": 0.7}'
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

