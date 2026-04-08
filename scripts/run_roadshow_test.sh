#!/bin/bash
# FAgent 路演多轮对话测试快速启动脚本

set -e

echo "============================================================"
echo "🎬 FAgent 路演多轮对话自动化测试"
echo "============================================================"
echo ""

# 切换到项目目录
cd <repo-root>

# 检查 Backend 服务是否运行
echo "📡 检查 Backend 服务状态..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend 服务运行中"
else
    echo "❌ Backend 服务未运行"
    echo ""
    echo "请先启动 Backend 服务:"
    echo "  python3 -m uvicorn backend.api.main:app --reload --port 8000"
    echo ""
    exit 1
fi

# 创建报告目录
mkdir -p reports

# 生成报告文件名（带日期）
REPORT_DATE=$(date +%Y-%m-%d_%H-%M-%S)
REPORT_FILE="reports/roadshow_test_${REPORT_DATE}.html"

# 运行测试
echo ""
echo "🚀 开始运行测试..."
echo "   报告输出：$REPORT_FILE"
echo ""

python3 tests/test_roadshow_multi_turn.py --output "$REPORT_FILE"

# 检查测试是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ 测试完成！"
    echo "============================================================"
    echo ""
    echo "📄 报告文件：$REPORT_FILE"
    echo ""
    
    # 询问是否打开报告
    read -p "是否在浏览器中打开报告？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$REPORT_FILE"
        echo "✅ 报告已在浏览器中打开"
    fi
    
    echo ""
    echo "📊 下一步:"
    echo "  1. 查看 HTML 报告中的'可路演示例'"
    echo "  2. 将优质对话复制到 docs/路演演示示例库.md"
    echo "  3. 对于需优化的场景，分析问题并改进"
    echo ""
else
    echo ""
    echo "❌ 测试失败，请检查错误信息"
    exit 1
fi
