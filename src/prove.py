"""
GreenProof Prove - Receipt chain and merkle proof infrastructure.

Government Waste Elimination Engine v3.0

All waste findings anchored with merkle proof.
Immutable receipts for DOGE alignment.

Receipt: anchor_receipt, proof_receipt
SLO: Proof generation ≤ 50ms, verification ≤ 10ms
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import (
    RECEIPTS_FILE,
    TENANT_ID,
    dual_hash,
    emit_receipt,
    merkle_proof,
    merkle_root,
    verify_merkle_proof,
)


# === PROOF CHAIN STATE ===
_PROOF_CHAIN: list[str] = []  # List of receipt hashes
_ANCHORS: list[dict[str, Any]] = []  # List of anchor points


def add_to_chain(
    receipt_hash: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Add receipt hash to proof chain.

    Args:
        receipt_hash: Receipt hash to add
        tenant_id: Tenant identifier

    Returns:
        dict: Chain addition result
    """
    _PROOF_CHAIN.append(receipt_hash)
    position = len(_PROOF_CHAIN) - 1

    return {
        "receipt_hash": receipt_hash,
        "position": position,
        "chain_length": len(_PROOF_CHAIN),
    }


def generate_proof(
    receipt_hash: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate merkle proof for receipt.

    Args:
        receipt_hash: Receipt hash to prove
        tenant_id: Tenant identifier

    Returns:
        dict: Proof result
    """
    start_time = time.time()

    if receipt_hash not in _PROOF_CHAIN:
        return {
            "valid": False,
            "error": "Receipt not in chain",
        }

    index = _PROOF_CHAIN.index(receipt_hash)
    proof = merkle_proof(_PROOF_CHAIN, index)
    root = merkle_root(_PROOF_CHAIN)

    result = {
        "receipt_hash": receipt_hash,
        "position": index,
        "merkle_proof": proof,
        "merkle_root": root,
        "chain_length": len(_PROOF_CHAIN),
        "proof_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    # Emit proof receipt
    receipt = {
        "receipt_type": "proof_generated",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "target_hash": receipt_hash,
        "merkle_root": root,
    }
    emit_receipt(receipt)

    return result


def verify_proof(
    receipt_hash: str,
    proof: dict[str, Any],
    expected_root: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify merkle proof for receipt.

    Args:
        receipt_hash: Receipt hash to verify
        proof: Merkle proof dict
        expected_root: Expected merkle root
        tenant_id: Tenant identifier

    Returns:
        dict: Verification result
    """
    start_time = time.time()

    valid = verify_merkle_proof(receipt_hash, proof, expected_root)

    result = {
        "receipt_hash": receipt_hash,
        "valid": valid,
        "expected_root": expected_root,
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    return result


def anchor_chain(
    anchor_type: str = "periodic",
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Create anchor point in proof chain.

    Args:
        anchor_type: Type of anchor (periodic, doge, cbam, etc.)
        tenant_id: Tenant identifier

    Returns:
        dict: Anchor result
    """
    if not _PROOF_CHAIN:
        return {"error": "No receipts in chain to anchor"}

    root = merkle_root(_PROOF_CHAIN)
    anchor_height = len(_ANCHORS)

    anchor = {
        "anchor_height": anchor_height,
        "merkle_root": root,
        "leaf_count": len(_PROOF_CHAIN),
        "anchor_type": anchor_type,
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "previous_anchor": _ANCHORS[-1]["merkle_root"] if _ANCHORS else None,
    }

    _ANCHORS.append(anchor)

    # Emit anchor receipt
    receipt = {
        "receipt_type": "anchor",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(anchor, sort_keys=True)),
        "merkle_root": root,
        "leaf_count": len(_PROOF_CHAIN),
        "anchor_type": anchor_type,
        "previous_anchor": anchor["previous_anchor"],
        "chain_height": anchor_height,
    }
    emit_receipt(receipt)

    return anchor


def get_chain_state() -> dict[str, Any]:
    """Get current proof chain state.

    Returns:
        dict: Chain state
    """
    return {
        "chain_length": len(_PROOF_CHAIN),
        "anchor_count": len(_ANCHORS),
        "current_root": merkle_root(_PROOF_CHAIN) if _PROOF_CHAIN else None,
        "latest_anchor": _ANCHORS[-1] if _ANCHORS else None,
    }


def load_receipts_to_chain(
    receipts_file: Path = RECEIPTS_FILE,
) -> int:
    """Load receipts from file into proof chain.

    Args:
        receipts_file: Path to receipts file

    Returns:
        int: Number of receipts loaded
    """
    if not receipts_file.exists():
        return 0

    count = 0
    with open(receipts_file) as f:
        for line in f:
            try:
                receipt = json.loads(line.strip())
                receipt_hash = receipt.get("payload_hash", dual_hash(line))
                add_to_chain(receipt_hash)
                count += 1
            except json.JSONDecodeError:
                continue

    return count


def batch_prove(
    receipt_hashes: list[str],
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Generate proofs for multiple receipts.

    Args:
        receipt_hashes: List of receipt hashes
        tenant_id: Tenant identifier

    Returns:
        list: List of proof results
    """
    return [generate_proof(h, tenant_id) for h in receipt_hashes]


def verify_chain_integrity(
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify integrity of entire proof chain.

    Args:
        tenant_id: Tenant identifier

    Returns:
        dict: Integrity check result
    """
    start_time = time.time()

    if not _PROOF_CHAIN:
        return {"valid": True, "chain_length": 0, "reason": "Empty chain"}

    # Verify each receipt can be proven
    invalid = []
    root = merkle_root(_PROOF_CHAIN)

    for i, receipt_hash in enumerate(_PROOF_CHAIN):
        proof = merkle_proof(_PROOF_CHAIN, i)
        if not verify_merkle_proof(receipt_hash, proof, root):
            invalid.append(i)

    valid = len(invalid) == 0

    result = {
        "valid": valid,
        "chain_length": len(_PROOF_CHAIN),
        "invalid_positions": invalid,
        "current_root": root,
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    # Emit integrity receipt
    receipt = {
        "receipt_type": "chain_integrity",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "valid": valid,
        "chain_length": len(_PROOF_CHAIN),
    }
    emit_receipt(receipt)

    return result


def reset_chain():
    """Reset proof chain (for testing)."""
    global _PROOF_CHAIN, _ANCHORS
    _PROOF_CHAIN = []
    _ANCHORS = []
