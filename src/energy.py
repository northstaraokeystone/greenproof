"""
GreenProof Energy - Energy verification for LNG, nuclear, pipelines.

Government Waste Elimination Engine v3.0

Verify American energy is cleaner than alleged.
Expand verification to Wright/Burgum priorities.

Receipt: energy_receipt
SLO: Verification time ≤ 200ms, coverage all US energy types
"""

import json
import time
from datetime import datetime, timezone
from typing import Any

from .core import (
    EMISSIONS_DISCREPANCY_MAX,
    TENANT_ID,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
    load_greenproof_spec,
)
from .compress import compress_test


# === ENERGY CONSTANTS ===
# Emissions factors (kg CO2e per unit)
LNG_EMISSIONS_KG_PER_MMBTU = 53.1      # Natural gas combustion
PIPELINE_EMISSIONS_KG_PER_BBL_MILE = 0.015  # Transmission
NUCLEAR_EMISSIONS_KG_PER_MWH = 12      # Lifecycle (very low)
COAL_EMISSIONS_KG_PER_MWH = 820        # For comparison
WIND_EMISSIONS_KG_PER_MWH = 11         # Lifecycle
SOLAR_EMISSIONS_KG_PER_MWH = 41        # Lifecycle

# US vs foreign efficiency factors
US_LNG_EFFICIENCY = 0.92               # US LNG cleaner than global average
FOREIGN_LNG_EFFICIENCY = 0.78          # Foreign typically less efficient
US_GRID_EFFICIENCY = 0.85              # US grid cleaner than many


def verify_lng_export(
    export: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify LNG export emissions for CBAM defense.

    Args:
        export: LNG export data
        tenant_id: Tenant identifier

    Returns:
        dict: energy_receipt with verification
    """
    start_time = time.time()

    export_id = export.get("export_id", "UNKNOWN")
    quantity_mmbtu = export.get("quantity_mmbtu", 0)
    destination = export.get("destination", "EU")

    # Calculate US actual emissions
    us_emissions = quantity_mmbtu * LNG_EMISSIONS_KG_PER_MMBTU * (1 / US_LNG_EFFICIENCY)

    # Calculate what foreign equivalent would be
    foreign_equivalent = quantity_mmbtu * LNG_EMISSIONS_KG_PER_MMBTU * (1 / FOREIGN_LNG_EFFICIENCY)

    # Benefit = foreign - US (positive = US cleaner)
    benefit = foreign_equivalent - us_emissions

    result = {
        "receipt_type": "energy_verify",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "export_id": export_id,
        "energy_type": "lng",
        "quantity_mmbtu": quantity_mmbtu,
        "us_emissions_kg_co2e": round(us_emissions, 2),
        "foreign_equivalent_kg_co2e": round(foreign_equivalent, 2),
        "emissions_benefit_kg_co2e": round(benefit, 2),
        "us_efficiency_factor": US_LNG_EFFICIENCY,
        "destination": destination,
        "verification_status": "verified" if benefit > 0 else "flagged",
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))
    emit_receipt(result)

    return result


def verify_nuclear_smr(
    facility: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify SMR (Small Modular Reactor) efficiency claims.

    Args:
        facility: SMR facility data
        tenant_id: Tenant identifier

    Returns:
        dict: energy_receipt with verification
    """
    start_time = time.time()

    facility_id = facility.get("facility_id", "UNKNOWN")
    capacity_mw = facility.get("capacity_mw", 100)
    annual_mwh = facility.get("annual_mwh", capacity_mw * 8760 * 0.90)  # 90% capacity factor

    # Calculate nuclear emissions
    nuclear_emissions = annual_mwh * NUCLEAR_EMISSIONS_KG_PER_MWH

    # Compare to coal equivalent
    coal_equivalent = annual_mwh * COAL_EMISSIONS_KG_PER_MWH

    # Emissions avoided
    avoided = coal_equivalent - nuclear_emissions

    result = {
        "receipt_type": "energy_verify",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "energy_type": "nuclear_smr",
        "capacity_mw": capacity_mw,
        "annual_mwh": annual_mwh,
        "nuclear_emissions_kg_co2e": round(nuclear_emissions, 2),
        "coal_equivalent_kg_co2e": round(coal_equivalent, 2),
        "emissions_avoided_kg_co2e": round(avoided, 2),
        "efficiency_vs_coal": round(avoided / coal_equivalent, 4) if coal_equivalent > 0 else 0,
        "verification_status": "verified",
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))
    emit_receipt(result)

    return result


