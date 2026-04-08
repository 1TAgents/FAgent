# FAgent Memory 系统开发计划

> 版本：v1.0  
> 创建日期：2026-04-08  
> 状态：准备实施

---

## 📋 开发原则

1. **顺序执行** - 完成一个功能再开始下一个
2. **测试驱动** - 每个功能完成后立即测试
3. **及时提交** - 测试通过后立即 commit
4. **文档同步** - 代码与文档同步更新

---

## 🛠️ CLI 工具开发（1.5 天）

### CLI-1: CLI 框架搭建（2 小时）
- [ ] 创建 `src/cli/` 目录结构
- [ ] 安装依赖：click, rich, prompt-toolkit
- [ ] 创建 `fagent_cli.py` 启动脚本
- [ ] 实现 `fagent --help` 和版本信息
- [ ] 测试：`fagent --version`

**测试命令**:
```bash
python fagent_cli.py --help
python fagent_cli.py --version
```

**Commit**: `feat(cli): 初始 CLI 框架`

---

### CLI-2: 会话管理命令（2 小时）
- [ ] `fagent session new` - 创建会话
- [ ] `fagent session list` - 列出会话
- [ ] `fagent session switch <cid>` - 切换会话
- [ ] `fagent session info` - 会话信息
- [ ] 测试：创建、列出、切换会话

**测试命令**:
```bash
fagent session new
fagent session list
fagent session switch session_20260408_001
fagent session info
```

**Commit**: `feat(cli): 会话管理命令`

---

### CLI-3: 消息操作命令（2 小时）
- [ ] `fagent message send "内容"` - 发送消息
- [ ] `fagent message list --limit 20` - 列出消息
- [ ] `fagent message show <mid>` - 显示详情
- [ ] `fagent message search "关键词"` - 搜索消息
- [ ] 测试：完整消息流

**测试命令**:
```bash
fagent message send "你好"
fagent message list --limit 10
fagent message show msg_abc123
fagent message search "贵州茅台"
```

**Commit**: `feat(cli): 消息操作命令`

---

### CLI-4: 记忆查询命令（2 小时）
- [ ] `fagent memory overview` - Level 1 概览
- [ ] `fagent memory messages` - Level 2 列表
- [ ] `fagent memory detail <mid>` - Level 3 详情
- [ ] `fagent memory tool <rid>` - Level 4 工具响应
- [ ] `fagent memory expand <sid>` - Level 5 展开摘要
- [ ] 测试：逐渐披露流程

**测试命令**:
```bash
fagent memory overview
fagent memory messages
fagent memory detail msg_001
fagent memory expand sum_123
```

**Commit**: `feat(cli): 记忆查询命令`

---

### CLI-5: 测试命令（2 小时）
- [ ] `fagent test message-flow` - 测试消息流
- [ ] `fagent test summary-generation` - 测试摘要
- [ ] `fagent test extraction` - 测试提取
- [ ] `fagent test all` - 运行所有测试
- [ ] 测试：自动化测试通过

**测试命令**:
```bash
fagent test all
```

**Commit**: `feat(cli): 测试命令`

---

### CLI-6: CLI 文档（1 小时）
- [ ] 创建 `docs/cli/README.md`
- [ ] 命令参考文档
- [ ] 使用示例
- [ ] 测试：文档完整性

**Commit**: `docs(cli): CLI 使用文档`

---

## 🧠 Phase 1: Message Memory 基础（3 天）

### Phase 1-1: ID 体系（4 小时）
- [ ] 创建 `src/memory/ids.py`
- [ ] 实现 `MemoryID` 数据类
- [ ] 实现 ID 生成：`new_message()`, `new_summary()`, `new_response()`
- [ ] 实现 ID 解析：`parse()`
- [ ] 单元测试：ID 生成与解析

**测试代码**:
```python
from src.memory.ids import MemoryID

# 测试生成
msg_id = MemoryID.new_message("session_001")
assert msg_id.cid == "session_001"
assert msg_id.mid.startswith("msg_")

# 测试解析
parsed = MemoryID.parse("session_001:msg_abc123")
assert parsed.cid == "session_001"
assert parsed.mid == "msg_abc123"
```

**Commit**: `feat(memory): ID 体系实现`

---

### Phase 1-2: 数据模型（4 小时）
- [ ] 创建 `src/memory/models/` 目录
- [ ] 实现 `RawMessage` 数据类
- [ ] 实现 `MessageSummary` 数据类
- [ ] 实现 `ToolResponse` 数据类
- [ ] 实现 `MemoryExtraction` 数据类
- [ ] 实现枚举：`Role`, `MessageStatus`, `ResponseStorage`
- [ ] 单元测试：数据模型序列化/反序列化

**测试代码**:
```python
from src.memory.models import RawMessage, Role

msg = RawMessage(
    cid="session_001",
    mid="msg_001",
    role=Role.USER,
    content="测试消息",
    timestamp=datetime.now().isoformat(),
    sequence_num=1
)
assert msg.content == "测试消息"
assert msg.role == Role.USER
```

