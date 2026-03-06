#!/bin/bash
# FastAPI 服务启动脚本

echo "🚀 启动 FAgent API 服务..."
echo "📍 服务地址: http://localhost:8000"
echo "📖 API 文档: http://localhost:8000/docs"
echo ""

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

