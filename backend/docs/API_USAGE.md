# API 使用文档

## 核心概念

| 概念 | 说明 |
|------|------|
| `cid` | 会话ID，**整数自增** |
| `message_id` | 消息ID，**整数自增**，全局唯一 |
| `role` | 消息角色：`user`、`assistant`、`system` |
| `content_type` | 内容类型：`text`、`image_url`、`multimodal` 等 |

## 消息流程

```
1. 用户消息 → 落库 → 获取 user_message_id
2. 按 message_id < user_message_id 过滤历史
3. 构建上下文 → 调用 LLM
4. AI 回复 → 落库 → 获取 assistant_message_id
5. 返回响应
```

## 数据库结构

```sql
-- 会话表
conversations (
    cid INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT,
    system_message TEXT
)

-- 消息表
messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cid INTEGER,
    role TEXT,           -- user/assistant/system
    content_type TEXT,   -- text/image_url/multimodal
    content TEXT,
    metadata TEXT,
    created_at TEXT
)
```

## API 接口

### 1. 创建会话

```bash
POST /api/chat/session/create
Content-Type: application/json

{
  "system_message": "你是一个股票交易助手",
  "metadata": {"user_id": "123"}
}

# 响应
{
  "cid": 1,
  "message": "Session created successfully"
}
```

### 2. 非流式对话

```bash
POST /api/chat/completion
Content-Type: application/json

{
  "cid": 1,
  "user_message": "查询苹果股票价格",
  "user_message_metadata": {"source": "android"},
  "temperature": 0.7,
  "history_limit": 20
}

# 响应
{
  "content": "AAPL 当前价格为...",
  "model": "xiaomi/mimo-v2-flash:free",
  "cid": 1,
  "user_message_id": 3,
  "assistant_message_id": 4,
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

### 3. 流式对话（SSE）

```bash
POST /api/chat/stream
Content-Type: application/json

{
  "cid": 1,
  "user_message": "介绍一下你自己",
  "temperature": 0.7
}

# 响应: text/event-stream
data: {"content": "我"}
data: {"content": "是"}
data: {"content": "..."}
data: {"done": true, "cid": 1, "user_message_id": 5, "assistant_message_id": 6}
data: [DONE]
```

### 4. 获取会话记录

```bash
GET /api/chat/conversation/{cid}

# 响应
{
  "cid": 1,
  "created_at": "2025-12-24T10:00:00",
  "updated_at": "2025-12-24T10:05:00",
  "message_count": 4,
  "messages": [
    {
      "message_id": 1,
      "cid": 1,
      "role": "user",
      "content_type": "text",
      "content": "你好",
      "metadata": null,
      "created_at": "2025-12-24T10:00:00"
    },
    {
      "message_id": 2,
      "cid": 1,
      "role": "assistant",
      "content_type": "text",
      "content": "你好！有什么可以帮助你的？",
      "metadata": null,
      "created_at": "2025-12-24T10:00:01"
    }
  ]
}
```

### 5. 获取历史消息（按 message_id 过滤）

```bash
GET /api/chat/conversation/{cid}/history?before_message_id=5&limit=10

# 响应
{
  "cid": 1,
  "before_message_id": 5,
  "messages": [...],
  "count": 4
}
```

### 6. 列出所有会话

```bash
GET /api/chat/conversations?limit=10&offset=0

# 响应
{
  "conversations": [
    {
      "cid": 2,
      "created_at": "...",
      "updated_at": "...",
      "message_count": 4
    },
    {
      "cid": 1,
      "created_at": "...",
      "updated_at": "...",
      "message_count": 4
    }
  ],
  "count": 2
}
```

### 7. 删除会话

```bash
DELETE /api/chat/conversation/{cid}

# 响应
{
  "message": "Conversation deleted successfully",
  "cid": 1
}
```

### 8. 清空会话消息

```bash
POST /api/chat/conversation/{cid}/clear

# 响应
{
  "message": "Conversation cleared successfully",
  "cid": 1
}
```

## Python 使用示例

```python
import requests

API_BASE = "http://localhost:8000"

# 1. 创建会话
resp = requests.post(f"{API_BASE}/api/chat/session/create", json={
    "system_message": "你是一个股票交易助手"
})
cid = resp.json()["cid"]
print(f"会话ID: {cid}")  # 整数，如 1

# 2. 发送消息
resp = requests.post(f"{API_BASE}/api/chat/completion", json={
    "cid": cid,
    "user_message": "查询苹果股票价格"
})
result = resp.json()
print(f"回复: {result['content']}")
print(f"消息ID: user={result['user_message_id']}, assistant={result['assistant_message_id']}")

# 3. 流式消息
with requests.post(f"{API_BASE}/api/chat/stream", json={
    "cid": cid,
    "user_message": "介绍一下你自己"
}, stream=True) as resp:
    for line in resp.iter_lines():
        if line:
            print(line.decode('utf-8'))

# 4. 查询会话记录
resp = requests.get(f"{API_BASE}/api/chat/conversation/{cid}")
conv = resp.json()
print(f"会话 {conv['cid']} 包含 {conv['message_count']} 条消息")
for msg in conv["messages"]:
    print(f"  [{msg['message_id']}] {msg['role']}: {msg['content'][:50]}...")
```

## 多模态消息

```python
# 图片 + 文本
resp = requests.post(f"{API_BASE}/api/chat/completion", json={
    "cid": cid,
    "user_message": [
        {"type": "text", "text": "这张图里有什么？"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
    ]
})
```

## 直接调用（不使用会话）

```python
# 不传 cid，直接传 messages
resp = requests.post(f"{API_BASE}/api/chat/completion", json={
    "messages": [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ],
    "temperature": 0.7
})
```

> 注意：不使用会话时，消息不会持久化

## 消息类型

| content_type | 说明 |
|--------------|------|
| `text` | 纯文本 |
| `image_url` | 图片 URL |
| `image_base64` | 图片 Base64 |
| `video_url` | 视频 URL |
| `audio_url` | 音频 URL |
| `multimodal` | 多模态混合 |

---

**最后更新：** 2025-12-24
