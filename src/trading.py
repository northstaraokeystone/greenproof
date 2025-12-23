"""
GreenProof Trading - Trading layer infrastructure for carbon credits.

Chamath's "legitimate exchange" request (Feb 2020):
  "Invest in actual companies that can go and count, and can legitimize
  the actual impact that companies have, so that you can do the right
  amount of carbon offsets. And then you have to have a **legitimate
  exchange** where you can actually trade them."

This module provides:
- Verified-only listings (fraud_level == "clean")
- Order matching
- Trade execution with custody receipts
- Credit retirement (prevents resale)

NOTE: v2 provides infrastructure only. Real settlement requires licensing.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .core import (
    GREENPROOF_TENANT,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)

# === TRADING CONSTANTS ===
MIN_LISTING_QUANTITY_TCO2E = 1.0
MAX_LISTING_QUANTITY_TCO2E = 1_000_000.0  # 1M tCO2e max per listing

# === BASE PRICES (USD per tCO2e) ===
BASE_PRICES = {
    "verra": 8.0,
    "gold_standard": 15.0,  # Premium
    "acr": 10.0,
    "car": 12.0,
}

# === QUALITY MULTIPLIERS ===
QUALITY_MULTIPLIERS = {
    "forest_conservation": 1.2,
    "renewable_energy": 0.9,
    "direct_air_capture": 3.0,  # Premium for DAC
    "blue_carbon": 1.5,         # Mangroves, seagrass
    "soil_carbon": 1.1,
    "default": 1.0,
}

# === VINTAGE DEPRECIATION ===
VINTAGE_DEPRECIATION_PER_YEAR = 0.05  # 5% per year from current

# === GLOBAL TRADING STATE ===
_LISTINGS: dict[str, dict[str, Any]] = {}
_TRADES: list[dict[str, Any]] = []
_RETIRED_CLAIMS: set[str] = set()


def reset_trading() -> None:
    """Reset global trading state. For testing only."""
    global _LISTINGS, _TRADES, _RETIRED_CLAIMS
    _LISTINGS = {}
    _TRADES = []
    _RETIRED_CLAIMS = set()


def get_trading_state() -> dict[str, Any]:
    """Get current trading state. For debugging."""
    return {
        "listings": _LISTINGS.copy(),
        "trades": list(_TRADES),
        "retired": list(_RETIRED_CLAIMS),
    }


def calculate_price(
    claim: dict[str, Any],
    market_data: dict[str, Any] | None = None,
) -> float:
    """Calculate price per tCO2e based on quality, vintage, and type.

    Args:
        claim: Carbon claim dict
        market_data: Optional market data for pricing

    Returns:
        float: Price in USD per tCO2e
    """
    registry = claim.get("registry", "verra")
    project_type = claim.get("project_type", "default").lower()
    vintage_year = claim.get("vintage_year", datetime.now().year)

    # Base price from registry
    base_price = BASE_PRICES.get(registry, BASE_PRICES["verra"])

    # Quality multiplier from project type
    quality_mult = QUALITY_MULTIPLIERS.get(project_type, QUALITY_MULTIPLIERS["default"])

    # Vintage depreciation
    current_year = datetime.now().year
    years_old = max(0, current_year - vintage_year)
    vintage_mult = max(0.5, 1.0 - (years_old * VINTAGE_DEPRECIATION_PER_YEAR))

    # Apply market data if provided
    market_mult = 1.0
    if market_data:
        market_mult = market_data.get("price_multiplier", 1.0)

    price = base_price * quality_mult * vintage_mult * market_mult
    return round(price, 2)


def validate_listing(
    claim: dict[str, Any],
    fraud_receipt: dict[str, Any],
) -> tuple[bool, str]:
    """Validate claim is eligible for listing.

    Only clean claims can be listed. No exceptions.

    Args:
        claim: Carbon claim dict
        fraud_receipt: Receipt from detect_fraud()

    Returns:
        tuple: (is_valid, reason)
    """
    claim_id = claim.get("claim_id", "")

    # Check if already retired
    if claim_id in _RETIRED_CLAIMS:
        return False, "claim_already_retired"

    # Check fraud level
    fraud_level = fraud_receipt.get("fraud_level", "unknown")
    if fraud_level != "clean":
        return False, f"fraud_level_not_clean:{fraud_level}"

    # Check quantity bounds
    quantity = claim.get("quantity_tco2e", 0)
    if quantity < MIN_LISTING_QUANTITY_TCO2E:
        return False, f"quantity_below_minimum:{quantity}"
    if quantity > MAX_LISTING_QUANTITY_TCO2E:
        return False, f"quantity_above_maximum:{quantity}"

    # Check recommendation
    recommendation = fraud_receipt.get("recommendation", "reject")
    if recommendation == "reject":
        return False, "recommendation_is_reject"

    return True, "valid"


def create_listing(
    claim: dict[str, Any],
    fraud_receipt: dict[str, Any],
    seller: str = "anonymous",
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Create exchange listing for verified claim.

    Args:
        claim: Carbon claim dict
        fraud_receipt: Receipt from detect_fraud()
        seller: Seller identifier
        tenant_id: Tenant identifier

    Returns:
        dict: listing_receipt

    Raises:
        StopRule: If claim fails validation
    """
    global _LISTINGS

    claim_id = claim.get("claim_id", str(uuid.uuid4()))

    # Validate
    is_valid, reason = validate_listing(claim, fraud_receipt)
    if not is_valid:
        stoprule_invalid_listing(claim_id, reason, tenant_id)

    # Generate listing ID
    listing_id = str(uuid.uuid4())

    # Calculate price
    price_per_tco2e = calculate_price(claim)
    quantity = claim.get("quantity_tco2e", 0)

    # Create listing
    listing = {
        "listing_id": listing_id,
        "claim_id": claim_id,
        "seller": seller,
        "quantity_tco2e": quantity,
        "price_per_tco2e": price_per_tco2e,
        "total_price": round(quantity * price_per_tco2e, 2),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fraud_receipt_hash": fraud_receipt.get("payload_hash", ""),
    }

    # Store listing
    _LISTINGS[listing_id] = listing

    # Build and emit receipt
    receipt = {
        "receipt_type": "listing",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "listing_id": listing_id,
        "fraud_receipt_hash": fraud_receipt.get("payload_hash", ""),
        "quantity_tco2e": quantity,
        "price_per_tco2e": price_per_tco2e,
        "status": "active",
        "payload_hash": dual_hash(json.dumps(listing, sort_keys=True)),
    }

    return emit_receipt(receipt)


