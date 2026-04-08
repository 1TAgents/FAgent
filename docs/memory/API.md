# FAgent Memory API 文档

> 版本：v1.0  
> 对应设计文档：DESIGN.md

---

## 一、快速开始

```python
from src.memory import FAgentMemory

# 初始化
memory = FAgentMemory("fagent_memory")

# 开始新会话
cid = memory.start_session()

# 保存消息
memory.save_message(role="user", content="帮我分析贵州茅台")

# 构建 LLM 上下文
context = memory.build_context(cid)

# 查询
messages = memory.api.get_conversation_messages(cid)
detail = memory.api.get_message_detail(cid, "msg_abc123")
```

---

## 二、核心 API

### 2.1 会话管理

```python
# 开始新会话
cid = memory.start_session()
# 返回：session_20260408_001

# 结束会话
memory.end_session(cid)

# 获取会话列表
sessions = memory.list_sessions(status="active")
# 返回：[{"cid": "...", "created_at": "...", "message_count": 10}, ...]

# 获取会话详情
info = memory.get_session_info(cid)
# 返回：{"cid": "...", "title": "...", "message_count": 10, ...}
```

### 2.2 消息操作

```python
# 保存消息
mid = memory.save_message(
    cid=cid,
    role="user",
    content="帮我分析贵州茅台",
    metadata={"source": "feishu"}
)
# 返回：msg_abc123

# 获取单条消息
msg = memory.get_message(cid, mid)
# 返回：RawMessage 对象

# 获取消息列表（分页）
messages = memory.get_messages(cid, start=0, limit=50)
# 返回：[RawMessage, ...]

# 删除消息（软删除）
memory.delete_message(cid, mid)
```

### 2.3 逐渐披露 API

```python
# Level 1: 会话概览
overview = memory.api.get_conversation_overview(cid)

# Level 2: 消息列表
messages = memory.api.get_conversation_messages(cid, limit=20)

# Level 3: 单条详情
detail = memory.api.get_message_detail(cid, "msg_abc123")

# Level 4: 工具响应
tool = memory.api.get_tool_response_detail("resp_xyz789")

# Level 5: 展开摘要
expanded = memory.api.expand_summary("sum_def456")
```

### 2.4 搜索

```python
# 会话内搜索
results = memory.api.search_messages(cid, "贵州茅台", limit=10)

# 跨会话搜索
results = memory.api.search_all_sessions("买入建议", limit=20)

# 语义搜索（向量）
results = memory.api.semantic_search("白酒股票分析", limit=10)
```

---

## 三、记忆层 API

### 3.1 L1 瞬时记忆

```python
# 获取当前会话的瞬时记忆
immediate = memory.immediate.get()

# 添加对话轮次
memory.immediate.add_turn("user", "帮我分析茅台")

# 设置行情快照
memory.immediate.set_market_snapshot({"600519": {...}})

# 清空（会话结束时）
memory.immediate.clear()
```

### 3.2 L2 工作记忆

```python
# 创建任务
task_id = memory.working.create_task(
    task_type="analysis",
    title="分析贵州茅台",
    context={"symbol": "600519"}
)

# 获取活跃任务
tasks = memory.working.get_active_tasks()

# 追加决策记录
memory.working.append_decision(task_id, {
    "type": "analysis",
    "content": "PE 处于历史低位"
})

# 更新任务状态
memory.working.update_task_status(task_id, "completed", result={...})

# 获取任务详情
task = memory.working.get_task(task_id)
```

### 3.3 L3 长期记忆

```python
# === 用户画像 ===
profile = memory.longterm.get_profile()
memory.longterm.update_profile({
    "risk_tolerance": "medium",
    "stop_loss_ratio": 0.05
})

# === 交易记录 ===
memory.longterm.record_trade(Trade(...))
trades = memory.longterm.get_trades("600519", limit=10)
similar = memory.longterm.search_similar_trades("白酒买入", limit=5)

# === 策略管理 ===
memory.longterm.save_strategy(Strategy(...))
strategies = memory.longterm.list_strategies()
strategy = memory.longterm.get_strategy("strategy_001")

# === 知识库 ===
memory.longterm.add_knowledge(Knowledge(...))
knowledge = memory.longterm.search_knowledge("PE 估值", limit=5)

# === 合规日志 ===
memory.longterm.log_decision(ComplianceLog(...))
logs = memory.longterm.get_compliance_logs("600519", limit=10)
```

