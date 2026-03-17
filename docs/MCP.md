# MCP 服务开发文档

## 概述

MCP（Model Context Protocol）服务为 FAgent 提供标准化的金融数据工具接口，支持所有 Agent 通过统一协议调用行情、财务等数据。

### 数据服务架构

```
┌─────────────────┐
│  FAgent 应用层   │
└────────┬────────┘
         │ MCP Client
┌────────▼────────┐
│  MCP Server     │  ← 9 个工具
└────────┬────────┘
         │
┌────────▼────────┐
│  Data Service   │  ← 新增数据服务层
│  (SQLite+Redis) │
└────────┬────────┘
         │
┌────────▼────────┐
│   AKShare       │  ← 外部数据源
└─────────────────┘
```

**核心特性：**
- ✅ **分层存储** - Redis 缓存（60s）+ SQLite 数据库（永久）
- ✅ **定时同步** - 交易日 15:30 自动同步 K 线，周六 02:00 同步股票列表
- ✅ **智能加载** - 启动预加载热点数据 + 懒加载补充
- ✅ **离线可用** - 历史数据本地化，无需实时 API

**新增工具：**
- `data_quote` - 行情（优先数据库/缓存）
- `data_kline` - K 线（数据库自动补充）
- `data_sync` - 手动同步单只股票
- `index_quote` - 主流指数行情（沪深 300/中证 500/上证 50 等）✨
- `index_kline` - 指数 K 线数据 ✨
- `industry_quote` - 行业板块行情 ✨
- `industry_kline` - 行业 K 线 ✨
- `industry_detail` - 行业成分股 ✨

## 架构

```
┌─────────────────┐      MCP Client      ┌─────────────────┐
│   SubAgents     │ ───────────────────► │   MCP Server    │
│  (MarketAgent)  │                      │   (Port 8002)   │
└─────────────────┘                      └────────┬────────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    │             │             │
                            ┌───────▼──────┐ ┌──▼────────┐ ┌──▼────────┐
                            │ AKShare      │ │  Cache    │ │  Tools    │
                            │ Adapter      │ │ (Redis)   │ │ Registry  │
                            └──────────────┘ └───────────┘ └───────────┘
```

## 快速开始

### 启动 MCP Server

```bash
cd <repo-root>
PYTHONPATH=. python3 -m uvicorn agents.mcp.server:app --reload --port 8002
```

### 健康检查

```bash
curl http://localhost:8002/health
# {"status":"healthy","tools_count":6}
```

---

## 可用工具

### 1. stock_quote - 实时行情

获取股票实时价格、涨跌幅、成交量等数据。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| symbol | string | ✅ | - | 股票代码（如：600519, AAPL） |
| market | string | ❌ | "A" | 市场类型（A=股，US=美股，HK=港股） |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "stock_quote", "arguments": {"symbol": "600519", "market": "A"}}'
```

**返回示例：**
```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "name": "贵州茅台",
    "market": "A",
    "price": 1700.00,
    "change": 10.5,
    "change_percent": 0.62,
    "volume": 1234567,
    "turnover": 2098765432.10,
    "timestamp": "2026-03-15 15:00:00"
  }
}
```

**缓存 TTL：** 60 秒

---

### 2. stock_kline - K 线数据

获取股票 K 线历史数据，支持多种周期。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| symbol | string | ✅ | - | 股票代码 |
| period | string | ❌ | "daily" | 周期（daily/weekly/monthly/1m/5m/15m/30m/60m） |
| count | integer | ❌ | 100 | 返回条数（1-1000） |
| market | string | ❌ | "A" | 市场类型 |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "stock_kline", "arguments": {"symbol": "600519", "period": "daily", "count": 30}}'
```

**缓存 TTL：** 300 秒（5 分钟）

---

### 3. stock_search - 股票搜索

根据关键词搜索股票（代码或名称）。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | ✅ | - | 搜索关键词 |
| market | string | ❌ | "A" | 市场类型 |
| limit | integer | ❌ | 10 | 返回数量（1-50） |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "stock_search", "arguments": {"keyword": "茅台", "market": "A", "limit": 5}}'
```

**缓存 TTL：** 3600 秒（1 小时）

---

### 4. stock_fund_flow - 资金流向

获取股票资金流向数据（主力/散户流入流出）。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| symbol | string | ✅ | - | 股票代码 |
| market | string | ❌ | "A" | 市场类型 |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "stock_fund_flow", "arguments": {"symbol": "600519"}}'
```

