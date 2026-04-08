# FAgent Memory 使用示例

> 版本：v1.0

---

## 示例 1：保存和检索消息

```python
from src.memory import FAgentMemory
from datetime import datetime

# 初始化
memory = FAgentMemory("fagent_memory")

# 开始新会话
cid = memory.start_session()
print(f"会话 ID: {cid}")

# 保存用户消息
msg_mid = memory.save_message(
    cid=cid,
    role="user",
    content="帮我分析贵州茅台的投资价值"
)

# 保存助手回复
memory.save_message(
    cid=cid,
    role="assistant",
    content="好的，正在获取贵州茅台 (600519) 的行情数据..."
)

# 检索消息
msg = memory.get_message(cid, msg_mid)
print(f"消息内容：{msg.content}")

# 获取会话所有消息
messages = memory.get_messages(cid, limit=50)
print(f"会话共有 {len(messages)} 条消息")

# 结束会话
memory.end_session(cid)
```

---

## 示例 2：逐渐披露查询

```python
from src.memory import FAgentMemory

memory = FAgentMemory("fagent_memory")
cid = "session_20260408_001"

# === Level 1: 概览 ===
overview = memory.api.get_conversation_overview(cid)
print(f"会话 {cid} 有 {len(overview['summaries'])} 个摘要")
for summary in overview['summaries']:
    print(f"  - {summary['sid']}: {summary['summary'][:50]}...")

# === Level 2: 消息列表 ===
messages = memory.api.get_conversation_messages(cid, limit=10)
for msg in messages['messages']:
    print(f"{msg['mid']}: {msg['content_preview'][:50]}...")

# === Level 3: 单条详情 ===
detail = memory.api.get_message_detail(cid, "msg_abc123")
print(f"完整内容:\n{detail['message']['content']}")

# === Level 4: 工具响应 ===
tool = memory.api.get_tool_response_detail("resp_xyz789")
print(f"工具：{tool['tool_name']}")
print(f"摘要：{tool['summary']}")
print(f"完整数据：{tool['full_content'][:500]}...")

# === Level 5: 展开摘要 ===
expanded = memory.api.expand_summary("sum_def456")
print(f"摘要覆盖 {expanded['message_count']} 条消息:")
for msg in expanded['covered_messages']:
    print(f"  - {msg['mid']}: {msg['content'][:100]}...")
```

---

## 示例 3：任务管理

```python
from src.memory import FAgentMemory
from datetime import datetime, timedelta

memory = FAgentMemory("fagent_memory")
cid = memory.start_session()

# 创建分析任务
task_id = memory.working.create_task(
    task_type="analysis",
    title="分析贵州茅台投资价值",
    context={"symbol": "600519", "user_request": "分析投资价值"}
)
print(f"任务 ID: {task_id}")

# 追加决策记录
memory.working.append_decision(task_id, {
    "timestamp": datetime.now().isoformat(),
    "decision": "获取近 3 年财报数据",
    "reason": "用户需要了解基本面"
})

memory.working.append_decision(task_id, {
    "timestamp": datetime.now().isoformat(),
    "decision": "分析 PE/PB 估值",
    "reason": "对比历史估值和同行"
})

# 添加待办
memory.working.add_todo(task_id, {
    "action": "fetch_market_data",
    "done": False
})
memory.working.add_todo(task_id, {
    "action": "analyze_financials",
    "done": False
})
memory.working.add_todo(task_id, {
    "action": "generate_report",
    "done": False
})

# 获取活跃任务
tasks = memory.working.get_active_tasks()
for task in tasks:
    print(f"任务：{task.title}")
    print(f"  待办：{len([t for t in task.todo_queue if not t['done']])} 项")
    print(f"  决策记录：{len(task.decision_chain)} 条")

# 完成任务
memory.working.update_task_status(task_id, "completed", result={
    "report_path": "reports/600519_analysis_20260408.md",
    "recommendation": "买入"
})
```

---

## 示例 4：长期记忆 - 用户画像

