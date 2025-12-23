"""
GreenProof Expose - Competitor exposure scanner.

Government Waste Elimination Engine v3.0

Compression-test legacy automaker ESG claims.
Expose fraudulent claims from GM, Ford, VW, Stellantis, Toyota, Honda.

Receipt: exposure_receipt
SLO: Scan time ≤ 500ms per company, fraud detection ≥ 90%
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
from .compress import compress_test, check_physical_consistency


# === EXPOSE CONSTANTS ===
LEGACY_AUTOMAKERS = ["gm", "ford", "vw", "stellantis", "toyota", "honda"]
ESG_CLAIM_SOURCES = ["annual_report", "sustainability_report", "sec_filing"]
EXPOSURE_THRESHOLD = 0.70  # Below this = likely fraudulent claims

# Fraud level thresholds
FRAUD_LEVELS = {
    "verified": 0.85,
    "suspect": 0.70,
    "likely_fraud": 0.50,
    "confirmed_fraud": 0.0,
}


def scan_company(
    company: str,
    claims: list[dict[str, Any]] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Scan single company's ESG claims.

    Args:
        company: Company name
        claims: Optional list of claims to test
        tenant_id: Tenant identifier

    Returns:
        dict: Scan result with exposure findings
    """
    start_time = time.time()

    company_lower = company.lower()

    # Generate synthetic claims if none provided
    if claims is None:
        claims = _generate_synthetic_claims(company)

    results = []
    fraud_count = 0
    total_compression = 0.0

    for claim in claims:
        result = compression_test_claim(claim)
        results.append(result)

        if result["fraud_level"] in ["likely_fraud", "confirmed_fraud"]:
            fraud_count += 1

        total_compression += result["compression_ratio"]

    avg_compression = total_compression / len(claims) if claims else 0
    overall_fraud_level = classify_fraud_level(avg_compression)

    scan_result = {
        "company": company,
        "is_legacy_automaker": company_lower in LEGACY_AUTOMAKERS,
        "claims_scanned": len(claims),
        "fraud_claims": fraud_count,
        "fraud_rate": fraud_count / len(claims) if claims else 0,
        "average_compression_ratio": round(avg_compression, 4),
        "overall_fraud_level": overall_fraud_level,
        "scan_results": results,
        "scan_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    # Emit scan receipt
    receipt = {
        "receipt_type": "company_scan",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(scan_result, sort_keys=True)),
        "company": company,
        "claims_scanned": len(claims),
        "fraud_rate": scan_result["fraud_rate"],
    }
    emit_receipt(receipt)

    return scan_result


def extract_esg_claims(
    report: dict[str, Any],
    source: str,
) -> list[dict[str, Any]]:
    """Extract ESG claims from report.

    Args:
        report: Report data
        source: Source type (annual_report, sustainability_report, sec_filing)

    Returns:
        list: Extracted claims
    """
    claims = []

    # Extract emissions claims
    if "emissions" in report:
        claims.append({
            "claim_type": "emissions_reduction",
            "claim_source": source,
            "claim_text": f"Emissions: {report['emissions']}",
            "claim_data": report["emissions"],
        })

    # Extract EV claims
    if "ev_sales" in report or "ev_percentage" in report:
        claims.append({
            "claim_type": "ev_transition",
            "claim_source": source,
            "claim_text": f"EV Sales: {report.get('ev_sales', report.get('ev_percentage'))}",
            "claim_data": report.get("ev_sales") or report.get("ev_percentage"),
        })

    # Extract renewable energy claims
    if "renewable_energy" in report:
        claims.append({
            "claim_type": "renewable_energy",
            "claim_source": source,
            "claim_text": f"Renewable: {report['renewable_energy']}%",
            "claim_data": report["renewable_energy"],
        })

    # Extract offset claims
    if "offsets_purchased" in report:
        claims.append({
            "claim_type": "offset_purchase",
            "claim_source": source,
            "claim_text": f"Offsets: {report['offsets_purchased']} tonnes",
            "claim_data": report["offsets_purchased"],
        })

    return claims


def compression_test_claim(
    claim: dict[str, Any],
) -> dict[str, Any]:
    """Run compression test on ESG claim.

    Args:
        claim: Claim to test

    Returns:
        dict: Test result with fraud level
    """
    compression = compress_test(claim)
    physical_ok = check_physical_consistency(claim)

    fraud_level = classify_fraud_level(compression["compression_ratio"])

    # Override if physics violation
    if not physical_ok:
        fraud_level = "confirmed_fraud"

    return {
        "claim_type": claim.get("claim_type", "unknown"),
        "claim_source": claim.get("claim_source", "unknown"),
        "compression_ratio": compression["compression_ratio"],
        "physical_consistency": physical_ok,
        "fraud_level": fraud_level,
    }


