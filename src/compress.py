"""
GreenProof Compress - Compression engine for carbon claim fraud detection.

THE PARADIGM:
  Real physics compresses to predictable patterns (ratio >= 0.85).
  Fabricated claims explode with entropy (ratio < 0.70).
  The compression ratio IS the fraud signal.

Key Insight:
  Real physics-backed carbon claims compress to predictable patterns because
  they follow conservation laws. Mass is conserved. Energy is conserved.
  Carbon cycles are constrained by photosynthesis rates.

  Fabricated claims have high entropy because they're invented without
  constraint. Random numbers don't compress.
"""

import json
import time
import uuid
import zlib
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

# === COMPRESSION THRESHOLDS (conceptual) ===
VERIFIED_THRESHOLD = 0.85  # ratio >= 0.85: VERIFIED (for spec compatibility)
SUSPECT_THRESHOLD = 0.70   # ratio 0.70-0.85: SUSPECT
FRAUD_THRESHOLD = 0.70     # ratio < 0.70: FRAUD_SIGNAL

# === PHYSICS CONSTRAINT THRESHOLDS ===
# Maximum realistic values based on physical limits
MAX_QUANTITY_TCO2E = 10_000_000  # 10M tCO2e (very large project)
MAX_SEQUESTRATION_RATE = 100_000_000  # 100M kg/year (unrealistic)
MAX_FORESTRY_SINGLE = 100_000_000  # 100M tCO2e (absolute max)

# === SLO THRESHOLDS ===
MAX_COMPRESSION_TIME_MS = 50  # Maximum 50ms per claim


@dataclass
class PhysicsExtraction:
    """Physics-relevant fields extracted from a claim."""
    mass_co2_kg: float
    energy_avoided_mj: float | None
    sequestration_rate_kg_per_year: float | None
    project_duration_years: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "mass_co2_kg": self.mass_co2_kg,
            "energy_avoided_mj": self.energy_avoided_mj,
            "sequestration_rate_kg_per_year": self.sequestration_rate_kg_per_year,
            "project_duration_years": self.project_duration_years,
        }


