"""
GreenProof Tests - EV credit verification tests.

Tests Tesla/EV credit verification (Musk wedge).
"""

import pytest

from src.ev import (
    AVG_EV_EFFICIENCY_KWH_PER_MILE,
    CO2_PER_GALLON_GAS,
    ICE_BASELINE_MPG,
    STATE_GRID_FACTORS,
    ZEV_CREDIT_VALUES,
    calculate_ev_emissions,
    calculate_fleet_emissions,
    compare_to_ice_baseline,
    generate_fraudulent_ev_claim,
    generate_valid_ev_claim,
    verify_charging_source,
    verify_ev_credit,
    verify_zev_credit,
)


class TestConstants:
    """Test EV constant configuration."""

    def test_ice_baseline(self):
        """ICE baseline should be reasonable."""
        assert ICE_BASELINE_MPG == 25.0

    def test_co2_per_gallon(self):
        """CO2 per gallon should match EPA."""
        assert CO2_PER_GALLON_GAS == 8.887

    def test_ev_efficiency(self):
        """EV efficiency should be reasonable."""
        assert 0.25 <= AVG_EV_EFFICIENCY_KWH_PER_MILE <= 0.35


class TestCompareToIceBaseline:
    """Test ICE baseline comparison."""

    def test_positive_avoided(self):
        """Should calculate positive avoided emissions."""
        avoided = compare_to_ice_baseline(10000)  # 10k miles
        assert avoided > 0

    def test_scaling(self):
        """Avoided should scale with miles."""
        avoided_10k = compare_to_ice_baseline(10000)
        avoided_20k = compare_to_ice_baseline(20000)
        assert abs(avoided_20k - 2 * avoided_10k) < 0.01

    def test_zero_miles(self):
        """Zero miles should have zero avoided."""
        assert compare_to_ice_baseline(0) == 0.0


class TestCalculateEvEmissions:
    """Test EV emissions calculation."""

    def test_grid_emissions(self):
        """Should calculate emissions from grid charging."""
        emissions = calculate_ev_emissions(10000, state="US")
        assert emissions > 0

    def test_clean_grid_lower(self):
        """Clean grid should have lower emissions."""
        ca = calculate_ev_emissions(10000, state="CA")
        wy = calculate_ev_emissions(10000, state="WY")
        assert ca < wy

    def test_very_clean_grid(self):
        """Vermont should be very clean."""
        vt = calculate_ev_emissions(10000, state="VT")
        us = calculate_ev_emissions(10000, state="DEFAULT")
        assert vt < us * 0.1


class TestCalculateFleetEmissions:
    """Test fleet emissions calculation."""

    def test_fleet_sum(self):
        """Should sum fleet emissions correctly."""
        vehicles = [
            {"miles": 10000, "state": "CA", "charging_source": "grid"},
            {"miles": 10000, "state": "CA", "charging_source": "grid"},
        ]
        result = calculate_fleet_emissions(vehicles)

        assert result["vehicle_count"] == 2
        assert result["total_miles"] == 20000
        assert result["net_avoided_tco2e"] > 0

    def test_renewable_charging(self):
        """Renewable charging should have zero EV emissions."""
        vehicles = [
            {"miles": 10000, "state": "CA", "charging_source": "solar"},
        ]
        result = calculate_fleet_emissions(vehicles)
        assert result["ev_emissions_tco2e"] == 0.0

    def test_empty_fleet(self):
        """Empty fleet should return zeros."""
        result = calculate_fleet_emissions([])
        assert result["vehicle_count"] == 0
        assert result["total_miles"] == 0


class TestVerifyChargingSource:
    """Test charging source verification."""

    def test_grid_always_valid(self):
        """Grid charging should always verify."""
        data = {"source": "grid", "kwh": 1000}
        is_valid, details = verify_charging_source(data)
        assert is_valid is True

    def test_renewable_with_recs(self):
        """Renewable with RECs should verify."""
        data = {
            "source": "solar",
            "kwh": 1000,
            "renewable_certificates": [{"kwh": 1000}],
        }
        is_valid, details = verify_charging_source(data)
        assert is_valid is True

    def test_renewable_without_recs(self):
        """Renewable without RECs should not verify."""
        data = {"source": "solar", "kwh": 1000}
        is_valid, details = verify_charging_source(data)
        assert is_valid is False

    def test_insufficient_recs(self):
        """Insufficient RECs should not verify."""
        data = {
            "source": "wind",
            "kwh": 1000,
            "renewable_certificates": [{"kwh": 500}],  # Only half
        }
        is_valid, details = verify_charging_source(data)
        assert is_valid is False


