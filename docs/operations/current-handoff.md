# Current Handoff

This file is no longer the canonical active handoff system for this project.

## Canonical Active State
- Mind project space: `projects/verifyiq-api-regression`
- Canonical active continuity lives in Mind checkpoints, memories, and session summaries.

## Use Instead
- List active checkpoints: `mind checkpoint list "projects/verifyiq-api-regression" --status active`
- Recover a specific checkpoint: `mind checkpoint recover "projects/verifyiq-api-regression" --name <checkpoint-name>`
- Search durable context: `mind search "<keywords>" --space "projects/verifyiq-api-regression" --detail`
- Refresh active state: `mind checkpoint set "projects/verifyiq-api-regression" "Goal" "Pending work" --notes "Current status"`

## Repo Boundary
- Keep active task state, working context, and handoff continuity in Mind only.
- Keep durable runbooks in `docs/operations/*`.
- Keep validated long-term findings in `docs/knowledge-base/*`.

Do not record live handoff state in this file anymore.
