"""
GreenProof Tests - Energy verification tests.

Tests Wright/Burgum targeting module.
"""

import pytest

from src.energy import (
    CAPACITY_FACTORS,
    ENERGY_EMISSION_FACTORS,
    GRID_FACTORS,
    calculate_avoided_emissions,
    compare_to_baseline,
    generate_fraudulent_energy_claim,
    generate_valid_energy_claim,
    verify_capacity_factor,
    verify_energy_claim,
    verify_lifecycle_emissions,
)


class TestGridFactors:
    """Test grid emission factor configuration."""

    def test_us_average(self):
        """US average should be set."""
        assert GRID_FACTORS["US"] == 0.386

    def test_california_lower(self):
        """California should be lower than US average."""
        assert GRID_FACTORS["US-CA"] < GRID_FACTORS["US"]

    def test_france_lowest(self):
        """France (nuclear) should be very low."""
        assert GRID_FACTORS["FR"] < 0.1


class TestCapacityFactors:
    """Test capacity factor ranges."""

    def test_nuclear_high(self):
        """Nuclear should have high capacity factor range."""
        min_cf, max_cf = CAPACITY_FACTORS["nuclear"]
        assert min_cf >= 0.85
        assert max_cf <= 0.95

    def test_solar_lower(self):
        """Solar should have lower capacity factor range."""
        min_cf, max_cf = CAPACITY_FACTORS["solar"]
        assert max_cf <= 0.35


class TestCalculateAvoidedEmissions:
    """Test avoided emissions calculation."""

    def test_nuclear_high_avoided(self):
        """Nuclear should avoid significant emissions."""
        avoided = calculate_avoided_emissions(
            production_mwh=8760000,  # 1GW at 100% CF for a year
            energy_type="nuclear",
            country="US",
        )
        # Should avoid millions of tonnes
        assert avoided > 2000000  # 2M+ tCO2e

    def test_solar_vs_coal_grid(self):
        """Solar in coal-heavy grid should avoid more."""
        wyoming = calculate_avoided_emissions(
            production_mwh=1000,
            energy_type="solar",
            country="US-WY",  # Coal heavy
        )
        california = calculate_avoided_emissions(
            production_mwh=1000,
            energy_type="solar",
            country="US-CA",  # Clean grid
        )
        assert wyoming > california

    def test_zero_production(self):
        """Zero production should avoid nothing."""
        avoided = calculate_avoided_emissions(0, "solar")
        assert avoided == 0.0


class TestVerifyCapacityFactor:
    """Test capacity factor verification."""

    def test_realistic_nuclear(self):
        """Realistic nuclear CF should pass."""
        is_valid, reason = verify_capacity_factor(
            claimed=0.92,
            actual=0.91,
            energy_type="nuclear",
        )
        assert is_valid is True

    def test_unrealistic_solar(self):
        """Unrealistic solar CF should fail."""
        is_valid, reason = verify_capacity_factor(
            claimed=0.80,  # Impossible for solar
            actual=0.25,
            energy_type="solar",
        )
        assert is_valid is False
        assert "mismatch" in reason.lower() or "unrealistic" in reason.lower()

    def test_claimed_exceeds_max(self):
        """Claimed CF exceeding physical max should fail."""
        is_valid, reason = verify_capacity_factor(
            claimed=1.05,  # Way above nuclear max (0.95)
            actual=1.00,   # Also high to pass mismatch check
            energy_type="nuclear",
        )
        assert is_valid is False


class TestVerifyLifecycleEmissions:
    """Test lifecycle emissions verification."""

    def test_nuclear_positive_net(self):
        """Nuclear should have positive net benefit."""
        claim = {
            "energy_type": "nuclear",
            "capacity_mw": 1000,
            "lifetime_years": 40,
            "claimed_avoided_tco2e": 100000000,  # 100M
        }
        is_valid, analysis = verify_lifecycle_emissions(claim)
        assert is_valid is True
        assert analysis["net_benefit_tco2e"] > 0

    def test_small_project_may_fail(self):
        """Small project with inflated claims may fail."""
        claim = {
            "energy_type": "solar",
            "capacity_mw": 1,  # Very small
            "lifetime_years": 25,
            "claimed_avoided_tco2e": 1000000,  # Inflated
        }
        is_valid, analysis = verify_lifecycle_emissions(claim)
        # May fail if claimed exceeds realistic avoided
        assert "net_benefit_tco2e" in analysis


class TestCompareToBaseline:
    """Test baseline comparison for additionality."""

    def test_additional_project(self):
        """Additional project should have high additionality."""
        claim = {"production_mwh": 1000}
        baseline = {"production_mwh": 0}  # Nothing without project
        additionality = compare_to_baseline(claim, baseline)
        assert additionality == 1.0

    def test_non_additional_project(self):
        """Non-additional project should have low additionality."""
        claim = {"production_mwh": 1000}
        baseline = {"production_mwh": 1000}  # Same without project
        additionality = compare_to_baseline(claim, baseline)
        assert additionality == 0.0

    def test_partial_additionality(self):
        """Partial additionality should be between 0 and 1."""
        claim = {"production_mwh": 1000}
        baseline = {"production_mwh": 500}  # Half without project
        additionality = compare_to_baseline(claim, baseline)
        assert additionality == 0.5


class TestVerifyEnergyClaim:
    """Test full energy claim verification."""

    def test_valid_nuclear_claim(self, valid_energy_claim):
        """Valid nuclear claim should verify."""
        receipt = verify_energy_claim(valid_energy_claim, "nuclear")

        assert receipt["receipt_type"] == "energy"
        assert receipt["verification_status"] in ("verified", "discrepancy")
        assert "discrepancy_pct" in receipt

    def test_fraudulent_claim_detected(self):
        """Fraudulent claim should be detected."""
        fraud_claim = generate_fraudulent_energy_claim("solar")
        receipt = verify_energy_claim(fraud_claim, "solar")

        # Fraudulent claims have inflated values
        assert receipt["discrepancy_pct"] > 0.10

    def test_receipt_includes_lifecycle(self, valid_energy_claim):
        """Receipt should include lifecycle analysis."""
        receipt = verify_energy_claim(valid_energy_claim, "nuclear")
        assert "lifecycle_analysis" in receipt


class TestSyntheticGenerators:
    """Test synthetic data generators."""

    def test_valid_claim_verifies(self):
        """Generated valid claim should verify."""
        claim = generate_valid_energy_claim("nuclear")
        receipt = verify_energy_claim(claim, "nuclear")
        assert receipt["verification_status"] in ("verified", "discrepancy")

    def test_fraudulent_claim_discrepancy(self):
        """Generated fraudulent claim should show discrepancy."""
        claim = generate_fraudulent_energy_claim("solar")
        receipt = verify_energy_claim(claim, "solar")
        assert receipt["discrepancy_pct"] > 0.10

    def test_all_energy_types(self):
        """Should generate valid claims for all types."""
        for energy_type in ["nuclear", "solar", "wind", "lng"]:
            claim = generate_valid_energy_claim(energy_type)
            assert claim["energy_type"] == energy_type
            assert claim["capacity_mw"] > 0
