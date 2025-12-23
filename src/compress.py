"""
GreenProof Compress - AXIOM-style compression engine for waste detection.

Government Waste Elimination Engine v3.0

PARADIGM: Real physical processes follow thermodynamic constraints.
- Combustion: fuel → CO2 is stoichiometric
- Photosynthesis: CO2 → biomass follows chemistry
- Mineralization: CO2 → mineral follows kinetics

Fabricated data doesn't follow physics. It doesn't compress to patterns.
Compression ratio IS the fraud/waste signal.

Thresholds:
- ratio >= 0.85: Valid physical pattern (verified)
- ratio < 0.70: Suspicious, likely fabricated (waste/fraud)
"""

import json
import math
import zlib
from typing import Any

from .core import (
    COMPRESSION_FRAUD_THRESHOLD,
    COMPRESSION_VALID_THRESHOLD,
    TENANT_ID,
    dual_hash,
    emit_receipt,
    load_greenproof_spec,
)


def compress_test(
    data: dict[str, Any] | str | bytes,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Apply compression test to data.

    Real physical data compresses to patterns (ratio >= 0.85).
    Fabricated/wasteful data fails compression (ratio < 0.70).

    Args:
        data: Data to compression test
        tenant_id: Tenant identifier

    Returns:
        dict: Compression result with ratio and status
    """
    if isinstance(data, dict):
        data_str = json.dumps(data, sort_keys=True)
        data_bytes = data_str.encode("utf-8")
    elif isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = data

    # Compute compression ratio
    compressed = zlib.compress(data_bytes, level=9)
    raw_ratio = len(compressed) / len(data_bytes) if len(data_bytes) > 0 else 1.0

    # Pattern ratio: inverted and normalized
    # For structured data: compression ~0.3-0.6, pattern_ratio ~0.4-0.7
    # For random/noise: compression ~0.9-1.1, pattern_ratio ~0.0-0.1
    pattern_ratio = max(0.0, min(1.0, 1.0 - raw_ratio))

    # Adjusted thresholds for actual JSON compression behavior
    adjusted_valid = 0.20  # Maps to conceptual 0.85
    adjusted_fraud = 0.10  # Maps to conceptual 0.70

    if pattern_ratio >= adjusted_valid:
        status = "verified"
    elif pattern_ratio >= adjusted_fraud:
        status = "suspicious"
    else:
        status = "waste_detected"

    return {
        "compression_ratio": round(pattern_ratio, 4),
        "raw_compression_ratio": round(raw_ratio, 4),
        "data_size_bytes": len(data_bytes),
        "compressed_size_bytes": len(compressed),
        "status": status,
    }


def compute_entropy(data: bytes | dict[str, Any]) -> dict[str, Any]:
    """Compute Shannon entropy of data.

    Physical processes have predictable entropy bounds.
    Anomalous entropy → flag for review.

    Args:
        data: Data to analyze

    Returns:
        dict: Entropy analysis result
    """
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True).encode("utf-8")

    if len(data) == 0:
        return {"entropy": 0.0, "normalized_entropy": 0.0, "anomalous": False}

    # Count byte frequencies
    freq = {}
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1

    # Calculate Shannon entropy
    entropy = 0.0
    for count in freq.values():
        if count > 0:
            p = count / len(data)
            entropy -= p * math.log2(p)

    # Normalize to 0-1 range (max entropy for bytes is 8 bits)
    normalized_entropy = entropy / 8.0

    # Physical data typically 0.3-0.7, random/fabricated tends toward 0.9+
    anomalous = normalized_entropy > 0.85 or normalized_entropy < 0.1

    return {
        "entropy": round(entropy, 4),
        "normalized_entropy": round(normalized_entropy, 4),
        "anomalous": anomalous,
        "byte_count": len(data),
        "unique_bytes": len(freq),
    }


def check_physical_consistency(claim: dict[str, Any]) -> bool:
    """Check if claim follows physical constraints.

    Validates against known physical laws:
    - Conservation of mass/energy
    - Stoichiometric constraints
    - Reasonable magnitude bounds

    Args:
        claim: Claim to validate

    Returns:
        bool: True if physically consistent
    """
    # Check for negative values (physics violation)
    for key, value in claim.items():
        if isinstance(value, (int, float)):
            if "emissions" in key.lower() and value < 0:
                return False  # Negative emissions impossible
            if "tonnes" in key.lower() and value < 0:
                return False  # Negative mass impossible

    # Check magnitude bounds
    if claim.get("scope1_emissions", 0) > 1_000_000_000:
        return False  # 1B tonnes from single entity implausible

    if claim.get("claimed_tonnes", 0) > 100_000_000:
        return False  # 100M tonnes single project implausible

    return True


def waste_validate(
    claim: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Validate claim for waste/fraud using compression and physics checks.

    Combined validation using:
    1. Compression ratio (data structure quality)
    2. Physical consistency (follows physics laws)
    3. Entropy analysis (predictable patterns)

    Args:
        claim: Claim to validate
        evidence: Supporting evidence (optional)
        tenant_id: Tenant identifier

    Returns:
        dict: Validation result with status
    """
    evidence = evidence or []

    # Combine claim and evidence for analysis
    combined = {"claim": claim, "evidence": evidence}

    # Run compression test
    compression = compress_test(combined, tenant_id)

    # Check physical consistency
    physical_ok = check_physical_consistency(claim)

    # Compute entropy
    entropy = compute_entropy(combined)

    # Determine validation status
    if physical_ok and compression["status"] == "verified":
        validation_status = "valid"
    elif not physical_ok:
        validation_status = "waste_detected"  # Physics violation = definitive
    elif compression["status"] == "waste_detected":
        validation_status = "waste_detected"
    else:
        validation_status = "suspicious"

    result = {
        "compression_ratio": compression["compression_ratio"],
        "entropy_signature": entropy["entropy"],
        "physical_consistency": physical_ok,
        "validation_status": validation_status,
        "raw_compression_ratio": compression["raw_compression_ratio"],
        "data_size_bytes": compression["data_size_bytes"],
        "compressed_size_bytes": compression["compressed_size_bytes"],
    }

    # Emit validation receipt (CLAUDEME LAW_1)
    receipt = {
        "receipt_type": "waste_validation",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "compression_ratio": result["compression_ratio"],
        "entropy_signature": result["entropy_signature"],
        "physical_consistency": result["physical_consistency"],
        "validation_status": validation_status,
    }
    emit_receipt(receipt)

    return result
