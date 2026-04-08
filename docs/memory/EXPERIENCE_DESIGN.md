# FAgent Experience Memory 设计补充

> 版本：v1.0  
> 创建日期：2026-04-08  
> 状态：设计待实施（第二阶段）

---

## 一、设计目标

为 FAgent 添加**自我进化**能力，让 Agent 从历史任务中学习经验，避免重复探索，提高效率。

### 1.1 核心思路

```
人类处理问题的过程:
第一次：探索 → 试错 → 成功 → 形成经验
第二次：直接应用经验 → 更高效
第 N 次：经验内化 → 直觉反应

Agent 也应该这样！
```

### 1.2 与 Message Memory 的关系

```
┌─────────────────────────────────────────────────────────────────────┐
│              Memory 系统整体架构                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐                                               │
│  │ Message Memory  │ ← 基础层：原始消息、摘要、工具响应             │
│  │ (第一阶段)      │   当前设计重点                                  │
│  └────────┬────────┘                                               │
│           ↓                                                         │
│  ┌─────────────────┐                                               │
│  │ Experience      │ ← 提炼层：从消息/任务中提取的经验              │
│  │ Memory          │   第二阶段实施                                  │
│  │ (第二阶段)      │                                                 │
│  └────────┬────────┘                                               │
│           ↓                                                         │
│  ┌─────────────────┐                                               │
│  │ Skill Memory    │ ← 内化层：固化的经验（可复用的技能）           │
│  │ (长期演化)      │   类似人类的"肌肉记忆"                         │
│  └─────────────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据模型

### 2.1 经验记录

```python
@dataclass
class Experience:
    """经验记录"""
    exp_id: str
    problem_type: str           # 问题类型（如：stock_analysis, trade_decision）
    problem_pattern: str        # 问题模式（用于匹配）
    
    # === 解决链路 ===
    solution_steps: list[Step]  # 解决步骤
    tools_used: list[str]       # 使用的工具
    time_cost_seconds: int      # 耗时
    
    # === 效果评估 ===
    success: bool               # 是否成功
    user_satisfaction: float    # 用户满意度 0-1
    efficiency_score: float     # 效率评分
    
    # === 经验提炼 ===
    key_learnings: list[str]    # 关键学习
    shortcuts: list[Shortcut]   # 可跳过的步骤
    warnings: list[str]         # 注意事项
    
    # === 使用统计 ===
    use_count: int = 0          # 被引用次数
    last_used_at: str = None
    created_at: str = None
```

### 2.2 解决步骤

```python
@dataclass
class Step:
    """解决步骤"""
    step_num: int
    action: str                 # 动作（工具调用/分析/决策）
    description: str
    result_summary: str
    is_essential: bool = True   # 是否必要步骤
```

### 2.3 快捷方式

```python
@dataclass
class Shortcut:
    """快捷方式"""
    description: str            # 描述
    skip_steps: list[int]       # 可跳过的步骤编号
    condition: str              # 适用条件
```

---

## 三、数据库设计

```sql
-- 经验表
CREATE TABLE experiences (
    exp_id TEXT PRIMARY KEY,
    problem_type TEXT NOT NULL,
    problem_pattern TEXT NOT NULL,
    solution_steps TEXT,  -- JSON
    tools_used TEXT,  -- JSON
    time_cost_seconds INTEGER,
    success INTEGER DEFAULT 1,
    user_satisfaction REAL,
    efficiency_score REAL,
    key_learnings TEXT,  -- JSON
    shortcuts TEXT,  -- JSON
    warnings TEXT,  -- JSON
    use_count INTEGER DEFAULT 0,
    last_used_at TEXT,
    created_at TEXT NOT NULL
);

-- 索引
CREATE INDEX idx_exp_type ON experiences(problem_type);
CREATE INDEX idx_exp_pattern ON experiences(problem_pattern);
```

---

## 四、核心 API

### 4.1 保存经验

```python
# 任务完成后自动提取经验
experience = memory.experience.extract_from_task(task_id)
memory.experience.save_experience(experience)
```

### 4.2 查找相关经验

```python
# 接收新问题时查找相关经验
experiences = memory.experience.find_relevant_experiences(
    current_problem="分析贵州茅台",
    limit=3
)

