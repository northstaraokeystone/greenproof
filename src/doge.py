"""
GreenProof DOGE - Department of Government Efficiency fraud audit integration.

Government Waste Elimination Engine v3.0

Target $50B+ in EPA/DOE spending with weak verification.
Flag programs with weakest verification for DOGE audit.

Receipt: waste_receipt
SLO: Audit time ≤ 100ms per grant, waste detection ≥ 90%
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


# === DOGE CONSTANTS ===
EPA_GRANT_THRESHOLD = 50_000_000_000  # $50B+ IRA allocations
DOE_LOAN_THRESHOLD = 10_000_000_000   # $10B+ clean energy loans
WEAK_VERIFICATION_THRESHOLD = 0.60    # Below this = high fraud risk
DOGE_DASHBOARD_REFRESH_SEC = 3600     # Hourly updates


def audit_epa_grant(
    grant: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Audit single EPA grant for waste.

    Args:
        grant: Grant dict with grant_id, amount, verification data
        tenant_id: Tenant identifier

    Returns:
        dict: waste_receipt with waste analysis
    """
    start_time = time.time()

    grant_id = grant.get("grant_id", "UNKNOWN")
    amount = grant.get("amount", 0) or grant.get("allocated_amount_usd", 0)

    # Run compression test on grant data
    compression = compress_test(grant)

    # Calculate verification ratio
    verification_ratio = _calculate_verification_ratio(grant)

    # Calculate waste
    verification_gap = 1.0 - verification_ratio
    waste_amount = calculate_waste(grant, verification_gap)
    waste_percentage = waste_amount / amount if amount > 0 else 0

    # Determine recommendation
    if verification_ratio >= 0.90:
        recommendation = "approved"
    elif verification_ratio >= WEAK_VERIFICATION_THRESHOLD:
        recommendation = "investigate"
    elif verification_ratio >= 0.40:
        recommendation = "suspend"
    else:
        recommendation = "terminate"

    result = {
        "receipt_type": "waste",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "grant_id": grant_id,
        "program": "epa",
        "allocated_amount_usd": amount,
        "verification_ratio": round(verification_ratio, 4),
        "waste_amount_usd": round(waste_amount, 2),
        "waste_percentage": round(waste_percentage, 4),
        "verification_gap": _describe_verification_gap(grant),
        "recommendation": recommendation,
        "compression_ratio": compression["compression_ratio"],
        "audit_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",  # Computed below
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))

    # Emit waste receipt (CLAUDEME LAW_1)
    emit_receipt(result)

    return result


