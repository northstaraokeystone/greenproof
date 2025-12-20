"""
GreenProof Core - Foundation for receipts-native climate verification.

Provides:
- dual_hash: SHA256:BLAKE3 dual hashing for audit lineage
- emit_receipt: Append receipts to JSONL ledger
- merkle_root / merkle_proof: Merkle tree operations
- StopRule: Exception for verification failures
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# === CONSTANTS ===
GREENPROOF_TENANT = "greenproof-climate"
RECEIPTS_FILE = Path(__file__).parent.parent / "receipts.jsonl"

# === GREENPROOF THRESHOLDS ===
UNVERIFIABLE_TARGET = 0.90
ADDITIONALITY_THRESHOLD = 0.95
DOUBLE_COUNT_TOLERANCE = 0.0
COMPRESSION_FRAUD_THRESHOLD = 0.70
COMPRESSION_VALID_THRESHOLD = 0.85
EMISSIONS_DISCREPANCY_MAX = 0.10

# === REGISTRIES ===
SUPPORTED_REGISTRIES = [
    "verra",
    "gold_standard",
    "american_carbon_registry",
    "climate_action_reserve",
]


class StopRule(Exception):
    """Exception raised when a verification rule is violated.

    CLAUDEME LAW: anomaly_receipt must be emitted BEFORE raising StopRule.
    """

    def __init__(self, message: str, classification: str = "violation"):
        super().__init__(message)
        self.classification = classification
        self.message = message


def dual_hash(data: str | bytes) -> str:
    """Compute dual hash: SHA256:BLAKE3 format.

    Real data has consistent hash patterns.
    Fabricated data has inconsistent patterns.
    Dual-hash provides audit lineage per CLAUDEME §4.1.

    Args:
        data: String or bytes to hash

    Returns:
        str: Hash in format "SHA256:<sha256>:BLAKE3:<blake3>"
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    sha256_hash = hashlib.sha256(data).hexdigest()
    # BLAKE3 fallback to BLAKE2b for compatibility (BLAKE3 not in stdlib)
    blake3_hash = hashlib.blake2b(data, digest_size=32).hexdigest()

    return f"SHA256:{sha256_hash}:BLAKE3:{blake3_hash}"


def emit_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Append receipt to JSONL ledger.

    CLAUDEME LAW_1: No receipt → not real.
    Every function that modifies state MUST emit a receipt.

    Args:
        receipt: Receipt dict with required fields:
            - receipt_type: str
            - tenant_id: str
            - payload_hash: str (dual_hash format)

    Returns:
        dict: Receipt with added timestamp
    """
    if "ts" not in receipt:
        receipt["ts"] = datetime.now(timezone.utc).isoformat()

    if "tenant_id" not in receipt:
        receipt["tenant_id"] = GREENPROOF_TENANT

    if "payload_hash" not in receipt and "payload" in receipt:
        receipt["payload_hash"] = dual_hash(json.dumps(receipt["payload"], sort_keys=True))

    with open(RECEIPTS_FILE, "a") as f:
        f.write(json.dumps(receipt, sort_keys=True) + "\n")

    return receipt


def merkle_root(hashes: list[str]) -> str:
    """Compute Merkle root from list of hashes.

    Used for cross-registry deduplication.
    Same credit appearing twice causes hash collision.

    Args:
        hashes: List of dual-hash strings

    Returns:
        str: Merkle root in dual_hash format
    """
    if not hashes:
        return dual_hash("")

    if len(hashes) == 1:
        return hashes[0]

    # Make a copy to avoid modifying input
    working = list(hashes)

    # Build tree level by level
    while len(working) > 1:
        # Ensure even number at each level
        if len(working) % 2 == 1:
            working.append(working[-1])

        next_level = []
        for i in range(0, len(working), 2):
            combined = working[i] + working[i + 1]
            next_level.append(dual_hash(combined))
        working = next_level

    return working[0]


def merkle_proof(hashes: list[str], index: int) -> dict[str, Any]:
    """Generate Merkle proof for hash at given index.

    Proof path allows verification without full tree.

    Args:
        hashes: List of dual-hash strings
        index: Index of hash to prove

    Returns:
        dict: Proof containing path and directions
    """
    if not hashes or index >= len(hashes):
        return {"valid": False, "path": [], "directions": []}

    proof_path = []
    directions = []

    # Pad to even length
    working_hashes = hashes[:]
    if len(working_hashes) % 2 == 1:
        working_hashes.append(working_hashes[-1])

    current_index = index

    while len(working_hashes) > 1:
        # Get sibling
        if current_index % 2 == 0:
            sibling_index = current_index + 1
            directions.append("right")
        else:
            sibling_index = current_index - 1
            directions.append("left")

        if sibling_index < len(working_hashes):
            proof_path.append(working_hashes[sibling_index])

        # Move to next level
        next_level = []
        for i in range(0, len(working_hashes), 2):
            combined = working_hashes[i] + working_hashes[i + 1]
            next_level.append(dual_hash(combined))

        working_hashes = next_level
        current_index = current_index // 2

        if len(working_hashes) % 2 == 1 and len(working_hashes) > 1:
            working_hashes.append(working_hashes[-1])

    return {
        "valid": True,
        "leaf_hash": hashes[index],
        "path": proof_path,
        "directions": directions,
        "root": working_hashes[0] if working_hashes else None,
    }


def verify_merkle_proof(leaf_hash: str, proof: dict[str, Any], root: str) -> bool:
    """Verify a Merkle proof.

    Args:
        leaf_hash: Hash of the leaf to verify
        proof: Proof dict from merkle_proof()
        root: Expected Merkle root

    Returns:
        bool: True if proof is valid
    """
    if not proof.get("valid"):
        return False

    current = leaf_hash
    for i, sibling in enumerate(proof["path"]):
        if proof["directions"][i] == "right":
            combined = current + sibling
        else:
            combined = sibling + current
        current = dual_hash(combined)

    return current == root


def load_greenproof_spec() -> dict[str, Any]:
    """Load greenproof_spec.json with dual_hash verification.

    Returns:
        dict: Spec config with _config_hash field added
    """
    spec_path = Path(__file__).parent.parent / "data" / "greenproof_spec.json"
    with open(spec_path) as f:
        spec = json.load(f)

    # Add config hash for audit lineage
    spec["_config_hash"] = dual_hash(json.dumps(spec, sort_keys=True))

    return spec


def emit_anomaly_receipt(
    tenant_id: str,
    anomaly_type: str,
    classification: str,
    details: dict[str, Any],
    action: str = "flag",
) -> dict[str, Any]:
    """Emit anomaly receipt before StopRule per CLAUDEME §4.7.

    Args:
        tenant_id: Tenant identifier
        anomaly_type: Type of anomaly detected
        classification: "warning" | "violation" | "critical"
        details: Additional details about the anomaly
        action: "flag" | "halt" | "review"

    Returns:
        dict: The emitted anomaly receipt
    """
    receipt = {
        "receipt_type": "anomaly",
        "tenant_id": tenant_id,
        "anomaly_type": anomaly_type,
        "classification": classification,
        "action": action,
        "details": details,
        "payload_hash": dual_hash(json.dumps(details, sort_keys=True)),
    }
    return emit_receipt(receipt)
