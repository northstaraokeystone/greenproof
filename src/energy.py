"""
GreenProof Energy - Energy producer verification module.

Wright/Burgum targeting hook:
  "Fake carbon credits let competitors claim 'green' without proving anything.
  Cryptographic verification protects legitimate energy producers from ESG theater."

Energy Types Supported:
1. Fossil - Oil, gas, coal (verify actual emissions vs. claimed)
2. Nuclear - Wright's priority (verify capacity factor, emissions avoided)
3. Renewable - Solar, wind (verify generation, additionality)
4. LNG - Wright's immediate focus (verify lifecycle emissions)

This module provides:
- Energy production claim verification
- Avoided emissions calculation
- Capacity factor validation
- Lifecycle emissions analysis
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

# === GRID EMISSION FACTORS (kg CO2e per kWh) ===
# Source: EPA eGRID 2022
GRID_FACTORS = {
    "US": 0.386,      # US average
    "US-CA": 0.225,   # California (low carbon grid)
    "US-TX": 0.396,   # Texas (ERCOT)
    "US-WY": 0.848,   # Wyoming (coal heavy)
    "DE": 0.350,      # Germany
    "FR": 0.056,      # France (nuclear)
    "CN": 0.581,      # China
    "IN": 0.708,      # India
    "BR": 0.080,      # Brazil (hydro)
    "DEFAULT": 0.400, # World average
}

# === ENERGY TYPE EMISSION FACTORS (kg CO2e per MWh) ===
ENERGY_EMISSION_FACTORS = {
    "coal": 1000.0,
    "natural_gas": 450.0,
    "oil": 750.0,
    "lng": 500.0,          # LNG with transport
    "nuclear": 12.0,        # Lifecycle including mining/construction
    "solar": 25.0,          # Lifecycle
    "wind": 11.0,           # Lifecycle
    "hydro": 24.0,          # Lifecycle
    "geothermal": 38.0,     # Lifecycle
    "biomass": 230.0,       # With sustainable sourcing
}

# === CAPACITY FACTOR RANGES (realistic) ===
CAPACITY_FACTORS = {
    "nuclear": (0.85, 0.95),      # Very consistent
    "coal": (0.40, 0.85),
    "natural_gas": (0.30, 0.60),  # Often peaking
    "lng": (0.35, 0.65),
    "solar": (0.15, 0.30),        # Location dependent
    "wind": (0.25, 0.45),         # Location dependent
    "hydro": (0.35, 0.55),        # Seasonal
    "geothermal": (0.85, 0.95),   # Very consistent
}


@dataclass
class EnergyVerification:
    """Result of energy claim verification."""
    verified: bool
    claimed_avoided_tco2e: float
    verified_avoided_tco2e: float
    discrepancy_pct: float
    capacity_factor_valid: bool
    lifecycle_valid: bool
    flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "claimed_avoided_tco2e": round(self.claimed_avoided_tco2e, 2),
            "verified_avoided_tco2e": round(self.verified_avoided_tco2e, 2),
            "discrepancy_pct": round(self.discrepancy_pct, 4),
            "capacity_factor_valid": self.capacity_factor_valid,
            "lifecycle_valid": self.lifecycle_valid,
            "flags": self.flags,
        }


def calculate_avoided_emissions(
    production_mwh: float,
    energy_type: str,
    grid_factor: float | None = None,
    country: str = "DEFAULT",
) -> float:
    """Calculate tCO2e avoided by clean energy production.

    Avoided = (grid_factor - source_factor) * production

    Args:
        production_mwh: Energy produced in MWh
        energy_type: Type of energy source
        grid_factor: Optional override for grid emission factor (kg CO2e/kWh)
        country: Country code for grid factor lookup

    Returns:
        float: tCO2e avoided
    """
    # Get grid emission factor (kg CO2e per kWh = kg CO2e per 0.001 MWh)
    if grid_factor is None:
        grid_factor = GRID_FACTORS.get(country, GRID_FACTORS["DEFAULT"])

    # Grid factor is kg/kWh, convert to kg/MWh (multiply by 1000)
    grid_factor_mwh = grid_factor * 1000

    # Get source emission factor (kg CO2e per MWh)
    source_factor = ENERGY_EMISSION_FACTORS.get(
        energy_type.lower(),
        ENERGY_EMISSION_FACTORS.get("natural_gas", 450.0)
    )

    # Avoided emissions (kg CO2e)
    avoided_kg = (grid_factor_mwh - source_factor) * production_mwh

    # Convert to tonnes
    avoided_tco2e = avoided_kg / 1000

    return max(0.0, avoided_tco2e)


def verify_capacity_factor(
    claimed: float,
    actual: float,
    energy_type: str,
) -> tuple[bool, str]:
    """Check if claimed capacity factor is realistic.

    Args:
        claimed: Claimed capacity factor (0-1)
        actual: Actual/measured capacity factor (0-1)
        energy_type: Type of energy source

    Returns:
        tuple: (is_valid, reason)
    """
    # Get realistic range
    min_cf, max_cf = CAPACITY_FACTORS.get(
        energy_type.lower(),
        (0.1, 0.9)  # Default range
    )

    # Check if actual is within realistic range
    if actual < min_cf * 0.8 or actual > max_cf * 1.1:
        return False, f"actual_cf_unrealistic:{actual}"

    # Check if claimed is within 10% of actual
    if abs(claimed - actual) / actual > 0.10:
        return False, f"claimed_vs_actual_mismatch:{claimed}vs{actual}"

    # Check if claimed exceeds physical maximum
    if claimed > max_cf * 1.05:
        return False, f"claimed_exceeds_max:{claimed}>{max_cf}"

    return True, "valid"


def verify_lifecycle_emissions(
    claim: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Verify full lifecycle emissions for energy project.

    Lifecycle includes:
    - Construction emissions
    - Operation emissions
    - Fuel supply chain (if applicable)
    - Decommissioning

    Args:
        claim: Energy claim dict

    Returns:
        tuple: (is_valid, lifecycle_analysis)
    """
    energy_type = claim.get("energy_type", "").lower()
    capacity_mw = claim.get("capacity_mw", 0)
    lifetime_years = claim.get("lifetime_years", 25)

    # Get lifecycle emission factor
    lifecycle_factor = ENERGY_EMISSION_FACTORS.get(energy_type, 500.0)

    # Estimate lifecycle emissions
    avg_capacity_factor = sum(CAPACITY_FACTORS.get(energy_type, (0.3, 0.5))) / 2
    annual_mwh = capacity_mw * 8760 * avg_capacity_factor
    lifetime_mwh = annual_mwh * lifetime_years

    # Lifecycle emissions (tCO2e)
    lifecycle_emissions = (lifecycle_factor * lifetime_mwh) / 1000

    # Compare to claimed avoided emissions
    claimed_avoided = claim.get("claimed_avoided_tco2e", 0)

    # Net benefit must be positive
    if claimed_avoided < lifecycle_emissions:
        return False, {
            "lifecycle_emissions_tco2e": round(lifecycle_emissions, 2),
            "claimed_avoided_tco2e": round(claimed_avoided, 2),
            "net_benefit_tco2e": round(claimed_avoided - lifecycle_emissions, 2),
            "reason": "negative_net_benefit",
        }

    return True, {
        "lifecycle_emissions_tco2e": round(lifecycle_emissions, 2),
        "claimed_avoided_tco2e": round(claimed_avoided, 2),
        "net_benefit_tco2e": round(claimed_avoided - lifecycle_emissions, 2),
        "reason": "positive_net_benefit",
    }


