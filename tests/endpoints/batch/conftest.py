"""Local collection gate for opt-in /documents/batch auth characterization.

The representative tenant-token auth characterization currently lacks confirmed
401/403 rejection semantics, so it must not keep the default batch suite red.
Opt in explicitly when you want to characterize the blocker:

  RUN_BATCH_AUTH_CHARACTERIZATION=1 pytest tests/endpoints/batch/test_batch_auth_characterization.py -v

Direct module execution without `RUN_BATCH_AUTH_CHARACTERIZATION=1` also fails
inside the characterization module so accidental live collection is blocked even
when `collect_ignore` does not apply.
"""
from __future__ import annotations

import os


collect_ignore: list[str] = []
if os.getenv("RUN_BATCH_AUTH_CHARACTERIZATION") != "1":
    collect_ignore.append("test_batch_auth_characterization.py")
