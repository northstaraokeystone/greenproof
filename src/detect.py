"""
GreenProof Detect - Combined fraud detection module.

Detection Types:
1. Compression Fraud - claim doesn't compress (ratio < 0.70)
2. Double-Counting - same claim on multiple registries
3. Additionality Failure - project would have happened anyway
4. Permanence Failure - sequestration reversed (fire, logging)
5. Leakage - emissions displaced, not reduced
6. Baseline Inflation - exaggerated baseline scenario

SLOs:
- Detection time <= 500ms per claim
- False positive rate <= 5%
- False negative rate <= 1% on known fraud cases
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .compress import FRAUD_THRESHOLD, VERIFIED_THRESHOLD
from .core import (
    GREENPROOF_TENANT,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)

# === SLO THRESHOLDS ===
MAX_DETECTION_TIME_MS = 500
MAX_FALSE_POSITIVE_RATE = 0.05
MAX_FALSE_NEGATIVE_RATE = 0.01

# === FRAUD SCORE WEIGHTS ===
FRAUD_WEIGHTS = {
    "compression_fraud": 0.35,      # Highest weight - physics-based
    "double_counting": 0.30,        # Critical - direct fraud indicator
    "additionality": 0.15,          # Important but harder to prove
    "permanence": 0.10,             # Risk-based
    "leakage": 0.10,                # Risk-based
}

# === FRAUD LEVEL THRESHOLDS ===
FRAUD_LEVELS = {
    "clean": (0.0, 0.20),           # score 0-0.20
    "suspect": (0.20, 0.50),        # score 0.20-0.50
    "likely_fraud": (0.50, 0.80),   # score 0.50-0.80
    "confirmed_fraud": (0.80, 1.0), # score 0.80-1.0
}


@dataclass
class FraudCheck:
    """Result of a single fraud check."""
    check_type: str
    passed: bool
    score: float  # 0.0 = clean, 1.0 = definite fraud
    confidence: float  # Confidence in the result
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            **self.details,
        }


def check_compression_fraud(compression_receipt: dict[str, Any]) -> FraudCheck:
    """Check if claim fails compression test.

    Uses the classification field from compress_claim which incorporates:
    - Physics consistency check (primary)
    - Adjusted compression ratio thresholds (secondary)

    Args:
        compression_receipt: Receipt from compress_claim()

    Returns:
        FraudCheck: Result of compression check
    """
    ratio = compression_receipt.get("compression_ratio", 0.0)
    classification = compression_receipt.get("classification", "unknown")
    physics_consistent = compression_receipt.get("physics_consistent", True)
    physics_violations = compression_receipt.get("physics_violations", [])

    # Use classification from compress_claim (already incorporates physics checks)
    if classification == "verified":
        return FraudCheck(
            check_type="compression_fraud",
            passed=True,
            score=0.0,
            confidence=0.95,
            details={"ratio": ratio, "classification": classification, "physics_consistent": physics_consistent},
        )
    elif classification == "suspect":
        return FraudCheck(
            check_type="compression_fraud",
            passed=True,
            score=0.3,  # Moderate score for suspect
            confidence=0.70,
            details={"ratio": ratio, "classification": classification, "physics_consistent": physics_consistent},
        )
    else:
        # fraud_signal - physics check failed or very low compression
        # High score for fraud signal, especially if physics violations present
        score = 0.9 if not physics_consistent else 0.7
        return FraudCheck(
            check_type="compression_fraud",
            passed=False,
            score=score,
            confidence=0.95 if not physics_consistent else 0.80,
            details={
                "ratio": ratio,
                "classification": classification,
                "physics_consistent": physics_consistent,
                "physics_violations": physics_violations,
            },
        )


def check_double_counting(registry_receipt: dict[str, Any]) -> FraudCheck:
    """Check if claim appears on multiple registries.

    Zero tolerance for double-counting.

    Args:
        registry_receipt: Receipt from register_claim()

    Returns:
        FraudCheck: Result of double-counting check
    """
    duplicates = registry_receipt.get("duplicates_found", 0)
    overlap = registry_receipt.get("overlap_percentage", 0.0)
    duplicate_registries = registry_receipt.get("duplicate_registries", [])

    if duplicates == 0:
        return FraudCheck(
            check_type="double_counting",
            passed=True,
            score=0.0,
            confidence=0.99,
            details={"duplicates": 0},
        )
    else:
        # Any duplicate is a fraud signal
        # Score increases with number of duplicates
        score = min(1.0, 0.5 + (duplicates * 0.25))
        return FraudCheck(
            check_type="double_counting",
            passed=False,
            score=score,
            confidence=0.99,  # High confidence - this is definitive
            details={
                "duplicates": duplicates,
                "duplicate_registries": duplicate_registries,
                "overlap": overlap,
            },
        )


def check_additionality(claim: dict[str, Any]) -> FraudCheck:
    """Check if project would have happened anyway (additionality failure).

    Additionality signals:
    - Grid-connected renewable in wealthy country = suspect
    - Regulatory compliance projects = suspect
    - High ROI without carbon revenue = likely non-additional

    Args:
        claim: Carbon claim dict

    Returns:
        FraudCheck: Result of additionality check
    """
    project_type = claim.get("project_type", "").lower()
    country = claim.get("location", {}).get("country", "")
    methodology = claim.get("methodology", "").upper()

    score = 0.0
    flags = []

    # High-risk project types for non-additionality
    non_additional_types = ["landfill_gas", "hydro", "grid_solar", "grid_wind"]
    for nat in non_additional_types:
        if nat in project_type:
            score += 0.2
            flags.append(f"high_risk_type:{nat}")

    # Wealthy country grid projects often non-additional
    wealthy_countries = ["US", "DE", "FR", "GB", "JP", "AU", "CA"]
    if country in wealthy_countries and "grid" in project_type:
        score += 0.15
        flags.append(f"wealthy_country_grid:{country}")

    # Old methodologies more likely to have additionality issues
    if methodology and methodology.startswith("AM") and len(methodology) < 5:
        # Old AM methodologies (AM0001-AM0100)
        score += 0.1
        flags.append(f"old_methodology:{methodology}")

    score = min(1.0, score)
    passed = score < 0.3  # Pass if low additionality risk

    return FraudCheck(
        check_type="additionality",
        passed=passed,
        score=score,
        confidence=0.60,  # Lower confidence - harder to prove
        details={"flags": flags},
    )


def check_permanence(claim: dict[str, Any]) -> FraudCheck:
    """Check for permanence risk (sequestration reversal).

    Permanence risks:
    - Forest projects in fire-prone regions
    - Political instability in project location
    - Short project duration
    - No buffer pool allocation

    Args:
        claim: Carbon claim dict

    Returns:
        FraudCheck: Result of permanence check
    """
    project_type = claim.get("project_type", "").lower()
    country = claim.get("location", {}).get("country", "")
    duration_years = claim.get("project_duration_years", 0)

    score = 0.0
    risks = []

    # Forest/land-use projects have inherent permanence risk
    land_use_types = ["forest", "redd", "afforestation", "reforestation", "soil"]
    is_land_use = any(t in project_type for t in land_use_types)

    if is_land_use:
        score += 0.15
        risks.append("land_use_project")

        # Fire-prone regions
        fire_prone = ["BR", "AU", "US", "ID", "CA", "RU"]
        if country in fire_prone:
            score += 0.10
            risks.append(f"fire_prone_region:{country}")

        # Short duration = higher reversal risk
        if duration_years < 10:
            score += 0.15
            risks.append(f"short_duration:{duration_years}y")
        elif duration_years < 20:
            score += 0.05
            risks.append(f"medium_duration:{duration_years}y")

    # High political risk countries
    high_risk_countries = ["VE", "MM", "SD", "SY", "AF"]
    if country in high_risk_countries:
        score += 0.20
        risks.append(f"high_political_risk:{country}")

    score = min(1.0, score)
    passed = score < 0.3

    return FraudCheck(
        check_type="permanence",
        passed=passed,
        score=score,
        confidence=0.65,
        details={"risk": score, "risk_factors": risks},
    )


def check_leakage(claim: dict[str, Any]) -> FraudCheck:
    """Check for leakage (emissions displaced, not reduced).

    Leakage occurs when:
    - Deforestation moves to adjacent area
    - Industrial production moves to unregulated jurisdiction
    - Energy demand shifts without reduction

    Args:
        claim: Carbon claim dict

    Returns:
        FraudCheck: Result of leakage check
    """
    project_type = claim.get("project_type", "").lower()
    quantity = claim.get("quantity_tco2e", 0)

    score = 0.0
    risks = []

    # REDD+ has high leakage risk
    if "redd" in project_type:
        score += 0.15
        risks.append("redd_leakage_risk")

    # Very large single-project claims = potential leakage
    if quantity > 100000:  # 100k tCO2e
        score += 0.10
        risks.append(f"large_claim:{quantity}tCO2e")

    # Avoided deforestation without landscape approach
    if "avoided" in project_type and "deforestation" in project_type:
        score += 0.10
        risks.append("avoided_deforestation_leakage")

    score = min(1.0, score)
    passed = score < 0.3

    return FraudCheck(
        check_type="leakage",
        passed=passed,
        score=score,
        confidence=0.55,  # Hardest to verify
        details={"risk": score, "risk_factors": risks},
    )


def calculate_fraud_score(checks: list[FraudCheck]) -> float:
    """Aggregate fraud probability from all checks.

    Uses weighted average based on check importance and confidence.
    Applies escalation for high-confidence failures.

    Escalation Logic:
    - If any check has score >= 0.8 AND confidence >= 0.9, escalate to >= 0.6
    - This ensures physics violations (compression_fraud) trigger likely_fraud

    Args:
        checks: List of FraudCheck results

    Returns:
        float: Aggregate fraud score (0.0-1.0)
    """
    if not checks:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0
    max_critical_score = 0.0

    for check in checks:
        weight = FRAUD_WEIGHTS.get(check.check_type, 0.1)
        # Adjust weight by confidence
        adjusted_weight = weight * check.confidence
        weighted_sum += check.score * adjusted_weight
        total_weight += adjusted_weight

        # Track maximum high-confidence critical score
        if check.confidence >= 0.90 and check.score >= 0.80:
            max_critical_score = max(max_critical_score, check.score)

    if total_weight == 0:
        return 0.0

    base_score = weighted_sum / total_weight

    # Apply escalation: if we have a high-confidence critical failure,
    # ensure the final score is at least in likely_fraud territory
    if max_critical_score >= 0.80:
        # Escalate to at least 0.6 (likely_fraud threshold)
        escalated_score = max(base_score, 0.6)
        return min(1.0, escalated_score)

    return min(1.0, base_score)


def classify_fraud_level(score: float) -> str:
    """Classify fraud level from aggregate score.

    Args:
        score: Aggregate fraud score (0.0-1.0)

    Returns:
        str: Fraud level - "clean" | "suspect" | "likely_fraud" | "confirmed_fraud"
    """
    for level, (low, high) in FRAUD_LEVELS.items():
        if low <= score < high:
            return level
    return "confirmed_fraud" if score >= 0.80 else "clean"


def get_recommendation(fraud_level: str) -> str:
    """Get action recommendation based on fraud level.

    Args:
        fraud_level: Fraud classification

    Returns:
        str: Recommendation - "approve" | "manual_review" | "reject"
    """
    recommendations = {
        "clean": "approve",
        "suspect": "manual_review",
        "likely_fraud": "reject",
        "confirmed_fraud": "reject",
    }
    return recommendations.get(fraud_level, "manual_review")


def detect_fraud(
    claim: dict[str, Any],
    compression_receipt: dict[str, Any],
    registry_receipt: dict[str, Any],
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Run all fraud detection checks and emit fraud_receipt.

    Args:
        claim: Original carbon claim
        compression_receipt: Receipt from compress_claim()
        registry_receipt: Receipt from register_claim()
        tenant_id: Tenant identifier

    Returns:
        dict: fraud_receipt with all check results
    """
    start_time = time.time()

    claim_id = claim.get("claim_id", compression_receipt.get("claim_id", "unknown"))

    # Run all checks
    checks = [
        check_compression_fraud(compression_receipt),
        check_double_counting(registry_receipt),
        check_additionality(claim),
        check_permanence(claim),
        check_leakage(claim),
    ]

    # Calculate aggregate score
    fraud_score = calculate_fraud_score(checks)
    fraud_level = classify_fraud_level(fraud_score)
    recommendation = get_recommendation(fraud_level)

    # Check SLO
    elapsed_ms = (time.time() - start_time) * 1000
    if elapsed_ms > MAX_DETECTION_TIME_MS:
        emit_anomaly_receipt(
            tenant_id=tenant_id,
            anomaly_type="detection_timeout",
            classification="warning",
            details={
                "claim_id": claim_id,
                "elapsed_ms": elapsed_ms,
                "threshold_ms": MAX_DETECTION_TIME_MS,
            },
            action="flag",
        )

    # Build checks dict
    checks_dict = {check.check_type: check.to_dict() for check in checks}

    # Build and emit receipt
    receipt = {
        "receipt_type": "fraud",
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "fraud_score": round(fraud_score, 4),
        "fraud_level": fraud_level,
        "checks": checks_dict,
        "recommendation": recommendation,
        "processing_time_ms": round(elapsed_ms, 2),
        "payload_hash": dual_hash(json.dumps({
            "claim_id": claim_id,
            "checks": checks_dict,
            "score": fraud_score,
        }, sort_keys=True)),
    }

    return emit_receipt(receipt)


