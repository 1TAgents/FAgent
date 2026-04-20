# 数据服务架构文档

## 概述

数据服务层为 FAgent 提供统一的股票数据访问接口，整合缓存、数据库、外部数据源，实现数据持久化、定时同步、智能加载。

---

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                  FAgent 应用层                           │
│  (MarketSubAgent, AnalysisAgent, etc.)                  │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Client
┌────────────────────▼────────────────────────────────────┐
│              MCP Server (:8002)                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Tool Registry                                    │   │
│  │  - stock_quote (实时)                             │   │
│  │  - stock_kline (历史)                             │   │
│  │  - data_quote (数据库 + 缓存) ⭐                   │   │
│  │  - data_kline (数据库 + 自动补充) ⭐               │   │
│  │  - data_sync (手动同步) ⭐                         │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           Data Service (数据服务层) ⭐                   │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  DataCache      │  │  StockDatabase  │              │
│  │  (Redis)        │  │  (SQLite)       │              │
│  │  - 行情 60s      │  │  - 历史 K 线       │              │
│  │  - K 线 5min     │  │  - 股票列表     │              │
│  │  - 搜索 1h       │  │  - 同步日志     │              │
│  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                        │
│           └──────────┬─────────┘                        │
│                      │                                  │
│           ┌──────────▼──────────┐                       │
│           │  DataSyncManager    │                       │
│           │  - 定时同步         │                       │
│           │  - 增量更新         │                       │
│           │  - 数据校验         │                       │
│           └──────────┬──────────┘                       │
└───────────────────────┼─────────────────────────────────┘
                        │
           ┌────────────▼────────────┐
           │   AKShare               │
           │   (外部数据源)          │
           └─────────────────────────┘
```

---

## 核心组件

### 1. DataService (`service.py`)

统一数据访问接口，提供：
- 实时行情查询
- K 线数据查询
- 股票列表查询
- 股票搜索
- 数据同步

**用法：**
```python
from agents.data_service import get_data_service

data_service = get_data_service(
    db_path="data/stock_data.db",
    redis_url="redis://localhost:6379",
    cache_enabled=True,
    auto_sync=True
)

# 查询行情（优先缓存/数据库）
quote = await data_service.get_quote("600519")

# 查询 K 线（数据库自动补充）
klines = await data_service.get_kline("600519", count=100)

# 手动同步
await data_service.sync_single_stock("600519")
```

---

### 2. StockDatabase (`database.py`)

SQLite 数据库，存储：
- **stocks** - 股票列表
- **klines** - K 线数据
- **sync_log** - 同步日志
- **sync_meta** - 同步元数据

**表结构：**

```sql
-- 股票列表
CREATE TABLE stocks (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- K 线数据
CREATE TABLE klines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL DEFAULT 'daily',
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    turnover REAL,
    change_percent REAL,
    UNIQUE(symbol, period, date)
);
```

**索引：**
- `idx_klines_symbol_date` - 加速 K 线查询
- `idx_stocks_market` - 加速市场筛选

---

### 3. DataCache (`cache.py`)

Redis 缓存层，TTL 策略：

| 数据类型 | TTL | 说明 |
|----------|-----|------|
| 实时行情 | 60s | 快速变化，短 TTL |
| K 线数据 | 5min | 相对稳定 |
| 搜索结果 | 1h | 热点数据 |
| 股票列表 | 2h | 变化少 |

**缓存键格式：**
- `quote:A:600519` - A 股行情
- `kline:600519:daily:2024-01-01:2024-03-15` - K 线
- `search:A:茅台:10` - 搜索
- `stocks:A` - 股票列表

---

### 4. DataSyncManager (`sync.py`)

数据同步管理器，负责：
- 股票列表同步（每周）
- K 线数据同步（每日盘后）
- 单只股票同步（按需）
- 数据校验

**同步策略：**

```python
# 股票列表 - 每周六 02:00
if now.hour == 2 and now.minute == 0 and now.weekday() == 5:
    await sync_manager.sync_stock_list()

# K 线数据 - 交易日 15:30
if now.hour == 15 and now.minute == 30 and now.weekday() < 5:
    await sync_manager.sync_recent_klines(days=1)
```

---

## MCP 工具

### data_quote - 行情查询

**优先级：**
1. Redis 缓存（60s TTL）
2. AKShare 实时拉取
3. 数据库（盘后数据）

**调用：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "data_quote", "arguments": {"symbol": "600519"}}'
```

---

### data_kline - K 线查询

**优先级：**
1. 数据库（主）
2. AKShare 补充（数据库缺失的日期）

