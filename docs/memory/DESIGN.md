# FAgent Memory 系统设计文档

> 版本：v1.2
> 创建日期：2026-04-08
> 更新日期：2026-04-20
> 状态：设计基线；核心存储、查询 API 与 layer 原型已实现，自动提取与 LLM 集成仍在继续
>
> 说明：本文件保留目标设计、关键决策与边界说明。判断当前代码已经落地到什么程度，请同时参考 `API.md` 和 `DEVELOPMENT_PLAN.md`。

---

## 一、设计目标

为 FAgent 构建一个**可追溯、分层披露、高效检索、自我进化**的记忆系统，支持：

- ✅ 用户交易偏好和习惯的长期记忆
- ✅ 会话上下文的短期记忆
- ✅ 交易决策的可追溯记录
- ✅ 策略和知识的持久化存储
- ✅ 高效的记忆检索和关联
- ✅ **原始数据完整保存，可精确召回**
- ✅ **摘要与原始数据双向链接**
- ✅ **逐渐披露的查询模式**
- ✅ **LLM 主动调用 Memory 工具**（动态扩展上下文）
- ✅ **经验自动提取与复用**（Agent 自我进化）

---

## 二、核心设计原则

### 2.1 原始数据永不丢失

```
┌─────────────────────────────────────────────────────────────────────┐
│                        数据保存原则                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  所有用户消息、助手回复、工具响应必须完整存储，永不修改，永不丢失    │
│                                                                     │
│  摘要是索引层，不是替代层 —— 摘要可以省略细节，但必须能追溯到原始数据 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 双向链接

```
摘要 (Summary)
    ↓ covered_mids (向下钻取)
原始消息列表 (RawMessages)
    ↓ summary_id (向上定位)
所属摘要 (Summary)
```

### 2.3 逐渐披露 (Progressive Disclosure)

类似技能文档的"概览 → 详情 → 源码"模式：

```
Level 1: 会话概览 (摘要列表)
    ↓ 展开
Level 2: 消息列表 (分页，带摘要标记)
    ↓ 查看详情
Level 3: 单条消息 (完整原始内容)
    ↓ 加载工具响应
Level 4: 工具响应详情 (摘要 + 懒加载完整数据)
```

### 2.4 精确寻址

通过 `cid:mid:sid:rid` ID 体系精确定位任意数据：

| ID 类型 | 格式 | 示例 | 用途 |
|---------|------|------|------|
| cid | `session_YYYYMMDD_HHMMSS` | `session_20260408_001` | 会话 ID |
| mid | `msg_xxx` / `tool_xxx` | `msg_abc123` | 消息 ID |
| sid | `sum_xxx` | `sum_def456` | 摘要 ID |
| rid | `resp_xxx` | `resp_xyz789` | 工具响应 ID |

---

## 三、数据模型

### 3.1 原始消息 (RawMessage)

```python
@dataclass
class RawMessage:
    """原始消息 - 完整存储，永不修改"""
    
    # === 标识 ===
    cid: str                    # 会话 ID
    mid: str                    # 消息 ID
    parent_mid: Optional[str]   # 父消息 ID（回复链）
    
    # === 内容 ===
    role: Role                  # user/assistant/system/tool
    content: str                # 原始内容（完整，不截断）
    content_hash: str           # 内容哈希（用于去重）
    
    # === 元数据 ===
    timestamp: str              # ISO 时间戳
    sequence_num: int           # 会话内序号
    
    # === 工具相关 ===
    tool_name: Optional[str]    # 工具名称（如果是工具调用/响应）
    tool_call_id: Optional[str] # 工具调用 ID
    tool_response_size: Optional[int]  # 工具响应大小
    
    # === 附件 ===
    attachments: list[dict]     # 文件、图片等
    metadata: dict              # 额外元数据
    
    # === 状态 ===
    status: MessageStatus       # raw/extracted/summarized/archived
    created_at: str
    updated_at: str
