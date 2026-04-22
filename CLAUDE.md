# CLAUDE.md

- Treat `AGENTS.md` as the canonical project contract. Use it first when repo rules and docs overlap.
- Repo scope: VerifyIQ API regression automation only. Stay inside Python + pytest live regression work.
- Use `./.venv/bin/python` for repo-local commands. Bootstrap `.venv` with `python3 -m venv .venv` when needed.
- Default validation: `./.venv/bin/python -m pytest tests/endpoints/parse/ -v`
- Broader validation when needed:
  - `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
  - `./.venv/bin/python tools/run_parse_full_regression.py`
  - `./.venv/bin/python -m pytest tests/endpoints/batch/ -v`
- Do not broaden scope, refactor working paths, or add local fixture fallbacks unless explicitly asked.
- `PARSE_FIXTURE_FILE` must stay `gs://`; request `fileType` mapping lives in `tests/endpoints/parse/file_types.py`.
- Trust live terminal output over stale counts or saved notes.
- Repo-local OpenCode automation handles Mind session recovery and checkpointing automatically in this repo; use `./.venv/bin/python tools/mind_session.py ...` only for troubleshooting or explicit durable summaries.
- Response order for work reports:
  1. diagnosis
  2. file-by-file changes
  3. exact rerun command
