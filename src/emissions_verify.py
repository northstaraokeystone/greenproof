"""
GreenProof Emissions Verification - AgentProof receipt chain for corporate emissions.

Cross-verifies self-reported emissions against external data sources:
- Satellite imagery
- IoT sensors
- Utility data

PARADIGM: Real emissions follow stoichiometry (fuel → CO2 is deterministic).
Fabricated emissions don't follow physics.
"""

import json
from typing import Any

from .core import (
    EMISSIONS_DISCREPANCY_MAX,
    GREENPROOF_TENANT,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
    load_greenproof_spec,
)


def ingest_emissions_report(report: dict[str, Any], tenant_id: str = GREENPROOF_TENANT) -> dict[str, Any]:
    """Ingest corporate emissions report.

    Compute dual_hash. Emit ingest_receipt. Return report with hash.

    Args:
        report: Corporate emissions report dict containing:
            - company_id: str
            - reporting_period: str (e.g., "2024-Q4")
            - scope1_emissions: float (tonnes CO2e)
            - scope2_emissions: float (tonnes CO2e)
            - scope3_emissions: float (optional, tonnes CO2e)
        tenant_id: Tenant identifier

    Returns:
        dict: Report with added report_hash field
    """
    report_hash = dual_hash(json.dumps(report, sort_keys=True))
    report["report_hash"] = report_hash

    receipt = {
        "receipt_type": "ingest",
        "tenant_id": tenant_id,
        "payload_hash": report_hash,
        "source": "emissions_report",
        "record_count": 1,
        "metadata": {
            "company_id": report.get("company_id"),
            "reporting_period": report.get("reporting_period"),
        },
    }
    emit_receipt(receipt)

    return report


