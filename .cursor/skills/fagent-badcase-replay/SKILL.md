---
name: fagent-badcase-replay
description: FAgent badcase replay and evaluation workflow. Use when Codex or Claude needs to replay entries from tests/badcases.json, validate multi-turn badcases with cid/message_id, start or check local FAgent services, compare actual answers against expected_answer, diagnose whether a failure is caused by the evaluator, an unreasonable expected answer, or an unfixed FAgent service bug, or improve the badcase regression loop.
---

# FAgent Badcase Replay

## Overview

Use this skill to turn user-reported FAgent badcases into repeatable regression checks. The canonical data source is `tests/badcases.json`; exact multi-turn replay uses the `replay.cid` and `replay.message_id` fields recorded on each case.

## Core Rule

For a multi-turn badcase, replay only the problematic user turn:

- `query` is the user message for the problematic turn.
- `replay.message_id` is that user turn's `messages.message_id`, also called `mid` in logs.
- The FAgent Agents router restores context by loading messages in the same `cid` with `message_id < replay.message_id`.
- Call the Agents router for exact replay. Do not call Backend send endpoints for exact replay because Backend creates a new user message.

Read `references/replay-contract.md` before changing the replay protocol, endpoint, or evaluation categories.

## Quick Start

Run from the FAgent repository root:

```bash
python .cursor/skills/fagent-badcase-replay/scripts/run_badcase_eval.py --list
python .cursor/skills/fagent-badcase-replay/scripts/run_badcase_eval.py --case-id BC-20260531-001 --judge-mode none
python .cursor/skills/fagent-badcase-replay/scripts/run_badcase_eval.py --case-id BC-20260531-001 --start-services
```

Use `--judge-mode llm` for real pass/fail evaluation. It needs `BADCASE_EVAL_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENAI_API_KEY`. Prefer `BADCASE_EVAL_MODEL` for the judge model if the service model is also under test.

## Workflow

1. Inspect the target badcase in `tests/badcases.json`.
2. Confirm it has a `replay` object for exact replay. If absent, add replay metadata only when the local DB still has the original turn.
3. Start or verify local services with the script when the user asks for runnable validation.
4. Replay through `POST /agent/chat/router/stream` using `cid`, `message_id`, `query`, `history_limit`, and `model`.
5. Evaluate actual output against `expected_answer`.
6. Classify failures into exactly one primary category:
   - `evaluator`: judge API failed, returned malformed output, or clearly misread the answer.
   - `expected_answer`: the expected answer is untestable, stale, contradictory, or over-constrained.
   - `fagent`: FAgent output does not satisfy a reasonable expected answer.
7. If FAgent is the issue, fix code first, add or update tests, rerun the badcase script, then commit.

## Script

Use `scripts/run_badcase_eval.py` as the default runner. It supports:

- `--list`: show available badcases.
- `--case-id ID`: run one or more specific cases.
- `--start-services`: start missing local services in tmux sessions.
- `--restart-owned`: restart only tmux sessions created by this script.
- `--judge-mode llm|none|heuristic`: choose evaluation mode.
- `--output path`: write a JSON report.

Do not paste API keys into commands or reports. The script reads keys from the environment or `.env` and redacts key values from output.

## Reporting

When reporting results to the user, include:

- badcase id, query, `cid`, and `message_id`
- pass/fail status and failure category
- a short excerpt or summary of the actual answer
- verification command
- next action when failed

Avoid saying a badcase passed only because the script exited successfully; inspect the judge result and any evaluator errors.
