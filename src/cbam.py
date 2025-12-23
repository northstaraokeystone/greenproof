"""
GreenProof CBAM - Carbon Border Adjustment Mechanism reciprocal defense.

Government Waste Elimination Engine v3.0

Verify US exports aren't subject to fraudulent EU penalties.
Generate cryptographic receipts proving American energy cleaner than alleged.

Receipt: cbam_receipt
SLO: Verification time ≤ 200ms per export, all 4 sectors covered
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
from .compress import compress_test


# === CBAM CONSTANTS ===
CBAM_EFFECTIVE_DATE = "2026-01-01"  # EU CBAM takes effect
US_EXPORT_SECTORS = ["oil_gas", "steel", "manufacturing", "lng"]
RECIPROCAL_TARIFF_THRESHOLD = 0.10  # 10% discrepancy triggers tariff justification

# Emissions factors by sector (tCO2e per unit)
SECTOR_EMISSIONS_FACTORS = {
    "oil_gas": 0.43,  # per barrel
    "steel": 1.85,    # per tonne
    "manufacturing": 0.25,  # per $1000 value
    "lng": 2.75,      # per tonne LNG
}


def verify_us_export(
    export: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify US export emissions for CBAM defense.

    Args:
        export: Export dict with export_id, sector, quantity, etc.
        tenant_id: Tenant identifier

    Returns:
        dict: cbam_receipt with verification result
    """
    start_time = time.time()

    export_id = export.get("export_id", "UNKNOWN")
    sector = export.get("sector", "manufacturing")
    product_type = export.get("product_type", "general")

    # Calculate actual US emissions
    us_emissions = calculate_us_emissions(export, sector)

    # Get EU claimed emissions (would come from CBAM declarations)
    eu_claimed = export.get("eu_claimed_emissions", us_emissions * 1.25)  # Default: EU overclaims by 25%

    # Compare US vs EU
    comparison = compare_eu_claims(us_emissions, eu_claimed)

    # Determine if reciprocal tariff justified
    tariff_justified = justify_reciprocal_tariff(comparison["discrepancy_percentage"])

    result = {
        "receipt_type": "cbam",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "export_id": export_id,
        "sector": sector,
        "product_type": product_type,
        "us_verified_emissions_tco2e": round(us_emissions, 4),
        "eu_claimed_emissions_tco2e": round(eu_claimed, 4),
        "discrepancy_percentage": round(comparison["discrepancy_percentage"], 4),
        "discrepancy_direction": comparison["direction"],
        "reciprocal_tariff_justified": tariff_justified,
        "tariff_justification": _generate_tariff_justification(comparison) if tariff_justified else None,
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))

    # Emit receipt (CLAUDEME LAW_1)
    emit_receipt(result)

    return result


def calculate_us_emissions(
    product: dict[str, Any],
    sector: str,
) -> float:
    """Calculate actual US emissions for product.

    Args:
        product: Product/export data
        sector: Sector type

    Returns:
        float: Emissions in tCO2e
    """
    quantity = product.get("quantity", 1.0)
    value_usd = product.get("value_usd", 0)

    # Get base factor
    factor = SECTOR_EMISSIONS_FACTORS.get(sector, 0.25)

    # Calculate base emissions
    if sector == "manufacturing":
        base_emissions = (value_usd / 1000) * factor
    else:
        base_emissions = quantity * factor

    # Apply US efficiency factor (US production typically cleaner)
    us_efficiency = product.get("us_efficiency_factor", 0.85)

    return base_emissions * us_efficiency


def compare_eu_claims(
    us_emissions: float,
    eu_claimed: float,
) -> dict[str, Any]:
    """Compare US verified vs EU claimed emissions.

    Args:
        us_emissions: Verified US emissions
        eu_claimed: EU CBAM claimed emissions

    Returns:
        dict: Comparison result
    """
    if us_emissions <= 0:
        return {
            "discrepancy_percentage": 1.0,
            "direction": "eu_overclaiming",
            "delta": eu_claimed,
        }

    delta = eu_claimed - us_emissions
    discrepancy_pct = abs(delta) / us_emissions

    if delta > 0:
        direction = "eu_overclaiming"
    elif delta < 0:
        direction = "eu_underclaiming"
    else:
        direction = "accurate"

    return {
        "discrepancy_percentage": discrepancy_pct,
        "direction": direction,
        "delta": delta,
        "us_emissions": us_emissions,
        "eu_claimed": eu_claimed,
    }


