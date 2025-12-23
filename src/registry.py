"""
GreenProof Registry - US-ONLY registry integration.

Government Waste Elimination Engine v3.0

KILLED: Gold Standard (too European, activist-heavy, no US enforcement leverage)
KILLED: Non-US Verra projects
FOCUS: US compliance/enforcement markets only

Supported US Registries:
- Verra (US projects only)
- American Carbon Registry
- Climate Action Reserve
"""

import json
from typing import Any

from .core import (
    SUPPORTED_REGISTRIES,
    TENANT_ID,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)


def us_only_mode() -> bool:
    """Check if US-only mode is enabled.

    Always returns True in v3. International registries killed.

    Returns:
        bool: Always True
    """
    return True


def filter_us_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to US-only projects.

    Removes non-US projects from list.

    Args:
        projects: List of project dicts

    Returns:
        list: Filtered US-only projects
    """
    us_locations = [
        "united states", "usa", "us", "america",
        "alaska", "hawaii", "puerto rico", "guam",
    ]

    us_states = [
        "alabama", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky",
        "louisiana", "maine", "maryland", "massachusetts", "michigan",
        "minnesota", "mississippi", "missouri", "montana", "nebraska",
        "nevada", "new hampshire", "new jersey", "new mexico", "new york",
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia",
        "washington", "west virginia", "wisconsin", "wyoming",
    ]

    all_us = set(us_locations + us_states)

    filtered = []
    for project in projects:
        location = project.get("project_location", "").lower()
        country = project.get("country", "").lower()

        if any(us_loc in location for us_loc in all_us) or country in all_us:
            filtered.append(project)

    return filtered


def get_supported_registries() -> list[str]:
    """Get list of supported US registries.

    Returns:
        list: Registry names
    """
    return SUPPORTED_REGISTRIES.copy()


def is_registry_supported(registry: str) -> bool:
    """Check if registry is supported.

    Args:
        registry: Registry name

    Returns:
        bool: True if supported
    """
    return registry.lower() in [r.lower() for r in SUPPORTED_REGISTRIES]


def verify_registry_project(
    project_id: str,
    registry: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify project exists in US registry.

    Args:
        project_id: Project identifier
        registry: Registry name
        tenant_id: Tenant identifier

    Returns:
        dict: Verification result
    """
    # Check registry is supported
    if not is_registry_supported(registry):
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="unsupported_registry",
            classification="warning",
            details={
                "registry": registry,
                "supported": SUPPORTED_REGISTRIES,
                "reason": "Non-US or deprecated registry",
            },
            action="flag",
        )
        return {
            "project_id": project_id,
            "registry": registry,
            "verified": False,
            "status": "unsupported_registry",
            "reason": "Registry not in US-only approved list",
        }

    # Synthetic verification for v3 (real API integration is v4)
    if project_id.startswith("CANCELLED"):
        status = "cancelled"
        verified = False
    elif project_id.startswith("RETIRED"):
        status = "retired"
        verified = False
    elif project_id.startswith("FOREIGN"):
        status = "non_us"
        verified = False
    else:
        status = "active"
        verified = True

    result = {
        "project_id": project_id,
        "registry": registry,
        "verified": verified,
        "status": status,
        "us_only_mode": True,
        "lookup_method": "synthetic_v3",
    }

    # Emit receipt (CLAUDEME LAW_1)
    receipt = {
        "receipt_type": "registry_verify",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "project_id": project_id,
        "registry": registry,
        "verified": verified,
        "status": status,
    }
    emit_receipt(receipt)

    return result


def cross_registry_check(
    project_id: str,
    registries: list[str] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Check project across US registries only.

    Args:
        project_id: Project identifier
        registries: Registries to check (default: all US)
        tenant_id: Tenant identifier

    Returns:
        dict: Cross-registry check result
    """
    if registries is None:
        registries = SUPPORTED_REGISTRIES

    # Filter to only supported registries
    registries = [r for r in registries if is_registry_supported(r)]

    results = []
    for registry in registries:
        result = verify_registry_project(project_id, registry, tenant_id)
        results.append(result)

    found_count = sum(1 for r in results if r["verified"])

    return {
        "project_id": project_id,
        "registries_checked": registries,
        "found_in": [r["registry"] for r in results if r["verified"]],
        "found_count": found_count,
        "us_only_mode": True,
    }


# === RESET FOR TESTING ===

def reset_registry():
    """Reset registry state for testing.

    No-op in v3 as registry is stateless.
    """
    pass


# === KILLED FUNCTIONS ===
# These existed in v2 but are removed in v3

def fetch_gold_standard(*args, **kwargs):
    """KILLED: Gold Standard integration removed in v3."""
    raise NotImplementedError(
        "Gold Standard integration KILLED in v3. "
        "Too European, activist-heavy, no US enforcement leverage."
    )


def normalize_gold_standard(*args, **kwargs):
    """KILLED: Gold Standard normalization removed in v3."""
    raise NotImplementedError(
        "Gold Standard integration KILLED in v3. "
        "Pivot to US compliance/enforcement markets only."
    )