def classify_fraud_level(ratio: float) -> str:
    """Classify fraud level based on compression ratio.

    Args:
        ratio: Compression ratio

    Returns:
        str: Fraud level classification
    """
    if ratio >= FRAUD_LEVELS["verified"]:
        return "verified"
    elif ratio >= FRAUD_LEVELS["suspect"]:
        return "suspect"
    elif ratio >= FRAUD_LEVELS["likely_fraud"]:
        return "likely_fraud"
    else:
        return "confirmed_fraud"


def batch_scan_industry(
    companies: list[str] | None = None,
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Scan all companies in list.

    Args:
        companies: List of company names (default: LEGACY_AUTOMAKERS)
        tenant_id: Tenant identifier

    Returns:
        list: Scan results for all companies
    """
    if companies is None:
        companies = LEGACY_AUTOMAKERS

    results = []
    for company in companies:
        result = scan_company(company, tenant_id=tenant_id)
        results.append(result)

    return results


def generate_exposure_report(
    receipts: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate public exposure report.

    Args:
        receipts: Scan results
        tenant_id: Tenant identifier

    Returns:
        dict: Exposure report
    """
    total_companies = len(receipts)
    fraud_companies = sum(
        1 for r in receipts
        if r.get("overall_fraud_level") in ["likely_fraud", "confirmed_fraud"]
    )

    total_claims = sum(r.get("claims_scanned", 0) for r in receipts)
    fraud_claims = sum(r.get("fraud_claims", 0) for r in receipts)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companies_scanned": total_companies,
        "companies_with_fraud": fraud_companies,
        "total_claims_analyzed": total_claims,
        "fraud_claims_detected": fraud_claims,
        "industry_fraud_rate": fraud_claims / total_claims if total_claims > 0 else 0,
        "company_rankings": sorted(
            [
                {
                    "company": r.get("company"),
                    "fraud_rate": r.get("fraud_rate", 0),
                    "fraud_level": r.get("overall_fraud_level"),
                }
                for r in receipts
            ],
            key=lambda x: x["fraud_rate"],
            reverse=True,
        ),
    }

    # Emit exposure report receipt
    receipt = {
        "receipt_type": "exposure_report",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(report, sort_keys=True)),
        "companies_scanned": total_companies,
        "fraud_rate": report["industry_fraud_rate"],
    }
    emit_receipt(receipt)

    return report


def compare_to_tesla(
    company_receipts: list[dict[str, Any]],
    tesla_receipts: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Direct comparison to Tesla.

    Args:
        company_receipts: Legacy automaker receipts
        tesla_receipts: Tesla receipts
        tenant_id: Tenant identifier

    Returns:
        dict: Comparison result
    """
    # Calculate averages
    company_avg = sum(
        r.get("average_compression_ratio", 0) for r in company_receipts
    ) / len(company_receipts) if company_receipts else 0

    tesla_avg = sum(
        r.get("average_compression_ratio", 0) for r in tesla_receipts
    ) / len(tesla_receipts) if tesla_receipts else 0.90  # Tesla default high

    delta = tesla_avg - company_avg

    if delta > 0.10:
        winner = "tesla"
    elif delta < -0.10:
        winner = "competitor"
    else:
        winner = "tie"

    comparison = {
        "tesla_compression_ratio": round(tesla_avg, 4),
        "competitor_compression_ratio": round(company_avg, 4),
        "delta": round(delta, 4),
        "winner": winner,
        "tesla_fraud_level": classify_fraud_level(tesla_avg),
        "competitor_fraud_level": classify_fraud_level(company_avg),
    }

    # Emit comparison receipt
    receipt = {
        "receipt_type": "exposure",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(comparison, sort_keys=True)),
        "company": "industry_vs_tesla",
        "claim_source": "comparison",
        "claim_type": "industry_comparison",
        "claim_text": f"Tesla vs Legacy Automakers",
        "compression_ratio": company_avg,
        "fraud_level": classify_fraud_level(company_avg),
        "evidence": [f"Delta: {delta:.4f}", f"Winner: {winner}"],
        "tesla_comparison": comparison,
    }
    emit_receipt(receipt)

    return comparison


def _generate_synthetic_claims(company: str) -> list[dict[str, Any]]:
    """Generate synthetic ESG claims for testing."""
    import random
    random.seed(hash(company) % 2**32)

    claims = []

    # Emissions claim
    claims.append({
        "claim_type": "emissions_reduction",
        "claim_source": "sustainability_report",
        "claim_text": f"{company} reduced emissions by {random.randint(5, 30)}%",
        "claim_data": {"reduction_pct": random.randint(5, 30)},
        "company": company,
    })

    # EV claim
    claims.append({
        "claim_type": "ev_transition",
        "claim_source": "annual_report",
        "claim_text": f"{company} EV sales grew {random.randint(10, 100)}%",
        "claim_data": {"ev_growth_pct": random.randint(10, 100)},
        "company": company,
    })

    # Renewable energy claim
    claims.append({
        "claim_type": "renewable_energy",
        "claim_source": "sec_filing",
        "claim_text": f"{company} uses {random.randint(20, 80)}% renewable energy",
        "claim_data": {"renewable_pct": random.randint(20, 80)},
        "company": company,
    })

    return claims