def compare_to_baseline(
    claim: dict[str, Any],
    baseline: dict[str, Any],
) -> float:
    """Calculate additionality by comparing to baseline scenario.

    Args:
        claim: Energy claim with production data
        baseline: Baseline scenario (what would have happened without project)

    Returns:
        float: Additionality factor (0.0-1.0)
    """
    claimed = claim.get("production_mwh", 0)
    baseline_production = baseline.get("production_mwh", 0)

    if claimed == 0:
        return 0.0

    # Additionality = (claimed - baseline) / claimed
    additionality = (claimed - baseline_production) / claimed

    return max(0.0, min(1.0, additionality))


def verify_energy_claim(
    claim: dict[str, Any],
    energy_type: str,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Verify energy production claim.

    Args:
        claim: Energy claim with:
            - production_mwh: float
            - capacity_mw: float
            - capacity_factor: float
            - claimed_avoided_tco2e: float
            - location: dict with country
        energy_type: Type of energy source
        tenant_id: Tenant identifier

    Returns:
        dict: energy_receipt with verification results
    """
    claim_id = claim.get("claim_id", str(uuid.uuid4()))
    production_mwh = claim.get("production_mwh", 0)
    capacity_mw = claim.get("capacity_mw", 0)
    claimed_cf = claim.get("capacity_factor", 0.5)
    claimed_avoided = claim.get("claimed_avoided_tco2e", 0)
    country = claim.get("location", {}).get("country", "DEFAULT")

    flags = []

    # Calculate actual capacity factor
    hours_in_year = 8760
    if capacity_mw > 0:
        actual_cf = production_mwh / (capacity_mw * hours_in_year)
    else:
        actual_cf = 0.0
        flags.append("zero_capacity")

    # Verify capacity factor
    cf_valid, cf_reason = verify_capacity_factor(claimed_cf, actual_cf, energy_type)
    if not cf_valid:
        flags.append(cf_reason)

    # Calculate verified avoided emissions
    verified_avoided = calculate_avoided_emissions(
        production_mwh=production_mwh,
        energy_type=energy_type,
        country=country,
    )

    # Calculate discrepancy
    if claimed_avoided > 0:
        discrepancy_pct = abs(claimed_avoided - verified_avoided) / claimed_avoided
    else:
        discrepancy_pct = 1.0 if verified_avoided > 0 else 0.0

    # Verify lifecycle
    lifecycle_valid, lifecycle_analysis = verify_lifecycle_emissions(claim)
    if not lifecycle_valid:
        flags.append("lifecycle_negative")

    # Determine verification status
    if discrepancy_pct > 0.20:
        status = "fraud"
        flags.append("high_discrepancy")
    elif discrepancy_pct > 0.10:
        status = "discrepancy"
        flags.append("moderate_discrepancy")
    else:
        status = "verified"

    verification = EnergyVerification(
        verified=(status == "verified"),
        claimed_avoided_tco2e=claimed_avoided,
        verified_avoided_tco2e=verified_avoided,
        discrepancy_pct=discrepancy_pct,
        capacity_factor_valid=cf_valid,
        lifecycle_valid=lifecycle_valid,
        flags=flags,
    )

    # Build and emit receipt
    receipt = {
        "receipt_type": "energy",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "energy_type": energy_type,
        "production_mwh": production_mwh,
        "claimed_avoided_tco2e": round(claimed_avoided, 2),
        "verified_avoided_tco2e": round(verified_avoided, 2),
        "discrepancy_pct": round(discrepancy_pct, 4),
        "verification_status": status,
        "capacity_factor_claimed": round(claimed_cf, 4),
        "capacity_factor_actual": round(actual_cf, 4),
        "lifecycle_analysis": lifecycle_analysis,
        "flags": flags,
        "payload_hash": dual_hash(json.dumps(verification.to_dict(), sort_keys=True)),
    }

    return emit_receipt(receipt)


def stoprule_energy_fraud(
    claim_id: str,
    discrepancy_pct: float,
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly and raise StopRule for energy fraud.

    Args:
        claim_id: ID of fraudulent claim
        discrepancy_pct: Discrepancy percentage
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="energy_fraud",
        classification="critical",
        details={
            "claim_id": claim_id,
            "discrepancy_pct": discrepancy_pct,
        },
        action="halt",
    )
    raise StopRule(
        f"Energy fraud detected: {claim_id} discrepancy={discrepancy_pct:.1%}",
        classification="critical",
    )


# === SYNTHETIC DATA GENERATORS (for testing) ===


def generate_valid_energy_claim(
    energy_type: str = "nuclear",
    capacity_mw: float = 1000.0,
) -> dict[str, Any]:
    """Generate valid energy claim for testing.

    Args:
        energy_type: Type of energy source
        capacity_mw: Capacity in MW

    Returns:
        dict: Valid energy claim
    """
    # Get realistic capacity factor
    min_cf, max_cf = CAPACITY_FACTORS.get(energy_type.lower(), (0.3, 0.5))
    capacity_factor = (min_cf + max_cf) / 2

    # Calculate production
    hours_in_year = 8760
    production_mwh = capacity_mw * hours_in_year * capacity_factor

    # Calculate avoided emissions
    avoided = calculate_avoided_emissions(
        production_mwh=production_mwh,
        energy_type=energy_type,
        country="US",
    )

    return {
        "claim_id": str(uuid.uuid4()),
        "energy_type": energy_type,
        "capacity_mw": capacity_mw,
        "production_mwh": production_mwh,
        "capacity_factor": capacity_factor,
        "claimed_avoided_tco2e": avoided,
        "location": {"country": "US"},
        "lifetime_years": 40 if energy_type == "nuclear" else 25,
    }


def generate_fraudulent_energy_claim(
    energy_type: str = "solar",
) -> dict[str, Any]:
    """Generate fraudulent energy claim for testing.

    Args:
        energy_type: Type of energy source

    Returns:
        dict: Fraudulent energy claim with inflated values
    """
    import random

    capacity_mw = random.uniform(10, 100)

    # Inflated capacity factor (above physical maximum)
    max_cf = CAPACITY_FACTORS.get(energy_type.lower(), (0.3, 0.5))[1]
    inflated_cf = max_cf * random.uniform(1.3, 1.8)  # 30-80% inflation

    # Calculate production with inflated CF
    hours_in_year = 8760
    production_mwh = capacity_mw * hours_in_year * inflated_cf

    # Calculate inflated avoided emissions
    avoided = calculate_avoided_emissions(
        production_mwh=production_mwh,
        energy_type=energy_type,
        country="US",
    )
    inflated_avoided = avoided * random.uniform(1.5, 3.0)

    return {
        "claim_id": str(uuid.uuid4()),
        "energy_type": energy_type,
        "capacity_mw": capacity_mw,
        "production_mwh": production_mwh,
        "capacity_factor": inflated_cf,
        "claimed_avoided_tco2e": inflated_avoided,
        "location": {"country": "US"},
        "lifetime_years": 25,
    }
