# FAgent Agent Rules

## Commit Convention

Use this format for every commit:

```text
<type>(<scope>): <subject>
```

Rules:
- `type` is required, `scope` is optional
- use imperative mood, for example `add` instead of `added`
- start the subject with a lowercase letter
- do not end the subject with a period
- keep the subject ideally within 50 characters and at most 72

Allowed types:
- `feat`
- `fix`
- `docs`
- `refactor`
- `perf`
- `style`
- `test`
- `chore`
- `ci`

Examples:
- `feat(router): add market route fallback`
- `fix(auth): handle missing bearer token`
- `docs(readme): clarify local startup steps`

## Git Identity Guard

Each clone or worktree must use an explicit repo-local git identity.
Do not force one shared identity for all collaborators.

Rules:
- never rely on global git `user.name` or `user.email`
- after clone, reclone, or `git worktree add`, run
  `scripts/setup_git_identity.sh "Your Name" "your-public-email"`
- use a public-safe email for this repo; GitHub noreply is recommended for public work
- prefer `git worktree add ...` over ad-hoc `git clone` when you need a clean verification tree
- do not commit or push if author or committer identity differs from the repo-local identity

This repo includes `.githooks/pre-commit` and `.githooks/pre-push` guards.
They are activated by `scripts/setup_git_identity.sh` via `core.hooksPath=.githooks`.

## Pre-Commit Security Checks

Before `git add` or `git commit`, check staged content for:
- API keys, secrets, tokens, passwords
- real `OPENROUTER_API_KEY`, `RQDATAC_CONF`, `JWT_SECRET`, or other credential values
- real usernames, emails, personal names, or machine-specific identifiers
- absolute local paths from macOS, Linux, or Windows home directories
- private domains, internal IP addresses, or unsanitized report outputs

Never commit:
- `.env`
- real credential values
- local databases, logs, or reports that contain private or machine-specific data

Only commit:
- `.env.example` with placeholder values
- sanitized sample data and reports

## Development Workflow

Every non-trivial change should follow this sequence:

1. Understand the request and identify the affected areas first: `frontend`, `backend`, `agents`, `src/memory`, `modules`, `tests`, `docs`.
2. Review the existing code path and any related docs before editing files.
3. Implement the smallest coherent change that solves the problem.
4. Run the most relevant verification for the touched area.
5. Fix any issues found during verification.
6. Before commit, check whether related documentation also needs updates, and update it in the same change when needed.
7. Commit only after the change is working and code, tests, and docs are aligned.

This workflow applies to feature work, bug fixes, refactors, and test updates.

## Badcase Logging Rule

User-reported product test failures must be recorded in the fixed badcase log:
`docs/BADCASES.md`.

Rules:
- If the user reports that a tested question, UI flow, API behavior, routing
  decision, tool call, or answer is wrong, first decide whether it is a real
  badcase. If it is, append or update an entry in `docs/BADCASES.md`.
- Record the original user prompt or action, expected behavior, actual behavior,
  root cause when known, affected area, verification, status, and fix commit
  when available.
- Keep entries chronological and stable. Do not delete resolved badcases; mark
  them as fixed and link the resolving commit.
- Do not paste secrets, private logs, full database rows, API keys, or personal
  data into the log. Summarize sensitive evidence.
- A fix for a badcase should usually include a regression test or a documented
  reason why no useful automated test exists.

## Module-Aware Verification

Choose verification based on what changed:

- `frontend/`: run the relevant build, lint, or UI smoke check
- `backend/` or `agents/`: run import checks, startup checks, health checks, or API smoke tests
- `src/memory/` or `fagent_cli.py`: run the relevant CLI or pytest subset
- `tests/`: run the touched tests or the narrowest useful regression set
- docs-only changes: verify commands, paths, filenames, and current behavior still match the repo

Prefer the smallest verification set that still proves the change is real.

## Documentation Sync Rules

If a change affects any of the items below, update the corresponding docs before commit:

- startup steps, ports, env vars, dependencies:
  update `README.md`, module `README.md`, or `backend/docs/DEBUG.md`
- API paths, request/response shapes, auth behavior, model list:
  update `backend/docs/API_USAGE.md`, module docs, or root/module README files
- architecture, routing, memory behavior, data flow:
  update `backend/docs/ARCHITECTURE.md`, `docs/memory/*`, or other affected design docs
- new durable docs under `docs/`:
  update `docs/README.md`

Do not leave behavior changes undocumented when the repo already has a doc covering that area.

## Cross-Project References

When working on architecture, runtime behavior, routing, logging, request tracing,
chat flow, memory handling, auth, or debugging strategy, and you need design
ideas or tradeoff references, review relevant approaches from these local projects
before settling on an implementation:

- `~/Learning/hermes-agent` or `https://github.com/NousResearch/hermes-agent`
- `~/Learning/openclaw` or `https://github.com/openclaw/openclaw`
- `~/Learning/opencode` or `https://github.com/anomalyco/opencode`
- `~/Learning/claude-code-rev`

Use them as references for strategy and tradeoffs, not as code to copy blindly.
If a collaborator does not have the local checkout, review the linked upstream repository instead.
Choose the parts that fit `FAgent`'s current stage and keep the implementation
coherent with the existing repo.