def batch_detect(
    claims: list[dict[str, Any]],
    compression_receipts: list[dict[str, Any]],
    registry_receipts: list[dict[str, Any]],
    tenant_id: str = GREENPROOF_TENANT,
) -> list[dict[str, Any]]:
    """Batch fraud detection for multiple claims.

    Args:
        claims: List of claims
        compression_receipts: Corresponding compression receipts
        registry_receipts: Corresponding registry receipts
        tenant_id: Tenant identifier

    Returns:
        list: List of fraud_receipts
    """
    receipts = []

    for claim, comp_rcpt, reg_rcpt in zip(
        claims, compression_receipts, registry_receipts
    ):
        try:
            receipt = detect_fraud(claim, comp_rcpt, reg_rcpt, tenant_id)
            receipts.append(receipt)
        except Exception as e:
            # Emit anomaly but continue processing
            emit_anomaly_receipt(
                tenant_id=tenant_id,
                anomaly_type="detection_error",
                classification="warning",
                details={
                    "claim_id": claim.get("claim_id"),
                    "error": str(e),
                },
                action="flag",
            )

    return receipts


def stoprule_fraud_detected(
    claim_id: str,
    fraud_level: str,
    fraud_score: float,
    tenant_id: str = GREENPROOF_TENANT,
) -> None:
    """Emit anomaly and raise StopRule for confirmed fraud.

    Args:
        claim_id: ID of fraudulent claim
        fraud_level: Fraud classification
        fraud_score: Aggregate fraud score
        tenant_id: Tenant identifier

    Raises:
        StopRule: Always
    """
    emit_anomaly_receipt(
        tenant_id=tenant_id,
        anomaly_type="confirmed_fraud",
        classification="critical",
        details={
            "claim_id": claim_id,
            "fraud_level": fraud_level,
            "fraud_score": fraud_score,
        },
        action="halt",
    )
    raise StopRule(
        f"Confirmed fraud: claim {claim_id} score={fraud_score:.2f} level={fraud_level}",
        classification="critical",
    )
