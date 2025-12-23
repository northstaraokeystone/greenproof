"""
GreenProof Detect - Waste and fraud detection with competitor exposure.

Government Waste Elimination Engine v3.0

Compression-based waste detection. The compression ratio IS the fraud signal.
Physics can't lie. Real data compresses. Fake doesn't.

Functions:
- detect_waste: Core waste detection via compression
- expose_competitor: Competitor ESG claim exposure
- generate_waste_report: Waste-focused reporting
"""

import json
from typing import Any

from .core import (
    COMPRESSION_FRAUD_THRESHOLD,
    TENANT_ID,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)
from .compress import compress_test, check_physical_consistency, waste_validate


# === THRESHOLDS ===
WASTE_THRESHOLD = 0.70  # Below this = waste/fraud
SUSPECT_THRESHOLD = 0.85  # Below this = suspicious


def detect_waste(
    claim: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Detect waste/fraud in claim using compression analysis.

    Wrapper for waste_validate with waste-focused language.

    Args:
        claim: Claim to analyze
        evidence: Supporting evidence
        tenant_id: Tenant identifier

    Returns:
        dict: Detection result
    """
    result = waste_validate(claim, evidence, tenant_id)

    # Add waste-specific fields
    waste_detected = result["validation_status"] == "waste_detected"
    waste_amount = None

    if waste_detected:
        # Estimate waste amount if financial data present
        if "amount_usd" in claim:
            waste_amount = claim["amount_usd"]
        elif "allocated_amount_usd" in claim:
            # Waste is proportional to verification gap
            gap = 1.0 - result["compression_ratio"]
            waste_amount = claim["allocated_amount_usd"] * gap

    return {
        **result,
        "waste_detected": waste_detected,
        "waste_amount_usd": waste_amount,
        "recommendation": _get_recommendation(result["validation_status"]),
    }


def _get_recommendation(status: str) -> str:
    """Get recommendation based on validation status."""
    recommendations = {
        "valid": "approved",
        "suspicious": "investigate",
        "waste_detected": "suspend",
    }
    return recommendations.get(status, "review")


def batch_detect(
    claims: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Batch waste detection across multiple claims.

    Args:
        claims: List of claims to analyze
        tenant_id: Tenant identifier

    Returns:
        dict: Batch detection summary
    """
    results = []
    total_waste = 0.0
    waste_count = 0

    for claim in claims:
        result = detect_waste(claim, tenant_id=tenant_id)
        results.append(result)

        if result["waste_detected"]:
            waste_count += 1
            if result["waste_amount_usd"]:
                total_waste += result["waste_amount_usd"]

    return {
        "total_claims": len(claims),
        "waste_detected_count": waste_count,
        "waste_detection_rate": waste_count / len(claims) if claims else 0,
        "total_waste_usd": total_waste,
        "results": results,
    }


def expose_competitor(
    company: str,
    claims: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Expose competitor ESG claims using compression testing.

    Compression-tests all claims and generates exposure report.

    Args:
        company: Company name
        claims: List of ESG claims to test
        tenant_id: Tenant identifier

    Returns:
        dict: Exposure result
    """
    exposure_results = []
    fraud_count = 0

    for claim in claims:
        # Add company context
        claim_with_context = {**claim, "company": company}

        # Run compression test
        result = detect_waste(claim_with_context, tenant_id=tenant_id)

        fraud_level = _classify_fraud_level(result["compression_ratio"])

        exposure_results.append({
            "claim": claim,
            "compression_ratio": result["compression_ratio"],
            "fraud_level": fraud_level,
            "physical_consistency": result["physical_consistency"],
        })

        if fraud_level in ["likely_fraud", "confirmed_fraud"]:
            fraud_count += 1

    exposure = {
        "company": company,
        "claims_tested": len(claims),
        "fraud_claims": fraud_count,
        "fraud_rate": fraud_count / len(claims) if claims else 0,
        "exposure_results": exposure_results,
    }

    # Emit exposure receipt (CLAUDEME LAW_1)
    receipt = {
        "receipt_type": "competitor_exposure",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(exposure, sort_keys=True)),
        "company": company,
        "claims_tested": len(claims),
        "fraud_claims": fraud_count,
        "fraud_rate": exposure["fraud_rate"],
    }
    emit_receipt(receipt)

    return exposure


def _classify_fraud_level(compression_ratio: float) -> str:
    """Classify fraud level based on compression ratio.

    Args:
        compression_ratio: Compression test result

    Returns:
        str: Fraud level classification
    """
    if compression_ratio >= 0.85:
        return "verified"
    elif compression_ratio >= 0.70:
        return "suspect"
    elif compression_ratio >= 0.50:
        return "likely_fraud"
    else:
        return "confirmed_fraud"


def generate_waste_report(
    results: list[dict[str, Any]],
    report_type: str = "summary",
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate waste-focused report from detection results.

    Args:
        results: Detection results from detect_waste or batch_detect
        report_type: "summary" | "detailed"
        tenant_id: Tenant identifier

    Returns:
        dict: Waste report
    """
    total = len(results)
    waste_items = [r for r in results if r.get("waste_detected")]
    suspicious_items = [r for r in results if r.get("validation_status") == "suspicious"]
    verified_items = [r for r in results if r.get("validation_status") == "valid"]

    total_waste_usd = sum(
        r.get("waste_amount_usd", 0) or 0
        for r in waste_items
    )

    report = {
        "report_type": "waste_elimination",
        "total_analyzed": total,
        "verified_count": len(verified_items),
        "suspicious_count": len(suspicious_items),
        "waste_detected_count": len(waste_items),
        "total_waste_usd": total_waste_usd,
        "detection_rate": len(waste_items) / total if total > 0 else 0,
        "recommendations": {
            "investigate": len(suspicious_items),
            "suspend": len(waste_items),
            "approved": len(verified_items),
        },
    }

    if report_type == "detailed":
        report["waste_items"] = waste_items
        report["suspicious_items"] = suspicious_items

    # Emit report receipt
    receipt = {
        "receipt_type": "waste_report",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(report, sort_keys=True)),
        "total_analyzed": total,
        "waste_detected_count": len(waste_items),
        "total_waste_usd": total_waste_usd,
    }
    emit_receipt(receipt)

    return report
