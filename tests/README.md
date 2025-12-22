# 测试模块

## Streamlit 测试界面

用于测试 FastAPI 流式和非流式接口的 Web 界面。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试界面

1. **启动 FastAPI 后端服务**（在另一个终端）：
   ```bash
   cd backend
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动 Streamlit 测试界面**：
   ```bash
   streamlit run streamlit_test.py
   ```

3. **访问测试界面**：
   浏览器会自动打开 `http://localhost:8501`

### 功能说明

- ✅ **API 健康检查**：自动检测后端服务状态
- ✅ **流式请求测试**：测试 SSE 流式输出
- ✅ **非流式请求测试**：测试普通 RESTful 接口
- ✅ **对话历史管理**：保存和管理对话历史
- ✅ **参数配置**：调整 Temperature 等参数

### 使用示例

1. 在输入框输入消息
2. 选择"流式 (SSE)"或"非流式"
3. 查看实时回复或完整回复
4. 查看 Token 使用情况（非流式）

