"""
GreenProof Carbon Credit Proof - Verify offset additionality.

Proves that claimed carbon removal would NOT have happened without the credit purchase.
Prevents selling existing forests as "new" carbon removal.

PARADIGM: Additionality is the delta between baseline (what would happen anyway)
and claimed removal. No delta = no additionality = invalid credit.
"""

import json
from typing import Any

from .core import (
    ADDITIONALITY_THRESHOLD,
    GREENPROOF_TENANT,
    SUPPORTED_REGISTRIES,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
    load_greenproof_spec,
)


def ingest_credit_claim(
    claim: dict[str, Any], registry: str, tenant_id: str = GREENPROOF_TENANT
) -> dict[str, Any]:
    """Ingest credit claim from registry.

    Compute dual_hash. Emit ingest_receipt.

    Args:
        claim: Credit claim dict containing:
            - credit_id: str
            - project_type: str (forestry, direct_air_capture, etc.)
            - claimed_tonnes: float
            - vintage_year: int
            - project_location: str (optional)
        registry: Registry name (verra, gold_standard, etc.)
        tenant_id: Tenant identifier

    Returns:
        dict: Claim with added claim_hash field
    """
    if registry not in SUPPORTED_REGISTRIES:
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="unsupported_registry",
            classification="warning",
            details={"registry": registry, "supported": SUPPORTED_REGISTRIES},
            action="flag",
        )

    claim_hash = dual_hash(json.dumps(claim, sort_keys=True))
    claim["claim_hash"] = claim_hash
    claim["registry"] = registry

    receipt = {
        "receipt_type": "ingest",
        "tenant_id": tenant_id,
        "payload_hash": claim_hash,
        "source": f"carbon_credit_{registry}",
        "record_count": 1,
        "metadata": {
            "credit_id": claim.get("credit_id"),
            "registry": registry,
            "project_type": claim.get("project_type"),
        },
    }
    emit_receipt(receipt)

    return claim


def compute_additionality(
    claim: dict[str, Any], baseline: dict[str, Any], tenant_id: str = GREENPROOF_TENANT
) -> dict[str, Any]:
    """Compare claimed removal against baseline.

    Additionality = (claimed - baseline) / claimed
    A score of 1.0 means 100% of the removal is additional.
    A score of 0.0 means the removal would happen anyway.

    Args:
        claim: Credit claim with claimed_tonnes
        baseline: Baseline data with baseline_tonnes (what would happen without project)
        tenant_id: Tenant identifier

    Returns:
        dict: Result with additionality_score and verification_status
    """
    claimed_tonnes = claim.get("claimed_tonnes", 0.0)
    baseline_tonnes = baseline.get("baseline_tonnes", 0.0)

    if claimed_tonnes <= 0:
        additionality_score = 0.0
    elif baseline_tonnes >= claimed_tonnes:
        # Baseline is higher than claimed - no additionality
        additionality_score = 0.0
    else:
        # How much is truly additional?
        additional_tonnes = claimed_tonnes - baseline_tonnes
        additionality_score = additional_tonnes / claimed_tonnes

    # Load threshold from spec
    spec = load_greenproof_spec()
    threshold = spec.get("additionality_threshold", ADDITIONALITY_THRESHOLD)

    # Determine status
    if additionality_score >= threshold:
        verification_status = "verified"
    elif additionality_score >= threshold * 0.8:
        verification_status = "flagged"
    else:
        verification_status = "failed"

    result = {
        "credit_id": claim.get("credit_id"),
        "registry": claim.get("registry"),
        "project_type": claim.get("project_type"),
        "claimed_tonnes": claimed_tonnes,
        "baseline_tonnes": baseline_tonnes,
        "additional_tonnes": max(0, claimed_tonnes - baseline_tonnes),
        "additionality_score": round(additionality_score, 4),
        "threshold": threshold,
        "verification_status": verification_status,
        "vintage_year": claim.get("vintage_year"),
    }

    # Emit carbon credit receipt
    receipt = {
        "receipt_type": "carbon_credit",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "credit_id": result["credit_id"],
        "registry": result["registry"],
        "project_type": result["project_type"],
        "claimed_tonnes": result["claimed_tonnes"],
        "baseline_tonnes": result["baseline_tonnes"],
        "additionality_score": result["additionality_score"],
        "vintage_year": result["vintage_year"],
        "registry_status": "active",  # Would be checked via verify_registry_entry
        "verification_status": verification_status,
    }
    emit_receipt(receipt)

    # Check if we should trigger stoprule
    if additionality_score < threshold * 0.5:  # Far below threshold
        stoprule_additionality_failure(additionality_score, threshold, tenant_id)

    return result


def verify_registry_entry(
    credit_id: str, registry: str, tenant_id: str = GREENPROOF_TENANT
) -> dict[str, Any]:
    """Query registry for credit existence and status.

    In v1.0, this is a synthetic check. Real registry API integration is v2.0.

    Args:
        credit_id: Credit identifier
        registry: Registry name
        tenant_id: Tenant identifier

    Returns:
        dict: Verification result with registry_status
    """
    # Synthetic registry check for v1.0
    # Real implementation would query Verra/Gold Standard APIs

    # Simulate registry lookup
    if credit_id.startswith("CANCELLED"):
        status = "cancelled"
    elif credit_id.startswith("RETIRED"):
        status = "retired"
    else:
        status = "active"

    result = {
        "credit_id": credit_id,
        "registry": registry,
        "registry_status": status,
        "verified": status == "active",
        "lookup_method": "synthetic_v1",
    }

    if status == "cancelled":
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="cancelled_credit",
            classification="violation",
            details={"credit_id": credit_id, "registry": registry},
            action="halt",
        )

    return result


def stoprule_additionality_failure(
    score: float, threshold: float, tenant_id: str = GREENPROOF_TENANT
) -> None:
    """Emit anomaly_receipt and raise StopRule for additionality failure.

    Args:
        score: Actual additionality score
        threshold: Required threshold

    Raises:
        StopRule: Always raises after emitting anomaly_receipt
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="additionality_failure",
        classification="violation",
        details={
            "additionality_score": score,
            "threshold": threshold,
            "deficit": threshold - score,
        },
        action="halt",
    )

    raise StopRule(
        f"Additionality score {score:.2%} below threshold {threshold:.2%}",
        classification="violation",
    )


def generate_synthetic_credit_claim(
    credit_id: str = "VCS-2024-001", registry: str = "verra"
) -> dict[str, Any]:
    """Generate synthetic credit claim for testing.

    Args:
        credit_id: Credit identifier
        registry: Registry name

    Returns:
        dict: Synthetic credit claim
    """
    return {
        "credit_id": credit_id,
        "project_type": "forestry",
        "claimed_tonnes": 10000.0,
        "vintage_year": 2024,
        "project_location": "Amazon Basin, Brazil",
        "methodology": "VM0007",
    }


def generate_synthetic_baseline(claimed_tonnes: float, additionality: float = 0.96) -> dict[str, Any]:
    """Generate synthetic baseline for testing.

    Args:
        claimed_tonnes: Claimed removal tonnes
        additionality: Desired additionality score (0-1)

    Returns:
        dict: Synthetic baseline
    """
    # baseline_tonnes = claimed_tonnes * (1 - additionality)
    baseline_tonnes = claimed_tonnes * (1 - additionality)

    return {
        "baseline_tonnes": baseline_tonnes,
        "baseline_method": "historical_average",
        "reference_period": "2019-2023",
        "deforestation_rate": 0.02,  # 2% annual baseline deforestation
    }
