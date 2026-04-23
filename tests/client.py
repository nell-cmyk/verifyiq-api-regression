import httpx

from tests import config
from tests.endpoints.batch.artifacts import attach as attach_batch_artifacts
from tests.endpoints.parse.artifacts import attach as attach_parse_artifacts

# IAP OIDC token is stable for ~1h; mint once per process.
_iap_token_cache: str | None = None


def get_iap_bearer() -> str:
    """Mint a Google-signed OIDC ID token for the IAP-protected resource.

    Requires Application Default Credentials — set GOOGLE_APPLICATION_CREDENTIALS
    to a service account JSON file whose principal is granted
    `roles/iap.httpsResourceAccessor` on the target backend.
    """
    global _iap_token_cache
    if _iap_token_cache:
        return _iap_token_cache

    try:
        import google.auth.transport.requests
        from google.oauth2 import id_token
    except ImportError as exc:
        raise RuntimeError(
            "google-auth is required for IAP access. Install with: pip install google-auth"
        ) from exc

    request = google.auth.transport.requests.Request()
    audience = config.require("IAP_CLIENT_ID")
    try:
        _iap_token_cache = id_token.fetch_id_token(request, audience)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to mint IAP OIDC token for audience {audience!r}. "
            "Verify GOOGLE_APPLICATION_CREDENTIALS points to a service account JSON "
            "with roles/iap.httpsResourceAccessor on the backend. "
            f"Underlying error: {exc}"
        ) from exc
    return _iap_token_cache


def platform_auth_headers() -> dict[str, str]:
    """Headers required to reach the app past IAP and satisfy the app's BearerAuth.

    IAP token rides on `Proxy-Authorization` so the app's `Authorization` header
    (the `sk_...` API key) is not consumed/overwritten by IAP.
    """
    return {
        "Proxy-Authorization": f"Bearer {get_iap_bearer()}",
        "Authorization": f"Bearer {config.require('API_KEY')}",
    }


def make_client(timeout: float = 60.0) -> httpx.Client:
    client = httpx.Client(
        base_url=config.require("BASE_URL"),
        headers={
            **platform_auth_headers(),
            "X-Tenant-Token": config.require("TENANT_TOKEN"),
        },
        timeout=timeout,
    )
    attach_batch_artifacts(client)
    attach_parse_artifacts(client)
    # Opt-in regression reporter hooks. No-op unless REGRESSION_REPORT=1.
    from tests.reporting import is_enabled
    if is_enabled():
        from tests.reporting.httpx_hooks import attach
        attach(client)
    return client