---

### 5. stock_rank - 股票排行

获取股票排行榜（涨幅榜/跌幅榜/成交额榜/成交量榜）。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| rank_type | string | ✅ | - | 排行类型（gain/loss/turnover/volume） |
| market | string | ❌ | "A" | 市场类型 |
| limit | integer | ❌ | 20 | 返回数量（1-100） |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "stock_rank", "arguments": {"rank_type": "gain", "market": "A", "limit": 10}}'
```

---

### 6. stock_financial - 财务指标

获取股票财务指标（市盈率/市净率/ROE 等）。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| symbol | string | ✅ | - | 股票代码 |
| market | string | ❌ | "A" | 市场类型 |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "stock_financial", "arguments": {"symbol": "600519"}}'
```

---

### 7. index_quote - 指数行情 ✨

获取主流指数实时行情（沪深 300/中证 500/上证 50/科创 50/创业板指等）。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| symbol | string | ✅ | - | 指数代码（如：000300, 000001, 399006） |

**主流指数代码：**
| 代码 | 名称 |
|------|------|
| 000001 | 上证指数 |
| 000016 | 上证 50 |
| 000300 | 沪深 300 |
| 000688 | 科创 50 |
| 000905 | 中证 500 |
| 399001 | 深证成指 |
| 399006 | 创业板指 |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "index_quote", "arguments": {"symbol": "000300"}}'
```

**返回示例：**
```json
{
  "success": true,
  "data": {
    "symbol": "000300",
    "name": "沪深 300",
    "price": 3500.00,
    "change": 25.5,
    "change_percent": 0.73,
    "volume": 123456789,
    "turnover": 9876543210.50,
    "timestamp": "2026-03-17 15:00:00"
  }
}
```

**缓存 TTL：** 60 秒

---

### 8. index_kline - 指数 K 线 ✨

获取指数 K 线历史数据，支持多种周期。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| symbol | string | ✅ | - | 指数代码 |
| period | string | ❌ | "daily" | 周期（daily/weekly/monthly） |
| count | integer | ❌ | 100 | 返回条数（1-1000） |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "index_kline", "arguments": {"symbol": "000300", "period": "daily", "count": 30}}'
```

**缓存 TTL：** 300 秒（5 分钟）

---

### 9. industry_quote - 行业板块行情 ✨

获取行业板块实时行情，可查询单个行业或所有行业涨幅榜。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| industry_name | string | ❌ | null | 行业名称（如：半导体、银行、医药；不传则返回所有行业） |

**调用示例：**
```bash
# 查询所有行业（按涨跌幅排序）
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "industry_quote"}'

# 查询单个行业
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "industry_quote", "arguments": {"industry_name": "半导体"}}'
```

**缓存 TTL：** 60 秒

---

### 10. industry_kline - 行业 K 线 ✨

获取行业指数 K 线历史数据。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| industry_name | string | ✅ | - | 行业名称（如：半导体、银行、医药） |
| period | string | ❌ | "daily" | 周期（daily/weekly/monthly） |
| count | integer | ❌ | 100 | 返回条数（1-1000） |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "industry_kline", "arguments": {"industry_name": "半导体", "period": "daily", "count": 30}}'
```

**缓存 TTL：** 300 秒（5 分钟）

---

### 11. industry_detail - 行业成分股 ✨

获取行业成分股列表，包含成分股代码、名称、权重等信息。

**参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| industry_name | string | ✅ | - | 行业名称（如：半导体、银行、医药） |

**调用示例：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "industry_detail", "arguments": {"industry_name": "半导体"}}'
```

**返回示例：**
```json
{
  "success": true,
  "data": {
    "industry_name": "半导体",
    "index_code": "BK0917",
    "stock_count": 150,
    "stocks": [
      {"symbol": "688981", "name": "中芯国际", "weight": 5.2},
      {"symbol": "002371", "name": "北方华创", "weight": 4.8},
      ...
    ],
    "timestamp": "2026-03-17 15:00:00"
  }
}
```

**缓存 TTL：** 3600 秒（1 小时）

---

## API 端点

| 端点 | 方法 | 说明 | 鉴权 |
|------|------|------|------|
| `/health` | GET | 健康检查 | ❌ |
| `/tools` | GET | 列出所有工具 | ❌ |
| `/tool/call` | POST | 调用工具 | ❌ |
| `/tool/{name}` | GET | 获取工具详情 | ❌ |
| `/docs` | GET | Swagger 文档 | ❌ |

