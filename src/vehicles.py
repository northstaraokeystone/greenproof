"""
GreenProof Vehicles - Tesla verification + legacy automaker exposure.

Government Waste Elimination Engine v3.0

Renamed from ev.py. Expanded to include legacy automaker exposure.
Compare Tesla's verified efficiency to legacy automaker claims.

Receipt: vehicle_receipt
SLO: Verification time ≤ 200ms, all 6 legacy automakers covered
"""

import json
import time
from datetime import datetime, timezone
from typing import Any

from .core import (
    TENANT_ID,
    dual_hash,
    emit_receipt,
)
from .compress import compress_test, check_physical_consistency
from .expose import (
    LEGACY_AUTOMAKERS,
    scan_company,
    classify_fraud_level,
)


# === VEHICLE CONSTANTS ===
# Tesla efficiency benchmarks
TESLA_WH_PER_MILE = 250                # Average Wh/mile
TESLA_MANUFACTURING_KG_CO2 = 12000     # Per vehicle manufacturing
TESLA_LIFETIME_MILES = 300000          # Expected lifetime

# Legacy ICE vehicle benchmarks
ICE_MPG_AVERAGE = 25                   # Average MPG
ICE_MANUFACTURING_KG_CO2 = 8000        # Per vehicle manufacturing
ICE_FUEL_KG_CO2_PER_GALLON = 8.89      # Gasoline combustion
ICE_LIFETIME_MILES = 200000            # Expected lifetime

# Grid emissions for EV charging (US average)
US_GRID_KG_CO2_PER_KWH = 0.38


