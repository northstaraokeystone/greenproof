"""
GreenProof Prove - Receipt chain and merkle proofs.

Identical pattern to AXIOM/ProofPack. Provides:
- Receipt chaining across all verification stages
- Merkle proof generation for individual claims
- Proof verification
- Batch summarization
- Human-readable audit trails
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import (
    GREENPROOF_TENANT,
    RECEIPTS_FILE,
    dual_hash,
    emit_receipt,
    merkle_proof,
    merkle_root,
    verify_merkle_proof,
)


def chain_receipts(
    receipts: list[dict[str, Any]],
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Compute merkle root from receipts and emit chain_receipt.

    Args:
        receipts: List of receipt dicts (must have payload_hash)
        tenant_id: Tenant identifier

    Returns:
        dict: chain_receipt with merkle_root
    """
    if not receipts:
        root = dual_hash("")
        hashes = []
    else:
        # Extract payload hashes
        hashes = [r.get("payload_hash", dual_hash(json.dumps(r, sort_keys=True)))
                  for r in receipts]
        root = merkle_root(hashes)

    # Summarize by type
    type_counts = {}
    for r in receipts:
        rtype = r.get("receipt_type", "unknown")
        type_counts[rtype] = type_counts.get(rtype, 0) + 1

    # Build and emit receipt
    receipt = {
        "receipt_type": "chain",
        "tenant_id": tenant_id,
        "merkle_root": root,
        "receipt_count": len(receipts),
        "type_counts": type_counts,
        "chained_at": datetime.now(timezone.utc).isoformat(),
        "payload_hash": dual_hash(root),
    }

    return emit_receipt(receipt)


def prove_claim(
    claim_id: str,
    receipts: list[dict[str, Any]],
    chain: dict[str, Any],
) -> dict[str, Any]:
    """Generate merkle proof for a specific claim.

    Args:
        claim_id: ID of claim to prove
        receipts: List of receipts (same as used for chain)
        chain: chain_receipt from chain_receipts()

    Returns:
        dict: Proof containing path and verification data
    """
    # Find all receipts for this claim
    claim_receipts = [r for r in receipts if r.get("claim_id") == claim_id]

    if not claim_receipts:
        return {
            "valid": False,
            "claim_id": claim_id,
            "reason": "claim_not_found",
            "receipts": [],
        }

    # Get hashes for all receipts
    all_hashes = [r.get("payload_hash", dual_hash(json.dumps(r, sort_keys=True)))
                  for r in receipts]

    # Generate proof for first claim receipt
    first_receipt = claim_receipts[0]
    first_hash = first_receipt.get("payload_hash", dual_hash(json.dumps(first_receipt, sort_keys=True)))

    try:
        index = all_hashes.index(first_hash)
        proof = merkle_proof(all_hashes, index)
    except ValueError:
        return {
            "valid": False,
            "claim_id": claim_id,
            "reason": "hash_not_found",
            "receipts": claim_receipts,
        }

    return {
        "valid": proof.get("valid", False),
        "claim_id": claim_id,
        "leaf_hash": first_hash,
        "proof_path": proof.get("path", []),
        "directions": proof.get("directions", []),
        "merkle_root": chain.get("merkle_root"),
        "receipts": claim_receipts,
        "receipt_count": len(claim_receipts),
    }


def verify_proof(
    claim_receipt: dict[str, Any],
    proof: dict[str, Any],
    root: str,
) -> bool:
    """Verify a merkle proof for a claim receipt.

    Args:
        claim_receipt: The receipt to verify
        proof: Proof from prove_claim()
        root: Expected merkle root

    Returns:
        bool: True if proof is valid
    """
    if not proof.get("valid"):
        return False

    leaf_hash = claim_receipt.get(
        "payload_hash",
        dual_hash(json.dumps(claim_receipt, sort_keys=True))
    )

    # Reconstruct merkle proof dict for verify_merkle_proof
    proof_dict = {
        "valid": True,
        "leaf_hash": leaf_hash,
        "path": proof.get("proof_path", []),
        "directions": proof.get("directions", []),
    }

    return verify_merkle_proof(leaf_hash, proof_dict, root)


