# FAgent 部署指南

> 版本：0.1.0 | 更新日期：2026-05-15

## 架构概览

```
CLI (fagent_cli.py)
  │ HTTP (port 8000)
  ▼
Backend Service ────────────┐  (port 8000)
  • Session/Message 存储      │
  • Auth (JWT)               │
  • Rate Limiting            │
  • 转发到 Agents             │
  └─────────────────────────►│
                             ▼
                      Agents Service  (port 8001)
                        • Router (intent recognition)
                        • ReAct Loop (LLM tool calling)
                        • Tool Registry (11 tools)
                        • MCP Server (optional, port 8002)
```

三个独立进程：
1. **Backend** (8000) — 面向 Web/CLI 的网关层，处理认证、限流、会话管理
2. **Agents** (8001) — Agent 核心服务，执行 LLM 推理和工具调用
3. **MCP Server** (8002, 可选) — 外部行情数据接口

## 快速启动（开发环境）

### 1. 安装依赖

```bash
# Backend 依赖
cd <project-root>/backend
pip install -r requirements.txt

# Agents 依赖
cd <project-root>/agents
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# LLM 提供商 API Key（必须）
export OPENAI_API_KEY="your-api-key-here"

# 可选：指定默认模型
export LLM_MODEL="mimo-v2-flash"

# 可选：OLLAMA 本地模型
export OLLAMA_BASE_URL="http://localhost:11434/v1"

# 可选：MCP Server 地址
export MCP_BASE_URL="http://localhost:8002"
```

### 3. 启动服务

```bash
# 终端 1：启动 Backend（port 8000）
cd <project-root>
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 终端 2：启动 Agents（port 8001）
python -m uvicorn agents.api.main:app --host 0.0.0.0 --port 8001
```

### 4. 验证

```bash
# 检查 Backend
curl http://localhost:8000/health

# 检查 Agents
curl http://localhost:8001/health

# CLI 测试
python fagent_cli.py send "你好"
```

## 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | — | **必须设置**，LLM API 密钥 |
| `LLM_MODEL` | 空（使用提供商默认） | 默认推理模型 |
| `AGENTS_BASE_URL` | `http://localhost:8001` | Backend 转发到的 Agents 地址 |
| `FAGENT_BACKEND_URL` | `http://localhost:8000` | CLI 连接的后端地址 |
| `JWT_SECRET` | `fagent-secret-key-change-in-production` | JWT 签名密钥 |
| `MCP_BASE_URL` | `http://localhost:8002` | MCP Server 地址 |
| `MCP_API_KEYS` | 空 | MCP 服务的 API Keys（JSON 格式） |
| `LOG_LEVEL` | `DEBUG` | 日志级别 |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | 本地 Ollama 服务地址 |
| `PAPER_TRADING_DB_PATH` | `data/paper_trading.db` | 模拟交易数据库路径 |

## 生产环境配置

### 1. 安全加固

```bash
# 必须修改 JWT_SECRET
export JWT_SECRET="<strong-random-string>"

# 修改 CORS 配置（backend/api/main.py 和 agents/api/main.py）
# 将 allow_origins=["*"] 改为具体域名
allow_origins=["https://your-domain.com"]
```

### 2. 反向代理（Nginx）

```nginx
# /etc/nginx/sites-available/fagent
upstream backend {
    server 127.0.0.1:8000;
}

upstream agents {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name api.your-domain.com;

    # SSL 配置（生产环境必须启用）
    # ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;
    # listen 443 ssl;

    client_max_body_size 10M;

    # Backend 代理
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 120s;
    }

    # Agents 直接代理（内部调用）
    location /agents/ {
        proxy_pass http://agents/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 120s;
    }
}
```

### 3. Systemd 服务管理

```ini
# /etc/systemd/system/fagent-backend.service
[Unit]
Description=FAgent Backend Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fagent
Environment=OPENAI_API_KEY=your-key
Environment=JWT_SECRET=your-secret
ExecStart=/opt/fagent/.venv/bin/python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/fagent-agents.service
[Unit]
Description=FAgent Agents Service
After=network.target fagent-backend.service

[Service]
Type=simple
WorkingDirectory=/opt/fagent
Environment=OPENAI_API_KEY=your-key
Environment=LOG_LEVEL=INFO
ExecStart=/opt/fagent/.venv/bin/python -m uvicorn agents.api.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable fagent-backend fagent-agents
sudo systemctl start fagent-backend fagent-agents
```

### 4. 数据目录

生产环境建议将数据目录放在独立路径：

```bash
export FAGENT_DATA_DIR="/var/lib/fagent"

# 目录结构：
# /var/lib/fagent/
#   ├── conversations.db    # 会话/消息数据库
#   ├── memory.db           # Memory 系统数据
#   ├── paper_trading.db    # 模拟交易数据
#   ├── current_cid         # CLI 当前会话 ID
#   └── logs/               # 日志目录
#       ├── backend/
#       └── agents/
```

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| CLI 报 "后端服务不可达" | Backend 未启动 | `curl http://localhost:8000/health` |
| 回复报错 "unexpected keyword" | Agents 服务运行旧代码 | 重启 Agents 进程 |
| SSE 流式中断 | 代理超时设置过短 | Nginx `proxy_read_timeout 120s` |
| 模型调用失败 | API Key 未设置 | `echo $OPENAI_API_KEY` |