---

## 四、上下文构建

```python
from src.memory.context_builder import ContextBudget

# 自定义预算
budget = ContextBudget(
    max_tokens=4000,
    recent_messages_ratio=0.40,
    summaries_ratio=0.30,
    memory_ratio=0.20,
    task_ratio=0.10
)

# 构建上下文
components = memory.context_builder.build_context(
    cid=cid,
    current_message_mid="msg_current",
    override_budget=budget
)

# 格式化为 LLM 输入
context_text = memory.context_builder.format_for_llm(components)

# 完整流程
prompt = f"""{context_text}

[用户问题]
{user_message}

请基于以上信息回答。
"""
```

---

## 五、工具响应处理

```python
# 处理工具响应
processed = memory.tool_handler.process(
    tool_name="market_data",
    response=large_response_text
)

# 保存工具响应
rid = memory.save_tool_response(
    cid=cid,
    mid=msg_mid,
    tool_call_id="call_123",
    tool_name="market_data",
    tool_input='{"symbol": "600519"}',
    response=processed
)

# 懒加载完整内容
full_content = memory.api.get_tool_response_detail(rid)["full_content"]

# 搜索工具响应内容
results = memory.search_tool_response(rid, "涨跌幅")
```

---

## 六、摘要管理

```python
# 手动生成摘要
summary = memory.summarizer.summarize_window(
    messages=messages[-10:],
    cid=cid
)

# 保存摘要
memory.save_summary(summary)

# 获取会话的所有摘要
summaries = memory.get_summaries(cid)

# 展开摘要查看原始消息
expanded = memory.api.expand_summary(summary.sid)

# 生成层级摘要（长会话）
global_summary = memory.summarizer.get_hierarchical_summary(
    all_messages=messages
)
```

---

## 七、记忆提取

```python
# 单条消息提取
extraction = memory.extractor.extract(message_text)
# 返回：ExtractedMemory 对象

# 批量提取
extractions = memory.batch_extractor.extract_from_conversation(
    messages=conversation_history,
    window_size=10
)

# 提取用户偏好
preferences = memory.batch_extractor.extract_user_preferences(
    all_messages=full_history
)

# 保存提取结果
memory.save_extraction(extraction)
```

---

## 八、ID 体系

### 8.1 生成 ID

```python
from src.memory.ids import MemoryID

# 生成消息 ID
msg_id = MemoryID.new_message(cid="session_001")
# 返回：MemoryID(cid="session_001", mid="msg_abc123", ...)

# 生成摘要 ID
sum_id = MemoryID.new_summary(cid="session_001", mid="msg_abc123")

# 生成工具响应 ID
resp_id = MemoryID.new_response(cid="session_001", tool_name="market_data")
```

### 8.2 解析 ID

```python
# 解析 ID 字符串
id_obj = MemoryID.parse("session_001:msg_abc123:sum_def456")
# 返回：MemoryID(cid="session_001", mid="msg_abc123", sid="sum_def456")

# 格式化
id_str = str(id_obj)
# 返回："session_001:msg_abc123:sum_def456"
```

---

## 九、错误处理

```python
from src.memory.exceptions import (
    MessageNotFoundError,
    SummaryNotFoundError,
    SessionNotFoundError,
    BudgetExceededError
)

try:
    msg = memory.get_message(cid, "invalid_mid")
except MessageNotFoundError as e:
    print(f"消息不存在：{e}")

try:
    context = memory.build_context(cid, mid, override_budget=tiny_budget)
except BudgetExceededError as e:
    print(f"上下文超出预算：{e}")
```

---

## 十、配置

```yaml
# fagent_memory/config.yaml
memory:
  budget:
    max_tokens: 4000
    reserved_tokens: 1000
    auto_adjust: true
  
  summarization:
    window_size: 10
    trigger: "hybrid"
    periodic_interval: 10
  
  extraction:
    enabled: true
    auto_save_longterm: true
    confidence_threshold: 0.7
  
  storage:
    tool_response:
      small_threshold: 500
      medium_threshold: 2000
      large_threshold: 10000
```

---

**API 文档结束**