**调用：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "data_kline", "arguments": {"symbol": "600519", "count": 100}}'
```

---

### data_sync - 手动同步

**用途：** 强制同步单只股票数据

**调用：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "data_sync", "arguments": {"symbol": "600519"}}'
```

---

## 定时同步

### 启动方式

```bash
# 独立运行定时任务
cd "$(git rev-parse --show-toplevel)"
python -m agents.data_service.scheduler
```

### 定时任务计划

| 时间 | 任务 | 说明 |
|------|------|------|
| 交易日 15:30 | K 线同步 | 同步当日 K 线数据 |
| 周六 02:00 | 股票列表 | 更新股票列表 |
| 服务启动 | 全量同步 | 检查并同步最近 30 天数据 |

### 日志位置

```
logs/data_service/scheduler.log
```

---

## 数据库位置

```
data/stock_data.db
```

---

## 性能优化

### 1. 缓存命中率

```python
# 查看缓存统计
stats = await redis.info("stats")
print(f"命中率：{stats['keyspace_hits'] / (stats['keyspace_hits'] + stats['keyspace_misses'])}")
```

**目标：** > 80%

### 2. 数据库查询优化

- ✅ 已添加索引
- ✅ 批量插入（事务）
- ✅ 定期清理旧数据

### 3. 并发控制

```python
# 同步时并发数限制
await sync_manager.sync_recent_klines(max_workers=5)
```

---

## 数据备份

### 备份数据库

```bash
# 每天备份
cp data/stock_data.db data/backup/stock_data_$(date +%Y%m%d).db

# 保留最近 7 天
find data/backup -name "*.db" -mtime +7 -delete
```

### 恢复数据库

```bash
cp data/backup/stock_data_20240315.db data/stock_data.db
```

---

## 故障排查

### 1. 数据不同步

**检查同步日志：**
```sql
SELECT * FROM sync_log ORDER BY created_at DESC LIMIT 10;
```

**手动触发同步：**
```bash
curl -X POST http://localhost:8002/tool/call \
  -d '{"tool_name": "data_sync", "arguments": {"symbol": "600519"}}'
```

### 2. 缓存未命中

**检查 Redis 连接：**
```bash
redis-cli ping  # 应返回 PONG
```

**查看缓存键：**
```bash
redis-cli keys "quote:*"
```

### 3. 数据库损坏

**检查完整性：**
```sql
PRAGMA integrity_check;
```

**重建数据库：**
```bash
rm data/stock_data.db
# 重启 MCP Server 会自动创建
```

---

## 扩展开发

### 添加新数据源

1. 创建适配器：
```python
# agents/data_service/adapters/tushare_adapter.py
class TushareAdapter:
    async def get_quote(self, symbol):
        # 实现逻辑
```

2. 在 DataService 中集成：
```python
class DataService:
    async def get_quote(self, symbol):
        # 1. 缓存
        # 2. 数据库
        # 3. AKShare
        # 4. Tushare (新增)
```

### 添加新表

```python
# 在 StockDatabase._init_tables() 中添加
cursor.execute("""
    CREATE TABLE IF NOT EXISTS financials (
        symbol TEXT,
        report_date TEXT,
        pe_ratio REAL,
        pb_ratio REAL,
        roe REAL,
        PRIMARY KEY (symbol, report_date)
    )
""")
```

---

## 监控指标

### 1. 数据量统计

```python
stats = data_service.get_stats()
print(f"股票数：{stats['stock_count']}")
print(f"K 线记录：{stats['kline_records']}")
print(f"最后同步：{stats['last_sync']}")
```

### 2. 缓存命中率

```python
# Redis INFO stats
hits = redis_info['keyspace_hits']
misses = redis_info['keyspace_misses']
hit_rate = hits / (hits + misses) * 100
print(f"缓存命中率：{hit_rate:.2f}%")
```

### 3. 同步成功率

```sql
SELECT 
    sync_type,
    COUNT(*) as total,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
    CAST(SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as success_rate
FROM sync_log
GROUP BY sync_type;
```

---

## 最佳实践

1. **启动时预加载** - 服务启动时同步最近 30 天数据
2. **盘后批量同步** - 15:30 后批量更新所有股票 K 线
3. **缓存优先** - 所有查询先查缓存/数据库
4. **增量更新** - 只同步缺失的数据
5. **错误重试** - 网络失败自动重试（最多 3 次）
6. **定期备份** - 每天备份数据库
7. **监控告警** - 同步失败发送告警

---

## 参考链接

- AKShare: https://github.com/akfamily/akshare
- Redis: https://redis.io
- SQLite: https://www.sqlite.org
