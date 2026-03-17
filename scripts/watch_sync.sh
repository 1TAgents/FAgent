#!/bin/bash
# 数据同步进度监控脚本

echo "======================================"
echo "FAgent 数据同步进度监控"
echo "======================================"
echo ""

while true; do
    # 获取状态
    STATUS=$(curl -s http://localhost:8003/status)
    
    # 解析字段
    IS_SYNCING=$(echo $STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print('🔄 同步中' if d.get('is_syncing') else '✅ 空闲')")
    CURRENT_TASK=$(echo $STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('current_task', 'N/A'))")
    PROGRESS=$(echo $STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('progress', '0/0'))")
    ERRORS=$(echo $STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('errors_count', 0))")
    UPTIME=$(echo $STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('uptime_hours', 0):.1f}小时\")")
    
    # 获取统计
    STATS=$(curl -s http://localhost:8003/stats)
    STOCK_COUNT=$(echo $STATS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stock_count', 0))")
    KLINE_COUNT=$(echo $STATS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('kline_records', 0))")
    DB_SIZE=$(echo $STATS | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('database_size_mb', 0):.2f} MB\")")
    
    # 显示
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "状态：$IS_SYNCING"
    echo "任务：$CURRENT_TASK"
    echo "进度：$PROGRESS"
    echo "错误：$ERRORS"
    echo ""
    echo "股票总数：$STOCK_COUNT 只"
    echo "K 线记录：$KLINE_COUNT 条"
    echo "数据库大小：$DB_SIZE"
    echo "运行时间：$UPTIME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # 计算预计剩余时间
    if [ "$IS_SYNCING" = "🔄 同步中" ]; then
        PARSED=$(echo $PROGRESS | python3 -c "import sys; p=sys.stdin.read().strip(); parts=p.split('/'); print(f'{int(parts[0])/int(parts[1])*100:.1f}')")
        echo "完成度：${PARSED}%"
        
        # 估算剩余时间（基于 1 只/秒）
        REMAINING=$(echo $PROGRESS | python3 -c "import sys; p=sys.stdin.read().strip(); parts=p.split('/'); print(int(parts[1])-int(parts[0]))")
        if [ "$REMAINING" -gt 0 ]; then
            HOURS=$((REMAINING / 3600))
            MINS=$(((REMAINING % 3600) / 60))
            echo "预计剩余：${HOURS}小时 ${MINS}分钟"
        fi
    fi
    
    echo ""
    echo "按 Ctrl+C 停止监控"
    echo ""
    
    sleep 10
done
