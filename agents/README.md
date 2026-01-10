# Agents 模块

智能体服务模块，提供多 Agent 协作的对话系统。

## 📁 目录结构

```
agents/
├── router/                     # 🆕 主路由器
│   ├── __init__.py
│   └── main_router.py          # 主路由 Agent（系统入口）
├── subagents/                  # 子智能体
│   ├── __init__.py
│   ├── market_agent.py         # 行情子 Agent
│   └── chat_agent.py           # 通用对话子 Agent（兜底）
├── services/                   # 服务层
│   ├── llm.py                  # LLM 服务
│   └── summary.py              # 总结服务
├── common/                     # 公共模块
│   └── market/                 # 行情数据服务
│       ├── service.py          # 行情服务
│       ├── client.py           # 数据源客户端
│       ├── cache.py            # 缓存管理
│       └── models.py           # 数据模型
├── mcp/                        # 🆕 MCP 服务
│   ├── __init__.py
│   └── market_server.py        # 行情 MCP Server
├── core/                       # 核心配置
│   └── prompts.py              # System Prompt 配置
├── api/                        # API 接口
│   ├── main.py                 # FastAPI 应用入口
│   ├── chat.py                 # 对话接口
│   └── market.py               # 行情接口
└── requirements.txt            # Python 依赖
```

## 🏗️ 架构设计

### 整体架构

```
                              用户请求
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                         MainRouter (主路由器)                       │
│                                                                     │
│  职责：                                                             │
│  1. 维护完整对话历史                                                │
│  2. 意图识别 + 路由决策                                             │
│  3. 提炼任务上下文给 SubAgent                                       │
│  4. 流式透传 SubAgent 的输出（不做二次处理）                        │
│                                                                     │
│  ⚠️ Router 自己不产生最终回复内容，只做决策和分发                   │
└────────────────────────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ MarketSubAgent  │    │  NewsSubAgent   │    │  ChatSubAgent   │
│                 │    │    (未来)       │    │    (兜底)       │
│ 处理：          │    │                 │    │                 │
│ - 行情查询      │    │ 处理：          │    │ 处理：          │
│ - K线分析       │    │ - 财经新闻      │    │ - 闲聊          │
│ - 趋势判断      │    │ - 公告解读      │    │ - 通用问答      │
│                 │    │                 │    │ - 兜底所有      │
└────────┬────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Market MCP Server                           │
│                                                                  │
│  职责：纯数据获取，无业务逻辑                                     │
│  - 封装 AKShare/东方财富 等数据源                                 │
│  - 提供标准化的 MCP 接口                                          │
│  - 可被其他系统复用                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 核心设计原则

#### 1. 上下文分层管理

| 组件 | 看到的内容 | 原因 |
|------|-----------|------|
| **Router** | 完整对话历史 | 需要理解上下文、解析指代、做路由决策 |
| **SubAgent** | 提炼后的任务上下文 | 专注执行，不重复理解历史，节省 Token |

```python
# Router 传给 SubAgent 的内容
TaskContext(
    task_type="GET_QUOTE",           # 任务类型
    query="查询平安银行的行情",        # 解析后的明确问题（已处理指代）
    params={"symbol": "000001"},     # 提取的参数
    context_summary="用户在对比股票"  # 相关上下文摘要（可选）
)
```

#### 2. 流式透传（避免二次输出）

```
✅ 高效模式：SubAgent 直接输出给用户

用户 → Router (路由决策) → SubAgent → 直接流式输出给用户
           │                              │
           └── 只做决策，不做内容处理 ──────┘
```

**Router 不对 SubAgent 的输出做二次 LLM 处理**，直接透传给用户。

#### 3. 工具分层

```
MarketSubAgent
    │
    ├─→ MCP Tools (外部数据)
    │     - get_quote()      获取实时行情
    │     - get_kline()      获取K线数据
    │     - search_stock()   搜索股票
    │
    └─→ 内部工具 (本地计算)
          - calculate_ma()   均线计算
          - analyze_trend()  趋势分析
          - detect_cross()   金叉死叉检测
