from __future__ import annotations

import os

from dotenv import load_dotenv

SKIP_DOTENV_ENV_VAR = "VERIFYIQ_SKIP_DOTENV"

if os.getenv(SKIP_DOTENV_ENV_VAR, "").strip() != "1":
    load_dotenv()


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in the values."
        )
    return value


def optional(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()