```python
from src.memory import FAgentMemory
from src.memory.models.profile import UserProfile, RiskLevel

memory = FAgentMemory("fagent_memory")

# 获取用户画像
profile = memory.longterm.get_profile()
if not profile:
    # 创建新画像
    profile = UserProfile(
        user_id="default",
        risk_tolerance=RiskLevel.MEDIUM,
        preferred_holding_period="long",
        max_position_ratio=0.3,
        stop_loss_ratio=0.05,
        take_profit_ratio=0.2
    )

# 更新画像（从对话中提取偏好）
profile.risk_tolerance = RiskLevel.MEDIUM
profile.preferred_holding_period = "long"
profile.stop_loss_ratio = 0.10
profile.preferred_industries = ["白酒", "消费", "金融"]

memory.longterm.update_profile(profile)

# 再次获取
profile = memory.longterm.get_profile()
print(f"风险承受：{profile.risk_tolerance.value}")
print(f"持仓周期：{profile.preferred_holding_period}")
print(f"止损比例：{profile.stop_loss_ratio*100:.0f}%")
print(f"偏好行业：{', '.join(profile.preferred_industries)}")
```

---

## 示例 5：长期记忆 - 交易记录

```python
from src.memory import FAgentMemory
from src.memory.models.trade import Trade, TradeType
from datetime import datetime

memory = FAgentMemory("fagent_memory")

# 记录交易
trade = Trade(
    trade_id="trade_20260408_001",
    symbol="600519",
    trade_type=TradeType.BUY,
    quantity=100,
    price=1800.0,
    amount=180000.0,
    executed_at=datetime.now().isoformat(),
    reason="基于价值分析买入，PE 处于历史低位",
    strategy_id="strategy_value_001"
)
memory.longterm.record_trade(trade)

# 查询交易历史
trades = memory.longterm.get_trades("600519", limit=10)
for t in trades:
    print(f"{t.executed_at[:10]} {t.trade_type.value} {t.quantity}股 @¥{t.price}")

# 语义检索相似交易
similar = memory.longterm.search_similar_trades("白酒股票买入", limit=5)
print(f"找到 {len(similar)} 笔相似交易")
for t in similar:
    print(f"  - {t.symbol}: {t.reason[:50]}...")
```

---

## 示例 6：工具响应处理

```python
from src.memory import FAgentMemory

memory = FAgentMemory("fagent_memory")
cid = memory.start_session()

# 模拟工具响应（大量数据）
market_data = """
贵州茅台 (600519) 行情数据
========================
当前价：1800.00 元
涨跌幅：+2.30%
成交量：1234567 股
成交额：2222222222 元
... (共 10000+ 字)
"""

# 处理响应（自动分级存储）
processed = memory.tool_handler.process("market_data", market_data)
print(f"响应大小：{processed.original_size} 字")
print(f"存储类型：{processed.size_category.value}")
print(f"摘要：{processed.summary[:100]}...")

# 保存工具响应
rid = memory.save_tool_response(
    cid=cid,
    mid="msg_current",
    tool_call_id="call_123",
    tool_name="market_data",
    tool_input='{"symbol": "600519"}',
    response=processed
)

# 懒加载完整内容
tool_detail = memory.api.get_tool_response_detail(rid)
full_content = tool_detail["full_content"]
print(f"完整内容前 500 字：{full_content[:500]}...")

# 在工具响应中搜索
results = memory.search_tool_response(rid, "涨跌幅")
print(f"找到 {len(results)} 条匹配")
```

---

## 示例 7：摘要生成

```python
from src.memory import FAgentMemory

memory = FAgentMemory("fagent_memory")
cid = memory.start_session()

# 保存一些消息
for i in range(15):
    memory.save_message(
        cid=cid,
        role="user" if i % 2 == 0 else "assistant",
        content=f"消息内容 {i}"
    )

# 生成摘要（每 10 条消息）
messages = memory.get_messages(cid, limit=10)
summary = memory.summarizer.summarize_window(messages, cid=cid)

# 保存摘要
memory.save_summary(summary)
print(f"摘要 ID: {summary.sid}")
print(f"覆盖消息：{summary.message_count} 条")
print(f"摘要内容：{summary.summary[:100]}...")

# 展开摘要
expanded = memory.api.expand_summary(summary.sid)
print(f"展开后看到 {expanded['message_count']} 条原始消息")
```

---

## 示例 8：LLM 上下文构建