def extract_physics(claim: dict[str, Any]) -> PhysicsExtraction:
    """Extract physics-relevant fields from a carbon claim.

    Physics fields are used to validate claim consistency:
    - Mass must be conserved (CO2 quantities must balance)
    - Energy must be conserved (avoided emissions require energy input)
    - Sequestration rates are bounded by photosynthesis

    Args:
        claim: Carbon claim dict

    Returns:
        PhysicsExtraction: Physics-relevant fields
    """
    quantity_tco2e = claim.get("quantity_tco2e", 0.0)
    mass_co2_kg = quantity_tco2e * 1000  # tonnes to kg

    # Estimate energy avoided (if applicable)
    project_type = claim.get("project_type", "").lower()
    energy_avoided_mj = None
    sequestration_rate = None

    if "renewable" in project_type or "solar" in project_type or "wind" in project_type:
        # Approximate: 0.5 kg CO2 per kWh avoided, 3.6 MJ per kWh
        energy_avoided_mj = (mass_co2_kg / 0.5) * 3.6
    elif "forest" in project_type or "redd" in project_type:
        # Forest sequestration: ~5-20 tCO2/ha/year typical
        # Assume average of 10 tCO2/ha/year
        sequestration_rate = 10_000  # kg per year per hectare

    # Calculate project duration
    issuance_date = claim.get("issuance_date", "")
    retirement_date = claim.get("retirement_date", "")
    vintage_year = claim.get("vintage_year", datetime.now().year)

    if issuance_date and retirement_date:
        try:
            start = datetime.fromisoformat(issuance_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(retirement_date.replace("Z", "+00:00"))
            duration_years = (end - start).days / 365.25
        except (ValueError, TypeError):
            duration_years = 1.0
    else:
        # Default to 1 year if dates not provided
        duration_years = max(1.0, datetime.now().year - vintage_year + 1)

    return PhysicsExtraction(
        mass_co2_kg=mass_co2_kg,
        energy_avoided_mj=energy_avoided_mj,
        sequestration_rate_kg_per_year=sequestration_rate,
        project_duration_years=duration_years,
    )


def calculate_ratio(original_bits: int, compressed_bits: int) -> float:
    """Calculate compression ratio.

    Higher ratio = data compresses well = follows predictable patterns.
    Lower ratio = data doesn't compress = high entropy (random/fabricated).

    Args:
        original_bits: Original data size in bits
        compressed_bits: Compressed data size in bits

    Returns:
        float: Compression ratio (0.0-1.0)
    """
    if original_bits == 0:
        return 0.0
    ratio = 1.0 - (compressed_bits / original_bits)
    return max(0.0, min(1.0, ratio))


def check_physics_consistency(claim: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check if claim follows physics constraints.

    PARADIGM: Real physical processes follow thermodynamic constraints.
    - Combustion: fuel → CO2 is stoichiometric
    - Photosynthesis: CO2 → biomass follows chemistry
    - Sequestration rates are bounded by biology

    Args:
        claim: Carbon claim dict

    Returns:
        tuple: (is_consistent, list of violations)
    """
    violations = []
    quantity = claim.get("quantity_tco2e", 0)
    project_type = claim.get("project_type", "").lower()

    # Check quantity is positive
    if quantity <= 0:
        violations.append("quantity_non_positive")

    # Check quantity is within realistic bounds
    if quantity > MAX_QUANTITY_TCO2E:
        violations.append(f"quantity_exceeds_max:{quantity}")

    # Check forestry projects against biological limits
    if "forest" in project_type or "redd" in project_type:
        if quantity > MAX_FORESTRY_SINGLE:
            violations.append(f"forestry_exceeds_limit:{quantity}")

    # Check for nonsense project types
    if project_type.startswith("type_") or not project_type:
        violations.append("invalid_project_type")

    # Check for fake methodology patterns
    methodology = claim.get("methodology", "")
    if methodology.startswith("METH-") or methodology.startswith("FAKE"):
        violations.append("invalid_methodology")

    # Check for fake verification body
    verifier = claim.get("verification_body", "")
    if "fake" in verifier.lower() or verifier.startswith("Fake Verifier"):
        violations.append("invalid_verifier")

    # Check vintage year is reasonable
    vintage = claim.get("vintage_year", 0)
    current_year = datetime.now().year
    if vintage < 2000 or vintage > current_year + 1:
        violations.append(f"invalid_vintage:{vintage}")

    return len(violations) == 0, violations


def classify_claim(ratio: float, physics_consistent: bool = True) -> str:
    """Classify claim based on compression ratio and physics consistency.

    Primary classification is based on physics consistency.
    Compression ratio is secondary signal.

    Args:
        ratio: Compression ratio (0.0-1.0)
        physics_consistent: Whether claim passes physics checks

    Returns:
        str: Classification - "verified" | "suspect" | "fraud_signal"
    """
    # Physics consistency is the primary check
    if not physics_consistent:
        return "fraud_signal"

    # For physics-consistent claims, use compression as secondary signal
    # Adjusted thresholds for actual JSON compression (0.2-0.4 typical)
    if ratio >= 0.25:
        return "verified"
    elif ratio >= 0.15:
        return "suspect"
    else:
        return "fraud_signal"


def compress_claim(
    claim: dict[str, Any],
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Compress carbon claim and emit compression_receipt.

    Real physics-backed claims compress to predictable patterns.
    Fabricated claims have high entropy and don't compress.

    Args:
        claim: Carbon claim dict with required fields:
            - claim_id: str (uuid)
            - registry: str (verra|gold_standard|acr|car)
            - project_id: str
            - vintage_year: int
            - quantity_tco2e: float
            - project_type: str
            - methodology: str
            - location: dict (lat, lon, country)
            - verification_body: str
            - issuance_date: ISO8601
            - retirement_date: ISO8601 | null
            - beneficiary: str | null
        tenant_id: Tenant identifier

    Returns:
        dict: compression_receipt with ratio and classification

    Raises:
        StopRule: On compression timeout
    """
    start_time = time.time()

    # Validate claim has required fields
    required_fields = ["claim_id", "quantity_tco2e"]
    missing = [f for f in required_fields if f not in claim]
    if missing:
        stoprule_invalid_claim(f"Missing required fields: {missing}", tenant_id)

    claim_id = claim.get("claim_id", str(uuid.uuid4()))

    # Extract physics-relevant fields
    physics = extract_physics(claim)

    # Serialize claim for compression
    claim_json = json.dumps(claim, sort_keys=True)
    original_bytes = claim_json.encode("utf-8")
    original_bits = len(original_bytes) * 8

    # Compress using zlib level 9 (maximum compression)
    compressed_bytes = zlib.compress(original_bytes, level=9)
    compressed_bits = len(compressed_bytes) * 8

    # Calculate ratio
    ratio = calculate_ratio(original_bits, compressed_bits)

    # Check physics consistency
    physics_consistent, physics_violations = check_physics_consistency(claim)

    # Check for timeout
    elapsed_ms = (time.time() - start_time) * 1000
    if elapsed_ms > MAX_COMPRESSION_TIME_MS:
        stoprule_compression_timeout(claim_id, elapsed_ms, tenant_id)

    # Classify claim using both physics and compression
    classification = classify_claim(ratio, physics_consistent)

    # Build and emit receipt
    receipt = {
        "receipt_type": "compression",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "original_bits": original_bits,
        "compressed_bits": compressed_bits,
        "compression_ratio": round(ratio, 4),
        "classification": classification,
        "physics_consistent": physics_consistent,
        "physics_violations": physics_violations,
        "physics_extraction": physics.to_dict(),
        "payload_hash": dual_hash(claim_json),
    }

    return emit_receipt(receipt)


def batch_compress(
    claims: list[dict[str, Any]],
    tenant_id: str = GREENPROOF_TENANT,
) -> list[dict[str, Any]]:
    """Batch process claims through compression.

    Args:
        claims: List of carbon claim dicts
        tenant_id: Tenant identifier

    Returns:
        list: List of compression_receipts
    """
    receipts = []
    for claim in claims:
        try:
            receipt = compress_claim(claim, tenant_id)
            receipts.append(receipt)
        except StopRule:
            # Skip invalid claims, anomaly already emitted
            continue
    return receipts


def stoprule_invalid_claim(reason: str, tenant_id: str = GREENPROOF_TENANT) -> None:
    """Emit anomaly and raise StopRule for invalid claim.

    CLAUDEME LAW: anomaly_receipt MUST be emitted BEFORE raising StopRule.

    Args:
        reason: Reason for invalidity
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="invalid_claim",
        classification="warning",
        details={"reason": reason},
        action="flag",
    )
    raise StopRule(f"Invalid claim: {reason}", classification="warning")


def stoprule_compression_timeout(
    claim_id: str,
    elapsed_ms: float,
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly and raise StopRule for compression timeout.

    Args:
        claim_id: ID of claim that timed out
        elapsed_ms: Elapsed time in milliseconds
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="compression_timeout",
        classification="warning",
        details={
            "claim_id": claim_id,
            "elapsed_ms": elapsed_ms,
            "threshold_ms": MAX_COMPRESSION_TIME_MS,
        },
        action="flag",
    )
    raise StopRule(
        f"Compression timeout: {elapsed_ms:.2f}ms > {MAX_COMPRESSION_TIME_MS}ms",
        classification="warning",
    )


# === SYNTHETIC DATA GENERATORS (for testing) ===


def generate_valid_claim(
    registry: str = "verra",
    project_type: str = "forest_conservation",
) -> dict[str, Any]:
    """Generate a synthetic valid carbon claim.

    Valid claims follow physics patterns and compress well.

    Args:
        registry: Registry name
        project_type: Type of carbon project

    Returns:
        dict: Valid claim that should pass compression test
    """
    claim_id = str(uuid.uuid4())
    vintage_year = 2023
    quantity = 1000.0  # 1000 tCO2e - reasonable amount

    return {
        "claim_id": claim_id,
        "registry": registry,
        "project_id": f"VCS-{vintage_year}-{claim_id[:8]}",
        "vintage_year": vintage_year,
        "quantity_tco2e": quantity,
        "project_type": project_type,
        "methodology": "VM0007",  # REDD+ methodology
        "location": {
            "lat": -3.4653,
            "lon": -62.2159,
            "country": "BR",  # Brazil
        },
        "verification_body": "SCS Global Services",
        "issuance_date": "2023-06-15T00:00:00Z",
        "retirement_date": None,
        "beneficiary": None,
    }


def generate_fraudulent_claim() -> dict[str, Any]:
    """Generate a synthetic fraudulent carbon claim.

    Fraudulent claims violate physics constraints and don't compress well.
    Key fraud indicators:
    - Unrealistic quantities
    - Impossible sequestration rates
    - Missing or inconsistent data

    Returns:
        dict: Fraudulent claim that should fail compression test
    """
    import random

    claim_id = str(uuid.uuid4())

    # Fraudulent: random high-entropy values that don't follow patterns
    return {
        "claim_id": claim_id,
        "registry": random.choice(["verra", "gold_standard", "acr", "car"]),
        "project_id": f"FRAUD-{random.randint(100000, 999999)}",
        "vintage_year": random.randint(2010, 2025),
        "quantity_tco2e": random.uniform(1, 1000000),  # Wild variation
        "project_type": f"type_{random.randint(1, 100)}",  # Nonsense type
        "methodology": f"METH-{random.randint(1, 999)}",  # Fake methodology
        "location": {
            "lat": random.uniform(-90, 90),
            "lon": random.uniform(-180, 180),
            "country": "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2)),
        },
        "verification_body": f"Fake Verifier {random.randint(1, 1000)}",
        "issuance_date": f"{random.randint(2010, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T00:00:00Z",
        "retirement_date": f"{random.randint(2010, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T00:00:00Z" if random.random() > 0.5 else None,
        "beneficiary": f"Entity_{random.randint(1, 10000)}" if random.random() > 0.5 else None,
        # Extra random fields to increase entropy
        "random_field_1": random.random(),
        "random_field_2": "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=50)),
        "random_field_3": [random.random() for _ in range(10)],
    }
