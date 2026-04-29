"""Reporting and redaction contract helpers for the planned Automation Hub.

These helpers define the evidence shape and sanitization rules the future live
hub must honor. They do not write reports or call live endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


RAW_BODY_POLICY_DISALLOWED = "disallowed"
RAW_BODY_POLICY_POLICY_CONTROLLED = "policy_controlled"

REDACTED = "[REDACTED]"
EXCLUDED_BY_POLICY = "[EXCLUDED_BY_POLICY]"

REQUIRED_EVIDENCE_SECTIONS = (
    "run_metadata",
    "selected_nodes",
    "node_result_summaries",
    "request_metadata",
    "safe_response_metadata",
    "response_body_policy",
    "timing",
    "dependency_inputs",
    "dependency_outputs",
    "skips",
    "failures",
    "rerun_selectors",
)

REDACTION_EXCLUSIONS = (
    "tokens",
    "cookies",
    "auth headers",
    "tenant/API keys",
    "raw document identifiers",
    "raw GCS object names",
    "sensitive response bodies",
    "fraud results",
    "artifact/export payloads",
)

_REDACT_NORMALIZED_KEYS = {
    "apikey",
    "authorization",
    "cookie",
    "iapclientid",
    "proxyauthorization",
    "secret",
    "setcookie",
    "tenantid",
    "tenanttoken",
    "token",
    "xapikey",
    "xtenanttoken",
}

_EXCLUDE_NORMALIZED_KEYS = {
    "artifactpayload",
    "authenticityscore",
    "body",
    "docid",
    "documentid",
    "documentids",
    "exportpayload",
    "fileuri",
    "fraudresults",
    "fraudscore",
    "gcsobject",
    "gcsobjectname",
    "gcsuri",
    "mathematicalfraudreport",
    "metadatafraudreport",
    "payload",
    "rawbody",
    "requestbody",
    "responsebody",
    "sensitivebody",
}

_EXCLUDE_NORMALIZED_SUFFIXES = (
    "documentid",
    "gcsuri",
    "objectname",
)


@dataclass(frozen=True)
class ArtifactPolicy:
    """Per-node evidence policy for future hub report generation."""

    response_body_policy: str
    raw_body_persistence: str
    notes: tuple[str, ...] = ()

    @property
    def raw_body_allowed(self) -> bool:
        return self.raw_body_persistence == RAW_BODY_POLICY_POLICY_CONTROLLED


@dataclass(frozen=True)
class HubEvidenceContract:
    """Durable shape of evidence the future hub must be able to record."""

    required_sections: tuple[str, ...]
    redaction_exclusions: tuple[str, ...]
    raw_response_body_policy: str


def default_evidence_contract() -> HubEvidenceContract:
    return HubEvidenceContract(
        required_sections=REQUIRED_EVIDENCE_SECTIONS,
        redaction_exclusions=REDACTION_EXCLUSIONS,
        raw_response_body_policy=(
            "Raw response bodies are not automatically persisted; persistence is allowed "
            "only when the endpoint artifact policy permits it."
        ),
    )


def metadata_only_policy(*notes: str) -> ArtifactPolicy:
    return ArtifactPolicy(
        response_body_policy="metadata_only",
        raw_body_persistence=RAW_BODY_POLICY_DISALLOWED,
        notes=tuple(notes),
    )


def policy_controlled_body_policy(*notes: str) -> ArtifactPolicy:
    return ArtifactPolicy(
        response_body_policy="policy_controlled",
        raw_body_persistence=RAW_BODY_POLICY_POLICY_CONTROLLED,
        notes=tuple(notes),
    )


def redact_evidence_metadata(value: Any) -> Any:
    """Return a sanitized copy of evidence metadata.

    This is intentionally conservative. Fields that may carry auth material are
    redacted, while raw identifiers, bodies, fraud details, and export/artifact
    payloads are excluded by policy.
    """

    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            normalized = _normalize_key(str(key))
            if _should_exclude(normalized):
                sanitized[str(key)] = EXCLUDED_BY_POLICY
            elif _should_redact(normalized):
                sanitized[str(key)] = REDACTED
            else:
                sanitized[str(key)] = redact_evidence_metadata(child)
        return sanitized
    if isinstance(value, list):
        return [redact_evidence_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_evidence_metadata(item) for item in value)
    return value


def _normalize_key(key: str) -> str:
    return "".join(char for char in key.lower() if char.isalnum())


def _should_redact(normalized_key: str) -> bool:
    return (
        normalized_key in _REDACT_NORMALIZED_KEYS
        or normalized_key.endswith("token")
        or normalized_key.endswith("secret")
        or normalized_key.endswith("apikey")
    )


def _should_exclude(normalized_key: str) -> bool:
    return normalized_key in _EXCLUDE_NORMALIZED_KEYS or any(
        normalized_key.endswith(suffix) for suffix in _EXCLUDE_NORMALIZED_SUFFIXES
    )
