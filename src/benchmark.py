"""
GreenProof Benchmark - Compression Anomaly Scoring for market data analysis.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

REFACTORED FROM expose.py - Uses legally-safe language.

LEGAL SAFEGUARDS:
- No "fraud" labels - uses "Compression Anomaly Score (CAS)" instead
- All outputs include legal disclaimers
- Scores are 0.0 to 1.0 (anomaly likelihood, not fraud determination)
- Reports are for "simulation purposes only"

Receipt: benchmark_receipt
SLO: Analysis time ≤ 500ms per company, anomaly detection accuracy ≥ 90%
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
from .compliance import (
    BENCHMARK_DISCLAIMER,
    MARKET_ANALYSIS_DISCLAIMER,
    inject_disclaimer,
    get_simulation_metadata,
)


# === BENCHMARK CONSTANTS ===
ANALYSIS_SUBJECTS = ["gm", "ford", "vw", "stellantis", "toyota", "honda"]
DATA_SOURCES = ["annual_report", "sustainability_report", "sec_filing"]
ANOMALY_INVESTIGATION_THRESHOLD = 0.70  # CAS above this warrants review

# Anomaly classification thresholds (CAS = 1 - compression_ratio)
ANOMALY_LEVELS = {
    "normal": 0.15,       # CAS 0.00-0.15 = normal variance
    "elevated": 0.30,     # CAS 0.15-0.30 = elevated, monitor
    "significant": 0.50,  # CAS 0.30-0.50 = significant, review recommended
    "high": 1.00,         # CAS 0.50+ = high anomaly, investigation warranted
}

# Legal disclaimer for all benchmark outputs
LEGAL_HEADER = f"""
{'='*70}
LEGAL DISCLAIMER
{'='*70}
{BENCHMARK_DISCLAIMER}

{MARKET_ANALYSIS_DISCLAIMER}
{'='*70}
"""


def benchmark_anomaly(
    subject: str,
    claims: list[dict[str, Any]] | None = None,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Benchmark data anomalies for a single subject.

    REFACTORED FROM: scan_company() in expose.py
    CHANGE: Uses CAS (Compression Anomaly Score) instead of "fraud level"

    Args:
        subject: Subject identifier (company name, etc.)
        claims: Optional list of data claims to analyze
        tenant_id: Tenant identifier

    Returns:
        dict: Benchmark result with CAS scores
    """
    start_time = time.time()

    subject_lower = subject.lower()

    # Generate synthetic claims if none provided
    if claims is None:
        claims = _generate_synthetic_claims(subject)

    results = []
    total_cas = 0.0

    for claim in claims:
        result = analyze_claim_anomaly(claim)
        results.append(result)
        total_cas += result["compression_anomaly_score"]

    avg_cas = total_cas / len(claims) if claims else 0
    overall_anomaly_level = classify_anomaly_level(avg_cas)

    # Count claims by anomaly level
    anomaly_counts = {
        "normal": 0,
        "elevated": 0,
        "significant": 0,
        "high": 0,
    }
    for r in results:
        level = r.get("anomaly_level", "normal")
        if level in anomaly_counts:
            anomaly_counts[level] += 1

    benchmark_result = {
        "subject": subject,
        "is_in_analysis_set": subject_lower in ANALYSIS_SUBJECTS,
        "claims_analyzed": len(claims),
        "anomaly_distribution": anomaly_counts,
        "average_cas": round(avg_cas, 4),
        "overall_anomaly_level": overall_anomaly_level,
        "claim_results": results,
        "analysis_time_ms": round((time.time() - start_time) * 1000, 2),
        # Simulation metadata
        "_simulation_metadata": get_simulation_metadata(),
    }

    # Inject legal disclaimers
    benchmark_result = inject_disclaimer(benchmark_result, "benchmark", "market")

    # Emit benchmark receipt
    receipt = {
        "receipt_type": "benchmark",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(benchmark_result, sort_keys=True)),
        "subject": subject,
        "claims_analyzed": len(claims),
        "average_cas": benchmark_result["average_cas"],
        "overall_anomaly_level": overall_anomaly_level,
    }
    emit_receipt(receipt)

    return benchmark_result


