# CLAUDE.md

- Treat `AGENTS.md` as the canonical project contract. Use it first when repo rules and docs overlap.
- Repo scope: VerifyIQ API regression automation only. Stay inside Python + pytest live regression work.
- Use `./.venv/bin/python` for repo-local commands. Bootstrap `.venv` with `python3 -m venv .venv` when needed.
- Planning source of truth: `docs/knowledge-base/repo-roadmap.md`.
- Default validation: `./.venv/bin/python tools/run_regression.py`
- Exact protected implementation/debug path: `./.venv/bin/python -m pytest tests/endpoints/parse/ -v`
- Broader validation when needed:
  - `./.venv/bin/python tools/run_regression.py --suite smoke`
  - `./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix`
  - `./.venv/bin/python tools/run_regression.py --suite full`
  - `./.venv/bin/python tools/run_regression.py --endpoint batch`
- Do not broaden scope, refactor working paths, or add local fixture fallbacks unless explicitly asked.
- `PARSE_FIXTURE_FILE` must stay `gs://`; request `fileType` mapping lives in `tests/endpoints/parse/file_types.py`.
- Trust live terminal output over stale counts or saved notes.
- Repo-local OpenCode and Codex automation handle Mind session recovery and checkpointing automatically in this repo; use `./.venv/bin/python tools/mind_session.py ...` only for troubleshooting, explicit durable summaries, or required Codex finish before handoff/commit.
- Response order for work reports:
  1. diagnosis
  2. file-by-file changes
  3. exact rerun command
