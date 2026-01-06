#!/bin/bash
# Agents 服务启动脚本

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 激活虚拟环境
source .venv/bin/activate

# 启动 Agents 服务（端口 8001）
uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001