```

**存储策略**: 全部存储到 SQLite `raw_messages` 表

---

### 3.2 消息摘要 (MessageSummary)

```python
@dataclass
class MessageSummary:
    """消息摘要 - 指向原始数据"""
    
    # === 标识 ===
    sid: str                    # 摘要 ID
    cid: str                    # 所属会话
    summary_type: str           # single/window/hierarchical
    
    # === 覆盖范围（关键：链接原始消息）===
    covered_mids: list[str]     # 覆盖的原始消息 ID 列表
    start_mid: str              # 起始消息 ID
    end_mid: str                # 结束消息 ID
    message_count: int          # 覆盖的消息数量
    
    # === 摘要内容 ===
    summary: str                # 摘要文本
    key_points: list[str]       # 关键点列表
    entities: dict              # 提取的实体（股票、数字等）
    topics: list[str]           # 话题标签
    
    # === 链接 ===
    parent_summary_id: Optional[str]  # 父摘要（层级摘要）
    child_summary_ids: list[str]      # 子摘要
    
    # === 导航 ===
    can_expand: bool = True     # 是否可以展开查看原始消息
    expansion_hint: str = ""    # 如何展开（查询提示）
    
    # === 元数据 ===
    created_at: str
    created_by: str             # auto/user/manual
```

**存储策略**: SQLite `summaries` 表

---

### 3.3 工具响应 (ToolResponse)

```python
@dataclass
class ToolResponse:
    """工具响应 - 分级存储"""
    
    # === 标识 ===
    rid: str                    # 响应 ID
    cid: str                    # 会话 ID
    mid: str                    # 关联的消息 ID
    tool_call_id: str           # 工具调用 ID
    
    # === 工具信息 ===
    tool_name: str              # 工具名称
    tool_input: str             # 工具输入参数
    
    # === 响应内容 ===
    response_size: int          # 原始响应大小（字节）
    storage_type: ResponseStorage  # inline/file/indexed
    
    # === 存储位置 ===
    inline_content: Optional[str]   # 内联内容（小响应）
    file_path: Optional[str]        # 文件路径（中/大响应）
    index_data: Optional[dict]      # 索引数据（大响应）
    
    # === 摘要（必有）===
    summary: str                # 响应摘要（用于快速浏览）
    key_data: dict              # 关键数据（结构化提取）
    
    # === 导航 ===
    can_load_full: bool = True  # 是否可以加载完整内容
    load_hint: str = ""         # 如何加载
    
    # === 元数据 ===
    created_at: str
    execution_time_ms: Optional[int]
```

**存储策略**:

| 响应大小 | 存储方式 |
|----------|----------|
| < 500 字 | 内联存储到数据库 |
| 500-2000 字 | 存文件，数据库存路径 + 摘要 |
| > 2000 字 | 存文件 + 索引，数据库存索引 + 摘要 |

---

### 3.4 记忆提取记录 (MemoryExtraction)

```python
@dataclass
class MemoryExtraction:
    """从消息中提取的记忆"""
    
    extraction_id: str
    cid: str
    mid: str
    
    # === 提取内容 ===
    intent_type: str            # query/analysis/trade/review/preference
    confidence: float           # 置信度 0-1
    extracted_data: dict        # 提取的结构化数据
    
    # === 保存位置标记 ===
    saved_to_immediate: bool    # 是否保存到 L1
    saved_to_working: bool      # 是否保存到 L2
    saved_to_longterm: bool     # 是否保存到 L3
    
    created_at: str
```

---

## 四、数据库设计

### 4.1 表结构

```sql
-- 原始消息表
CREATE TABLE raw_messages (
    cid TEXT NOT NULL,
    mid TEXT NOT NULL,
    parent_mid TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sequence_num INTEGER NOT NULL,
    tool_name TEXT,
    tool_call_id TEXT,
    tool_response_size INTEGER,
    attachments TEXT,  -- JSON
    metadata TEXT,  -- JSON
    status TEXT NOT NULL DEFAULT 'raw',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (cid, mid)
);

