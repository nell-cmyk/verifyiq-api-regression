import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in the values."
        )
    return value


BASE_URL: str = _require("BASE_URL")
TENANT_TOKEN: str = _require("TENANT_TOKEN")
API_KEY: str = _require("API_KEY")
IAP_CLIENT_ID: str = _require("IAP_CLIENT_ID")
