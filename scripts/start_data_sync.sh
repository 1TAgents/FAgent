#!/bin/bash
# 数据同步服务启动脚本

set -e

echo "======================================"
echo "FAgent 数据同步服务"
echo "======================================"

# 进入项目目录
cd ~/Learning/FAgent

# 检查 Redis 是否运行
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Redis 未运行，正在启动..."
    redis-server --daemonize yes
    sleep 2
fi

echo "✓ Redis 运行正常"

# 创建数据目录
mkdir -p data

# 启动数据同步服务
echo "🚀 启动数据同步服务（Port 8003）..."
PYTHONPATH=. python3 -m uvicorn agents.data_sync.service:app --reload --host 0.0.0.0 --port 8003 &

echo ""
echo "✅ 服务已启动"
echo ""
echo "使用指南:"
echo "  查看状态：curl http://localhost:8003/status"
echo "  查看统计：curl http://localhost:8003/stats"
echo "  同步股票列表：curl -X POST http://localhost:8003/sync/stocks"
echo "  同步单只股票：curl -X POST http://localhost:8003/sync/klines -H 'Content-Type: application/json' -d '{\"symbol\":\"600519\"}'"
echo "  启动后台全量同步：curl -X POST http://localhost:8003/sync/historical"
echo ""
echo "停止服务：pkill -f 'uvicorn agents.data_sync.service'"
echo "======================================"