# 返回按成功率、使用次数、时效性排序的经验列表
```

### 4.3 优化工作流

```python
# 基于经验优化工作流
optimized_steps = memory.experience.get_optimized_workflow(
    problem_type="stock_analysis",
    base_workflow=default_workflow
)

# 返回应用了最佳经验快捷方式的工作流
```

---

## 五、经验提取流程

```
任务完成
    ↓
1. 分析解决链路
   - 从 decision_chain 中提取步骤
   - 标记必要/非必要步骤
    ↓
2. 评估效果
   - 成功/失败
   - 用户满意度（从反馈推断）
   - 效率评分（步骤数、耗时）
    ↓
3. 提炼关键学习
   - 成功因素
   - 教训
   - 注意事项
    ↓
4. 识别快捷方式
   - 可合并的步骤
   - 可跳过的步骤
   - 可简化的流程
    ↓
5. 保存到经验库
   - SQLite 存储
   - 向量索引（用于语义检索）
    ↓
完成
```

---

## 六、经验应用流程

```
接收新问题
    ↓
1. 检索相关经验
   - 关键词匹配
   - 语义匹配（向量）
   - 按评分排序
    ↓
2. 应用最佳经验
   - 使用快捷方式优化工作流
   - 避免已知陷阱
    ↓
3. 执行任务
    ↓
4. 评估结果
   - 成功/失败
   - 效率对比（与历史经验）
    ↓
5. 更新经验
   - 增加使用次数
   - 更新成功率
   - 必要时提取新经验
    ↓
完成
```

---

## 七、LLM Memory Query Tools

### 7.1 工具列表

```python
# 供 LLM 主动调用的 Memory 查询工具

tools = [
    {
        "name": "memory_search_messages",
        "description": "在历史消息中搜索相关内容"
    },
    {
        "name": "memory_get_message_detail",
        "description": "获取单条消息的完整内容"
    },
    {
        "name": "memory_get_user_profile",
        "description": "获取用户画像和偏好"
    },
    {
        "name": "memory_get_trade_history",
        "description": "获取某股票的交易历史"
    },
    {
        "name": "memory_expand_summary",
        "description": "展开摘要查看原始消息"
    },
    {
        "name": "memory_get_tool_response",
        "description": "获取工具响应的完整内容"
    },
    {
        "name": "memory_find_experiences",
        "description": "查找相关经验",
        "parameters": {
            "query": "问题描述"
        }
    }
]
```

### 7.2 使用示例

```
用户：贵州茅台现在能买吗？

[LLM 思考]
- 需要知道用户之前的交易记录
- 需要了解用户的风险偏好
- 需要查看之前的分析结论

[工具调用 1]
memory_get_user_profile()
→ 返回：风险 medium，持仓周期 long，止损 5%

[工具调用 2]
memory_get_trade_history("600519")
→ 返回：2026-01-15 BUY 100 股 @¥1680

[工具调用 3]
memory_search_messages(query="茅台 分析", limit=5)
→ 返回：之前的分析讨论

[工具调用 4]
memory_find_experiences(query="白酒股票分析")
→ 返回：3 个相关经验，最佳经验成功率 85%

[最终回复]
基于您的投资偏好（长线、风险中等）和持仓历史（1 月买入 100 股@1680），
以及过往分析白酒股票的经验，当前茅台 1800 元，已有 7% 收益。建议...
```

---

## 八、实施计划

| Phase | 内容 | 时间 | 依赖 |
|-------|------|------|------|
| Phase 10 | Experience Memory 基础架构 | 3 天 | Phase 1-7 完成 |
| Phase 11 | 经验自动提取器 | 2 天 | Phase 10 完成 |
| Phase 12 | 经验检索与应用 | 2 天 | Phase 11 完成 |
| Phase 9 | Memory Query Tools | 2 天 | Phase 1-7 完成 |

**第二阶段总计**: 11 天

---

## 九、与 Message Memory 的关联

| 方面 | Message Memory | Experience Memory |
|------|----------------|-------------------|
| 数据来源 | 用户消息、工具响应 | 从 Message 提取 |
| 存储内容 | 原始数据 + 摘要 | 经验 + 快捷方式 |
| 检索方式 | 精确查询 + 关键词 | 语义匹配 + 评分 |
| 用途 | 上下文构建、追溯 | 工作流优化、避免重复 |
| 实施阶段 | 第一阶段 | 第二阶段 |

---

**文档结束**
