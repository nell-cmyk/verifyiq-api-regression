from __future__ import annotations

import importlib
import sys

import pytest


_LIVE_ENV_VARS = (
    "BASE_URL",
    "TENANT_TOKEN",
    "API_KEY",
    "IAP_CLIENT_ID",
)


def _reload(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_config_import_is_safe_without_live_env(monkeypatch):
    monkeypatch.setenv("VERIFYIQ_SKIP_DOTENV", "1")
    for name in _LIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    module = _reload("tests.config")

    assert module.optional("BASE_URL") == ""


def test_require_raises_clear_error_when_env_missing(monkeypatch):
    monkeypatch.setenv("VERIFYIQ_SKIP_DOTENV", "1")
    monkeypatch.delenv("BASE_URL", raising=False)

    module = _reload("tests.config")

    with pytest.raises(RuntimeError, match="Required environment variable 'BASE_URL' is not set"):
        module.require("BASE_URL")


def test_client_import_is_safe_without_live_env(monkeypatch):
    monkeypatch.setenv("VERIFYIQ_SKIP_DOTENV", "1")
    for name in _LIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    _reload("tests.config")
    module = _reload("tests.client")

    assert hasattr(module, "make_client")


def test_make_client_fails_clearly_when_base_url_missing(monkeypatch):
    monkeypatch.setenv("VERIFYIQ_SKIP_DOTENV", "1")
    for name in _LIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    _reload("tests.config")
    module = _reload("tests.client")

    with pytest.raises(RuntimeError, match="Required environment variable 'BASE_URL' is not set"):
        module.make_client()
