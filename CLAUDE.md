# FAgent Claude Rules

Claude Code should follow the canonical repository rules in `AGENTS.md`.

Important shared workflow:
- User-reported badcases are recorded in `docs/badcases.json`.
- When a user says a tested question, answer, route, tool call, UI flow, or API
  behavior is wrong, decide whether it is a real badcase and append or update
  the log entry before finishing the fix.
- Every badcase entry must include `query` and `expected_answer`.
- For multi-turn badcases, record only the problematic user turn in `query`.
- If the local database still has the session, add replay metadata with
  `cid` and the user turn `message_id`/`mid`; use it with the Agents router
  endpoint for exact replay. Backend send endpoints create a new message and
  are not exact replay.
- Keep `query` and `expected_answer` even when `replay` exists, because the
  database is local runtime state.
- Keep the badcase log chronological. Do not delete resolved cases; mark them
  as fixed and reference the resolving commit when available.
- Do not record secrets, private logs, API keys, or raw personal data in the log.
- After editing the log, run `python -m pytest tests/test_badcases_log.py -q`.