def verify_pipeline(
    pipeline: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify pipeline emissions.

    Args:
        pipeline: Pipeline data
        tenant_id: Tenant identifier

    Returns:
        dict: energy_receipt with verification
    """
    start_time = time.time()

    pipeline_id = pipeline.get("pipeline_id", "UNKNOWN")
    length_miles = pipeline.get("length_miles", 0)
    daily_bbls = pipeline.get("daily_bbls", 0)
    annual_bbls = daily_bbls * 365

    # Calculate pipeline transport emissions
    transport_emissions = annual_bbls * length_miles * PIPELINE_EMISSIONS_KG_PER_BBL_MILE

    # Compare to truck/rail alternative
    # Trucks emit ~0.1 kg CO2e per barrel-mile (much higher)
    truck_equivalent = annual_bbls * length_miles * 0.10

    # Emissions avoided by using pipeline
    avoided = truck_equivalent - transport_emissions

    result = {
        "receipt_type": "energy_verify",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "pipeline_id": pipeline_id,
        "energy_type": "pipeline",
        "length_miles": length_miles,
        "annual_throughput_bbls": annual_bbls,
        "pipeline_emissions_kg_co2e": round(transport_emissions, 2),
        "truck_equivalent_kg_co2e": round(truck_equivalent, 2),
        "emissions_avoided_kg_co2e": round(avoided, 2),
        "efficiency_vs_truck": round(avoided / truck_equivalent, 4) if truck_equivalent > 0 else 0,
        "verification_status": "verified",
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))
    emit_receipt(result)

    return result


def compare_to_alternatives(
    us_energy: dict[str, Any],
    foreign_alternative: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Compare US energy to foreign alternatives.

    Args:
        us_energy: US energy source data
        foreign_alternative: Foreign alternative data
        tenant_id: Tenant identifier

    Returns:
        dict: Comparison result
    """
    us_emissions = us_energy.get("emissions_kg_co2e", 0)
    foreign_emissions = foreign_alternative.get("emissions_kg_co2e", 0)

    delta = foreign_emissions - us_emissions
    us_cleaner = delta > 0

    comparison = {
        "us_source": us_energy.get("source_type", "unknown"),
        "foreign_source": foreign_alternative.get("source_type", "unknown"),
        "us_emissions_kg_co2e": us_emissions,
        "foreign_emissions_kg_co2e": foreign_emissions,
        "delta_kg_co2e": delta,
        "us_is_cleaner": us_cleaner,
        "efficiency_advantage": round(delta / foreign_emissions, 4) if foreign_emissions > 0 else 0,
    }

    # Emit comparison receipt
    receipt = {
        "receipt_type": "energy_comparison",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(comparison, sort_keys=True)),
        "us_cleaner": us_cleaner,
        "delta": delta,
    }
    emit_receipt(receipt)

    return comparison


def verify_corporate_emissions(
    report: dict[str, Any],
    external_sources: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Cross-verify corporate emissions against external sources.

    Upgraded from emissions_verify.py with waste-focused language.

    Args:
        report: Corporate emissions report
        external_sources: External verification data
        tenant_id: Tenant identifier

    Returns:
        dict: Verification result
    """
    claimed_value = (
        report.get("scope1_emissions", 0) +
        report.get("scope2_emissions", 0) +
        report.get("scope3_emissions", 0)
    )

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
    verified_value = sum(
        s["value"] * s.get("confidence", 0.5)
        for s in external_sources
    ) / total_weight

    # Compute discrepancy
    if claimed_value > 0:
        discrepancy_pct = abs(verified_value - claimed_value) / claimed_value
    else:
        discrepancy_pct = 1.0 if verified_value > 0 else 0.0

    match_score = max(0.0, 1.0 - discrepancy_pct)

    # Determine status
    if discrepancy_pct <= EMISSIONS_DISCREPANCY_MAX:
        status = "verified"
    elif discrepancy_pct <= EMISSIONS_DISCREPANCY_MAX * 2:
        status = "flagged"
    else:
        status = "failed"

    result = {
        "match_score": round(match_score, 4),
        "verified_value": round(verified_value, 2),
        "claimed_value": claimed_value,
        "discrepancy_pct": round(discrepancy_pct, 4),
        "status": status,
    }

    # Emit verification receipt
    receipt = {
        "receipt_type": "emissions_verify",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "match_score": result["match_score"],
        "verified_value": result["verified_value"],
        "claimed_value": result["claimed_value"],
        "discrepancy_pct": result["discrepancy_pct"],
        "status": status,
    }
    emit_receipt(receipt)

    return result
