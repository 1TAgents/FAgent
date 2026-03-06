# Backend 模块

后端服务模块，提供 API 接口和核心业务逻辑。

## 📁 目录结构

```
backend/
├── api/                    # API 服务层
│   ├── main.py             # FastAPI 应用入口
│   ├── chat.py             # 对话接口（SSE + REST）
│   └── middleware.py       # 请求上下文中间件
├── core/                   # 核心组件
│   ├── context.py          # 请求上下文管理（rid/cid）
│   └── logging.py          # 日志配置（loguru）
├── services/               # 业务服务层
│   ├── llm.py              # LLM 服务（OpenAI SDK）
│   ├── session.py          # 会话管理
│   └── storage.py          # 消息存储（SQLite）
├── data/                   # 数据目录（已忽略）
├── logs/                   # 日志目录（已忽略）
├── requirements.txt        # Python 依赖
└── ARCHITECTURE.md         # 架构文档
```

## 🚀 快速开始

### 1. 激活虚拟环境

```bash
# 在项目根目录执行
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
openrounter_p=your_api_key
LLM_MODEL=xiaomi/mimo-v2-flash:free
LOG_LEVEL=INFO
```

### 4. 运行服务

```bash
# 在项目根目录执行
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 API 文档

运行服务后访问：http://localhost:8000/docs

### 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat/completion` | POST | 非流式对话 |
| `/api/chat/stream` | POST | 流式对话（SSE）|
| `/api/chat/session/create` | POST | 创建会话 |
| `/api/chat/conversation/{cid}` | GET | 获取会话记录 |

## 🔧 技术栈

- **FastAPI** - Web 框架
- **SSE** - 流式输出
- **SQLite** - 消息持久化
- **OpenAI SDK** - LLM 客户端
- **Loguru** - 日志系统

## 📋 待实现

- [ ] `agents/` - 多智能体模块（LangGraph）
- [ ] `api/strategy.py` - 策略接口
- [ ] `api/backtest.py` - 回测接口
- [ ] `api/trading.py` - 交易接口

---

详细架构设计参见 [ARCHITECTURE.md](ARCHITECTURE.md)
