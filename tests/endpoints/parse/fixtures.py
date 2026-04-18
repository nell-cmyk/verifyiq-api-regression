import os


def _require_fixture(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "GCS-backed fixtures are required for /parse happy path tests. "
            "Set PARSE_FIXTURE_FILE to a gs:// URI and PARSE_FIXTURE_FILE_TYPE to the document type."
        )
    return value


PARSE_FIXTURE_FILE: str = _require_fixture("PARSE_FIXTURE_FILE")
PARSE_FIXTURE_FILE_TYPE: str = _require_fixture("PARSE_FIXTURE_FILE_TYPE")

if not PARSE_FIXTURE_FILE.startswith("gs://"):
    raise RuntimeError(
        f"PARSE_FIXTURE_FILE must be a gs:// URI (server-side fetch by the API). "
        f"Got: {PARSE_FIXTURE_FILE!r}"
    )

PARSE_REQUEST_BASE: dict = {
    "file": PARSE_FIXTURE_FILE,
    "fileType": PARSE_FIXTURE_FILE_TYPE,
    "pipeline": {"use_cache": False},
}