**Commit**: `feat(memory): 数据模型实现`

---

### Phase 1-3: 数据库初始化（4 小时）
- [ ] 创建 `src/memory/storage/database.py`
- [ ] 实现 `MemoryDatabase` 类
- [ ] 创建表：`raw_messages`, `summaries`, `tool_responses`, `conversations`, `memory_extractions`
- [ ] 创建索引
- [ ] 单元测试：表创建与连接

**测试代码**:
```python
from src.memory.storage.database import MemoryDatabase

db = MemoryDatabase("fagent_memory")
# 检查表是否存在
tables = db.get_tables()
assert "raw_messages" in tables
assert "summaries" in tables
```

**Commit**: `feat(memory): 数据库初始化`

---

### Phase 1-4: 原始消息存储（4 小时）
- [ ] 实现 `db.save_message(msg)`
- [ ] 实现 `db.get_message(cid, mid)`
- [ ] 实现 `db.get_messages(cid, start, limit)`
- [ ] 实现 `db.delete_message(cid, mid)`
- [ ] 单元测试：CRUD 操作

**测试代码**:
```python
# 保存
db.save_message(msg)

# 检索
retrieved = db.get_message(msg.cid, msg.mid)
assert retrieved.content == msg.content

# 列表
messages = db.get_messages(msg.cid, limit=10)
assert len(messages) > 0
```

**Commit**: `feat(memory): 原始消息存储`

---

### Phase 1-5: 摘要存储（3 小时）
- [ ] 实现 `db.save_summary(summary)`
- [ ] 实现 `db.get_summary(sid)`
- [ ] 实现 `db.get_summaries_for_conversation(cid)`
- [ ] 实现 `db.get_messages_by_range(cid, start_mid, end_mid)`
- [ ] 单元测试：摘要 CRUD

**测试代码**:
```python
# 保存摘要
db.save_summary(summary)

# 检索
retrieved = db.get_summary(summary.sid)
assert retrieved.message_count == summary.message_count

# 获取会话摘要
summaries = db.get_summaries_for_conversation(cid)
assert len(summaries) > 0
```

**Commit**: `feat(memory): 摘要存储`

---

### Phase 1-6: 工具响应存储（3 小时）
- [ ] 实现 `db.save_tool_response(response)`
- [ ] 实现 `db.get_tool_response(rid)`
- [ ] 实现 `db.get_tool_response_by_call_id(tool_call_id)`
- [ ] 实现文件存储：大响应保存到文件
- [ ] 单元测试：工具响应 CRUD

**测试代码**:
```python
# 保存
db.save_tool_response(response)

# 检索
retrieved = db.get_tool_response(response.rid)
assert retrieved.tool_name == response.tool_name

# 懒加载
full_content = retrieved.get_full_content()
assert full_content is not None
```

**Commit**: `feat(memory): 工具响应存储`

---

## 📊 Phase 2: API 层（3 天）

### Phase 2-1: 逐渐披露 API-L1（2 小时）
- [ ] 实现 `api.get_conversation_overview(cid)`
- [ ] 格式化摘要列表
- [ ] 添加导航提示
- [ ] 单元测试：概览返回

**测试代码**:
```python
overview = memory.api.get_conversation_overview(cid)
assert "summaries" in overview
assert overview["cid"] == cid
```

**Commit**: `feat(memory): Level 1 概览 API`

---

### Phase 2-2: 逐渐披露 API-L2（2 小时）
- [ ] 实现 `api.get_conversation_messages(cid, start, limit)`
- [ ] 实现分页
- [ ] 标记摘要状态
- [ ] 单元测试：消息列表

**测试代码**:
```python
messages = memory.api.get_conversation_messages(cid, limit=20)
assert "messages" in messages
assert len(messages["messages"]) <= 20
```

**Commit**: `feat(memory): Level 2 消息列表 API`

---

### Phase 2-3: 逐渐披露 API-L3（2 小时）
- [ ] 实现 `api.get_message_detail(cid, mid)`
- [ ] 返回完整原始内容
- [ ] 添加相关摘要
- [ ] 单元测试：消息详情

**测试代码**:
```python
detail = memory.api.get_message_detail(cid, mid)
assert "message" in detail
assert detail["message"]["content"] == original_content
```

**Commit**: `feat(memory): Level 3 消息详情 API`

---

### Phase 2-4: 逐渐披露 API-L4（2 小时）
- [ ] 实现 `api.get_tool_response_detail(rid)`
- [ ] 实现懒加载完整内容
- [ ] 返回摘要 + 关键数据
- [ ] 单元测试：工具响应详情

**测试代码**:
```python
tool = memory.api.get_tool_response_detail(rid)
assert "full_content" in tool
assert tool["tool_name"] == expected_name
```

**Commit**: `feat(memory): Level 4 工具响应 API`

---

### Phase 2-5: 逐渐披露 API-L5（2 小时）
- [ ] 实现 `api.expand_summary(sid)`
- [ ] 获取覆盖的原始消息
- [ ] 返回摘要 + 原始消息列表
- [ ] 单元测试：摘要展开