-- 索引
CREATE INDEX idx_messages_cid ON raw_messages(cid);
CREATE INDEX idx_messages_hash ON raw_messages(content_hash);
CREATE INDEX idx_messages_seq ON raw_messages(cid, sequence_num);

-- 摘要表
CREATE TABLE summaries (
    sid TEXT PRIMARY KEY,
    cid TEXT NOT NULL,
    summary_type TEXT NOT NULL,
    covered_mids TEXT NOT NULL,  -- JSON
    start_mid TEXT NOT NULL,
    end_mid TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    summary TEXT NOT NULL,
    key_points TEXT,  -- JSON
    entities TEXT,  -- JSON
    topics TEXT,  -- JSON
    parent_summary_id TEXT,
    child_summary_ids TEXT,  -- JSON
    can_expand INTEGER DEFAULT 1,
    expansion_hint TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'auto'
);

-- 工具响应表
CREATE TABLE tool_responses (
    rid TEXT PRIMARY KEY,
    cid TEXT NOT NULL,
    mid TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input TEXT NOT NULL,
    response_size INTEGER NOT NULL,
    storage_type TEXT NOT NULL,
    inline_content TEXT,
    file_path TEXT,
    index_data TEXT,  -- JSON
    summary TEXT NOT NULL,
    key_data TEXT,  -- JSON
    can_load_full INTEGER DEFAULT 1,
    load_hint TEXT,
    created_at TEXT NOT NULL,
    execution_time_ms INTEGER
);

-- 会话元数据表
CREATE TABLE conversations (
    cid TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_message_mid TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    metadata TEXT  -- JSON
);