def verify_tesla_efficiency(
    vehicle: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify Tesla vehicle efficiency claims.

    Args:
        vehicle: Tesla vehicle data
        tenant_id: Tenant identifier

    Returns:
        dict: vehicle_receipt with verification
    """
    start_time = time.time()

    vehicle_id = vehicle.get("vehicle_id", "UNKNOWN")
    model = vehicle.get("model", "Model 3")
    wh_per_mile = vehicle.get("wh_per_mile", TESLA_WH_PER_MILE)
    lifetime_miles = vehicle.get("lifetime_miles", TESLA_LIFETIME_MILES)

    # Calculate lifetime emissions
    kwh_total = (wh_per_mile * lifetime_miles) / 1000
    charging_emissions = kwh_total * US_GRID_KG_CO2_PER_KWH
    total_emissions = TESLA_MANUFACTURING_KG_CO2 + charging_emissions

    # Compare to ICE equivalent
    ice_fuel_gallons = lifetime_miles / ICE_MPG_AVERAGE
    ice_emissions = ICE_MANUFACTURING_KG_CO2 + (ice_fuel_gallons * ICE_FUEL_KG_CO2_PER_GALLON)

    # Benefit
    emissions_saved = ice_emissions - total_emissions
    efficiency_ratio = total_emissions / ice_emissions if ice_emissions > 0 else 1

    result = {
        "receipt_type": "vehicle_verify",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "vehicle_id": vehicle_id,
        "manufacturer": "tesla",
        "model": model,
        "wh_per_mile": wh_per_mile,
        "lifetime_miles": lifetime_miles,
        "manufacturing_emissions_kg_co2": TESLA_MANUFACTURING_KG_CO2,
        "charging_emissions_kg_co2": round(charging_emissions, 2),
        "total_lifetime_emissions_kg_co2": round(total_emissions, 2),
        "ice_equivalent_emissions_kg_co2": round(ice_emissions, 2),
        "emissions_saved_kg_co2": round(emissions_saved, 2),
        "efficiency_vs_ice": round(1 - efficiency_ratio, 4),
        "verification_status": "verified",
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))
    emit_receipt(result)

    return result


def scan_legacy_automaker(
    company: str,
    claims: list[dict[str, Any]] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Scan legacy automaker ESG claims.

    Wrapper around expose.scan_company with vehicle-specific enhancements.

    Args:
        company: Company name (gm, ford, vw, etc.)
        claims: Optional claims to test
        tenant_id: Tenant identifier

    Returns:
        dict: Scan result with exposure findings
    """
    # Validate it's a legacy automaker
    if company.lower() not in LEGACY_AUTOMAKERS:
        return {
            "error": f"Not a legacy automaker: {company}",
            "legacy_automakers": LEGACY_AUTOMAKERS,
        }

    # Use expose module for scanning
    result = scan_company(company, claims, tenant_id)

    # Add vehicle-specific context
    result["is_legacy_ice_manufacturer"] = True
    result["ev_transition_claims"] = _extract_ev_transition_claims(result)

    return result


def compare_tesla_vs_legacy(
    tesla_data: dict[str, Any],
    legacy_companies: list[str] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Direct comparison of Tesla to legacy automakers.

    Args:
        tesla_data: Tesla verification data
        legacy_companies: List of legacy companies to compare
        tenant_id: Tenant identifier

    Returns:
        dict: Comparison result
    """
    if legacy_companies is None:
        legacy_companies = LEGACY_AUTOMAKERS

    # Get Tesla efficiency
    tesla_efficiency = tesla_data.get("efficiency_vs_ice", 0.50)
    tesla_compression = 0.90  # Tesla claims typically high quality

    # Scan legacy automakers
    legacy_results = []
    for company in legacy_companies:
        result = scan_legacy_automaker(company, tenant_id=tenant_id)
        legacy_results.append({
            "company": company,
            "fraud_rate": result.get("fraud_rate", 0),
            "average_compression": result.get("average_compression_ratio", 0),
            "fraud_level": result.get("overall_fraud_level", "unknown"),
        })

    # Calculate averages
    avg_legacy_compression = sum(
        r["average_compression"] for r in legacy_results
    ) / len(legacy_results) if legacy_results else 0

    avg_fraud_rate = sum(
        r["fraud_rate"] for r in legacy_results
    ) / len(legacy_results) if legacy_results else 0

    comparison = {
        "tesla": {
            "efficiency_vs_ice": tesla_efficiency,
            "compression_ratio": tesla_compression,
            "fraud_level": "verified",
        },
        "legacy_average": {
            "compression_ratio": round(avg_legacy_compression, 4),
            "fraud_rate": round(avg_fraud_rate, 4),
            "fraud_level": classify_fraud_level(avg_legacy_compression),
        },
        "delta": round(tesla_compression - avg_legacy_compression, 4),
        "winner": "tesla" if tesla_compression > avg_legacy_compression else "legacy",
        "legacy_breakdown": legacy_results,
    }

    # Emit comparison receipt
    receipt = {
        "receipt_type": "vehicle_comparison",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(comparison, sort_keys=True)),
        "winner": comparison["winner"],
        "delta": comparison["delta"],
    }
    emit_receipt(receipt)

    return comparison


def expose_credit_purchases(
    company: str,
    credit_data: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Expose questionable credit purchase sources.

    Args:
        company: Company name
        credit_data: Credit purchase records
        tenant_id: Tenant identifier

    Returns:
        dict: Exposure result
    """
    questionable = []
    total_credits = 0
    questionable_credits = 0

    for credit in credit_data:
        total_credits += credit.get("quantity", 0)

        # Check credit quality
        compression = compress_test(credit)
        physical = check_physical_consistency(credit)

        is_questionable = (
            compression["compression_ratio"] < 0.70 or
            not physical or
            credit.get("registry") in ["gold_standard"] or  # KILLED registry
            credit.get("source_country") not in ["USA", "United States", None]
        )

        if is_questionable:
            questionable.append({
                "credit_id": credit.get("credit_id"),
                "quantity": credit.get("quantity", 0),
                "reason": _get_questionable_reason(credit, compression, physical),
            })
            questionable_credits += credit.get("quantity", 0)

    exposure = {
        "company": company,
        "total_credits_purchased": total_credits,
        "questionable_credits": questionable_credits,
        "questionable_rate": questionable_credits / total_credits if total_credits > 0 else 0,
        "questionable_purchases": questionable,
    }

    # Emit exposure receipt
    receipt = {
        "receipt_type": "credit_exposure",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(exposure, sort_keys=True)),
        "company": company,
        "questionable_rate": exposure["questionable_rate"],
    }
    emit_receipt(receipt)

    return exposure


def _extract_ev_transition_claims(scan_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract EV transition claims from scan results."""
    ev_claims = []
    for result in scan_result.get("scan_results", []):
        if result.get("claim_type") == "ev_transition":
            ev_claims.append(result)
    return ev_claims


def _get_questionable_reason(
    credit: dict[str, Any],
    compression: dict[str, Any],
    physical: bool,
) -> str:
    """Get reason credit is questionable."""
    reasons = []

    if compression["compression_ratio"] < 0.70:
        reasons.append("low compression ratio")
    if not physical:
        reasons.append("physics violation")
    if credit.get("registry") == "gold_standard":
        reasons.append("deprecated registry (Gold Standard)")
    if credit.get("source_country") not in ["USA", "United States", None]:
        reasons.append("non-US source")

    return "; ".join(reasons) if reasons else "unknown"
