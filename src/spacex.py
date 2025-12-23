"""
GreenProof SpaceX - SpaceX/Starlink net benefit module.

Government Waste Elimination Engine v3.0

Prove SpaceX is "net negative" through avoided terrestrial infrastructure.
Calculate launch emissions vs. avoided fiber/cell tower/data center construction.

Receipt: spacex_receipt
SLO: Calculation time ≤ 100ms per mission, accuracy within 5%
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


# === SPACEX CONSTANTS ===
FALCON9_EMISSIONS_KG_CO2 = 425_000      # Per launch (kerosene RP-1)
FALCON_HEAVY_EMISSIONS_KG_CO2 = 1_200_000  # Per launch (3 cores)
STARSHIP_EMISSIONS_KG_CO2 = 250_000     # Per launch (methane, cleaner)
STARLINK_SATELLITES_ACTIVE = 6000       # Current constellation size

# Avoided infrastructure emissions
FIBER_AVOIDED_KG_CO2_PER_KM = 50        # Per km fiber construction avoided
CELL_TOWER_KG_CO2_PER_UNIT = 75_000     # Per cell tower not built
DATA_CENTER_KG_CO2_PER_MW = 500_000     # Per MW capacity not built

# Starlink service coverage
STARLINK_COVERAGE_RADIUS_KM = 550       # Per ground station
USERS_PER_SATELLITE = 1000              # Conservative estimate


def calculate_launch_emissions(
    vehicle: str,
    payload_kg: float = 0,
) -> float:
    """Calculate launch emissions for vehicle.

    Args:
        vehicle: "falcon9" | "falcon_heavy" | "starship"
        payload_kg: Payload mass (optional)

    Returns:
        float: Emissions in kg CO2
    """
    base_emissions = {
        "falcon9": FALCON9_EMISSIONS_KG_CO2,
        "falcon_heavy": FALCON_HEAVY_EMISSIONS_KG_CO2,
        "starship": STARSHIP_EMISSIONS_KG_CO2,
    }

    emissions = base_emissions.get(vehicle.lower(), FALCON9_EMISSIONS_KG_CO2)

    # Slight adjustment for payload mass (heavier = more fuel)
    if payload_kg > 0:
        payload_factor = 1.0 + (payload_kg / 50000) * 0.1
        emissions *= payload_factor

    return emissions


def calculate_avoided_emissions(
    service: str,
    coverage_area: dict[str, Any],
) -> float:
    """Calculate avoided terrestrial infrastructure emissions.

    Args:
        service: Service type ("starlink", "rideshare", "dedicated")
        coverage_area: Coverage parameters

    Returns:
        float: Avoided emissions in kg CO2
    """
    avoided = 0.0

    if service.lower() == "starlink":
        # Calculate avoided fiber
        fiber_km = coverage_area.get("fiber_displaced_km", 0)
        avoided += fiber_km * FIBER_AVOIDED_KG_CO2_PER_KM

        # Calculate avoided cell towers
        towers = coverage_area.get("cell_towers_displaced", 0)
        avoided += towers * CELL_TOWER_KG_CO2_PER_UNIT

        # Calculate avoided data center capacity
        dc_mw = coverage_area.get("data_center_mw_displaced", 0)
        avoided += dc_mw * DATA_CENTER_KG_CO2_PER_MW

        # Estimate based on coverage if specific values not provided
        if avoided == 0:
            coverage_km2 = coverage_area.get("coverage_km2", 0)
            users_served = coverage_area.get("users_served", 0)

            # Estimate: 1000 km2 coverage = 50km fiber + 2 towers avoided
            if coverage_km2 > 0:
                avoided += (coverage_km2 / 1000) * 50 * FIBER_AVOIDED_KG_CO2_PER_KM
                avoided += (coverage_km2 / 500) * CELL_TOWER_KG_CO2_PER_UNIT

            # Estimate: 1000 users = 10km fiber avoided
            if users_served > 0:
                avoided += (users_served / 1000) * 10 * FIBER_AVOIDED_KG_CO2_PER_KM

    return avoided


def net_benefit(
    launch_emissions: float,
    avoided_emissions: float,
) -> dict[str, Any]:
    """Calculate net benefit of launch.

    Args:
        launch_emissions: Emissions from launch
        avoided_emissions: Emissions avoided

    Returns:
        dict: Net benefit analysis
    """
    net = avoided_emissions - launch_emissions

    if net > 0:
        status = "net_negative"  # More avoided than emitted = good
    elif net == 0:
        status = "net_neutral"
    else:
        status = "net_positive"  # More emitted than avoided = bad

    return {
        "launch_emissions_kg_co2": round(launch_emissions, 2),
        "avoided_emissions_kg_co2": round(avoided_emissions, 2),
        "net_benefit_kg_co2": round(net, 2),
        "net_status": status,
        "benefit_ratio": round(avoided_emissions / launch_emissions, 4) if launch_emissions > 0 else 0,
    }


def verify_starlink_claim(
    claim: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify Starlink infrastructure displacement claim.

    Args:
        claim: Starlink claim data
        tenant_id: Tenant identifier

    Returns:
        dict: spacex_receipt with verification
    """
    start_time = time.time()

    mission_id = claim.get("mission_id", "UNKNOWN")
    vehicle = claim.get("vehicle", "falcon9")
    satellites_deployed = claim.get("satellites_deployed", 60)

    # Calculate launch emissions
    launch_em = calculate_launch_emissions(vehicle)

    # Calculate avoided based on satellites
    coverage = {
        "coverage_km2": satellites_deployed * STARLINK_COVERAGE_RADIUS_KM * 2,
        "users_served": satellites_deployed * USERS_PER_SATELLITE,
    }
    avoided_em = calculate_avoided_emissions("starlink", coverage)

    # Calculate net benefit
    benefit = net_benefit(launch_em, avoided_em)

    result = {
        "receipt_type": "spacex",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "mission_id": mission_id,
        "vehicle": vehicle,
        "launch_emissions_kg_co2": launch_em,
        "service_type": "starlink",
        "avoided_infrastructure": {
            "type": "mixed",
            "satellites_deployed": satellites_deployed,
            "coverage_km2": coverage["coverage_km2"],
            "users_served": coverage["users_served"],
            "avoided_emissions_kg_co2": avoided_em,
        },
        "net_benefit_kg_co2": benefit["net_benefit_kg_co2"],
        "net_status": benefit["net_status"],
        "benefit_ratio": benefit["benefit_ratio"],
        "calculation_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))

    # Emit receipt (CLAUDEME LAW_1)
    emit_receipt(result)

    return result


def batch_mission_analysis(
    missions: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Analyze multiple missions.

    Args:
        missions: List of mission data
        tenant_id: Tenant identifier

    Returns:
        list: List of spacex_receipts
    """
    results = []
    for mission in missions:
        if mission.get("service_type", "starlink") == "starlink":
            result = verify_starlink_claim(mission, tenant_id)
        else:
            # Generic mission analysis
            result = _analyze_generic_mission(mission, tenant_id)
        results.append(result)
    return results


def generate_regulatory_brief(
    receipts: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate brief for regulatory submission.

    Args:
        receipts: SpaceX verification receipts
        tenant_id: Tenant identifier

    Returns:
        dict: Regulatory brief
    """
    total_launches = len(receipts)
    total_launch_emissions = sum(r.get("launch_emissions_kg_co2", 0) for r in receipts)
    total_avoided = sum(
        r.get("avoided_infrastructure", {}).get("avoided_emissions_kg_co2", 0)
        for r in receipts
    )

    net_negative_count = sum(1 for r in receipts if r.get("net_status") == "net_negative")

    overall_benefit = net_benefit(total_launch_emissions, total_avoided)

    brief = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_launches_analyzed": total_launches,
        "total_launch_emissions_kg_co2": round(total_launch_emissions, 2),
        "total_avoided_emissions_kg_co2": round(total_avoided, 2),
        "net_benefit_kg_co2": overall_benefit["net_benefit_kg_co2"],
        "overall_status": overall_benefit["net_status"],
        "net_negative_launch_count": net_negative_count,
        "net_negative_rate": net_negative_count / total_launches if total_launches > 0 else 0,
        "regulatory_summary": _generate_regulatory_summary(overall_benefit),
    }

    # Emit brief receipt
    receipt = {
        "receipt_type": "spacex_regulatory_brief",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(brief, sort_keys=True)),
        "launches_analyzed": total_launches,
        "net_benefit": overall_benefit["net_benefit_kg_co2"],
    }
    emit_receipt(receipt)

    return brief


