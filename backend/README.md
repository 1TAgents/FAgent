# Backend 模块

后端服务模块，提供 API 接口和多智能体系统。

## 📁 目录结构

```
backend/
├── api/                # API 服务
│   ├── chat.py        # 对话接口（SSE + REST）
│   ├── strategy.py    # 策略接口
│   ├── backtest.py    # 回测接口
│   └── trading.py     # 交易接口
├── agents/            # 智能体模块
│   ├── supervisor.py  # 主管智能体
│   ├── chat_agent.py  # 对话智能体
│   ├── strategy_agent.py  # 策略智能体
│   ├── backtest_agent.py  # 回测智能体
│   ├── trading_agent.py   # 交易智能体
│   └── graph.py       # LangGraph 工作流
├── services/          # 服务层
│   ├── llm.py        # LLM 服务
│   ├── data.py       # 数据服务
│   └── storage.py    # 存储服务
├── requirements.txt   # Python 依赖
└── ARCHITECTURE.md    # 架构文档
```

## 🚀 快速开始

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要的配置
# OPENROUTER_API_KEY=your_api_key
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### 运行服务

```bash
# 开发模式
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Python
python -m api.main
```

## 📖 文档

- [架构文档](ARCHITECTURE.md) - 详细的技术架构和设计说明
- [API 文档](http://localhost:8000/docs) - FastAPI 自动生成的 API 文档（运行服务后访问）

## 🔧 技术栈

- **FastAPI** - 现代、快速的 Web 框架
- **LangGraph** - 多智能体工作流编排
- **LangChain** - LLM 工具和集成
- **OpenAI SDK** - LLM API 客户端

## 📝 开发指南

### 添加新的 API 端点

1. 在 `api/` 目录下创建新的路由文件
2. 在 `api/main.py` 中注册路由
3. 更新 API 文档

### 添加新的智能体

1. 在 `agents/` 目录下创建新的智能体文件
2. 在 `agents/graph.py` 中添加到工作流
3. 实现智能体的核心逻辑

## 🤝 贡献

请遵循项目的代码规范和开发流程。