def analyze_claim_anomaly(
    claim: dict[str, Any],
) -> dict[str, Any]:
    """Analyze single claim for compression anomalies.

    REFACTORED FROM: compression_test_claim() in expose.py
    CHANGE: Returns CAS instead of "fraud_level"

    Args:
        claim: Claim data to analyze

    Returns:
        dict: Analysis result with CAS
    """
    compression = compress_test(claim)
    physical_ok = check_physical_consistency(claim)

    # CAS = 1 - compression_ratio (higher = more anomalous)
    compression_ratio = compression["compression_ratio"]
    cas = round(1.0 - compression_ratio, 4)

    anomaly_level = classify_anomaly_level(cas)

    # Physics inconsistency increases CAS
    if not physical_ok:
        cas = min(1.0, cas + 0.30)
        anomaly_level = "high"

    return {
        "claim_type": claim.get("claim_type", "unknown"),
        "data_source": claim.get("claim_source", "unknown"),
        "compression_ratio": compression_ratio,
        "compression_anomaly_score": cas,
        "physical_consistency": physical_ok,
        "anomaly_level": anomaly_level,
        "investigation_recommended": cas >= ANOMALY_INVESTIGATION_THRESHOLD,
    }


def classify_anomaly_level(cas: float) -> str:
    """Classify anomaly level based on CAS.

    REFACTORED FROM: classify_fraud_level() in expose.py
    CHANGE: Uses neutral "anomaly" language

    Args:
        cas: Compression Anomaly Score (0.0 to 1.0)

    Returns:
        str: Anomaly level classification
    """
    if cas < ANOMALY_LEVELS["normal"]:
        return "normal"
    elif cas < ANOMALY_LEVELS["elevated"]:
        return "elevated"
    elif cas < ANOMALY_LEVELS["significant"]:
        return "significant"
    else:
        return "high"


def batch_benchmark_analysis(
    subjects: list[str] | None = None,
    tenant_id: str = TENANT_ID,
) -> list[dict[str, Any]]:
    """Batch benchmark analysis for multiple subjects.

    REFACTORED FROM: batch_scan_industry() in expose.py

    Args:
        subjects: List of subjects to analyze (default: ANALYSIS_SUBJECTS)
        tenant_id: Tenant identifier

    Returns:
        list: Benchmark results for all subjects
    """
    if subjects is None:
        subjects = ANALYSIS_SUBJECTS

    results = []
    for subject in subjects:
        result = benchmark_anomaly(subject, tenant_id=tenant_id)
        results.append(result)

    return results


