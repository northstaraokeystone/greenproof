"""
GreenProof EV - Tesla/EV credit verification module.

Musk wedge hook:
  "You've sold billions in carbon credits. Wright says renewables are
  'just hype.' We prove which credits are real physics vs. paper theater."

Tesla Revenue Context:
- Tesla sold $7.3B in regulatory credits 2018-2024
- Revenue depends on credit quality perception
- Fake credits from competitors dilute Tesla's real credits

This module provides:
- EV credit claim verification
- Fleet emissions calculation
- Charging source verification
- ICE baseline comparison
- State-specific ZEV credit verification
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .core import (
    GREENPROOF_TENANT,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)

# === CONSTANTS ===

# Average miles per gallon for ICE baseline comparison
ICE_BASELINE_MPG = 25.0

# CO2 emissions per gallon of gasoline (kg)
CO2_PER_GALLON_GAS = 8.887

# Average EV efficiency (kWh per mile)
AVG_EV_EFFICIENCY_KWH_PER_MILE = 0.30

# Grid emission factors by state (kg CO2e per kWh)
STATE_GRID_FACTORS = {
    "CA": 0.225,   # California - low carbon
    "TX": 0.396,   # Texas - ERCOT
    "FL": 0.389,   # Florida
    "NY": 0.261,   # New York
    "WA": 0.084,   # Washington - hydro heavy
    "WY": 0.848,   # Wyoming - coal heavy
    "VT": 0.012,   # Vermont - very clean
    "DEFAULT": 0.386,  # US average
}

# ZEV credit values by state (credits per EV)
ZEV_CREDIT_VALUES = {
    "CA": 4.0,     # California - original ZEV program
    "NY": 4.0,     # New York - Section 177 state
    "MA": 4.0,     # Massachusetts
    "OR": 4.0,     # Oregon
    "VT": 4.0,     # Vermont
    "NJ": 4.0,     # New Jersey
    "MD": 4.0,     # Maryland
    "CT": 4.0,     # Connecticut
    "CO": 4.0,     # Colorado
    "DEFAULT": 0.0,  # Non-ZEV states
}

# Credit price estimates (USD per credit)
CREDIT_PRICES = {
    "CA": 2000.0,  # California ZEV credits
    "federal": 7500.0,  # Federal EV credit value
    "DEFAULT": 1500.0,
}


@dataclass
class EVVerification:
    """Result of EV credit verification."""
    verified: bool
    vehicle_count: int
    total_miles: float
    claimed_credits: float
    verified_credits: float
    charging_source_verified: bool
    discrepancy_pct: float
    flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "vehicle_count": self.vehicle_count,
            "total_miles": round(self.total_miles, 2),
            "claimed_credits": round(self.claimed_credits, 4),
            "verified_credits": round(self.verified_credits, 4),
            "charging_source_verified": self.charging_source_verified,
            "discrepancy_pct": round(self.discrepancy_pct, 4),
            "flags": self.flags,
        }


def compare_to_ice_baseline(
    ev_miles: float,
    ice_mpg: float = ICE_BASELINE_MPG,
) -> float:
    """Calculate emissions avoided vs ICE baseline.

    Args:
        ev_miles: Total EV miles driven
        ice_mpg: ICE baseline miles per gallon

    Returns:
        float: tCO2e avoided compared to ICE
    """
    # Gallons of gas an ICE would have used
    ice_gallons = ev_miles / ice_mpg

    # CO2 from burning that gasoline (kg)
    ice_emissions_kg = ice_gallons * CO2_PER_GALLON_GAS

    # Convert to tonnes
    ice_emissions_tco2e = ice_emissions_kg / 1000

    return ice_emissions_tco2e


def calculate_ev_emissions(
    ev_miles: float,
    state: str = "DEFAULT",
    ev_efficiency: float = AVG_EV_EFFICIENCY_KWH_PER_MILE,
) -> float:
    """Calculate actual EV emissions from charging.

    Args:
        ev_miles: Total EV miles driven
        state: State for grid factor lookup
        ev_efficiency: kWh per mile

    Returns:
        float: tCO2e from EV charging
    """
    # Total kWh consumed
    kwh_consumed = ev_miles * ev_efficiency

    # Grid emission factor
    grid_factor = STATE_GRID_FACTORS.get(state, STATE_GRID_FACTORS["DEFAULT"])

    # Emissions from charging (kg)
    ev_emissions_kg = kwh_consumed * grid_factor

    # Convert to tonnes
    ev_emissions_tco2e = ev_emissions_kg / 1000

    return ev_emissions_tco2e


def calculate_fleet_emissions(
    vehicles: list[dict[str, Any]],
) -> dict[str, float]:
    """Calculate total fleet emissions avoided.

    Args:
        vehicles: List of vehicle dicts with:
            - miles: float
            - state: str (optional)
            - charging_source: str (optional) - "grid", "solar", "wind"

    Returns:
        dict: Fleet emissions summary
    """
    total_miles = 0.0
    total_ice_baseline = 0.0
    total_ev_emissions = 0.0

    for vehicle in vehicles:
        miles = vehicle.get("miles", 0)
        state = vehicle.get("state", "DEFAULT")
        charging_source = vehicle.get("charging_source", "grid")

        total_miles += miles

        # ICE baseline
        ice_avoided = compare_to_ice_baseline(miles)
        total_ice_baseline += ice_avoided

        # EV emissions (depends on charging source)
        if charging_source in ("solar", "wind", "renewable"):
            # Zero emissions from renewable charging
            ev_emissions = 0.0
        else:
            ev_emissions = calculate_ev_emissions(miles, state)
        total_ev_emissions += ev_emissions

    # Net avoided = ICE baseline - EV emissions
    net_avoided = total_ice_baseline - total_ev_emissions

    return {
        "total_miles": round(total_miles, 2),
        "ice_baseline_tco2e": round(total_ice_baseline, 4),
        "ev_emissions_tco2e": round(total_ev_emissions, 4),
        "net_avoided_tco2e": round(net_avoided, 4),
        "vehicle_count": len(vehicles),
    }


def verify_charging_source(
    charging_data: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Verify charging was from claimed energy source.

    Args:
        charging_data: Charging data with:
            - source: str ("grid", "solar", "wind", "renewable")
            - kwh: float
            - timestamps: list (optional)
            - renewable_certificates: list (optional)

    Returns:
        tuple: (is_verified, verification_details)
    """
    source = charging_data.get("source", "grid")
    kwh = charging_data.get("kwh", 0)
    certificates = charging_data.get("renewable_certificates", [])

    details = {
        "claimed_source": source,
        "kwh": kwh,
        "certificates_provided": len(certificates),
    }

    if source == "grid":
        # Grid charging always verifiable
        return True, {**details, "verification": "grid_default"}

    if source in ("solar", "wind", "renewable"):
        # Renewable claims require certificates or direct evidence
        if certificates:
            # Has RECs
            total_rec_kwh = sum(c.get("kwh", 0) for c in certificates)
            if total_rec_kwh >= kwh:
                return True, {**details, "verification": "rec_verified", "rec_kwh": total_rec_kwh}
            else:
                return False, {
                    **details,
                    "verification": "insufficient_recs",
                    "rec_kwh": total_rec_kwh,
                    "shortfall_kwh": kwh - total_rec_kwh,
                }
        else:
            # No certificates - can't verify renewable claim
            return False, {**details, "verification": "no_certificates"}

    return False, {**details, "verification": "unknown_source"}


