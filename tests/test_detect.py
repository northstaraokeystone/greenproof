"""
GreenProof Tests - Fraud detection tests.

Tests combined fraud detection across all check types.
"""

import pytest

from src.compress import compress_claim
from src.detect import (
    FRAUD_LEVELS,
    FRAUD_WEIGHTS,
    MAX_FALSE_NEGATIVE_RATE,
    MAX_FALSE_POSITIVE_RATE,
    FraudCheck,
    batch_detect,
    calculate_fraud_score,
    check_additionality,
    check_compression_fraud,
    check_double_counting,
    check_leakage,
    check_permanence,
    classify_fraud_level,
    detect_fraud,
    get_recommendation,
)
from src.registry import register_claim


class TestFraudWeights:
    """Test fraud weight configuration."""

    def test_weights_sum_to_one(self):
        """Fraud weights should sum to 1.0."""
        total = sum(FRAUD_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01  # Allow small float error

    def test_compression_highest_weight(self):
        """Compression fraud should have highest weight."""
        assert FRAUD_WEIGHTS["compression_fraud"] >= max(
            w for k, w in FRAUD_WEIGHTS.items() if k != "compression_fraud"
        )


class TestCheckCompressionFraud:
    """Test compression fraud check."""

    def test_verified_passes(self):
        """High ratio should pass."""
        receipt = {"compression_ratio": 0.90, "classification": "verified"}
        check = check_compression_fraud(receipt)
        assert check.passed is True
        assert check.score == 0.0

    def test_fraud_signal_fails(self):
        """Low ratio should fail."""
        receipt = {"compression_ratio": 0.50, "classification": "fraud_signal"}
        check = check_compression_fraud(receipt)
        assert check.passed is False
        assert check.score > 0.5

    def test_suspect_partial(self):
        """Mid ratio should have partial score."""
        receipt = {"compression_ratio": 0.75, "classification": "suspect"}
        check = check_compression_fraud(receipt)
        assert check.passed is True
        assert 0 < check.score < 0.5


class TestCheckDoubleConting:
    """Test double-counting check."""

    def test_no_duplicates_passes(self):
        """No duplicates should pass."""
        receipt = {"duplicates_found": 0, "overlap_percentage": 0.0}
        check = check_double_counting(receipt)
        assert check.passed is True
        assert check.score == 0.0
        assert check.confidence == 0.99

    def test_duplicates_fail(self):
        """Duplicates should fail."""
        receipt = {"duplicates_found": 2, "duplicate_registries": ["verra", "gold_standard"]}
        check = check_double_counting(receipt)
        assert check.passed is False
        assert check.score >= 0.5
        assert check.confidence == 0.99


class TestCheckAdditionality:
    """Test additionality check."""

    def test_forest_conservation_passes(self):
        """Forest conservation should generally pass."""
        claim = {
            "project_type": "forest_conservation",
            "location": {"country": "BR"},
            "methodology": "VM0007",
        }
        check = check_additionality(claim)
        assert check.score < 0.5

    def test_wealthy_country_grid_flags(self):
        """Wealthy country grid project should flag."""
        claim = {
            "project_type": "grid_solar",
            "location": {"country": "US"},
            "methodology": "AM0001",
        }
        check = check_additionality(claim)
        assert check.score > 0


class TestCheckPermanence:
    """Test permanence check."""

    def test_renewable_low_risk(self):
        """Renewable energy has low permanence risk."""
        claim = {
            "project_type": "renewable_energy",
            "location": {"country": "US"},
        }
        check = check_permanence(claim)
        assert check.score == 0.0

    def test_forest_has_risk(self):
        """Forest project has inherent risk."""
        claim = {
            "project_type": "forest_conservation",
            "location": {"country": "BR"},  # Fire-prone
        }
        check = check_permanence(claim)
        assert check.score > 0

    def test_high_political_risk(self):
        """High risk country should increase score."""
        claim = {
            "project_type": "forest",
            "location": {"country": "VE"},  # Venezuela
        }
        check = check_permanence(claim)
        assert check.score >= 0.20


class TestCheckLeakage:
    """Test leakage check."""

    def test_redd_has_risk(self):
        """REDD+ projects have leakage risk."""
        claim = {
            "project_type": "redd",
            "quantity_tco2e": 10000,
        }
        check = check_leakage(claim)
        assert check.score > 0

    def test_large_claim_risk(self):
        """Very large claims have leakage risk."""
        claim = {
            "project_type": "renewable",
            "quantity_tco2e": 500000,
        }
        check = check_leakage(claim)
        assert check.score > 0


class TestCalculateFraudScore:
    """Test aggregate fraud score calculation."""

    def test_all_pass_low_score(self):
        """All passing checks should give low score."""
        checks = [
            FraudCheck("compression_fraud", True, 0.0, 0.95),
            FraudCheck("double_counting", True, 0.0, 0.99),
            FraudCheck("additionality", True, 0.0, 0.60),
        ]
        score = calculate_fraud_score(checks)
        assert score < 0.1

    def test_one_fail_increases_score(self):
        """One failing check should increase score."""
        checks = [
            FraudCheck("compression_fraud", False, 0.8, 0.90),
            FraudCheck("double_counting", True, 0.0, 0.99),
            FraudCheck("additionality", True, 0.0, 0.60),
        ]
        score = calculate_fraud_score(checks)
        assert score > 0.2

    def test_empty_checks(self):
        """Empty checks should return 0."""
        assert calculate_fraud_score([]) == 0.0


class TestClassifyFraudLevel:
    """Test fraud level classification."""

    def test_clean(self):
        """Low score should be clean."""
        assert classify_fraud_level(0.10) == "clean"

    def test_suspect(self):
        """Mid-low score should be suspect."""
        assert classify_fraud_level(0.35) == "suspect"

    def test_likely_fraud(self):
        """Mid-high score should be likely_fraud."""
        assert classify_fraud_level(0.65) == "likely_fraud"

    def test_confirmed_fraud(self):
        """High score should be confirmed_fraud."""
        assert classify_fraud_level(0.90) == "confirmed_fraud"


class TestGetRecommendation:
    """Test recommendation generation."""

    def test_clean_approve(self):
        """Clean should recommend approve."""
        assert get_recommendation("clean") == "approve"

    def test_suspect_review(self):
        """Suspect should recommend review."""
        assert get_recommendation("suspect") == "manual_review"

    def test_fraud_reject(self):
        """Fraud should recommend reject."""
        assert get_recommendation("likely_fraud") == "reject"
        assert get_recommendation("confirmed_fraud") == "reject"


class TestDetectFraud:
    """Test full fraud detection pipeline."""

    def test_valid_claim_clean(self, valid_claim):
        """Valid claim should be classified as clean."""
        comp_receipt = compress_claim(valid_claim)
        reg_receipt = register_claim(valid_claim)
        fraud_receipt = detect_fraud(valid_claim, comp_receipt, reg_receipt)

        assert fraud_receipt["receipt_type"] == "fraud"
        assert fraud_receipt["fraud_level"] in ("clean", "suspect")
        assert fraud_receipt["recommendation"] in ("approve", "manual_review")

    def test_fraud_receipt_has_checks(self, valid_claim):
        """Fraud receipt should include all checks."""
        comp_receipt = compress_claim(valid_claim)
        reg_receipt = register_claim(valid_claim)
        fraud_receipt = detect_fraud(valid_claim, comp_receipt, reg_receipt)

        assert "checks" in fraud_receipt
        assert "compression_fraud" in fraud_receipt["checks"]
        assert "double_counting" in fraud_receipt["checks"]
        assert "additionality" in fraud_receipt["checks"]

    def test_processing_time_included(self, valid_claim):
        """Processing time should be included."""
        comp_receipt = compress_claim(valid_claim)
        reg_receipt = register_claim(valid_claim)
        fraud_receipt = detect_fraud(valid_claim, comp_receipt, reg_receipt)

        assert "processing_time_ms" in fraud_receipt


class TestBatchDetect:
    """Test batch fraud detection."""

    def test_batch_multiple(self, valid_claim):
        """Should process multiple claims."""
        claims = [valid_claim.copy() for _ in range(3)]
        for i, c in enumerate(claims):
            c["claim_id"] = f"batch-{i}"

        comp_receipts = [compress_claim(c) for c in claims]
        reg_receipts = [register_claim(c) for c in claims]
        fraud_receipts = batch_detect(claims, comp_receipts, reg_receipts)

        assert len(fraud_receipts) == 3
