# FAgent Badcase Replay Contract

## Data Source

Canonical file: `tests/badcases.json`.

Each replayable case should contain:

```json
{
  "id": "BC-YYYYMMDD-001",
  "query": "problematic user turn only",
  "expected_answer": "observable acceptance criteria",
  "replay": {
    "cid": 47,
    "message_id": 148,
    "assistant_message_id": 149,
    "history_limit": 10,
    "model": "deepseek-v4-pro",
    "endpoint": "POST /agent/chat/router/stream"
  }
}
```

`message_id` is the user turn `mid`. `assistant_message_id` is useful for auditing the original failure but is not sent during replay.

## Exact Replay Endpoint

Use Agents directly:

```http
POST /agent/chat/router/stream
Content-Type: application/json

{
  "cid": 47,
  "message_id": 148,
  "user_message": "你现在能查询最新数据行情吗？",
  "history_limit": 10,
  "model": "deepseek-v4-pro"
}
```

The response is SSE:

```text
data: {"content":"..."}
data: [DONE]
```

The router rebuilds context from the local DB by loading messages where `cid = replay.cid` and `message_id < replay.message_id`.

## Not Exact Replay

Backend send endpoints such as `POST /api/chat/send/stream` create a new user message before calling Agents. They are useful for end-to-end smoke tests, but they are not exact replay of a stored badcase turn.

## Evaluation Categories

Use one primary failure category:

| Category | Meaning | Typical action |
| --- | --- | --- |
| `evaluator` | Judge failed, returned malformed JSON, could not access an API, or made an obviously wrong judgment. | Fix the eval prompt, parser, model config, or rerun with another judge. |
| `expected_answer` | The expected answer is vague, untestable, stale, contradictory, or asks for behavior FAgent should not provide. | Rewrite the badcase expected answer and explain why. |
| `fagent` | FAgent output does not satisfy a reasonable expected answer. | Fix FAgent code, prompt, routing, tool behavior, or data dependency. |

Do not weaken `expected_answer` just to turn a failing FAgent case green.

## Service Defaults

Defaults are loaded from `.env` when present:

- Agents: `AGENTS_BASE_URL`, or `http://localhost:${AGENTS_PORT:-8001}`
- Backend: `http://localhost:${BACKEND_PORT:-8000}`
- Frontend: `http://localhost:${FRONTEND_PORT:-5173}`

The replay script can start missing services in tmux. It only kills script-owned tmux sessions when `--restart-owned` is passed.
