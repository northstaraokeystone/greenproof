"""
GreenProof Registry - Multi-registry integration for carbon credits.

Solves the double-counting problem across registries:
1. Verra (VCS) - largest voluntary market registry
2. Gold Standard - premium quality focus
3. ACR (American Carbon Registry) - US-focused
4. CAR (Climate Action Reserve) - California-focused

Key Problem:
  Same offset can be registered on multiple registries, sold multiple times.
  Europol: "Up to 90% of market volume fraudulent in some countries"

Solution:
  Identity hashing + cross-registry scan + overlap detection
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .core import (
    GREENPROOF_TENANT,
    SUPPORTED_REGISTRIES,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)

# === REGISTRY MAPPINGS ===
# Maps registry-specific field names to GreenProof canonical schema
REGISTRY_FIELD_MAPPINGS = {
    "verra": {
        "project_id": "ID",
        "project_name": "Name",
        "methodology": "Methodology",
        "vintage_year": "Vintage",
        "quantity_tco2e": "Quantity",
        "status": "Status",
        "country": "Country/Area",
        "verification_body": "Validation/Verification Body",
    },
    "gold_standard": {
        "project_id": "GS ID",
        "project_name": "Project Name",
        "methodology": "Methodology",
        "vintage_year": "Vintage Year",
        "quantity_tco2e": "VERs Issued",
        "status": "Status",
        "country": "Host Country",
        "verification_body": "Validation Body",
    },
    "acr": {
        "project_id": "Project ID",
        "project_name": "Project Title",
        "methodology": "Protocol",
        "vintage_year": "Vintage Year",
        "quantity_tco2e": "ERTs Issued",
        "status": "Project Status",
        "country": "Location",
        "verification_body": "Verification Body",
    },
    "car": {
        "project_id": "Project ID",
        "project_name": "Project Name",
        "methodology": "Protocol",
        "vintage_year": "Vintage",
        "quantity_tco2e": "CRTs Issued",
        "status": "Status",
        "country": "Project Location",
        "verification_body": "Verifier",
    },
}

# === GLOBAL REGISTRY STATE (for deduplication) ===
_IDENTITY_REGISTRY: dict[str, list[dict[str, Any]]] = {}


def reset_registry() -> None:
    """Reset global registry state. For testing only."""
    global _IDENTITY_REGISTRY
    _IDENTITY_REGISTRY = {}


def get_registry_state() -> dict[str, list[dict[str, Any]]]:
    """Get current registry state. For debugging."""
    return _IDENTITY_REGISTRY.copy()


def normalize_claim(claim: dict[str, Any], registry: str) -> dict[str, Any]:
    """Normalize registry-specific claim to GreenProof canonical schema.

    Args:
        claim: Raw claim from registry
        registry: Registry name (verra, gold_standard, acr, car)

    Returns:
        dict: Normalized claim in GreenProof schema
    """
    registry_lower = registry.lower().replace("-", "_").replace(" ", "_")

    if registry_lower not in REGISTRY_FIELD_MAPPINGS:
        # Unknown registry, return as-is with registry tag
        claim["registry"] = registry_lower
        return claim

    mapping = REGISTRY_FIELD_MAPPINGS[registry_lower]

    normalized = {
        "claim_id": claim.get("claim_id", str(uuid.uuid4())),
        "registry": registry_lower,
    }

    # Apply field mappings
    for canonical_field, registry_field in mapping.items():
        if registry_field in claim:
            normalized[canonical_field] = claim[registry_field]
        elif canonical_field in claim:
            normalized[canonical_field] = claim[canonical_field]

    # Copy any fields not in mapping
    for key, value in claim.items():
        if key not in normalized and key not in mapping.values():
            normalized[key] = value

    return normalized


def hash_claim_identity(claim: dict[str, Any]) -> str:
    """Create identity hash for deduplication.

    Identity is based on: project_id + vintage_year + quantity
    This catches the same offset registered across multiple registries.

    Args:
        claim: Normalized claim dict

    Returns:
        str: Identity hash (dual-hash format)
    """
    # Build identity string from key fields
    identity_parts = [
        str(claim.get("project_id", "")),
        str(claim.get("vintage_year", "")),
        str(claim.get("quantity_tco2e", "")),
        str(claim.get("location", {}).get("country", claim.get("country", ""))),
    ]
    identity_string = "|".join(identity_parts)
    return dual_hash(identity_string)


def register_claim(
    claim: dict[str, Any],
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Register claim in global registry for deduplication tracking.

    Args:
        claim: Normalized claim dict
        tenant_id: Tenant identifier

    Returns:
        dict: registry_receipt with duplicate info
    """
    global _IDENTITY_REGISTRY

    identity_hash = hash_claim_identity(claim)
    claim_id = claim.get("claim_id", str(uuid.uuid4()))
    registry = claim.get("registry", "unknown")

    # Check for existing entries
    existing = _IDENTITY_REGISTRY.get(identity_hash, [])
    duplicates_found = len(existing)
    duplicate_registries = list(set(e["registry"] for e in existing))

    # Calculate overlap percentage
    if duplicates_found > 0:
        unique_registries = len(set(duplicate_registries + [registry]))
        overlap_pct = (duplicates_found + 1 - unique_registries) / (duplicates_found + 1)
    else:
        overlap_pct = 0.0

    # Add to registry
    _IDENTITY_REGISTRY.setdefault(identity_hash, []).append({
        "claim_id": claim_id,
        "registry": registry,
        "ts": datetime.now(timezone.utc).isoformat(),
    })

    # Build and emit receipt
    receipt = {
        "receipt_type": "registry",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "source_registry": registry,
        "identity_hash": identity_hash,
        "duplicates_found": duplicates_found,
        "duplicate_registries": duplicate_registries,
        "overlap_percentage": round(overlap_pct, 4),
        "normalization_applied": True,
        "payload_hash": dual_hash(json.dumps(claim, sort_keys=True)),
    }

    return emit_receipt(receipt)


