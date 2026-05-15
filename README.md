# FAgent

FAgent 是一个面向股票/期货研究场景的对话式应用，当前以 Web 端为主，由 `frontend`、`backend`、`agents` 三个服务层组成。仓库里同时保留了 Memory/CLI、数据同步和策略模块的实验代码，但主链路仍然是 Web 对话与行情工具调用。

## 当前状态

- Web 前端已可运行，支持会话侧边栏、流式消息、登录/注册弹窗
- Backend 已提供会话存储、消息持久化、认证接口、模型列表代理和市场模块接口
- Agents 已提供 Router 路由、行情工具、标题生成和 OpenRouter 兼容 LLM 调用
- 未配置真实 LLM API Key 时，Agents 会自动进入 Mock 模式，便于联调
- `src/memory/` 与 `fagent_cli.py` 已落地基础版本，但仍处于实验性阶段
- CLI 已提供 `doctor security-scan`，可在提交前扫描本机路径、API key、token 和私钥等高风险内容

## 架构

```text
Frontend (React 19 / Vite 7, :5173)
        |
        v
Backend (FastAPI, :8000)
  - 会话/消息存储
  - 认证与用户隔离
  - SSE / REST API
  - 调用 Agents
        |
        v
Agents (FastAPI, :8001)
  - Router 路由
  - Chat / Market SubAgent
  - 标题生成
  - 行情工具与缓存
  - OpenRouter 兼容 LLM
```

可选组件：

- `agents/data_sync/service.py`：独立数据同步服务，默认端口 `8003`
- `src/memory/`：本地记忆系统
- `modules/`：股票/期货策略与回测实验模块

## 主要能力

- 多会话创建、重命名、删除、历史拉取
- SSE 流式对话与非流式对话
- 首轮对话自动生成会话标题
- 用户注册 / 登录 / JWT 鉴权
- 行情查询：`quote` / `kline` / `search` / `analysis`
- 动态模型列表：前端通过 `/api/chat/models` 获取可用模型
- 市场模块接口：股票 / 期货实验能力

## 项目结构

```text
FAgent/
├── frontend/              # React Web 前端
├── backend/               # 面向前端的 API、存储、鉴权
├── agents/                # Router、LLM、行情工具
├── src/memory/            # 记忆系统实验代码
├── modules/               # 股票/期货策略与回测实验模块
├── tests/                 # 单测、脚本测试、联调脚本
├── docs/                  # 设计、报告与说明文档
└── fagent_cli.py          # CLI 入口
```

## 快速开始

### 1. 克隆仓库

```bash
git clone git@github-235:1TAgents/FAgent.git
cd FAgent
```

### 2. Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
pip install -r requirements-cli.txt
pip install -r tests/requirements.txt
```

### 3. 前端依赖

```bash
cd frontend
npm install
cd ..
```

### 4. 环境变量

复制 `.env.example` 为 `.env`，至少配置：

```bash
OPENROUTER_API_KEY=your_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=qwen3.5-plus
```

常用可选项：

- `AGENTS_BASE_URL=http://localhost:8001`
- `RQDATAC_CONF=...`：需要接 RQData 时再配置
- `JWT_SECRET=...`
- `DATABASE_PATH=data/conversations.db`

### 5. 启动服务

```bash
# 终端 1
uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001

# 终端 2
AGENTS_BASE_URL=http://localhost:8001 \
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# 终端 3
cd frontend
npm run dev
```

### 6. 访问

- Frontend: `http://localhost:5173`
- Backend Docs: `http://localhost:8000/docs`
- Agents Docs: `http://localhost:8001/docs`

## 常用接口

- `POST /api/chat/session/create`
- `POST /api/chat/send`
- `POST /api/chat/send/stream`
- `GET /api/chat/conversations`
- `PATCH /api/chat/conversation/{cid}`
- `DELETE /api/chat/conversation/{cid}`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/chat/models`
- `POST /api/chat/market/chat`

## CLI 诊断

提交或发布前可以运行本地安全扫描：

```bash
python3 fagent_cli.py doctor security-scan
```

默认只扫描 git 已跟踪文件，输出相对路径、行号和规则名，不打印命中的敏感值。需要检查未跟踪文件时使用：

```bash
python3 fagent_cli.py doctor security-scan --include-untracked
```

只检查本次暂存区内容时使用：

```bash
python3 fagent_cli.py doctor security-scan --staged
```

## 文档导航

- [Backend 文档](backend/README.md)
- [Agents 文档](agents/README.md)
- [Frontend 文档](frontend/README.md)
- [测试说明](tests/README.md)
- [文档总览](docs/README.md)

## 当前限制

- 未配置 `OPENROUTER_API_KEY` 时，Agents 只返回 Mock 内容，不会调用真实模型
- Memory 核心存储和查询 API 已有基础实现，但 CLI 的部分命令仍在补齐
- Android 文档仍然保留在仓库中，但属于未来规划，不是当前交付

## 反馈

- 问题反馈：<https://github.com/1TAgents/FAgent/issues>