def _analyze_generic_mission(
    mission: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Analyze non-Starlink mission."""
    mission_id = mission.get("mission_id", "UNKNOWN")
    vehicle = mission.get("vehicle", "falcon9")

    launch_em = calculate_launch_emissions(vehicle, mission.get("payload_kg", 0))

    result = {
        "receipt_type": "spacex",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "mission_id": mission_id,
        "vehicle": vehicle,
        "launch_emissions_kg_co2": launch_em,
        "service_type": mission.get("service_type", "dedicated"),
        "avoided_infrastructure": None,
        "net_benefit_kg_co2": -launch_em,  # No avoided = negative benefit
        "net_status": "net_positive",
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))
    emit_receipt(result)

    return result


def _generate_regulatory_summary(benefit: dict[str, Any]) -> str:
    """Generate regulatory summary text."""
    net = benefit["net_benefit_kg_co2"]
    status = benefit["net_status"]

    if status == "net_negative":
        return (
            f"SpaceX operations demonstrate net negative emissions impact. "
            f"Avoided infrastructure emissions exceed launch emissions by "
            f"{abs(net):,.0f} kg CO2 ({abs(net)/1000:,.1f} tonnes). "
            f"Operations qualify as efficiency-positive per Waste Elimination criteria."
        )
    elif status == "net_neutral":
        return "SpaceX operations demonstrate emissions neutrality."
    else:
        return (
            f"SpaceX operations show net emissions of {net:,.0f} kg CO2. "
            f"Additional infrastructure displacement documentation recommended."
        )
