#!/bin/bash
# Streamlit 测试界面启动脚本

echo "🧪 启动 FAgent API 测试界面..."
echo "📍 测试界面: http://localhost:8501"
echo ""
echo "⚠️  请确保 FastAPI 服务已启动 (http://localhost:8000)"
echo ""

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动 Streamlit
streamlit run streamlit_test.py

