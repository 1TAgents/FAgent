# Badcase Log

This is the fixed log for user-reported FAgent badcases.

Use this file when a tested question, answer, route, tool call, UI flow, or API
behavior is wrong. Keep entries chronological. Do not delete resolved cases;
mark them as fixed and include the resolving commit when available.

## Entry Template

```markdown
## BC-YYYYMMDD-NNN - Short title

- Date: YYYY-MM-DD
- Status: open | fixed | won't fix
- Area: frontend | backend | agents | routing | tools | docs | tests
- User prompt/action:
  - `...`
- Expected:
  - ...
- Actual:
  - ...
- Root cause:
  - ...
- Fix:
  - ...
- Verification:
  - ...
- Commit:
  - `hash subject`
```

## BC-20260531-001 - Self-introduction answer returned raw capability text

- Date: 2026-05-31
- Status: fixed
- Area: agents, routing
- User prompt/action:
  - `你有哪些功能？`
- Expected:
  - FAgent should use its authoritative capability data as context, then
    synthesize a natural answer for the user.
  - The answer can summarize the main capabilities, but it should not simply
    stream the raw `describe_fagent` tool output.
- Actual:
  - The response was the full `describe_fagent` capability text, streamed almost
    directly as the final answer.
- Root cause:
  - `ReActRouter.process_stream()` special-cased `TaskType.DESCRIBE_SELF` and
    returned `_run_self_description()` directly, bypassing model synthesis.
- Fix:
  - Changed self-capability handling so `describe_fagent` is used as an
    authoritative context source, then the model writes the final answer.
- Verification:
  - `python -m pytest -q` passed.
  - API smoke test confirmed `你有哪些功能？` now returns a synthesized overview.
- Commit:
  - `c3166dd fix(agent): synthesize self capability answers`

## BC-20260531-002 - Specific market-capability question repeated full self-introduction

- Date: 2026-05-31
- Status: fixed
- Area: agents, routing
- User prompt/action:
  - `你现在能查询最新数据行情吗？`
- Expected:
  - FAgent should answer the specific capability question directly: whether it
    can query latest market data, how the user should provide a stock name or
    code, and what data-source/cache limits apply.
  - It should not repeat the complete capability overview.
- Actual:
  - The response was effectively the same full capability description returned
    for `你有哪些功能？`.
- Root cause:
  - The router could classify focused capability questions as `describe_self`.
  - There was no separate task type for concrete ability/boundary questions.
  - Direct passthrough of `describe_fagent` made the duplicate answer obvious.
- Fix:
  - Added `TaskType.CAPABILITY_QA` for concrete capability questions.
  - Added route normalization so overbroad `describe_self` decisions for
    specific capability questions are repaired to `capability_qa`.
  - Added instructions that the model must not invent details absent from the
    authoritative capability data.
- Verification:
  - `python -m pytest -q` passed.
  - API smoke test confirmed `你现在能查询最新数据行情吗？` now answers only the
    market-data capability question and no longer repeats the full list.
- Commit:
  - `c3166dd fix(agent): synthesize self capability answers`

