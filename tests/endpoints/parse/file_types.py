"""Registry-to-request fileType policy for /parse."""
from __future__ import annotations

REQUEST_FILE_TYPE_ALIASES: dict[str, str] = {
    "TIN": "TINID",
    "ACR": "ACRICard",
    "WaterBill": "WaterUtilityBillingStatement",
}


def request_file_type_for(registry_file_type: str) -> str:
    """Return the request fileType for a registry fileType label."""
    value = registry_file_type.strip()
    if not value:
        raise ValueError("registry file_type must be a non-empty string")
    return REQUEST_FILE_TYPE_ALIASES.get(value, value)