```

## 📦 核心组件

### 1. MainRouter (主路由器)

```python
class MainRouter:
    """
    主路由器 - 整个对话系统的入口
    
    职责：
    1. 维护完整对话历史
    2. 意图识别 + 路由决策
    3. 提炼任务上下文给 SubAgent
    4. 流式透传 SubAgent 的输出
    """
    
    async def process_stream(self, cid: int, user_message: str) -> AsyncIterator[str]:
        # 1. 更新历史
        self._add_to_history(cid, "user", user_message)
        
        # 2. 路由决策 + 提炼上下文
        route, task_context = await self._route(cid, user_message)
        
        # 3. 分发到对应的 SubAgent
        subagent = self.subagents.get(route, self.subagents["chat"])
        
        # 4. 流式透传（不做二次处理）
        async for chunk in subagent.process_stream(task_context):
            yield chunk
```

### 2. SubAgent 基类

```python
@dataclass
class TaskContext:
    """任务上下文（Router 传给 SubAgent）"""
    task_type: str           # 任务类型
    query: str               # 解析后的明确问题
    params: dict             # 提取的参数
    context_summary: str     # 相关上下文摘要

class BaseSubAgent(ABC):
    """SubAgent 基类"""
    
    @abstractmethod
    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        """处理任务并流式输出"""
        pass
```

### 3. MarketSubAgent (行情子Agent)

```python
class MarketSubAgent(BaseSubAgent):
    """
    行情子智能体
    
    处理：行情查询、K线分析、趋势判断
    工具：MCP Tools + 内部分析工具
    """
    
    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        if context.task_type == "GET_QUOTE":
            # 调用 MCP Tool 获取数据
            data = await self.mcp_client.call_tool("get_quote", context.params)
            # 流式生成分析
            async for chunk in self._generate_analysis(data, context.query):
                yield chunk
```

### 4. ChatSubAgent (兜底子Agent)

```python
class ChatSubAgent(BaseSubAgent):
    """
    通用对话子智能体（兜底）
    
    处理：闲聊、通用问答、无法分类的问题
    """
    
    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        # 直接调用 LLM
        async for chunk in self.llm.stream(context.query):
            yield chunk
```

### 5. Market MCP Server

```python
# 基于 MCP Python SDK
from mcp.server import Server
from mcp.types import Tool

server = Server("market-data")

@server.tool()
async def get_quote(symbol: str) -> dict:
    """获取股票实时行情"""
    return market_service.get_quote(symbol).to_dict()

@server.tool()
async def get_kline(symbol: str, period: str = "daily", count: int = 30) -> dict:
    """获取K线数据"""
    return market_service.get_kline(symbol, period, count).to_dict()
```

## 🔄 调用流程示例

### 场景：多轮行情查询

```
用户: "你好"
    │
    ▼
Router: 保存历史，判断为 chat 类型
    │ context = TaskContext(task_type="GREETING", query="你好")
    ▼
ChatSubAgent: 直接 LLM 回复
    │
    ▼
返回: "你好，我是FAgent..."

用户: "帮我看看茅台行情"
    │
    ▼
Router: 保存历史，判断为 market 类型
    │ context = TaskContext(
    │     task_type="GET_QUOTE", 
    │     params={"symbol": "600519"}
    │ )
    ▼
MarketSubAgent: 
    │ 1. 调用 MCP Tool: get_quote("600519")
    │ 2. 流式生成分析
    ▼
返回: "茅台当前1856元，涨幅1.2%..."

用户: "那平安银行呢"  ← 有指代词"那"
    │
    ▼
Router: 看完整历史，理解"那"= 查行情
    │ context = TaskContext(
    │     task_type="GET_QUOTE",
    │     params={"symbol": "000001"},
    │     context_summary="用户在对比股票"
    │ )
    ▼
MarketSubAgent: 只收到明确任务，不需要理解"那"
    │
    ▼
返回: "平安银行当前12.5元..."
```

## 📋 实施计划

### Phase 1: 基础架构 (当前)
- [ ] MainRouter 实现
- [ ] TaskContext 数据结构
- [ ] SubAgent 基类
- [ ] ChatSubAgent (兜底)
- [ ] 改造现有 MarketSubAgent

### Phase 2: MCP 集成
- [ ] Market MCP Server
- [ ] MCP Client 集成到 MarketSubAgent
- [ ] 工具定义和注册

### Phase 3: 优化迭代
- [ ] 意图识别优化（规则 + LLM 混合）
- [ ] 上下文提炼优化
- [ ] 更多 SubAgent (News, Trade...)

## 🚀 快速开始

### 1. 激活虚拟环境

```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r agents/requirements.txt
```

### 3. 启动服务

```bash
uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001
```

### 4. API 文档

访问：http://localhost:8001/docs

## 📖 相关文档

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [LangGraph](https://github.com/langchain-ai/langgraph) (设计参考)
