# FAgent Memory 使用示例

> 更新日期：2026-04-20
> 说明：示例已改为匹配当前代码中的真实类名与方法。

## 示例 1：创建会话并保存消息

```python
from src.memory.manager import MemoryManager
from src.memory.api import MemoryAPI

memory = MemoryManager("fagent_memory")
api = MemoryAPI(memory)

cid = memory.start_session("贵州茅台研究")
mid = memory.save_message(
    cid=cid,
    role="user",
    content="帮我看看贵州茅台最近表现"
)

detail = api.get_message_detail(cid, mid)
print(detail["message"]["content"])
```

## 示例 2：读取消息列表

```python
from src.memory.manager import MemoryManager
from src.memory.api import MemoryAPI

memory = MemoryManager("fagent_memory")
api = MemoryAPI(memory)

cid = memory.current_cid
result = api.get_conversation_messages(cid, start=0, limit=10)

for msg in result["messages"]:
    print(msg["mid"], msg["role"], msg["content_preview"])
```

## 示例 3：保存摘要并展开

```python
from src.memory.ids import MemoryID
from src.memory.manager import MemoryManager
from src.memory.api import MemoryAPI
from src.memory.models.summary import MessageSummary

memory = MemoryManager("fagent_memory")
api = MemoryAPI(memory)

cid = memory.current_cid
messages = memory.get_messages(cid, limit=10)
first_mid = messages[0].mid
last_mid = messages[-1].mid

summary_id = MemoryID.new_summary(cid, last_mid)

summary = MessageSummary(
    sid=summary_id.sid,
    cid=cid,
    summary_type="window",
    covered_mids=[m.mid for m in messages],
    start_mid=first_mid,
    end_mid=last_mid,
    message_count=len(messages),
    summary="本轮会话主要在讨论贵州茅台的行情和估值。",
    key_points=["关注近 30 日表现", "希望补充趋势判断"],
    topics=["白酒", "估值", "趋势"]
)

memory.save_summary(summary)

overview = api.get_conversation_overview(cid)
expanded = api.expand_summary(summary.sid)

print(overview["summaries"])
print(expanded["message_count"])
```

## 示例 4：保存工具响应

```python
from src.memory.ids import MemoryID
from src.memory.manager import MemoryManager
from src.memory.api import MemoryAPI
from src.memory.models.tool_response import ToolResponse, ResponseStorage

memory = MemoryManager("fagent_memory")
api = MemoryAPI(memory)

cid = memory.current_cid
msg_mid = memory.save_message(cid=cid, role="tool", content="tool placeholder")

resp_id = MemoryID.new_response(cid, "market_data")

response = ToolResponse(
    rid=resp_id.rid,
    cid=cid,
    mid=msg_mid,
    tool_call_id="call_001",
    tool_name="market_data",
    tool_input='{"symbol":"600519"}',
    response_size=42,
    storage_type=ResponseStorage.INLINE,
    inline_content='{"close": 1688.0}',
    summary="返回了贵州茅台的最新收盘价",
    key_data={"symbol": "600519", "close": 1688.0}
)

memory.save_tool_response(response)

tool_detail = api.get_tool_response_detail(resp_id.rid)
print(tool_detail["summary"])
print(tool_detail["full_content"])
```

## 示例 5：使用 L1 瞬时记忆

```python
from src.memory.layers.immediate import ImmediateMemory

immediate = ImmediateMemory()
immediate.add_turn("user", "帮我分析一下茅台")
immediate.add_turn("assistant", "好的，我先获取行情数据")
immediate.set_market_snapshot(["600519"], {"close": 1688.0})

print(immediate.get_recent_turns())
print(immediate.to_dict())
```

## 示例 6：使用 L2 工作记忆

```python
from datetime import datetime, timedelta
from src.memory.layers.working import WorkingMemory, Task

working = WorkingMemory("fagent_memory/working/tasks.db")

task = Task(
    task_id="task_001",
    task_type="analysis",
    title="分析贵州茅台",
    context={"symbol": "600519"},
    status="active",
    decision_chain=[],
    todo_queue=[],
    created_at=datetime.now().isoformat(),
    expires_at=(datetime.now() + timedelta(hours=2)).isoformat()
)

working.create_task(task)
working.append_decision("task_001", {"step": "load_quote", "reason": "先看最新行情"})
working.add_todo("task_001", {"action": "load_kline", "done": False})

print(working.get_task("task_001"))
print(working.get_active_tasks())
```

## 示例 7：使用 L3 长期记忆

```python
from src.memory.layers.longterm import LongTermMemory

longterm = LongTermMemory("fagent_memory")

longterm.update_profile({
    "user_id": "default",
    "risk_tolerance": "medium",
    "preferred_holding_period": "long",
    "preferred_industries": ["白酒", "消费"]
})

longterm.record_trade({
    "trade_id": "trade_001",
    "symbol": "600519",
    "trade_type": "buy",
    "quantity": 100,
    "price": 1688.0,
    "amount": 168800.0,
    "executed_at": "2026-04-20T09:30:00",
    "reason": "估值回落后分批买入"
})

print(longterm.get_profile())
print(longterm.get_trades("600519"))
```

## 当前注意事项

- `MemoryManager` 当前不会自动创建 `MemoryAPI`
- `MemoryManager` 也不会自动挂三层记忆对象
- CLI 里和 Memory 相关的命令还没有全部与这些接口打通
