# 测试模块

## 测试框架

测试用例与测试逻辑分离，使用 JSON 配置测试数据。

### 文件结构

```
tests/
├── test_cases.json    # 测试用例数据（JSON 格式）
├── test_runner.py     # 通用测试运行器
├── test_market.py     # Market 模块测试（旧版，硬编码）
├── test_multi_turn.py # 多轮对话测试（旧版，硬编码）
└── README.md
```

### 快速开始

```bash
# 列出所有测试用例
python tests/test_runner.py --list

# 运行指定测试套件
python tests/test_runner.py --suite market_service

# 按 tag 运行
python tests/test_runner.py --tag smoke

# 运行所有测试
python tests/test_runner.py --all
```

### 测试套件

| 套件 | 描述 | 需要服务 |
|------|------|----------|
| `market_service` | Market Service 单元测试 | 否 |
| `market_subagent` | Market SubAgent 集成测试 | 否 |
| `market_api` | Market API 端点测试 | 是 (8001) |
| `multi_turn_chat` | 多轮对话测试 | 是 (8000+8001) |
| `cache` | 缓存功能测试 | 否 |

### Tags

| Tag | 描述 |
|-----|------|
| `smoke` | 冒烟测试，核心功能验证 |
| `a_share` | A股相关 |
| `quote` | 行情查询 |
| `kline` | K线数据 |
| `api` | API 端点测试 |
| `chat` | 对话功能 |

### 添加新测试用例

编辑 `test_cases.json`，在对应 suite 的 cases 数组中添加：

```json
{
  "id": "MS006",
  "name": "测试用例名称",
  "function": "market_service.xxx",
  "input": { "param": "value" },
  "expected": { "success": true },
  "tags": ["tag1", "tag2"]
}
```

---

## Streamlit 测试界面（旧）

用于测试 FastAPI 流式和非流式接口的 Web 界面。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试界面

1. **启动 FastAPI 后端服务**（在另一个终端）：
   ```bash
   uvicorn backend.api.main:app --reload --port 8000
   ```

2. **启动 Streamlit 测试界面**：
   ```bash
   streamlit run tests/streamlit_test.py
   ```

3. **访问测试界面**：
   浏览器会自动打开 `http://localhost:8501`

### 功能说明

- ✅ **API 健康检查**：自动检测后端服务状态
- ✅ **流式请求测试**：测试 SSE 流式输出
- ✅ **非流式请求测试**：测试普通 RESTful 接口
- ✅ **对话历史管理**：保存和管理对话历史
- ✅ **参数配置**：调整 Temperature 等参数