def audit_doe_loan(
    loan: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Audit single DOE loan/subsidy for waste.

    Args:
        loan: Loan dict with loan_id, amount, verification data
        tenant_id: Tenant identifier

    Returns:
        dict: waste_receipt with waste analysis
    """
    start_time = time.time()

    loan_id = loan.get("loan_id", loan.get("grant_id", "UNKNOWN"))
    amount = loan.get("amount", 0) or loan.get("allocated_amount_usd", 0)

    # Run compression test
    compression = compress_test(loan)

    # Calculate verification ratio
    verification_ratio = _calculate_verification_ratio(loan)

    # Calculate waste
    verification_gap = 1.0 - verification_ratio
    waste_amount = calculate_waste(loan, verification_gap)
    waste_percentage = waste_amount / amount if amount > 0 else 0

    # Determine recommendation
    if verification_ratio >= 0.90:
        recommendation = "approved"
    elif verification_ratio >= WEAK_VERIFICATION_THRESHOLD:
        recommendation = "investigate"
    elif verification_ratio >= 0.40:
        recommendation = "suspend"
    else:
        recommendation = "terminate"

    result = {
        "receipt_type": "waste",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "grant_id": loan_id,
        "program": "doe",
        "allocated_amount_usd": amount,
        "verification_ratio": round(verification_ratio, 4),
        "waste_amount_usd": round(waste_amount, 2),
        "waste_percentage": round(waste_percentage, 4),
        "verification_gap": _describe_verification_gap(loan),
        "recommendation": recommendation,
        "compression_ratio": compression["compression_ratio"],
        "audit_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))
    emit_receipt(result)

    return result


def batch_audit(
    grants: list[dict[str, Any]],
    source: str = "epa",
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Batch audit EPA or DOE programs.

    Args:
        grants: List of grants/loans to audit
        source: "epa" or "doe"
        tenant_id: Tenant identifier

    Returns:
        list: List of waste_receipts
    """
    audit_fn = audit_epa_grant if source == "epa" else audit_doe_loan

    results = []
    for grant in grants:
        result = audit_fn(grant, tenant_id)
        results.append(result)

    return results


def calculate_waste(
    grant: dict[str, Any],
    verification_gap: float,
) -> float:
    """Calculate $ wasted based on verification gap.

    Waste = allocated_amount × verification_gap × waste_factor

    Args:
        grant: Grant data
        verification_gap: 1 - verification_ratio

    Returns:
        float: Estimated waste in USD
    """
    amount = grant.get("amount", 0) or grant.get("allocated_amount_usd", 0)

    # Waste factor increases with gap severity
    if verification_gap > 0.60:
        waste_factor = 0.90  # Very weak verification = 90% waste
    elif verification_gap > 0.40:
        waste_factor = 0.70  # Weak verification = 70% waste
    elif verification_gap > 0.20:
        waste_factor = 0.40  # Moderate gap = 40% waste
    else:
        waste_factor = 0.10  # Small gap = 10% waste

    return amount * verification_gap * waste_factor


def generate_dashboard(
    receipts: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate DOGE dashboard summary.

    Args:
        receipts: List of waste_receipts
        tenant_id: Tenant identifier

    Returns:
        dict: Dashboard summary
    """
    total_audited = len(receipts)
    total_allocated = sum(r.get("allocated_amount_usd", 0) for r in receipts)
    total_waste = sum(r.get("waste_amount_usd", 0) for r in receipts)

    by_recommendation = {
        "approved": [],
        "investigate": [],
        "suspend": [],
        "terminate": [],
    }

    for r in receipts:
        rec = r.get("recommendation", "investigate")
        if rec in by_recommendation:
            by_recommendation[rec].append(r)

    by_program = {"epa": [], "doe": []}
    for r in receipts:
        prog = r.get("program", "epa")
        if prog in by_program:
            by_program[prog].append(r)

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_grants_audited": total_audited,
        "total_allocated_usd": total_allocated,
        "total_waste_identified_usd": total_waste,
        "waste_rate": total_waste / total_allocated if total_allocated > 0 else 0,
        "by_recommendation": {
            k: len(v) for k, v in by_recommendation.items()
        },
        "by_program": {
            k: {"count": len(v), "waste": sum(r.get("waste_amount_usd", 0) for r in v)}
            for k, v in by_program.items()
        },
        "top_waste_grants": sorted(
            receipts,
            key=lambda r: r.get("waste_amount_usd", 0),
            reverse=True
        )[:10],
    }

    # Emit dashboard receipt
    receipt = {
        "receipt_type": "doge_dashboard",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(dashboard, sort_keys=True)),
        "total_audited": total_audited,
        "total_waste_usd": total_waste,
    }
    emit_receipt(receipt)

    return dashboard


def flag_weak_verification(
    grants: list[dict[str, Any]],
    threshold: float = WEAK_VERIFICATION_THRESHOLD,
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Flag programs with verification below threshold.

    Args:
        grants: List of grants to check
        threshold: Verification threshold
        tenant_id: Tenant identifier

    Returns:
        list: Grants with weak verification
    """
    weak = []
    for grant in grants:
        ratio = _calculate_verification_ratio(grant)
        if ratio < threshold:
            weak.append({
                **grant,
                "verification_ratio": ratio,
                "flagged_reason": "weak_verification",
            })

    return weak


def total_waste_estimate(
    receipts: list[dict[str, Any]],
) -> float:
    """Sum total waste across all audits.

    Args:
        receipts: List of waste_receipts

    Returns:
        float: Total waste in USD
    """
    return sum(r.get("waste_amount_usd", 0) for r in receipts)


def _calculate_verification_ratio(data: dict[str, Any]) -> float:
    """Calculate verification ratio from grant/loan data.

    Higher ratio = better verification.
    """
    # Check for explicit verification fields
    if "verification_ratio" in data:
        return data["verification_ratio"]

    if "verification_score" in data:
        return data["verification_score"]

    # Infer from compression and data quality
    compression = compress_test(data)

    # Check for key verification indicators
    indicators = 0
    max_indicators = 5

    if data.get("third_party_audit"):
        indicators += 1
    if data.get("site_visit_completed"):
        indicators += 1
    if data.get("outcome_metrics"):
        indicators += 1
    if data.get("financial_audit"):
        indicators += 1
    if data.get("progress_reports"):
        indicators += 1

    indicator_score = indicators / max_indicators

    # Combine compression and indicators
    return (compression["compression_ratio"] * 0.4 + indicator_score * 0.6)


def _describe_verification_gap(data: dict[str, Any]) -> str:
    """Describe what verification is missing."""
    missing = []

    if not data.get("third_party_audit"):
        missing.append("No third-party audit")
    if not data.get("site_visit_completed"):
        missing.append("No site visit")
    if not data.get("outcome_metrics"):
        missing.append("No outcome metrics")
    if not data.get("financial_audit"):
        missing.append("No financial audit")
    if not data.get("progress_reports"):
        missing.append("No progress reports")

    if not missing:
        return "Verification complete"

    return "; ".join(missing)