def verify_zev_credit(
    claim: dict[str, Any],
    state: str,
) -> dict[str, Any]:
    """Verify state-specific ZEV credit claim.

    Args:
        claim: ZEV credit claim
        state: State for ZEV program

    Returns:
        dict: ZEV verification result
    """
    vehicle_count = claim.get("vehicle_count", 0)
    claimed_credits = claim.get("claimed_credits", 0)

    # Get credit value for state
    credit_per_vehicle = ZEV_CREDIT_VALUES.get(state, ZEV_CREDIT_VALUES["DEFAULT"])

    # Calculate verified credits
    verified_credits = vehicle_count * credit_per_vehicle

    # Calculate discrepancy
    if claimed_credits > 0:
        discrepancy_pct = abs(claimed_credits - verified_credits) / claimed_credits
    else:
        discrepancy_pct = 1.0 if verified_credits > 0 else 0.0

    return {
        "state": state,
        "vehicle_count": vehicle_count,
        "credit_per_vehicle": credit_per_vehicle,
        "claimed_credits": claimed_credits,
        "verified_credits": verified_credits,
        "discrepancy_pct": round(discrepancy_pct, 4),
        "is_zev_state": credit_per_vehicle > 0,
    }


def verify_ev_credit(
    claim: dict[str, Any],
    vehicle_data: list[dict[str, Any]],
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Verify EV credit claim.

    Args:
        claim: EV credit claim with:
            - claim_id: str
            - vehicle_count: int
            - total_miles: float
            - claimed_credits: float
            - state: str (optional)
        vehicle_data: List of vehicle dicts for fleet calculation
        tenant_id: Tenant identifier

    Returns:
        dict: ev_receipt with verification results
    """
    claim_id = claim.get("claim_id", str(uuid.uuid4()))
    claimed_vehicle_count = claim.get("vehicle_count", 0)
    claimed_miles = claim.get("total_miles", 0)
    claimed_credits = claim.get("claimed_credits", 0)
    state = claim.get("state", "CA")  # Default to CA (largest market)

    flags = []

    # Calculate fleet emissions
    fleet_result = calculate_fleet_emissions(vehicle_data)

    # Check vehicle count
    actual_vehicle_count = fleet_result["vehicle_count"]
    if actual_vehicle_count != claimed_vehicle_count:
        flags.append(f"vehicle_count_mismatch:{claimed_vehicle_count}vs{actual_vehicle_count}")

    # Check miles
    actual_miles = fleet_result["total_miles"]
    if abs(actual_miles - claimed_miles) / max(claimed_miles, 1) > 0.05:
        flags.append(f"miles_mismatch:{claimed_miles}vs{actual_miles}")

    # Verify charging sources
    charging_verified = True
    for vehicle in vehicle_data:
        charging_data = vehicle.get("charging_data", {"source": "grid", "kwh": vehicle.get("miles", 0) * AVG_EV_EFFICIENCY_KWH_PER_MILE})
        verified, _ = verify_charging_source(charging_data)
        if not verified:
            charging_verified = False
            flags.append(f"charging_unverified:{vehicle.get('id', 'unknown')}")

    # Calculate verified credits based on net avoided emissions
    # Using rough conversion: 1 credit ≈ 0.5 tCO2e avoided
    verified_credits = fleet_result["net_avoided_tco2e"] * 2.0

    # Calculate discrepancy
    if claimed_credits > 0:
        discrepancy_pct = abs(claimed_credits - verified_credits) / claimed_credits
    else:
        discrepancy_pct = 1.0 if verified_credits > 0 else 0.0

    # Determine status
    if discrepancy_pct > 0.25:
        status = "fraud"
        flags.append("high_discrepancy")
    elif discrepancy_pct > 0.10:
        status = "discrepancy"
        flags.append("moderate_discrepancy")
    else:
        status = "verified"

    verification = EVVerification(
        verified=(status == "verified"),
        vehicle_count=actual_vehicle_count,
        total_miles=actual_miles,
        claimed_credits=claimed_credits,
        verified_credits=verified_credits,
        charging_source_verified=charging_verified,
        discrepancy_pct=discrepancy_pct,
        flags=flags,
    )

    # Build and emit receipt
    receipt = {
        "receipt_type": "ev",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "vehicle_count": actual_vehicle_count,
        "total_miles": round(actual_miles, 2),
        "claimed_credits": round(claimed_credits, 4),
        "verified_credits": round(verified_credits, 4),
        "charging_source_verified": charging_verified,
        "discrepancy_pct": round(discrepancy_pct, 4),
        "verification_status": status,
        "fleet_emissions": fleet_result,
        "flags": flags,
        "payload_hash": dual_hash(json.dumps(verification.to_dict(), sort_keys=True)),
    }

    return emit_receipt(receipt)


def stoprule_ev_fraud(
    claim_id: str,
    discrepancy_pct: float,
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly and raise StopRule for EV credit fraud.

    Args:
        claim_id: ID of fraudulent claim
        discrepancy_pct: Discrepancy percentage
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="ev_credit_fraud",
        classification="critical",
        details={
            "claim_id": claim_id,
            "discrepancy_pct": discrepancy_pct,
        },
        action="halt",
    )
    raise StopRule(
        f"EV credit fraud detected: {claim_id} discrepancy={discrepancy_pct:.1%}",
        classification="critical",
    )


# === SYNTHETIC DATA GENERATORS (for testing) ===


def generate_valid_ev_claim(
    vehicle_count: int = 100,
    avg_miles_per_vehicle: float = 12000.0,
    state: str = "CA",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate valid EV credit claim for testing.

    Args:
        vehicle_count: Number of vehicles
        avg_miles_per_vehicle: Average annual miles
        state: State for registration

    Returns:
        tuple: (claim, vehicle_data)
    """
    vehicle_data = []
    total_miles = 0.0

    for i in range(vehicle_count):
        miles = avg_miles_per_vehicle * (0.9 + 0.2 * (i % 5) / 5)  # Slight variation
        total_miles += miles
        vehicle_data.append({
            "id": f"VEH-{i:04d}",
            "miles": miles,
            "state": state,
            "charging_source": "grid",
            "charging_data": {
                "source": "grid",
                "kwh": miles * AVG_EV_EFFICIENCY_KWH_PER_MILE,
            },
        })

    # Calculate expected credits
    fleet_result = calculate_fleet_emissions(vehicle_data)
    expected_credits = fleet_result["net_avoided_tco2e"] * 2.0

    claim = {
        "claim_id": str(uuid.uuid4()),
        "vehicle_count": vehicle_count,
        "total_miles": total_miles,
        "claimed_credits": expected_credits,  # Accurate claim
        "state": state,
    }

    return claim, vehicle_data


def generate_fraudulent_ev_claim(
    vehicle_count: int = 100,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate fraudulent EV credit claim for testing.

    Args:
        vehicle_count: Claimed number of vehicles

    Returns:
        tuple: (claim, vehicle_data) with inflated values
    """
    import random

    # Actual vehicles is less than claimed
    actual_vehicles = int(vehicle_count * random.uniform(0.4, 0.7))

    vehicle_data = []
    total_miles = 0.0

    for i in range(actual_vehicles):
        miles = 10000.0 * random.uniform(0.8, 1.2)
        total_miles += miles
        vehicle_data.append({
            "id": f"VEH-{i:04d}",
            "miles": miles,
            "state": "CA",
            "charging_source": "grid",
            "charging_data": {
                "source": "grid",
                "kwh": miles * AVG_EV_EFFICIENCY_KWH_PER_MILE,
            },
        })

    # Inflated claims
    claimed_miles = total_miles * random.uniform(1.5, 2.5)
    fleet_result = calculate_fleet_emissions(vehicle_data)
    actual_credits = fleet_result["net_avoided_tco2e"] * 2.0
    claimed_credits = actual_credits * random.uniform(2.0, 4.0)

    claim = {
        "claim_id": str(uuid.uuid4()),
        "vehicle_count": vehicle_count,  # Inflated
        "total_miles": claimed_miles,    # Inflated
        "claimed_credits": claimed_credits,  # Inflated
        "state": "CA",
    }

    return claim, vehicle_data