---

## 中间件

### 限流

- **60 次/分钟**（按 IP）
- **1000 次/小时**（按 IP）
- 超过限制返回 `429 Too Many Requests`

### API Key 鉴权（可选）

设置环境变量启用：
```bash
export MCP_API_KEYS="key1,key2,key3"
```

请求时添加 Header：
```bash
curl -H "X-API-Key: key1" http://localhost:8002/tool/call ...
```

---

## Python SDK 使用

### 基本用法

```python
from agents.mcp.client import MCPClient

# 初始化客户端
mcp = MCPClient(base_url="http://localhost:8002")

# 调用工具
result = await mcp.call("stock_quote", symbol="600519")
print(result)
```

### 快捷方法

```python
# 获取行情
quote = await mcp.get_quote("600519")
print(quote.summary())  # 贵州茅台 (600519) 当前股价 1700.00 元...

# 获取 K 线
kline = await mcp.get_kline("600519", period="daily", count=30)
print(kline.summary())  # K 线摘要

# 搜索股票
stocks = await mcp.search("茅台", limit=5)
for stock in stocks:
    print(f"{stock.name}({stock.symbol})")
```

### 在 SubAgent 中使用

```python
from agents.subagents.market_agent import MarketSubAgent

class MySubAgent(BaseSubAgent):
    def __init__(self):
        super().__init__()
        self.mcp = MCPClient()
    
    async def process_stream(self, context: TaskContext):
        # 调用 MCP 工具
        quote = await self.mcp.get_quote("600519")
        yield quote.summary()
```

---

## 缓存配置

### Redis 缓存

安装 Redis：
```bash
pip install redis
```

启动 Redis：
```bash
redis-server
```

配置缓存（在 `server.py` 中）：
```python
adapter = AKShareAdapter(
    redis_url="redis://localhost:6379",
    cache_enabled=True
)
```

### 缓存 TTL

| 数据类型 | TTL |
|----------|-----|
| 实时行情 | 60 秒 |
| K 线数据 | 300 秒 |
| 股票搜索 | 3600 秒 |

---

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "data": null,
  "error": "错误信息"
}
```

### 常见错误

| HTTP 状态码 | 说明 |
|------------|------|
| 400 | 参数错误 |
| 401 | 缺少 API Key |
| 403 | 无效的 API Key |
| 404 | 工具不存在 |
| 429 | 请求超限 |
| 500 | 服务器错误 |

---

## 开发指南

### 添加新工具

1. 在 `adapters/akshare_adapter.py` 中实现方法：
```python
async def get_new_data(self, symbol: str) -> Dict:
    # 实现逻辑
    return {"data": "value"}
```

2. 在 `server.py` 中注册：
```python
tool_registry.register(
    name="stock_new_tool",
    handler=adapter.get_new_data,
    description="新工具描述",
    parameters={...}  # JSON Schema
)
```

3. 测试：
```bash
curl -X POST http://localhost:8002/tool/call \
  -d '{"tool_name": "stock_new_tool", "arguments": {"symbol": "600519"}}'
```

---

## 故障排查

### MCP Server 无法启动

```bash
# 检查端口占用
lsof -ti:8002 | xargs kill -9

# 检查语法
PYTHONPATH=. python3 -m py_compile agents/mcp/server.py
```

### 工具调用失败

1. 检查日志：
```bash
tail -f logs/mcp/*.log
```

2. 检查 AKShare：
```python
python3 -c "import akshare as ak; print(ak.__version__)"
```

### 缓存未生效

1. 检查 Redis 连接：
```bash
redis-cli ping  # 应返回 PONG
```

2. 检查缓存日志：
```bash
grep "缓存命中" logs/mcp/*.log
```

---

## 性能优化建议

1. **启用 Redis 缓存** - 减少重复 API 调用
2. **调整缓存 TTL** - 根据数据更新频率
3. **批量查询** - 避免频繁单条查询
4. **限流配置** - 根据服务器能力调整

---

## 安全建议

1. **生产环境启用 API Key** - 设置 `MCP_API_KEYS`
2. **配置 CORS** - 限制允许的域名
3. **HTTPS** - 生产环境使用 HTTPS
4. **日志审计** - 定期检查请求日志