def cross_verify_emissions(
    report_hash: str,
    external_sources: list[dict[str, Any]],
    claimed_value: float,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Compare report hash against satellite/IoT/utility hashes.

    Compute match_score (0-1). Emit emissions_verify_receipt.

    Args:
        report_hash: Hash of original corporate report
        external_sources: List of external verification sources, each with:
            - source_type: str (satellite, iot_sensors, utility_data)
            - value: float (verified emissions in tonnes CO2e)
            - confidence: float (0-1)
        claimed_value: Claimed emissions from report (tonnes CO2e)
        tenant_id: Tenant identifier

    Returns:
        dict: Verification result with match_score and status
    """
    if not external_sources:
        return {
            "match_score": 0.0,
            "verified_value": 0.0,
            "claimed_value": claimed_value,
            "discrepancy_pct": 1.0,
            "status": "failed",
            "reason": "no_external_sources",
        }

    # Compute weighted average of external sources
    total_weight = sum(s.get("confidence", 0.5) for s in external_sources)
    verified_value = sum(s["value"] * s.get("confidence", 0.5) for s in external_sources) / total_weight

    # Compute discrepancy
    if claimed_value > 0:
        discrepancy_pct = abs(verified_value - claimed_value) / claimed_value
    else:
        discrepancy_pct = 1.0 if verified_value > 0 else 0.0

    # Match score: 1.0 = perfect match, 0.0 = complete mismatch
    match_score = max(0.0, 1.0 - discrepancy_pct)

    # Determine status
    spec = load_greenproof_spec()
    threshold = spec.get("emissions_discrepancy_max", EMISSIONS_DISCREPANCY_MAX)

    if discrepancy_pct <= threshold:
        status = "verified"
    elif discrepancy_pct <= threshold * 2:
        status = "flagged"
    else:
        status = "failed"

    # Compute external source hashes
    external_source_hashes = [dual_hash(json.dumps(s, sort_keys=True)) for s in external_sources]

    result = {
        "match_score": round(match_score, 4),
        "verified_value": round(verified_value, 2),
        "claimed_value": claimed_value,
        "discrepancy_pct": round(discrepancy_pct, 4),
        "status": status,
        "external_source_hashes": external_source_hashes,
    }

    # Emit verification receipt
    receipt = {
        "receipt_type": "emissions_verify",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "report_hash": report_hash,
        "external_source_hashes": external_source_hashes,
        "match_score": result["match_score"],
        "verified_value": result["verified_value"],
        "claimed_value": result["claimed_value"],
        "discrepancy_pct": result["discrepancy_pct"],
        "status": status,
    }
    emit_receipt(receipt)

    return result


def detect_discrepancy(
    report: dict[str, Any],
    verified: dict[str, Any],
    threshold: float | None = None,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Compare self-reported vs verified values.

    If delta > threshold, emit anomaly_receipt and call stoprule_emissions_discrepancy().

    Args:
        report: Original emissions report
        verified: Verification result from cross_verify_emissions
        threshold: Max allowed discrepancy (default from spec)
        tenant_id: Tenant identifier

    Returns:
        dict: Discrepancy analysis result

    Raises:
        StopRule: If discrepancy exceeds threshold
    """
    if threshold is None:
        spec = load_greenproof_spec()
        threshold = spec.get("emissions_discrepancy_max", EMISSIONS_DISCREPANCY_MAX)

    discrepancy_pct = verified.get("discrepancy_pct", 0.0)
    claimed = verified.get("claimed_value", 0.0)
    actual = verified.get("verified_value", 0.0)

    result = {
        "claimed_value": claimed,
        "verified_value": actual,
        "discrepancy_pct": discrepancy_pct,
        "threshold": threshold,
        "exceeds_threshold": discrepancy_pct > threshold,
        "delta": abs(actual - claimed),
    }

    if discrepancy_pct > threshold:
        stoprule_emissions_discrepancy(discrepancy_pct, threshold, tenant_id)

    return result


def stoprule_emissions_discrepancy(
    delta: float, threshold: float, tenant_id: str = GREENPROOF_TENANT
) -> None:
    """Emit anomaly_receipt and raise StopRule for emissions discrepancy.

    CLAUDEME §4.7: anomaly_receipt MUST be emitted BEFORE raising StopRule.

    Args:
        delta: Actual discrepancy percentage
        threshold: Maximum allowed discrepancy

    Raises:
        StopRule: Always raises after emitting anomaly_receipt
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="emissions_discrepancy",
        classification="violation",
        details={
            "discrepancy_pct": delta,
            "threshold": threshold,
            "delta_over_threshold": delta - threshold,
        },
        action="halt",
    )

    raise StopRule(
        f"Emissions discrepancy {delta:.2%} exceeds threshold {threshold:.2%}",
        classification="violation",
    )


def generate_synthetic_emissions_report(company_id: str = "TEST-CORP-001") -> dict[str, Any]:
    """Generate synthetic emissions report for testing.

    Args:
        company_id: Company identifier

    Returns:
        dict: Synthetic emissions report
    """
    return {
        "company_id": company_id,
        "reporting_period": "2024-Q4",
        "scope1_emissions": 15000.0,  # Direct emissions (tonnes CO2e)
        "scope2_emissions": 8500.0,  # Indirect from energy (tonnes CO2e)
        "scope3_emissions": 45000.0,  # Value chain emissions (tonnes CO2e)
        "methodology": "GHG Protocol",
        "boundary": "operational_control",
    }


def generate_synthetic_external_sources(
    claimed_value: float, discrepancy: float = 0.05
) -> list[dict[str, Any]]:
    """Generate synthetic external verification sources.

    Args:
        claimed_value: Value to base verification on
        discrepancy: How much to deviate from claimed (0.0 = exact match)

    Returns:
        list: List of external source dicts
    """
    import random

    random.seed(42)  # Reproducible for testing

    # Satellite slightly over-estimates
    satellite_value = claimed_value * (1 + discrepancy * 0.8)

    # IoT sensors slightly under-estimates
    iot_value = claimed_value * (1 - discrepancy * 0.5)

    # Utility data is closest to claimed
    utility_value = claimed_value * (1 + discrepancy * 0.2)

    return [
        {"source_type": "satellite", "value": satellite_value, "confidence": 0.85},
        {"source_type": "iot_sensors", "value": iot_value, "confidence": 0.92},
        {"source_type": "utility_data", "value": utility_value, "confidence": 0.95},
    ]