**测试代码**:
```python
expanded = memory.api.expand_summary(sid)
assert "covered_messages" in expanded
assert len(expanded["covered_messages"]) == expected_count
```

**Commit**: `feat(memory): Level 5 摘要展开 API`

---

### Phase 2-6: 搜索 API（3 小时）
- [ ] 实现 `api.search_messages(cid, query, limit)`
- [ ] 关键词匹配
- [ ] 高亮显示
- [ ] 单元测试：搜索功能

**测试代码**:
```python
results = memory.api.search_messages(cid, "贵州茅台", limit=10)
assert "results" in results
assert len(results["results"]) > 0
```

**Commit**: `feat(memory): 搜索 API`

---

## 🎯 Phase 3: 提取器与三层记忆（4 天）

### Phase 3-1: 消息提取器（4 小时）
- [ ] 创建 `src/memory/extractors/message_extractor.py`
- [ ] 实现 `SingleMessageExtractor.extract()`
- [ ] 意图识别（LLM 调用）
- [ ] 实体提取
- [ ] 单元测试：消息提取

**Commit**: `feat(memory): 消息提取器`

---

### Phase 3-2: 批量提取器（3 小时）
- [ ] 创建 `src/memory/extractors/batch_extractor.py`
- [ ] 实现 `extract_from_conversation()`
- [ ] 实现 `extract_user_preferences()`
- [ ] 单元测试：批量提取

**Commit**: `feat(memory): 批量提取器`

---

### Phase 3-3: L1 瞬时记忆（3 小时）
- [ ] 创建 `src/memory/layers/immediate.py`
- [ ] 实现 `ImmediateMemory` 类
- [ ] 实现会话级存储
- [ ] 实现 `clear()`, `add_turn()`, `set_market_snapshot()`
- [ ] 单元测试：瞬时记忆

**Commit**: `feat(memory): L1 瞬时记忆`

---

### Phase 3-4: L2 工作记忆（4 小时）
- [ ] 创建 `src/memory/layers/working.py`
- [ ] 实现 `WorkingMemory` 类
- [ ] 实现任务管理：`create_task()`, `get_task()`, `update_task_status()`
- [ ] 实现决策链：`append_decision()`
- [ ] 实现待办队列：`add_todo()`
- [ ] 单元测试：工作记忆

**Commit**: `feat(memory): L2 工作记忆`

---

### Phase 3-5: L3 长期记忆 - 用户画像（3 小时）
- [ ] 创建 `src/memory/layers/longterm.py`
- [ ] 实现 `UserProfile` 模型
- [ ] 实现 `get_profile()`, `update_profile()`
- [ ] 单元测试：用户画像

**Commit**: `feat(memory): L3 用户画像`

---

### Phase 3-6: L3 长期记忆 - 交易记录（4 小时）
- [ ] 实现 `Trade` 模型
- [ ] 实现 `record_trade()`, `get_trades()`
- [ ] 实现 `search_similar_trades()`（向量检索）
- [ ] 单元测试：交易记录

**Commit**: `feat(memory): L3 交易记录`

---

### Phase 3-7: L3 长期记忆 - 策略与知识（4 小时）
- [ ] 实现 `Strategy` 模型
- [ ] 实现 `Knowledge` 模型
- [ ] 实现 `save_strategy()`, `add_knowledge()`
- [ ] 实现 `search_knowledge()`（向量检索）
- [ ] 单元测试：策略与知识

**Commit**: `feat(memory): L3 策略与知识`

---

## 📝 每日开发流程

```
早上:
1. 查看开发计划
2. 选择当日任务
3. 开始实施

每个任务:
1. 编写代码
2. 编写测试
3. 运行测试
4. 测试通过 → commit
5. 测试失败 → 修复 → 重新测试

晚上:
1. 更新开发进度
2. 记录问题与解决方案
3. 准备次日任务
```

---

## 📊 进度跟踪

| 日期 | 任务 | 状态 | 备注 |
|------|------|------|------|
| 2026-04-08 | CLI 工具开发 | ✅ 全部完成 | commit: 当前 |
| - CLI-1: CLI 框架 | ✅ 完成 | click + rich 框架 |
| - CLI-2: 会话管理 | ✅ 完成 | 5 个命令 |
| - CLI-3: 消息操作 | ✅ 完成 | 4 个命令 |
| - CLI-4: 记忆查询 | ✅ 完成 | 6 个命令 |
| - CLI-5: 测试命令 | ✅ 完成 | 5 个命令 |
| - CLI-6: CLI 文档 | ✅ 完成 | 完整指南 |

CLI 工具总结:
- 20 个 CLI 命令
- 5 个测试文件
- 1 个完整文档
- 所有测试通过 (14/14)

---

## 🐛 问题记录

### 问题 1
- **发现时间**: 
- **问题描述**: 
- **解决方案**: 
- **状态**: 待解决

---

**文档结束**