def check_duplicate(
    identity_hash: str,
    ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Check if claim identity already exists.

    Args:
        identity_hash: Identity hash from hash_claim_identity()
        ledger: Optional ledger to search (uses global if None)

    Returns:
        dict: First matching claim, or None if not found
    """
    global _IDENTITY_REGISTRY

    if ledger is not None:
        # Search provided ledger
        for entry in ledger:
            if hash_claim_identity(entry) == identity_hash:
                return entry
        return None

    # Search global registry
    existing = _IDENTITY_REGISTRY.get(identity_hash, [])
    if existing:
        return existing[0]
    return None


def fetch_registry_data(
    registry: str,
    project_id: str,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Fetch project data from registry API.

    NOTE: v2 uses synthetic data. Real API integration is v3 scope.

    Args:
        registry: Registry name
        project_id: Project identifier
        tenant_id: Tenant identifier

    Returns:
        dict: Project data (synthetic in v2)
    """
    # v2: Return synthetic data matching registry schema
    registry_lower = registry.lower().replace("-", "_").replace(" ", "_")

    synthetic_data = {
        "project_id": project_id,
        "registry": registry_lower,
        "status": "active",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,  # Flag for v2
    }

    # Emit fetch receipt for audit trail
    emit_receipt({
        "receipt_type": "registry_fetch",
        "tenant_id": tenant_id,
        "registry": registry_lower,
        "project_id": project_id,
        "status": "synthetic",
        "payload_hash": dual_hash(json.dumps(synthetic_data, sort_keys=True)),
    })

    return synthetic_data


def cross_registry_scan(
    claim: dict[str, Any],
    tenant_id: str = GREENPROOF_TENANT,
) -> list[dict[str, Any]]:
    """Scan all registries for matching claims.

    This is the core double-counting detection mechanism.

    Args:
        claim: Claim to scan for
        tenant_id: Tenant identifier

    Returns:
        list: Matching claims from all registries
    """
    global _IDENTITY_REGISTRY

    identity_hash = hash_claim_identity(claim)
    matches = []

    # Check global registry
    existing = _IDENTITY_REGISTRY.get(identity_hash, [])
    matches.extend(existing)

    # Emit scan receipt
    emit_receipt({
        "receipt_type": "registry_scan",
        "tenant_id": tenant_id,
        "claim_id": claim.get("claim_id"),
        "identity_hash": identity_hash,
        "matches_found": len(matches),
        "registries_scanned": SUPPORTED_REGISTRIES,
        "payload_hash": dual_hash(json.dumps({
            "identity_hash": identity_hash,
            "matches": len(matches),
        }, sort_keys=True)),
    })

    return matches


def calculate_overlap(claims: list[dict[str, Any]]) -> float:
    """Calculate percentage overlap (double-counting) in a set of claims.

    Args:
        claims: List of claims to analyze

    Returns:
        float: Overlap percentage (0.0 = no duplicates, 1.0 = all duplicates)
    """
    if not claims:
        return 0.0

    # Hash all claims
    identity_hashes = [hash_claim_identity(c) for c in claims]

    # Count duplicates
    unique_hashes = set(identity_hashes)
    total = len(identity_hashes)
    unique = len(unique_hashes)

    if total == 0:
        return 0.0

    # Overlap = (total - unique) / total
    overlap = (total - unique) / total
    return round(overlap, 4)


def stoprule_duplicate_claim(
    claim_id: str,
    duplicates: list[dict[str, Any]],
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly and raise StopRule for duplicate claim.

    CLAUDEME LAW: anomaly_receipt MUST be emitted BEFORE raising StopRule.

    Args:
        claim_id: ID of duplicate claim
        duplicates: List of existing claims
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="duplicate_claim",
        classification="critical",
        details={
            "claim_id": claim_id,
            "duplicate_count": len(duplicates),
            "duplicate_registries": list(set(d.get("registry") for d in duplicates)),
        },
        action="halt",
    )
    raise StopRule(
        f"Duplicate claim detected: {claim_id} found in {len(duplicates)} registries",
        classification="critical",
    )


# === SYNTHETIC DATA GENERATORS (for testing) ===


def generate_unique_claims(count: int = 10) -> list[dict[str, Any]]:
    """Generate unique carbon claims for testing.

    Args:
        count: Number of claims to generate

    Returns:
        list: Unique claims
    """
    claims = []
    for i in range(count):
        claims.append({
            "claim_id": str(uuid.uuid4()),
            "registry": SUPPORTED_REGISTRIES[i % len(SUPPORTED_REGISTRIES)],
            "project_id": f"PROJECT-{i:04d}",
            "vintage_year": 2020 + (i % 5),
            "quantity_tco2e": 1000.0 + (i * 100),
            "project_type": "forest_conservation",
            "location": {"country": "BR"},
        })
    return claims


def generate_duplicate_claims(count: int = 5) -> list[dict[str, Any]]:
    """Generate duplicate carbon claims for testing.

    Same project registered on multiple registries = double-counting.

    Args:
        count: Number of duplicate sets to generate

    Returns:
        list: Claims with duplicates
    """
    claims = []
    for i in range(count):
        base_claim = {
            "project_id": f"DUP-PROJECT-{i:04d}",
            "vintage_year": 2023,
            "quantity_tco2e": 5000.0,
            "project_type": "renewable_energy",
            "location": {"country": "IN"},
        }
        # Same project on multiple registries
        for registry in ["verra", "gold_standard"]:
            claim = base_claim.copy()
            claim["claim_id"] = str(uuid.uuid4())
            claim["registry"] = registry
            claims.append(claim)
    return claims
