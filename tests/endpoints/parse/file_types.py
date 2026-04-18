"""Shared registry-to-API fileType mapping for /parse matrix-style flows."""
from __future__ import annotations

API_FILE_TYPE_ALIASES: dict[str, str] = {
    "TIN": "TINID",
    "ACR": "ACRICard",
    "WaterBill": "WaterUtilityBillingStatement",
}


def api_file_type_for(registry_file_type: str) -> str:
    """Return the API-accepted fileType for a registry fileType label."""
    return API_FILE_TYPE_ALIASES.get(registry_file_type, registry_file_type)
