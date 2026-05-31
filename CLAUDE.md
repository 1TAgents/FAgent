# FAgent Claude Rules

Claude Code should follow the canonical repository rules in `AGENTS.md`.

Important shared workflow:
- User-reported badcases are recorded in `docs/badcases.json`.
- When a user says a tested question, answer, route, tool call, UI flow, or API
  behavior is wrong, decide whether it is a real badcase and append or update
  the log entry before finishing the fix.
- Every badcase entry must include `query` and `expected_answer`.
- Keep the badcase log chronological. Do not delete resolved cases; mark them
  as fixed and reference the resolving commit when available.
- Do not record secrets, private logs, API keys, or raw personal data in the log.
- After editing the log, run `python -m pytest tests/test_badcases_log.py -q`.