def generate_benchmark_report(
    results: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate benchmark analysis report.

    REFACTORED FROM: generate_exposure_report() in expose.py
    CHANGE: Uses CAS and neutral language throughout

    Args:
        results: Benchmark results
        tenant_id: Tenant identifier

    Returns:
        dict: Benchmark report with disclaimers
    """
    total_subjects = len(results)

    # Count by anomaly level
    level_counts = {
        "normal": 0,
        "elevated": 0,
        "significant": 0,
        "high": 0,
    }
    for r in results:
        level = r.get("overall_anomaly_level", "normal")
        if level in level_counts:
            level_counts[level] += 1

    total_claims = sum(r.get("claims_analyzed", 0) for r in results)

    # Calculate average CAS
    total_cas = sum(r.get("average_cas", 0) for r in results)
    avg_cas = total_cas / total_subjects if total_subjects > 0 else 0

    report = {
        "report_type": "benchmark_analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "subjects_analyzed": total_subjects,
        "anomaly_level_distribution": level_counts,
        "total_claims_analyzed": total_claims,
        "average_compression_anomaly_score": round(avg_cas, 4),
        "investigation_recommended_count": level_counts["significant"] + level_counts["high"],
        "subject_rankings": sorted(
            [
                {
                    "subject": r.get("subject"),
                    "cas": r.get("average_cas", 0),
                    "anomaly_level": r.get("overall_anomaly_level"),
                }
                for r in results
            ],
            key=lambda x: x["cas"],
            reverse=True,
        ),
        # Legal header (print-ready)
        "legal_header": LEGAL_HEADER,
        # Simulation metadata
        "_simulation_metadata": get_simulation_metadata(),
    }

    # Inject legal disclaimers
    report = inject_disclaimer(report, "benchmark", "market", "simulation")

    # Emit report receipt
    receipt = {
        "receipt_type": "benchmark_report",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(report, sort_keys=True)),
        "subjects_analyzed": total_subjects,
        "average_cas": report["average_compression_anomaly_score"],
    }
    emit_receipt(receipt)

    return report


def compare_to_reference(
    subject_results: list[dict[str, Any]],
    reference_results: list[dict[str, Any]],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Compare subject CAS to reference benchmark.

    REFACTORED FROM: compare_to_tesla() in expose.py
    CHANGE: Generic comparison without naming specific companies as "winners"

    Args:
        subject_results: Subject benchmark results
        reference_results: Reference benchmark results
        tenant_id: Tenant identifier

    Returns:
        dict: Comparison result
    """
    # Calculate averages
    subject_avg = sum(
        r.get("average_cas", 0) for r in subject_results
    ) / len(subject_results) if subject_results else 0

    reference_avg = sum(
        r.get("average_cas", 0) for r in reference_results
    ) / len(reference_results) if reference_results else 0.10  # Reference default low CAS

    delta = subject_avg - reference_avg

    # Neutral comparison result
    if abs(delta) < 0.10:
        comparison_result = "within_normal_variance"
    elif delta > 0:
        comparison_result = "subject_higher_anomaly"
    else:
        comparison_result = "reference_higher_anomaly"

    comparison = {
        "reference_avg_cas": round(reference_avg, 4),
        "subject_avg_cas": round(subject_avg, 4),
        "delta": round(delta, 4),
        "comparison_result": comparison_result,
        "reference_anomaly_level": classify_anomaly_level(reference_avg),
        "subject_anomaly_level": classify_anomaly_level(subject_avg),
        "statistical_note": (
            "CAS differences may be due to data quality, reporting methodology, "
            "or underlying operational differences. Further analysis by qualified "
            "professionals is recommended before drawing conclusions."
        ),
        # Legal disclaimers
        "_legal_disclaimers": [
            BENCHMARK_DISCLAIMER,
            MARKET_ANALYSIS_DISCLAIMER,
        ],
        "_simulation_metadata": get_simulation_metadata(),
    }

    # Emit comparison receipt
    receipt = {
        "receipt_type": "benchmark_comparison",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(comparison, sort_keys=True)),
        "comparison_result": comparison_result,
        "delta": comparison["delta"],
    }
    emit_receipt(receipt)

    return comparison


def _generate_synthetic_claims(subject: str) -> list[dict[str, Any]]:
    """Generate synthetic claims for analysis."""
    import random
    random.seed(hash(subject) % 2**32)

    claims = []

    # Emissions claim
    claims.append({
        "claim_type": "emissions_data",
        "claim_source": "sustainability_report",
        "claim_text": f"{subject} reported emissions change of {random.randint(5, 30)}%",
        "claim_data": {"change_pct": random.randint(5, 30)},
        "subject": subject,
    })

    # EV claim
    claims.append({
        "claim_type": "ev_data",
        "claim_source": "annual_report",
        "claim_text": f"{subject} EV sales data: {random.randint(10, 100)}% change",
        "claim_data": {"ev_change_pct": random.randint(10, 100)},
        "subject": subject,
    })

    # Energy claim
    claims.append({
        "claim_type": "energy_data",
        "claim_source": "sec_filing",
        "claim_text": f"{subject} renewable energy: {random.randint(20, 80)}%",
        "claim_data": {"renewable_pct": random.randint(20, 80)},
        "subject": subject,
    })

    return claims


# === BACKWARDS COMPATIBILITY ===
# These aliases allow existing code using expose.py names to continue working
# but emit deprecation warnings in logs

def scan_company(*args, **kwargs):
    """DEPRECATED: Use benchmark_anomaly() instead."""
    from warnings import warn
    warn(
        "scan_company() is deprecated. Use benchmark_anomaly() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return benchmark_anomaly(*args, **kwargs)


def batch_scan_industry(*args, **kwargs):
    """DEPRECATED: Use batch_benchmark_analysis() instead."""
    from warnings import warn
    warn(
        "batch_scan_industry() is deprecated. Use batch_benchmark_analysis() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return batch_benchmark_analysis(*args, **kwargs)


def generate_exposure_report(*args, **kwargs):
    """DEPRECATED: Use generate_benchmark_report() instead."""
    from warnings import warn
    warn(
        "generate_exposure_report() is deprecated. Use generate_benchmark_report() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return generate_benchmark_report(*args, **kwargs)