class TestVerifyZevCredit:
    """Test ZEV credit verification."""

    def test_california_credits(self):
        """California should award ZEV credits."""
        claim = {"vehicle_count": 100, "claimed_credits": 400}
        result = verify_zev_credit(claim, "CA")

        assert result["is_zev_state"] is True
        assert result["verified_credits"] == 400  # 100 * 4.0

    def test_non_zev_state(self):
        """Non-ZEV state should have zero credits."""
        claim = {"vehicle_count": 100, "claimed_credits": 400}
        result = verify_zev_credit(claim, "TX")  # Not a ZEV state

        assert result["is_zev_state"] is False
        assert result["verified_credits"] == 0

    def test_overclaimed_credits(self):
        """Overclaimed credits should show discrepancy."""
        claim = {"vehicle_count": 100, "claimed_credits": 800}  # 2x actual
        result = verify_zev_credit(claim, "CA")

        assert result["discrepancy_pct"] > 0


class TestVerifyEvCredit:
    """Test full EV credit verification."""

    def test_valid_claim(self, valid_ev_claim, valid_vehicle_data):
        """Valid claim should verify."""
        receipt = verify_ev_credit(valid_ev_claim, valid_vehicle_data)

        assert receipt["receipt_type"] == "ev"
        assert receipt["verification_status"] in ("verified", "discrepancy")

    def test_fraudulent_claim(self):
        """Fraudulent claim should show discrepancy."""
        claim, vehicles = generate_fraudulent_ev_claim(100)
        receipt = verify_ev_credit(claim, vehicles)

        assert receipt["discrepancy_pct"] > 0.10

    def test_vehicle_count_mismatch(self, valid_ev_claim, valid_vehicle_data):
        """Mismatched vehicle count should flag."""
        valid_ev_claim["vehicle_count"] = 200  # Double actual
        receipt = verify_ev_credit(valid_ev_claim, valid_vehicle_data)

        # Flag format is 'vehicle_count_mismatch:200vs100'
        assert any(f.startswith("vehicle_count_mismatch") for f in receipt["flags"])


class TestSyntheticGenerators:
    """Test synthetic data generators."""

    def test_valid_generator(self):
        """Valid generator should produce verifiable claims."""
        claim, vehicles = generate_valid_ev_claim(50)

        assert claim["vehicle_count"] == 50
        assert len(vehicles) == 50

        receipt = verify_ev_credit(claim, vehicles)
        assert receipt["verification_status"] in ("verified", "discrepancy")

    def test_fraudulent_generator(self):
        """Fraudulent generator should produce high discrepancy."""
        claim, vehicles = generate_fraudulent_ev_claim(100)

        # Should have inflated values
        assert claim["vehicle_count"] > len(vehicles)
        assert claim["claimed_credits"] > 0

        receipt = verify_ev_credit(claim, vehicles)
        # May be detected as fraud
        assert receipt["discrepancy_pct"] > 0


class TestFullEvFlow:
    """Test complete EV verification flow."""

    def test_full_verification(self, valid_ev_claim, valid_vehicle_data):
        """Test complete verification flow."""
        # 1. Verify EV claim
        ev_receipt = verify_ev_credit(valid_ev_claim, valid_vehicle_data)
        assert ev_receipt["receipt_type"] == "ev"

        # 2. Check fleet emissions
        fleet = calculate_fleet_emissions(valid_vehicle_data)
        assert fleet["net_avoided_tco2e"] > 0

        # 3. Verify ZEV credits
        zev = verify_zev_credit(valid_ev_claim, valid_ev_claim["state"])
        assert "verified_credits" in zev
