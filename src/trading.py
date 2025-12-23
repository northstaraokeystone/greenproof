"""
GreenProof Trading - Trading layer infrastructure.

Government Waste Elimination Engine v3.0

Zero fraud reaches listing. All trades produce receipts.
Trading integrity maintained via compression verification.

Receipt: trade_receipt
SLO: Zero fraud reaches listing, verification ≤ 100ms
"""

import json
import time
from datetime import datetime, timezone
from typing import Any

from .core import (
    TENANT_ID,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)
from .compress import compress_test, check_physical_consistency
from .detect import detect_waste


# === TRADING CONSTANTS ===
MIN_COMPRESSION_FOR_LISTING = 0.70     # Minimum to list
VERIFIED_THRESHOLD = 0.85               # Verified quality
TRADE_FEE_PERCENT = 0.02                # 2% trading fee


# Trading registry (in-memory for v3, persistent in v4)
_LISTINGS: dict[str, dict[str, Any]] = {}
_TRADES: list[dict[str, Any]] = []


def create_listing(
    asset: dict[str, Any],
    seller_id: str,
    price_usd: float,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Create listing for verified asset.

    Zero fraud reaches listing - all assets compression-tested.

    Args:
        asset: Asset data to list
        seller_id: Seller identifier
        price_usd: Listing price
        tenant_id: Tenant identifier

    Returns:
        dict: Listing result
    """
    start_time = time.time()

    # Compression test the asset
    compression = compress_test(asset)
    physical = check_physical_consistency(asset)

    # Zero fraud policy - reject low compression
    if compression["compression_ratio"] < MIN_COMPRESSION_FOR_LISTING:
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="listing_rejected",
            classification="warning",
            details={
                "compression_ratio": compression["compression_ratio"],
                "threshold": MIN_COMPRESSION_FOR_LISTING,
                "asset_type": asset.get("asset_type", "unknown"),
            },
            action="halt",
        )
        return {
            "success": False,
            "error": "Asset failed compression verification",
            "compression_ratio": compression["compression_ratio"],
            "min_required": MIN_COMPRESSION_FOR_LISTING,
        }

    # Reject physics violations
    if not physical:
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="physics_violation",
            classification="violation",
            details={"asset": asset},
            action="halt",
        )
        return {
            "success": False,
            "error": "Asset contains physics violations",
        }

    # Create listing
    listing_id = f"LIST-{len(_LISTINGS) + 1:08d}"

    listing = {
        "listing_id": listing_id,
        "asset": asset,
        "seller_id": seller_id,
        "price_usd": price_usd,
        "compression_ratio": compression["compression_ratio"],
        "verification_status": "verified" if compression["compression_ratio"] >= VERIFIED_THRESHOLD else "approved",
        "listed_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }

    _LISTINGS[listing_id] = listing

    # Emit listing receipt
    receipt = {
        "receipt_type": "listing_created",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(listing, sort_keys=True)),
        "listing_id": listing_id,
        "seller_id": seller_id,
        "price_usd": price_usd,
        "compression_ratio": compression["compression_ratio"],
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    emit_receipt(receipt)

    return {
        "success": True,
        "listing": listing,
    }


def execute_trade(
    listing_id: str,
    buyer_id: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Execute trade on listing.

    Args:
        listing_id: Listing to purchase
        buyer_id: Buyer identifier
        tenant_id: Tenant identifier

    Returns:
        dict: Trade result
    """
    listing = _LISTINGS.get(listing_id)

    if not listing:
        return {"success": False, "error": "Listing not found"}

    if listing["status"] != "active":
        return {"success": False, "error": f"Listing status: {listing['status']}"}

    # Calculate fees
    price = listing["price_usd"]
    fee = price * TRADE_FEE_PERCENT
    total = price + fee

    # Create trade record
    trade_id = f"TRADE-{len(_TRADES) + 1:08d}"

    trade = {
        "trade_id": trade_id,
        "listing_id": listing_id,
        "seller_id": listing["seller_id"],
        "buyer_id": buyer_id,
        "asset": listing["asset"],
        "price_usd": price,
        "fee_usd": fee,
        "total_usd": total,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    _TRADES.append(trade)

    # Update listing status
    listing["status"] = "sold"

    # Emit trade receipt
    receipt = {
        "receipt_type": "trade_executed",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(trade, sort_keys=True)),
        "trade_id": trade_id,
        "listing_id": listing_id,
        "buyer_id": buyer_id,
        "seller_id": listing["seller_id"],
        "price_usd": price,
        "fee_usd": fee,
    }
    emit_receipt(receipt)

    return {
        "success": True,
        "trade": trade,
    }


def get_listing(listing_id: str) -> dict[str, Any] | None:
    """Get listing by ID."""
    return _LISTINGS.get(listing_id)


def get_active_listings() -> list[dict[str, Any]]:
    """Get all active listings."""
    return [l for l in _LISTINGS.values() if l["status"] == "active"]


def get_trades(buyer_id: str = None, seller_id: str = None) -> list[dict[str, Any]]:
    """Get trades, optionally filtered."""
    trades = _TRADES

    if buyer_id:
        trades = [t for t in trades if t["buyer_id"] == buyer_id]
    if seller_id:
        trades = [t for t in trades if t["seller_id"] == seller_id]

    return trades


def verify_listing_integrity(
    listing_id: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Re-verify listing integrity.

    Args:
        listing_id: Listing to verify
        tenant_id: Tenant identifier

    Returns:
        dict: Verification result
    """
    listing = _LISTINGS.get(listing_id)

    if not listing:
        return {"valid": False, "error": "Listing not found"}

    # Re-run compression test
    compression = compress_test(listing["asset"])
    physical = check_physical_consistency(listing["asset"])

    # Check if still meets threshold
    still_valid = (
        compression["compression_ratio"] >= MIN_COMPRESSION_FOR_LISTING and
        physical
    )

    result = {
        "listing_id": listing_id,
        "original_compression": listing["compression_ratio"],
        "current_compression": compression["compression_ratio"],
        "physical_consistency": physical,
        "still_valid": still_valid,
        "status": "verified" if still_valid else "degraded",
    }

    # Emit verification receipt
    receipt = {
        "receipt_type": "listing_verified",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(result, sort_keys=True)),
        "listing_id": listing_id,
        "still_valid": still_valid,
    }
    emit_receipt(receipt)

    return result


def generate_market_report(
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate market activity report.

    Args:
        tenant_id: Tenant identifier

    Returns:
        dict: Market report
    """
    active_listings = get_active_listings()
    total_trades = len(_TRADES)
    total_volume = sum(t["price_usd"] for t in _TRADES)
    total_fees = sum(t["fee_usd"] for t in _TRADES)

    avg_compression = sum(
        l["compression_ratio"] for l in active_listings
    ) / len(active_listings) if active_listings else 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_listings": len(active_listings),
        "total_trades": total_trades,
        "total_volume_usd": total_volume,
        "total_fees_usd": total_fees,
        "average_listing_compression": round(avg_compression, 4),
        "fraud_blocked_count": 0,  # Would track rejected listings
    }

    # Emit report receipt
    receipt = {
        "receipt_type": "market_report",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(report, sort_keys=True)),
        "total_trades": total_trades,
        "total_volume": total_volume,
    }
    emit_receipt(receipt)

    return report


def reset_trading():
    """Reset trading state (for testing)."""
    global _LISTINGS, _TRADES
    _LISTINGS = {}
    _TRADES = []