```python
from src.memory import FAgentMemory
from src.memory.context_builder import ContextBudget

memory = FAgentMemory("fagent_memory")
cid = memory.start_session()

# ... 保存一些消息 ...

# 自定义上下文预算
budget = ContextBudget(
    max_tokens=4000,
    reserved_tokens=1000,
    recent_messages_ratio=0.40,
    summaries_ratio=0.30,
    memory_ratio=0.20,
    task_ratio=0.10,
    auto_adjust=True
)

# 构建上下文
components = memory.context_builder.build_context(
    cid=cid,
    current_message_mid="msg_current",
    override_budget=budget
)

# 格式化为 LLM 输入
context_text = memory.context_builder.format_for_llm(components)

# 构建完整 prompt
prompt = f"""{context_text}

[用户问题]
帮我分析下现在能不能买入贵州茅台

请基于以上信息给出分析和建议。
"""

# 发送给 LLM
response = llm.generate(prompt)
print(response)
```

---

## 示例 9：搜索

```python
from src.memory import FAgentMemory

memory = FAgentMemory("fagent_memory")
cid = "session_20260408_001"

# 会话内关键词搜索
results = memory.api.search_messages(cid, "贵州茅台", limit=10)
print(f"找到 {results['total_found']} 条相关消息")
for r in results['results']:
    print(f"  {r['mid']}: {r['content']}")

# 跨会话搜索
results = memory.api.search_all_sessions("买入建议", limit=20)
print(f"跨会话找到 {len(results)} 条")

# 语义搜索（向量）
results = memory.api.semantic_search("白酒股票估值分析", limit=10)
print(f"语义搜索找到 {len(results)} 条相关知识")
```

---

## 示例 10：完整工作流

```python
from src.memory import FAgentMemory
from src.memory.models.trade import Trade, TradeType
from datetime import datetime

# === 初始化 ===
memory = FAgentMemory("fagent_memory")
cid = memory.start_session()

# === 用户询问 ===
memory.save_message(
    cid=cid,
    role="user",
    content="贵州茅台现在能买吗？我通常只做长线投资"
)

# === 提取记忆 ===
extraction = memory.extractor.extract("贵州茅台现在能买吗？我通常只做长线投资")
memory.save_extraction(extraction)

# 更新用户画像
if extraction.preferences:
    profile = memory.longterm.get_profile()
    profile.preferred_holding_period = "long"
    memory.longterm.update_profile(profile)

# === 创建任务 ===
task_id = memory.working.create_task(
    task_type="analysis",
    title="分析贵州茅台买入时机",
    context={"symbol": "600519"}
)

# === 调用工具 ===
market_data = get_market_data("600519")
processed = memory.tool_handler.process("market_data", market_data)
memory.save_tool_response(cid, "msg_002", "call_001", "market_data", processed)

# === 记录决策 ===
memory.working.append_decision(task_id, {
    "timestamp": datetime.now().isoformat(),
    "decision": "建议买入",
    "reason": "PE 处于历史低位，业绩稳定增长"
})

# === 构建 LLM 上下文 ===
components = memory.context_builder.build_context(cid, "msg_002")
context_text = memory.context_builder.format_for_llm(components)

# === 生成回复 ===
prompt = f"""{context_text}

[用户问题]
贵州茅台现在能买吗？

请给出分析和建议。
"""
response = llm.generate(prompt)

# === 保存回复 ===
memory.save_message(
    cid=cid,
    role="assistant",
    content=response
)

# === 用户执行交易 ===
memory.save_message(
    cid=cid,
    role="user",
    content="好的，买入 100 股"
)

# === 记录交易 ===
trade = Trade(
    trade_id=f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    symbol="600519",
    trade_type=TradeType.BUY,
    quantity=100,
    price=1800.0,
    amount=180000.0,
    executed_at=datetime.now().isoformat(),
    reason="基于 FAgent 分析建议"
)
memory.longterm.record_trade(trade)

# === 记录合规日志 ===
from src.memory.models.compliance import ComplianceLog
log = ComplianceLog(
    log_id=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    decision_type="trade",
    symbol="600519",
    decision="BUY",
    reasoning="PE 处于历史低位",
    risks_disclosed=["市场波动风险", "行业政策风险"],
    timestamp=datetime.now().isoformat()
)
memory.longterm.log_decision(log)

# === 完成任务 ===
memory.working.update_task_status(task_id, "completed", result={
    "action": "executed_trade",
    "trade_id": trade.trade_id
})

# === 结束会话 ===
memory.end_session(cid)

print("完整工作流完成!")
```

---

**示例文档结束**
