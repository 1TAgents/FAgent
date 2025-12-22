# API 使用文档

## 消息存储和会话管理

### 核心概念

- **conversation_id (cid)**: 会话ID，标识一个完整的对话会话
- **message_id**: 消息ID，标识会话中的每一条消息
- **content_type**: 消息内容类型（text、image_url、video_url、multimodal 等）
- **metadata**: 每条消息可携带的元数据
- **持久化存储**: 所有消息存储在 SQLite 数据库中（`data/conversations.db`）

### 消息类型（与 OpenAI API 一致）

| content_type | 说明 | 示例 |
|--------------|------|------|
| text | 纯文本 | `"Hello"` |
| image_url | 图片 URL | `{"type": "image_url", "image_url": {"url": "https://..."}}` |
| image_base64 | 图片 Base64 | `{"type": "image_base64", "data": "base64..."}` |
| video_url | 视频 URL | `{"type": "video_url", "video_url": {"url": "https://..."}}` |
| audio_url | 音频 URL | `{"type": "audio_url", "audio_url": {"url": "https://..."}}` |
| multimodal | 多模态混合 | `[{"type": "text", "text": "..."}, {"type": "image_url", ...}]` |

### 数据库结构

```
conversations 表:
- conversation_id (主键)
- created_at
- updated_at
- metadata (JSON)
- system_message

messages 表:
- message_id (主键)
- conversation_id (外键)
- role (user/assistant/system)
- content_type (text/image_url/video_url/multimodal 等)
- content (JSON 或字符串)
- metadata (JSON，每条消息的元数据)
- created_at
```

## API 接口

### 1. 创建会话

```bash
POST /api/chat/session/create
Content-Type: application/json

{
  "system_message": "你是一个股票交易助手",  # 可选
  "metadata": {"user_id": "123"}  # 可选
}

# 响应
{
  "conversation_id": "xxx-xxx-xxx",
  "session_id": "xxx-xxx-xxx",  # 向后兼容
  "message": "Session created successfully"
}
```

### 2. 根据 conversation_id 查询完整会话记录

```bash
GET /api/chat/conversation/{conversation_id}

# 响应
{
  "conversation_id": "xxx-xxx-xxx",
  "created_at": "2025-12-22T10:00:00",
  "updated_at": "2025-12-22T10:05:00",
  "metadata": {...},
  "system_message": "...",
  "message_count": 10,
  "messages": [
    {
      "message_id": "msg-001",
      "conversation_id": "xxx-xxx-xxx",
      "role": "user",
      "content": "你好",
      "created_at": "2025-12-22T10:00:00"
    },
    {
      "message_id": "msg-002",
      "conversation_id": "xxx-xxx-xxx",
      "role": "assistant",
      "content": "你好！有什么可以帮助你的？",
      "created_at": "2025-12-22T10:00:01"
    },
    ...
  ]
}
```

### 3. 发送消息（使用会话）

#### 纯文本消息

```bash
POST /api/chat/completion
Content-Type: application/json

{
  "session_id": "xxx-xxx-xxx",
  "user_message": "查询苹果股票价格",
  "user_message_metadata": {
    "source": "android_app",
    "client_version": "1.0.0"
  },
  "temperature": 0.7
}

# 响应
{
  "content": "AAPL 当前价格为...",
  "model": "xiaomi/mimo-v2-flash:free",
  "message_id": "msg-xxx-xxx",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

#### 多模态消息（图片 + 文本）

```bash
POST /api/chat/completion
Content-Type: application/json