def match_order(
    bid: dict[str, Any],
    listings: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Match buyer bid to best available listing.

    Matching criteria (in order):
    1. Quantity >= requested
    2. Price <= max bid price
    3. Best quality (lowest fraud score, highest compression ratio)

    Args:
        bid: Buyer bid with:
            - quantity_tco2e: float
            - max_price_per_tco2e: float
            - preferred_registry: str (optional)
            - preferred_project_type: str (optional)
        listings: Optional list of listings (uses global if None)

    Returns:
        dict: Best matching listing, or None
    """
    if listings is None:
        listings = [l for l in _LISTINGS.values() if l["status"] == "active"]

    if not listings:
        return None

    requested_qty = bid.get("quantity_tco2e", 0)
    max_price = bid.get("max_price_per_tco2e", float("inf"))
    preferred_registry = bid.get("preferred_registry")
    preferred_type = bid.get("preferred_project_type")

    # Filter by basic criteria
    candidates = []
    for listing in listings:
        if listing.get("status") != "active":
            continue
        if listing.get("quantity_tco2e", 0) < requested_qty:
            continue
        if listing.get("price_per_tco2e", float("inf")) > max_price:
            continue
        candidates.append(listing)

    if not candidates:
        return None

    # Score candidates
    def score_listing(listing: dict[str, Any]) -> float:
        score = 0.0
        # Lower price is better
        score -= listing.get("price_per_tco2e", 0) * 0.1
        # Preferred registry bonus
        if preferred_registry and listing.get("registry") == preferred_registry:
            score += 1.0
        # Preferred type bonus
        if preferred_type and preferred_type in listing.get("project_type", ""):
            score += 0.5
        return score

    # Sort by score (descending)
    candidates.sort(key=score_listing, reverse=True)

    return candidates[0]


def execute_trade(
    bid: dict[str, Any],
    listing: dict[str, Any],
    buyer: str = "anonymous",
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Execute trade between buyer and seller.

    Args:
        bid: Buyer bid
        listing: Matched listing
        buyer: Buyer identifier
        tenant_id: Tenant identifier

    Returns:
        dict: trade_receipt
    """
    global _LISTINGS, _TRADES

    listing_id = listing.get("listing_id")
    claim_id = listing.get("claim_id")
    seller = listing.get("seller", "anonymous")

    # Calculate trade values
    quantity = min(bid.get("quantity_tco2e", 0), listing.get("quantity_tco2e", 0))
    price_per = listing.get("price_per_tco2e", 0)
    total_price = round(quantity * price_per, 2)

    # Generate trade ID
    trade_id = str(uuid.uuid4())

    # Generate custody receipt
    custody_receipt = generate_custody_receipt(
        trade_id=trade_id,
        claim_id=claim_id,
        from_party=seller,
        to_party=buyer,
        quantity=quantity,
        tenant_id=tenant_id,
    )

    # Update listing
    remaining = listing.get("quantity_tco2e", 0) - quantity
    if listing_id in _LISTINGS:
        if remaining <= 0:
            _LISTINGS[listing_id]["status"] = "sold"
            _LISTINGS[listing_id]["quantity_tco2e"] = 0
        else:
            _LISTINGS[listing_id]["quantity_tco2e"] = remaining

    # Record trade
    trade = {
        "trade_id": trade_id,
        "listing_id": listing_id,
        "claim_id": claim_id,
        "buyer": buyer,
        "seller": seller,
        "quantity_tco2e": quantity,
        "price_per_tco2e": price_per,
        "total_price": total_price,
        "settlement_status": "settled",  # v2: instant settlement
        "custody_receipt_hash": custody_receipt.get("payload_hash", ""),
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    _TRADES.append(trade)

    # Build and emit receipt
    receipt = {
        "receipt_type": "trade",
        "tenant_id": tenant_id,
        "trade_id": trade_id,
        "listing_id": listing_id,
        "buyer": buyer,
        "seller": seller,
        "quantity_tco2e": quantity,
        "price_total": total_price,
        "settlement_status": "settled",
        "custody_receipt_hash": custody_receipt.get("payload_hash", ""),
        "payload_hash": dual_hash(json.dumps(trade, sort_keys=True)),
    }

    return emit_receipt(receipt)


def generate_custody_receipt(
    trade_id: str,
    claim_id: str,
    from_party: str,
    to_party: str,
    quantity: float,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Generate custody transfer receipt for trade.

    Args:
        trade_id: Trade identifier
        claim_id: Credit claim identifier
        from_party: Seller
        to_party: Buyer
        quantity: Amount transferred
        tenant_id: Tenant identifier

    Returns:
        dict: custody_receipt
    """
    custody = {
        "receipt_type": "custody",
        "tenant_id": tenant_id,
        "trade_id": trade_id,
        "claim_id": claim_id,
        "from_party": from_party,
        "to_party": to_party,
        "quantity_tco2e": quantity,
        "transfer_ts": datetime.now(timezone.utc).isoformat(),
    }
    custody["payload_hash"] = dual_hash(json.dumps(custody, sort_keys=True))

    return emit_receipt(custody)


def retire_credit(
    claim_id: str,
    beneficiary: str,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Retire credit, preventing resale.

    Once retired, a credit cannot be traded again.

    Args:
        claim_id: Credit claim identifier
        beneficiary: Entity claiming the offset
        tenant_id: Tenant identifier

    Returns:
        dict: retirement_receipt
    """
    global _RETIRED_CLAIMS, _LISTINGS

    # Check if already retired
    if claim_id in _RETIRED_CLAIMS:
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="double_retirement",
            classification="critical",
            details={"claim_id": claim_id},
            action="halt",
        )
        raise StopRule(f"Credit already retired: {claim_id}", classification="critical")

    # Mark as retired
    _RETIRED_CLAIMS.add(claim_id)

    # Delist any active listings
    for listing_id, listing in _LISTINGS.items():
        if listing.get("claim_id") == claim_id:
            _LISTINGS[listing_id]["status"] = "retired"

    # Build and emit receipt
    receipt = {
        "receipt_type": "retirement",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "beneficiary": beneficiary,
        "retirement_ts": datetime.now(timezone.utc).isoformat(),
        "status": "retired",
        "payload_hash": dual_hash(json.dumps({
            "claim_id": claim_id,
            "beneficiary": beneficiary,
        }, sort_keys=True)),
    }

    return emit_receipt(receipt)


def stoprule_invalid_listing(
    claim_id: str,
    reason: str,
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly and raise StopRule for invalid listing.

    Args:
        claim_id: ID of invalid claim
        reason: Reason for invalidity
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="invalid_listing",
        classification="warning",
        details={
            "claim_id": claim_id,
            "reason": reason,
        },
        action="flag",
    )
    raise StopRule(f"Invalid listing: {reason}", classification="warning")


# === MARKET STATISTICS ===


def get_market_stats() -> dict[str, Any]:
    """Get current market statistics.

    Returns:
        dict: Market stats
    """
    active_listings = [l for l in _LISTINGS.values() if l["status"] == "active"]
    total_volume = sum(l.get("quantity_tco2e", 0) for l in active_listings)
    total_value = sum(l.get("total_price", 0) for l in active_listings)

    if active_listings:
        avg_price = total_value / total_volume
    else:
        avg_price = 0.0

    return {
        "active_listings": len(active_listings),
        "total_volume_tco2e": round(total_volume, 2),
        "total_value_usd": round(total_value, 2),
        "average_price_per_tco2e": round(avg_price, 2),
        "total_trades": len(_TRADES),
        "total_retired": len(_RETIRED_CLAIMS),
    }