-- 记忆提取记录表
CREATE TABLE memory_extractions (
    extraction_id TEXT PRIMARY KEY,
    cid TEXT NOT NULL,
    mid TEXT NOT NULL,
    intent_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    extracted_data TEXT,  -- JSON
    saved_to_immediate INTEGER DEFAULT 0,
    saved_to_working INTEGER DEFAULT 0,
    saved_to_longterm INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
```

---

## 五、API 设计

### 5.1 逐渐披露 API

#### Level 1: 会话概览

```python
def get_conversation_overview(cid: str) -> dict:
    """
    获取会话概览（只看摘要列表）
    
    返回:
    {
        "cid": "session_001",
        "type": "overview",
        "summaries": [
            {
                "sid": "sum_123",
                "message_count": 10,
                "summary": "用户询问了贵州茅台...",
                "can_expand": true,
                "expansion_hint": "使用 expand_summary(sid='sum_123')"
            }
        ],
        "has_raw_messages": true,
        "expand_hint": "使用 get_conversation_messages(cid='session_001')"
    }
    """
```

#### Level 2: 消息列表

```python
def get_conversation_messages(
    cid: str,
    start: int = 0,
    limit: int = 50
) -> dict:
    """
    获取消息列表（分页，带摘要标记）
    
    返回:
    {
        "cid": "session_001",
        "type": "messages",
        "messages": [
            {
                "mid": "msg_001",
                "role": "user",
                "content_preview": "帮我分析贵州茅台...",
                "timestamp": "2026-04-08T10:00:00",
                "has_summary": true,
                "is_tool_response": false,
                "expand_hint": "使用 get_message_detail(cid='session_001', mid='msg_001')"
            }
        ],
        "pagination": {
            "start": 0,
            "limit": 50,
            "has_more": true
        }
    }
    """
```

#### Level 3: 单条消息详情

```python
def get_message_detail(cid: str, mid: str) -> dict:
    """
    获取单条消息完整详情（完整原始内容）
    
    返回:
    {
        "cid": "session_001",
        "mid": "msg_001",
        "type": "message_detail",
        "message": {
            "role": "user",
            "content": "完整原始内容...",  # 完整！
            "timestamp": "2026-04-08T10:00:00",
            "sequence_num": 1,
            "attachments": [],
            "metadata": {}
        },
        "related_summaries": [...],
        "can_expand": false,
        "navigate_up_hint": "使用 get_conversation_messages() 返回列表"
    }
    """
```

#### Level 4: 工具响应详情

```python
def get_tool_response_detail(rid: str) -> dict:
    """
    获取工具响应详情（支持懒加载完整内容）
    
    返回:
    {
        "rid": "resp_123",
        "cid": "session_001",
        "mid": "msg_002",
        "type": "tool_response_detail",
        "tool_name": "market_data",
        "tool_input": "{\"symbol\": \"600519\"}",
        "summary": "贵州茅台当前价 1800 元...",
        "key_data": {"price": 1800, "change": 0.023},
        "response_size": 15000,
        "storage_type": "file",
        "full_content": "...",  # 懒加载完整内容
        "navigate_up_hint": "..."
    }
    """
```

#### Level 5: 展开摘要

```python
def expand_summary(sid: str) -> dict:
    """
    展开摘要，查看覆盖的原始消息
    
    返回:
    {
        "sid": "sum_123",
        "cid": "session_001",
        "type": "summary_expanded",
        "summary": {
            "summary": "用户询问了贵州茅台...",
            "key_points": ["估值分析", "买入建议"],
            "topics": ["白酒", "价值投资"]
        },
        "covered_messages": [
            {
                "mid": "msg_001",
                "role": "user",
                "content": "完整原始内容...",
                "timestamp": "..."
            }
        ],
        "message_count": 10,
        "navigate_up_hint": "使用 get_conversation_overview() 返回概览"
    }
    """
```

### 5.2 搜索 API

```python
def search_messages(
    cid: str,
    query: str,
    limit: int = 20
) -> dict:
    """
    在会话内搜索消息（完整内容中搜索）
    
    返回:
    {
        "cid": "session_001",
        "query": "贵州茅台",
        "results": [
            {
                "mid": "msg_001",
                "role": "user",
                "content": "...贵州茅台...",  # 高亮匹配
                "timestamp": "...",
                "expand_hint": "使用 get_message_detail(...)"
            }
        ],
        "total_found": 5
    }
    """
```

---

## 六、消息处理流水线

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Message → Memory 流水线                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户消息 / 工具响应                                                     │
│       ↓                                                                 │
│  ┌─────────────────┐                                                   │
│  │ 1. 保存原始数据 │ ←── 完整内容，永不修改                            │
│  │ (RawMessage)    │     存储：SQLite raw_messages 表                  │
│  └────────┬────────┘                                                   │
│           ↓                                                           │
│  ┌─────────────────┐                                                   │
│  │ 2. 提取记忆     │ ←── 意图、实体、偏好                              │
│  │ (Extraction)    │     存储：memory_extractions 表                   │
│  └────────┬────────┘                                                   │
│           ↓                                                           │
│  ┌─────────────────┐                                                   │
│  │ 3. 生成摘要     │ ←── 可选，定期或触发式                            │
│  │ (Summary)       │     存储：summaries 表，链接原始 mid              │
│  └────────┬────────┘                                                   │
│           ↓                                                           │
│  ┌─────────────────┐                                                   │
│  │ 4. 更新三层记忆 │ ←── L1/L2/L3 按重要性                             │
│  │ (L1/L2/L3)      │     存储：immediate/working/longterm              │
│  └─────────────────┘                                                   │
│                                                                         │
│  检索时：摘要 → 原始消息 (通过 covered_mids 或 mid 精确查找)            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 七、LLM 上下文构建

### 7.1 Context Builder 架构

```python
class ContextBuilder:
    """LLM 上下文构建器"""
    
    def build_context(
        self,
        cid: str,
        current_message_mid: str
    ) -> list[ContextComponent]:
        """
        为 LLM 构建上下文
        
        策略：
        1. 总是包含最近的 N 条原始消息（保持对话连贯性）
        2. 用摘要填充历史对话（节省 token）
        3. 注入相关的长期记忆（用户偏好、历史交易）
        4. 添加当前任务上下文
        5. 根据 token 预算动态调整
        """
```

### 7.2 上下文组件

| 组件类型 | 内容 | 优先级 | 说明 |
|----------|------|--------|------|
| 当前任务 | 任务目标、待办 | 10 | 最高优先级 |
| 用户画像 | 风险偏好、持仓周期 | 9 | 高优先级 |
| 最近消息 | 最近 10 条原始消息 | 8 | 保持对话连贯 |
| 工具响应摘要 | 工具输出摘要 | 7 | 不是完整内容 |
| 历史摘要 | 压缩的旧对话 | 6 | 节省 token |
| 交易历史 | 相关股票交易记录 | 5 | 按相关性检索 |
| 知识 | 相关知识条目 | 4 | 按语义检索 |

### 7.3 实际输出示例

```
[当前任务]
ID: task_20260408_001
类型：analysis
目标：分析贵州茅台投资价值
状态：active
待办：2 项未完成

[用户偏好]
风险承受：medium
持仓周期：long
单只最大仓位：30%
止损比例：5%
止盈比例：20%

[最近对话]
user: 帮我分析下贵州茅台
assistant: 好的，正在获取行情数据...
[工具：market_data]
贵州茅台 (600519) 当前价：1800 元，涨跌幅：+2.3%
user: 现在能买吗？

[历史摘要 2026-04-07]
用户询问了白酒行业整体情况，分析了五粮液和泸州老窖的财报...
关键点：估值对比，行业趋势

[相关交易]
600519 交易历史
- 2026-01-15 BUY 100 股 @¥1680
- 2025-12-01 BUY 50 股 @¥1620
```

---

## 八、目录结构

```
FAgent/
├── src/
│   └── memory/
│       ├── __init__.py
│       ├── ids.py              # ID 体系
│       ├── manager.py          # 统一入口
│       ├── api.py              # 逐渐披露 API
│       ├── context_builder.py  # LLM 上下文构建
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── message.py      # RawMessage
│       │   ├── summary.py      # MessageSummary
│       │   ├── tool_response.py # ToolResponse
│       │   ├── extraction.py   # MemoryExtraction
│       │   ├── trade.py        # Trade
│       │   ├── strategy.py     # Strategy
│       │   └── profile.py      # UserProfile
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py     # SQLite 操作
│       │   └── file_storage.py # 大文件存储
│       │
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── message_extractor.py  # 消息提取
│       │   ├── batch_extractor.py    # 批量提取
│       │   └── triggers.py           # 触发器
│       │
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── summarizer.py         # 摘要生成
│       │   ├── tool_handler.py       # 工具响应处理
│       │   └── context_manager.py    # 上下文管理
│       │
│       └── layers/
│           ├── __init__.py
│           ├── immediate.py    # L1 瞬时
│           ├── working.py      # L2 工作
│           └── longterm.py     # L3 长期
│
├── fagent_memory/              # 数据存储
│   ├── memory.db               # SQLite 数据库
│   ├── tool_responses/         # 工具响应文件
│   ├── working/
│   └── longterm/
│
├── docs/
│   └── memory/
│       ├── DESIGN.md           # 本设计文档
│       ├── API.md              # API 文档
│       └── EXAMPLES.md         # 使用示例
│
└── tests/
    └── memory/
```

---

## 九、实施计划

### 第一阶段：Message Memory（当前优先级）

| Phase | 内容 | 时间 | 状态 |
|-------|------|------|------|
| Phase 1 | ID 体系 + 数据模型 + 数据库 | 2 天 | 已完成 |
| Phase 2 | 原始消息存储 + 检索 API | 1 天 | 已完成 |
| Phase 3 | 消息提取器 + 记忆保存 | 2 天 | 规划中 |
| Phase 4 | 摘要生成 + 双向链接 | 2 天 | 部分完成 |
| Phase 5 | 工具响应处理 + 分级存储 | 2 天 | 已完成 |
| Phase 6 | 逐渐披露 API（L1-L5） | 2 天 | 已完成 |
| Phase 7 | L1/L2/L3 三层记忆集成 | 2 天 | 部分完成 |

### 第二阶段：LLM 工具集成与经验进化

| Phase | 内容 | 时间 | 状态 |
|-------|------|------|------|
| Phase 8 | Context Builder + LLM 集成 | 2 天 | 规划中 |
| Phase 9 | Memory Query Tools（LLM 主动调用） | 2 天 | 规划中 |
| Phase 10 | Experience Memory（经验记忆） | 3 天 | 规划中 |
| Phase 11 | 经验自动提取器 | 2 天 | 规划中 |
| Phase 12 | 经验检索与应用 | 2 天 | 规划中 |
| Phase 13 | 测试 + 文档 + 示例 | 2 天 | 部分完成 |

**第一阶段总计**: 13 天  
**第二阶段总计**: 11 天  
**全部总计**: 24 天

---

## 十、关键决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| LLM 调用 Memory | 被动接收 / 主动查询 | **主动查询** | LLM 可根据需要动态扩展上下文 |
| 经验提取时机 | 手动 / 自动 | **自动（任务完成时）** | 降低使用门槛，持续积累 |
| 实施优先级 | 并行 / 分阶段 | **先 Message Memory** | 打好基础，再叠加智能 |
| 数据库 | SQLite / PostgreSQL | SQLite | 轻量，嵌入式，单用户足够 |
| 向量库 | ChromaDB / FAISS | ChromaDB | 持久化，易集成 |

---

## 十一、优化空间

### 11.1 短期优化

- [ ] FTS5 全文搜索替代关键词搜索
- [ ] 向量检索优化相关知识召回
- [ ] 摘要触发策略优化（关键词 + 定期混合）

### 11.2 中期优化

- [ ] 分布式存储支持（多设备同步）
- [ ] 增量摘要（只摘要新增消息）
- [ ] 记忆压缩算法（更高效的摘要）

### 11.3 长期优化

- [ ] 多用户支持（用户隔离）
- [ ] 记忆可视化（时间线、关系图）
- [ ] 自动记忆整理（定期归档旧数据）

---

## 十一、决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 数据库 | SQLite / PostgreSQL | SQLite | 轻量，嵌入式，单用户足够 |
| 向量库 | ChromaDB / FAISS | ChromaDB | 持久化，易集成 |
| 存储位置 | 项目内 / 独立目录 | `fagent_memory/` | 项目独立，便于备份 |
| 摘要触发 | 定期 / 关键词 | 混合 | 平衡效率和准确性 |

---

## 十三、附录

### A. ID 生成规则

```python
# 会话 ID
cid = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# 消息 ID
mid = f"msg_{uuid.uuid4().hex[:12]}"

# 摘要 ID
sid = f"sum_{uuid.uuid4().hex[:12]}"

# 工具响应 ID
rid = f"resp_{uuid.uuid4().hex[:12]}"
```

### B. 状态枚举

```python
class MessageStatus(str, Enum):
    RAW = "raw"           # 原始未处理
    EXTRACTED = "extracted"  # 已提取记忆
    SUMMARIZED = "summarized"  # 已生成摘要
    ARCHIVED = "archived"    # 已归档

class ResponseStorage(str, Enum):
    INLINE = "inline"      # 内联存储
    FILE = "file"          # 文件存储
    INDEXED = "indexed"    # 索引存储
```

### C. 配置示例

```yaml
# fagent_memory/config.yaml
memory:
  budget:
    max_tokens: 4000
    reserved_tokens: 1000
    ratios:
      recent_messages: 0.40
      summaries: 0.30
      longterm: 0.20
      task: 0.10
  
  summarization:
    window_size: 10
    trigger: "hybrid"  # periodic/keyword/hybrid
    periodic_interval: 10
  
  storage:
    tool_response_thresholds:
      small: 500
      medium: 2000
      large: 10000
```

---

**文档结束**

---

*说明：本设计文档保留设计意图与关键决策，不是逐行实现清单。*
*最后更新：2026-04-20*