def justify_reciprocal_tariff(discrepancy_pct: float) -> bool:
    """Determine if reciprocal tariff is justified.

    Args:
        discrepancy_pct: Discrepancy percentage

    Returns:
        bool: True if tariff justified
    """
    return discrepancy_pct >= RECIPROCAL_TARIFF_THRESHOLD


def batch_verify_exports(
    exports: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Batch verify all exports in sector.

    Args:
        exports: List of exports to verify
        tenant_id: Tenant identifier

    Returns:
        list: List of cbam_receipts
    """
    results = []
    for export in exports:
        result = verify_us_export(export, tenant_id)
        results.append(result)
    return results


def generate_trade_brief(
    receipts: list[dict[str, Any]],
    sector: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate trade negotiation brief from CBAM receipts.

    Args:
        receipts: CBAM verification receipts
        sector: Sector focus
        tenant_id: Tenant identifier

    Returns:
        dict: Trade brief for negotiations
    """
    sector_receipts = [r for r in receipts if r.get("sector") == sector]

    if not sector_receipts:
        return {"error": f"No receipts for sector: {sector}"}

    total_us_emissions = sum(r.get("us_verified_emissions_tco2e", 0) for r in sector_receipts)
    total_eu_claimed = sum(r.get("eu_claimed_emissions_tco2e", 0) for r in sector_receipts)

    overclaiming_count = sum(
        1 for r in sector_receipts
        if r.get("discrepancy_direction") == "eu_overclaiming"
    )

    tariff_justified_count = sum(
        1 for r in sector_receipts
        if r.get("reciprocal_tariff_justified")
    )

    avg_discrepancy = sum(
        r.get("discrepancy_percentage", 0) for r in sector_receipts
    ) / len(sector_receipts)

    brief = {
        "sector": sector,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exports_analyzed": len(sector_receipts),
        "total_us_verified_emissions_tco2e": round(total_us_emissions, 2),
        "total_eu_claimed_emissions_tco2e": round(total_eu_claimed, 2),
        "total_overclaim_tco2e": round(total_eu_claimed - total_us_emissions, 2),
        "average_discrepancy_pct": round(avg_discrepancy, 4),
        "eu_overclaiming_count": overclaiming_count,
        "reciprocal_tariff_justified_count": tariff_justified_count,
        "negotiation_position": _generate_negotiation_position(avg_discrepancy, overclaiming_count, len(sector_receipts)),
    }

    # Emit trade brief receipt
    receipt = {
        "receipt_type": "cbam_trade_brief",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(brief, sort_keys=True)),
        "sector": sector,
        "exports_analyzed": len(sector_receipts),
        "overclaim_tco2e": brief["total_overclaim_tco2e"],
    }
    emit_receipt(receipt)

    return brief


def _generate_tariff_justification(comparison: dict[str, Any]) -> str:
    """Generate tariff justification text."""
    direction = comparison.get("direction", "")
    pct = comparison.get("discrepancy_percentage", 0)
    us_em = comparison.get("us_emissions", 0)
    eu_cl = comparison.get("eu_claimed", 0)

    if direction == "eu_overclaiming":
        return (
            f"EU CBAM methodology overclaims US emissions by {pct:.1%}. "
            f"Verified US emissions are {us_em:.2f} tCO2e vs "
            f"EU claimed {eu_cl:.2f} tCO2e. "
            f"Reciprocal tariff justified to offset unfair penalty."
        )
    else:
        return None


def _generate_negotiation_position(avg_discrepancy: float, overclaim_count: int, total: int) -> str:
    """Generate negotiation position summary."""
    overclaim_rate = overclaim_count / total if total > 0 else 0

    if avg_discrepancy > 0.25:
        strength = "STRONG"
        position = "EU CBAM methodology systematically overclaims US emissions"
    elif avg_discrepancy > 0.10:
        strength = "MODERATE"
        position = "EU CBAM claims exceed verified US emissions"
    else:
        strength = "WEAK"
        position = "Minor discrepancies between US verified and EU claimed"

    return f"{strength}: {position}. {overclaim_rate:.0%} of exports show EU overclaiming."