{
  "session_id": "xxx-xxx-xxx",
  "user_message": [
    {"type": "text", "text": "这张图里有什么？"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
  ],
  "user_message_metadata": {
    "image_source": "camera"
  },
  "temperature": 0.7
}
```

**注意**: 消息会自动保存到数据库，包含 `message_id`、`conversation_id`、`content_type` 和 `metadata`

### 4. 流式发送消息（使用会话）

```bash
POST /api/chat/stream
Content-Type: application/json

{
  "session_id": "xxx-xxx-xxx",  # conversation_id
  "user_message": "介绍一下你自己",
  "temperature": 0.7
}

# 响应: text/event-stream
data: {"content": "我"}
data: {"content": "是"}
data: {"content": "..."}
data: [DONE]
```

### 5. 获取会话消息列表

```bash
GET /api/chat/session/{session_id}/messages

# 响应
{
  "conversation_id": "xxx-xxx-xxx",
  "session_id": "xxx-xxx-xxx",  # 向后兼容
  "messages": [
    {
      "message_id": "msg-001",
      "conversation_id": "xxx-xxx-xxx",
      "role": "user",
      "content": "...",
      "created_at": "..."
    },
    ...
  ],
  "count": 10
}
```

### 6. 列出所有会话

```bash
GET /api/chat/conversations?limit=10&offset=0

# 响应
{
  "conversations": [
    {
      "conversation_id": "xxx-xxx-xxx",
      "created_at": "2025-12-22T10:00:00",
      "updated_at": "2025-12-22T10:05:00",
      "metadata": {...},
      "message_count": 10
    },
    ...
  ],
  "count": 5
}
```

### 7. 删除会话

```bash
DELETE /api/chat/conversation/{conversation_id}

# 或使用向后兼容接口
DELETE /api/chat/session/{session_id}
```

### 8. 清空会话消息

```bash
POST /api/chat/session/{session_id}/clear
```

## Python 使用示例

### 基础文本对话

```python
import requests

API_BASE = "http://localhost:8000"

# 1. 创建会话
response = requests.post(f"{API_BASE}/api/chat/session/create", json={
    "system_message": "你是一个股票交易助手"
})
conversation_id = response.json()["conversation_id"]
print(f"会话ID: {conversation_id}")

# 2. 发送消息（带 metadata）
response = requests.post(f"{API_BASE}/api/chat/completion", json={
    "session_id": conversation_id,
    "user_message": "查询苹果股票价格",
    "user_message_metadata": {
        "source": "python_client",
        "timestamp": "2025-12-22T10:00:00"
    }
})
result = response.json()
print(f"回复: {result['content']}")
print(f"消息ID: {result['message_id']}")

# 3. 查询完整会话记录
response = requests.get(f"{API_BASE}/api/chat/conversation/{conversation_id}")
conversation = response.json()
print(f"会话包含 {conversation['message_count']} 条消息")
for msg in conversation["messages"]:
    print(f"[{msg['message_id']}] [{msg['content_type']}] {msg['role']}: {msg['content']}")
    if msg.get("metadata"):
        print(f"  metadata: {msg['metadata']}")
```

### 多模态消息（图片识别）

```python
# 发送图片 + 文本消息
response = requests.post(f"{API_BASE}/api/chat/completion", json={
    "session_id": conversation_id,
    "user_message": [
        {"type": "text", "text": "请分析这张 K 线图"},
        {"type": "image_url", "image_url": {"url": "https://example.com/kline.png"}}
    ],
    "user_message_metadata": {
        "image_type": "kline_chart",
        "symbol": "AAPL"
    }
})
print(response.json()["content"])
```

### 直接使用消息列表（不使用会话）

```python
response = requests.post(f"{API_BASE}/api/chat/completion", json={
    "messages": [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "这是什么图片？"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
            ],
            "metadata": {"source": "upload"}
        }
    ],
    "temperature": 0.7
})
```

## 消息 ID 说明

每条消息都有两个 ID：

1. **conversation_id**: 标识消息所属的会话
2. **message_id**: 唯一标识这条消息

这样可以：
- 根据 `conversation_id` 查询整个会话的所有消息
- 根据 `message_id` 精确定位某条消息
- 支持消息的增删改查操作

## 存储位置

数据库文件默认存储在：`backend/data/conversations.db`

可以通过修改 `MessageStorage` 的 `db_path` 参数来更改存储位置。

