# FAgent Memory API 文档

> 版本：v1.1
> 更新日期：2026-04-20
> 说明：本文档描述当前仓库里已经存在的 Memory API，而不是设计目标的全集。

## 一、核心对象

当前 Memory 相关代码主要分为两层：

- `MemoryManager`：负责会话、消息、摘要、工具响应的存储入口
- `MemoryAPI`：负责 L1-L5 的渐进式查询接口

示例初始化：

```python
from src.memory.manager import MemoryManager
from src.memory.api import MemoryAPI

memory = MemoryManager("fagent_memory")
api = MemoryAPI(memory)
```

说明：

- `MemoryManager` 当前是单例；同一 Python 进程里首次传入的 `data_dir` 会被复用
- `MemoryAPI` 不会自动挂到 `MemoryManager` 上，需要显式创建

## 二、MemoryManager

### 2.1 会话管理

```python
cid = memory.start_session("贵州茅台研究")
sessions = memory.list_sessions()
info = memory.get_session_info(cid)
ok = memory.switch_session(cid)
deleted = memory.delete_session(cid)
```

可用方法：

- `start_session(title: str | None = None) -> str`
- `list_sessions(status: str = "active") -> list[dict]`
- `switch_session(cid: str) -> bool`
- `get_session_info(cid: str | None = None) -> dict | None`
- `delete_session(cid: str) -> bool`

### 2.2 消息存储

```python
mid = memory.save_message(
    cid=cid,
    role="user",
    content="帮我看看贵州茅台"
)

message = memory.get_message(cid, mid)
messages = memory.get_messages(cid, start=0, limit=20)
```

可用方法：

- `save_message(cid, role, content, sequence_num=None, **kwargs) -> str`
- `get_message(cid, mid)`
- `get_messages(cid, start=0, limit=100)`

### 2.3 摘要与工具响应

```python
memory.save_summary(summary)
memory.get_summary(sid)
memory.get_summaries(cid)

memory.save_tool_response(response)
memory.get_tool_response(rid)
```

这部分依赖 `src/memory/models/summary.py` 和 `src/memory/models/tool_response.py` 中的数据类。

## 三、MemoryAPI

### 3.1 渐进式查询

```python
overview = api.get_conversation_overview(cid)
message_list = api.get_conversation_messages(cid, start=0, limit=20)
detail = api.get_message_detail(cid, mid)
tool_detail = api.get_tool_response_detail(rid)
expanded = api.expand_summary(sid)
```

已实现接口：

- `get_conversation_overview(cid)`
- `get_conversation_messages(cid, start=0, limit=50)`
- `get_message_detail(cid, mid)`
- `get_tool_response_detail(rid)`
- `expand_summary(sid)`
- `search_messages(cid, query, limit=20)`

### 3.2 返回结构说明

L1 概览：

```python
{
    "cid": "...",
    "type": "overview",
    "summaries": [...],
    "has_raw_messages": True,
    "expand_hint": "..."
}
```

L2 消息列表：

```python
{
    "cid": "...",
    "type": "messages",
    "messages": [
        {
            "mid": "...",
            "role": "user",
            "content_preview": "...",
            "has_summary": False,
            "expand_hint": "..."
        }
    ],
    "pagination": {
        "start": 0,
        "limit": 20,
        "has_more": False
    }
}
```

L3/L4/L5 会返回更完整的原始内容、工具响应或摘要覆盖消息。

## 四、独立 Layer 类

`MemoryManager` 目前还没有自动管理三层记忆，三层记忆是独立类：

- `src/memory/layers/immediate.py::ImmediateMemory`
- `src/memory/layers/working.py::WorkingMemory`
- `src/memory/layers/longterm.py::LongTermMemory`

这意味着：

- 可以单独使用这些类
- 但它们还没有被 Backend / Agents 自动接入
- CLI 也还没有完整封装它们

## 五、当前已实现 vs 未实现

### 已实现

- ID 体系
- 原始消息模型
- 摘要模型
- 工具响应模型
- SQLite 存储层
- L1-L5 查询 API
- 基础搜索
- Immediate / Working / LongTerm 三层基础类

### 尚未完成

- `MemoryManager` 自动暴露 `api` 属性
- 自动摘要生成
- 自动记忆提取与分层保存
- Context Builder
- LLM 主动调用 Memory 工具
- CLI 的完整 Memory 查询闭环

## 六、建议用法

如果你现在要在代码里接 Memory，推荐顺序是：

1. 用 `MemoryManager` 保存会话和消息
2. 用 `MemoryAPI` 做浏览、检索和展开
3. 单独实例化 `ImmediateMemory` / `WorkingMemory` / `LongTermMemory`
4. 不要假设设计文档中的所有接口都已经可调用