def summarize_batch(
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate statistics from a batch of receipts.

    Args:
        receipts: List of receipt dicts

    Returns:
        dict: Aggregated statistics
    """
    if not receipts:
        return {
            "total_receipts": 0,
            "type_breakdown": {},
            "claim_count": 0,
            "fraud_summary": {},
            "compression_stats": {},
        }

    # Count by type
    type_breakdown = {}
    for r in receipts:
        rtype = r.get("receipt_type", "unknown")
        type_breakdown[rtype] = type_breakdown.get(rtype, 0) + 1

    # Unique claims
    claim_ids = set(r.get("claim_id") for r in receipts if r.get("claim_id"))

    # Fraud summary
    fraud_receipts = [r for r in receipts if r.get("receipt_type") == "fraud"]
    fraud_levels = {}
    for fr in fraud_receipts:
        level = fr.get("fraud_level", "unknown")
        fraud_levels[level] = fraud_levels.get(level, 0) + 1

    fraud_summary = {
        "total_checked": len(fraud_receipts),
        "by_level": fraud_levels,
        "rejection_rate": fraud_levels.get("likely_fraud", 0) + fraud_levels.get("confirmed_fraud", 0),
    }

    # Compression stats
    compression_receipts = [r for r in receipts if r.get("receipt_type") == "compression"]
    if compression_receipts:
        ratios = [r.get("compression_ratio", 0) for r in compression_receipts]
        compression_stats = {
            "count": len(compression_receipts),
            "avg_ratio": round(sum(ratios) / len(ratios), 4),
            "min_ratio": round(min(ratios), 4),
            "max_ratio": round(max(ratios), 4),
            "verified_count": len([r for r in compression_receipts if r.get("classification") == "verified"]),
            "suspect_count": len([r for r in compression_receipts if r.get("classification") == "suspect"]),
            "fraud_signal_count": len([r for r in compression_receipts if r.get("classification") == "fraud_signal"]),
        }
    else:
        compression_stats = {"count": 0}

    return {
        "total_receipts": len(receipts),
        "type_breakdown": type_breakdown,
        "claim_count": len(claim_ids),
        "fraud_summary": fraud_summary,
        "compression_stats": compression_stats,
    }


def format_audit_trail(
    claim_id: str,
    receipts: list[dict[str, Any]] | None = None,
) -> str:
    """Generate human-readable audit trail for a claim.

    Args:
        claim_id: ID of claim to audit
        receipts: Optional list of receipts (loads from file if None)

    Returns:
        str: Formatted audit trail
    """
    if receipts is None:
        receipts = load_receipts()

    # Find all receipts for this claim
    claim_receipts = [r for r in receipts if r.get("claim_id") == claim_id]

    if not claim_receipts:
        return f"No receipts found for claim: {claim_id}"

    # Sort by timestamp
    claim_receipts.sort(key=lambda r: r.get("ts", ""))

    lines = [
        f"═══════════════════════════════════════════════════════════════",
        f"AUDIT TRAIL: {claim_id}",
        f"═══════════════════════════════════════════════════════════════",
        f"Total receipts: {len(claim_receipts)}",
        f"",
    ]

    for i, r in enumerate(claim_receipts, 1):
        rtype = r.get("receipt_type", "unknown")
        ts = r.get("ts", "unknown")
        payload_hash = r.get("payload_hash", "unknown")[:32] + "..."

        lines.append(f"[{i}] {rtype.upper()}")
        lines.append(f"    Timestamp: {ts}")
        lines.append(f"    Hash: {payload_hash}")

        # Type-specific details
        if rtype == "compression":
            ratio = r.get("compression_ratio", 0)
            classification = r.get("classification", "unknown")
            lines.append(f"    Compression Ratio: {ratio:.4f}")
            lines.append(f"    Classification: {classification}")

        elif rtype == "fraud":
            score = r.get("fraud_score", 0)
            level = r.get("fraud_level", "unknown")
            recommendation = r.get("recommendation", "unknown")
            lines.append(f"    Fraud Score: {score:.4f}")
            lines.append(f"    Level: {level}")
            lines.append(f"    Recommendation: {recommendation}")

        elif rtype == "registry":
            duplicates = r.get("duplicates_found", 0)
            overlap = r.get("overlap_percentage", 0)
            lines.append(f"    Duplicates Found: {duplicates}")
            lines.append(f"    Overlap: {overlap:.2%}")

        elif rtype == "listing":
            status = r.get("status", "unknown")
            price = r.get("price_per_tco2e", 0)
            lines.append(f"    Status: {status}")
            lines.append(f"    Price: ${price:.2f}/tCO2e")

        elif rtype == "trade":
            buyer = r.get("buyer", "unknown")
            seller = r.get("seller", "unknown")
            price_total = r.get("price_total", 0)
            lines.append(f"    Buyer: {buyer}")
            lines.append(f"    Seller: {seller}")
            lines.append(f"    Total: ${price_total:.2f}")

        elif rtype == "energy":
            status = r.get("verification_status", "unknown")
            discrepancy = r.get("discrepancy_pct", 0)
            lines.append(f"    Status: {status}")
            lines.append(f"    Discrepancy: {discrepancy:.2%}")

        elif rtype == "ev":
            status = r.get("verification_status", "unknown")
            vehicles = r.get("vehicle_count", 0)
            lines.append(f"    Status: {status}")
            lines.append(f"    Vehicles: {vehicles}")

        lines.append("")

    lines.append("═══════════════════════════════════════════════════════════════")

    return "\n".join(lines)


def load_receipts(filepath: Path | None = None) -> list[dict[str, Any]]:
    """Load receipts from JSONL ledger file.

    Args:
        filepath: Optional path to receipts file

    Returns:
        list: List of receipt dicts
    """
    if filepath is None:
        filepath = RECEIPTS_FILE

    receipts = []
    if filepath.exists():
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        receipts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    return receipts


def get_receipts_for_claims(
    claim_ids: list[str],
    receipts: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Get all receipts for a list of claims.

    Args:
        claim_ids: List of claim IDs
        receipts: Optional list of receipts (loads from file if None)

    Returns:
        dict: Mapping of claim_id -> list of receipts
    """
    if receipts is None:
        receipts = load_receipts()

    result = {cid: [] for cid in claim_ids}

    for r in receipts:
        cid = r.get("claim_id")
        if cid in result:
            result[cid].append(r)

    return result
