# 功能需求与开发规范 (Feature Specifications & Guidelines)

> 本文档用于记录系统功能的详细需求、技术方案及多端协作任务分配。
> 新需求请按模板追加至文档末尾。

---

## 0. 🛡️ 标准协作分工规范 (Standard Collaboration Workflow)

面对一个新的功能需求时，各端角色的标准职责划分如下：

### 🟢 Backend (后端开发)
**核心职责**：数据持久化、业务逻辑、接口契约。
1.  **数据库设计 (DB Schema)**: 设计表结构、索引、迁移脚本 (Migration)。
2.  **接口定义 (API Contract)**: 确定 API 路径、Method、请求参数、响应结构（优先提供 Mock 数据或文档）。
3.  **业务逻辑 (Business Logic)**: 实现核心业务流程、权限校验、错误处理。
4.  **任务调度 (Scheduling)**: 处理异步任务、队列、定时作业（如触发 Agent 任务）。

### 🔵 Agents (智能体开发)
**核心职责**：LLM 交互、Prompt 工程、工具能力。
1.  **Prompt 工程**: 设计、测试和优化 System Prompt 及 User Prompt。
2.  **工具开发 (Tools)**: 封装外部 API 或内部服务供 LLM 调用（Function Calling）。
3.  **服务封装**: 将复杂的 LLM 交互流程封装为简洁的 Python 函数/类，供 Backend 调用。
4.  **模型评估**: 验证不同模型（如 GPT-4, Claude, Gemini）在该场景下的表现。

### 🟠 Frontend (前端开发)
**核心职责**：界面呈现、用户交互、状态管理。
1.  **UI/UX 实现**: 根据设计稿或需求描述还原界面，注重响应式和交互体验。
2.  **状态管理**: 设计合理的前端数据流（Store/Hooks），处理 Loading、Error 等状态。
3.  **接口对接**: 调用 Backend 提供的 API，处理数据格式转换。
4.  **Mock 开发**: 在后端接口未就绪时，基于接口契约优先开发 UI。

---

## 1. 📝 需求：自动会话总结 (Auto Conversation Summary)

### � 时间线
- **提出时间**: 2026-01-07
- **最后更新**: 2026-01-08

### 🎯 需求目标
用户完成一轮对话后，系统自动生成简短标题（如 "Python 排序算法"），替换默认的 "Conversation ID"。

### 🛠️ 任务分工表

| 角色 | 任务项 | 详细说明 | 状态 | 完成时间 |
| :--- | :--- | :--- | :--- | :--- |
| **Backend** | **DB 变更** | `conversations` 表新增 `title` 字段 (TEXT)。 | ✅ Done | 2026-01-08 |
| **Backend** | **接口升级** | `create_conversation` 支持传入 `title`；新增 `PATCH /conversation/{cid}` 接口。 | ✅ Done | 2026-01-08 |
| **Backend** | **触发机制** | 在 `chat_stream` 结束后，异步触发 Agent 的总结任务。 | ✅ Done | 2026-01-08 |
| **Agents** | **Prompt 设计** | 设计"总结助手" Prompt，要求输出 5-15 字以内的标题。 | ✅ Done | 2026-01-08 |
| **Agents** | **接口封装** | 提供 `POST /agent/summary/generate` 接口。 | ✅ Done | 2026-01-08 |
| **Frontend** | **UI 展示** | 侧边栏列表渲染 `title` 字段（若为空则显示默认 ID）。 | ✅ Done | 2026-01-07 |
| **Frontend** | **被动更新** | 监听或在下次刷新时获取最新标题。 | ✅ Done | 2026-01-07 |

---

## 2. 🗂️ 需求：智能侧边栏 (Smart Sidebar)

### � 时间线
- **提出时间**: 2026-01-08
- **最后更新**: 2026-01-08

### 🎯 需求目标
仿照 ChatGPT 体验，对历史会话进行时间分组（今天、昨天、7天内），并支持重命名和删除。

### 🛠️ 任务分工表

