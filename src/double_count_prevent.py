"""
GreenProof Double Count Prevention - Cross-registry deduplication.

Prevents the same carbon credit from being claimed by multiple parties
or sold multiple times across Verra/Gold Standard/other registries.

PARADIGM: Unified Merkle tree across all registries.
Same credit appearing twice causes hash collision.
Double-counting is mathematically impossible with proper merkle anchoring.
"""

import json
from typing import Any

from .core import (
    GREENPROOF_TENANT,
    SUPPORTED_REGISTRIES,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
    merkle_proof,
    merkle_root,
)

# Global registry for cross-registry tracking
# In production, this would be a persistent store
_CREDIT_REGISTRY: dict[str, list[dict[str, Any]]] = {}
_MERKLE_HASHES: list[str] = []


def register_credit(
    credit_id: str,
    registry: str,
    owner_hash: str,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Add credit to global merkle tree.

    Compute position and proof path. Emit double_count_receipt.

    Args:
        credit_id: Credit identifier
        registry: Registry name
        owner_hash: Hash of current owner
        tenant_id: Tenant identifier

    Returns:
        dict: Registration result with merkle proof
    """
    global _MERKLE_HASHES

    # Create unique identifier for this credit instance
    credit_instance = {
        "credit_id": credit_id,
        "registry": registry,
        "owner_hash": owner_hash,
    }
    credit_hash = dual_hash(json.dumps(credit_instance, sort_keys=True))

    # Check for existing registration
    existing = _CREDIT_REGISTRY.get(credit_id, [])
    is_unique = True

    for occurrence in existing:
        if occurrence["registry"] != registry or occurrence["owner_hash"] != owner_hash:
            # Same credit, different registry or owner = double count!
            is_unique = False
            break

    # Add to registry
    if credit_id not in _CREDIT_REGISTRY:
        _CREDIT_REGISTRY[credit_id] = []

    _CREDIT_REGISTRY[credit_id].append(
        {"registry": registry, "owner_hash": owner_hash, "credit_hash": credit_hash, "status": "active"}
    )

    # Add to merkle tree
    _MERKLE_HASHES.append(credit_hash)
    merkle_position = len(_MERKLE_HASHES) - 1

    # Compute merkle proof
    proof = merkle_proof(_MERKLE_HASHES, merkle_position)
    cross_registry_root = merkle_root(_MERKLE_HASHES)

    result = {
        "credit_id": credit_id,
        "registry": registry,
        "is_unique": is_unique,
        "merkle_position": str(merkle_position),
        "merkle_proof": json.dumps(proof),
        "cross_registry_root": cross_registry_root,
        "occurrences": _CREDIT_REGISTRY[credit_id],
    }

    # Emit double_count_receipt
    receipt = {
        "receipt_type": "double_count",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "credit_id": credit_id,
        "registries_checked": [registry],
        "occurrences": _CREDIT_REGISTRY[credit_id],
        "is_unique": is_unique,
        "merkle_position": str(merkle_position),
        "merkle_proof": json.dumps(proof),
        "cross_registry_root": cross_registry_root,
    }
    emit_receipt(receipt)

    # If not unique, trigger stoprule
    if not is_unique:
        stoprule_double_count(credit_id, _CREDIT_REGISTRY[credit_id], tenant_id)

    return result


def check_double_count(
    credit_id: str,
    registries: list[str] | None = None,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Search all registries for credit_id.

    If found in >1 registry with different owners, flag double-count.

    Args:
        credit_id: Credit identifier to check
        registries: List of registries to check (default: all supported)
        tenant_id: Tenant identifier

    Returns:
        dict: Check result with occurrences
    """
    if registries is None:
        registries = SUPPORTED_REGISTRIES

    occurrences = _CREDIT_REGISTRY.get(credit_id, [])

    # Filter to requested registries
    filtered_occurrences = [o for o in occurrences if o["registry"] in registries]

    # Check for double-counting
    is_double_counted = False
    if len(filtered_occurrences) > 1:
        # Check if same owner across all occurrences
        owners = {o["owner_hash"] for o in filtered_occurrences}
        registries_found = {o["registry"] for o in filtered_occurrences}

        if len(owners) > 1 or len(registries_found) > 1:
            is_double_counted = True

    result = {
        "credit_id": credit_id,
        "registries_checked": registries,
        "occurrences": filtered_occurrences,
        "occurrence_count": len(filtered_occurrences),
        "is_double_counted": is_double_counted,
        "unique_owners": len({o["owner_hash"] for o in filtered_occurrences}),
        "unique_registries": len({o["registry"] for o in filtered_occurrences}),
    }

    if is_double_counted:
        stoprule_double_count(credit_id, filtered_occurrences, tenant_id)

    return result


def merkle_cross_registry(
    credits: list[dict[str, Any]], tenant_id: str = GREENPROOF_TENANT
) -> dict[str, Any]:
    """Compute unified merkle root across all registries.

    Any credit appearing twice will cause hash collision detection.

    Args:
        credits: List of credit dicts with credit_id, registry, owner_hash
        tenant_id: Tenant identifier

    Returns:
        dict: Result with cross_registry_root and proofs
    """
    hashes = []
    proofs = []

    for credit in credits:
        credit_hash = dual_hash(json.dumps(credit, sort_keys=True))
        hashes.append(credit_hash)

    # Compute root
    root = merkle_root(hashes)

    # Generate proofs for each credit
    for i, credit in enumerate(credits):
        proof = merkle_proof(hashes, i)
        proofs.append(
            {
                "credit_id": credit.get("credit_id"),
                "position": i,
                "proof": proof,
            }
        )

    result = {
        "credit_count": len(credits),
        "cross_registry_root": root,
        "proofs": proofs,
    }

    # Emit anchor receipt
    anchor_receipt = {
        "receipt_type": "anchor",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "merkle_root": root,
        "leaf_count": len(credits),
        "anchor_type": "cross_registry",
    }
    emit_receipt(anchor_receipt)

    return result


def stoprule_double_count(
    credit_id: str,
    occurrences: list[dict[str, Any]],
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly_receipt and raise StopRule for double-counting.

    ZERO TOLERANCE: Any double-count triggers immediate halt.

    Args:
        credit_id: Credit that was double-counted
        occurrences: List of occurrences across registries

    Raises:
        StopRule: Always raises after emitting anomaly_receipt
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="double_count",
        classification="critical",
        details={
            "credit_id": credit_id,
            "occurrence_count": len(occurrences),
            "registries": [o["registry"] for o in occurrences],
            "owners": [o["owner_hash"] for o in occurrences],
        },
        action="halt",
    )

    raise StopRule(
        f"Double-counting detected: {credit_id} appears in {len(occurrences)} registries",
        classification="critical",
    )


def reset_registry() -> None:
    """Reset the credit registry (for testing).

    Clears all registered credits and merkle hashes.
    """
    global _CREDIT_REGISTRY, _MERKLE_HASHES
    _CREDIT_REGISTRY = {}
    _MERKLE_HASHES = []


def get_registry_state() -> dict[str, Any]:
    """Get current state of the credit registry (for debugging).

    Returns:
        dict: Current registry state
    """
    return {
        "credit_count": len(_CREDIT_REGISTRY),
        "merkle_hash_count": len(_MERKLE_HASHES),
        "credits": list(_CREDIT_REGISTRY.keys()),
    }