| 角色 | 任务项 | 详细说明 | 状态 | 完成时间 |
| :--- | :--- | :--- | :--- | :--- |
| **Backend** | **重命名接口** | 实现 `PATCH /api/chat/conversation/{cid}`，支持修改 `title`。 | ✅ Done | 2026-01-08 |
| **Backend** | **删除接口** | 确保 `DELETE /api/chat/conversation/{cid}` 可用。 | ✅ Done | 2026-01-07 |
| **Frontend** | **时间分组** | 实现 `Today`, `Yesterday`, `Previous 7 Days` 的分组算法。 | ✅ Done | 2026-01-08 |
| **Frontend** | **交互实现** | 增加“编辑”和“删除”按钮（Hover 显示）；实现确认弹窗。 | ⏳ Pending | - |
| **Frontend** | **状态同步** | 操作成功后，乐观更新 (Optimistic Update) 本地列表。 | ⏳ Pending | - |

---

son
  {
    "title": "New Title"
  }
  ```
- **Response**: `200 OK`

### Request Headers (推荐)
所有 API 请求建议携带以下 Header：
- `X-Request-ID`: 请求追踪 ID（可选，后端会自动生成）

> 注：`cid` 在 request body 中传递，无需在 Header 中重复
## 3. 🔗 需求：请求追踪系统 (Request Tracing)

### 📅 时间线
- **提出时间**: 2026-01-11
- **最后更新**: 2026-01-11

### 🎯 需求目标
实现全链路请求追踪，通过 `request_id` + `cid` 串联同一请求在 Backend、Agents 等服务中的所有日志，便于问题排查。

### 📐 技术方案

**追踪标识：**
- `request_id (rid)`: 唯一标识一次请求，格式为 UUID 前8位（如 `a1b2c3d4`）
- `cid`: 会话 ID，标识同一会话的所有请求

**传递方式：**
- `request_id`: 前端 → Backend → Agents，通过 HTTP Header `X-Request-ID` 传递
- `cid`: 在 request body 中传递（已有字段，无需额外处理）
- 如果前端未提供 `X-Request-ID`，Backend 自动生成

**日志格式：**
```
[rid=a1b2c3d4 cid=5] [REQ] POST /api/chat/send/stream
[rid=a1b2c3d4 cid=5] [ROUTER_INTENT] route=market | task=get_quote
[rid=a1b2c3d4 cid=5] [TOOL_CALL] market_service.get_quote
```

### 🛠️ 任务分工表

| 角色 | 任务项 | 详细说明 | 状态 | 完成时间 |
| :--- | :--- | :--- | :--- | :--- |
| **Backend** | **中间件** | 从 Header 获取或自动生成 `request_id`，存入上下文 | ✅ Done | 2026-01-11 |
| **Backend** | **日志前缀** | 所有日志自动添加 `[rid=xxx cid=yyy]` 前缀 | ✅ Done | 2026-01-11 |
| **Backend** | **Header 传递** | 调用 Agents 时传递 `X-Request-ID` Header | ✅ Done | 2026-01-11 |
| **Agents** | **中间件** | 从 Header 获取 `rid`，从 body 获取 `cid`，存入上下文 | ✅ Done | 2026-01-11 |
| **Agents** | **日志前缀** | Router/SubAgent 日志自动添加追踪前缀 | ✅ Done | 2026-01-11 |
| **Frontend** | **生成 rid** | 每次请求生成 UUID 作为 `request_id` | ✅ Done | 2026-01-11 |
| **Frontend** | **Header 设置** | 在 API 请求中添加 `X-Request-ID` Header | ✅ Done | 2026-01-11 |

### 📝 前端实现指南

```typescript
// 生成 request_id
const generateRequestId = () => crypto.randomUUID().slice(0, 8);

// API 请求示例
const sendMessage = async (cid: number, message: string) => {
  const requestId = generateRequestId();
  
  const response = await fetch('/api/chat/send/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': requestId,  // cid 已在 body 中，无需 Header
    },
    body: JSON.stringify({ cid, user_message: message }),
  });
  
  // ...
};
```

---

## 4. 🔌 接口契约草稿 (API Draft)

### Update Conversation Title
- **Endpoint**: `PATCH /api/chat/conversation/{cid}`
- **Body**:
  ```j