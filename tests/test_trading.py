"""
GreenProof Tests - Trading layer tests.

Tests Chamath's "legitimate exchange" infrastructure.
"""

import pytest

from src.compress import compress_claim
from src.core import StopRule
from src.detect import detect_fraud
from src.registry import register_claim
from src.trading import (
    calculate_price,
    create_listing,
    execute_trade,
    generate_custody_receipt,
    get_market_stats,
    get_trading_state,
    match_order,
    reset_trading,
    retire_credit,
    validate_listing,
)


class TestCalculatePrice:
    """Test price calculation."""

    def test_base_price_verra(self):
        """Verra base price should apply."""
        claim = {"registry": "verra", "vintage_year": 2024}
        price = calculate_price(claim)
        assert price >= 6.0  # Base is 8.0, minus depreciation

    def test_gold_standard_premium(self):
        """Gold Standard should have premium."""
        verra = {"registry": "verra", "vintage_year": 2024}
        gs = {"registry": "gold_standard", "vintage_year": 2024}
        assert calculate_price(gs) > calculate_price(verra)

    def test_dac_premium(self):
        """Direct air capture should have premium."""
        regular = {"registry": "verra", "project_type": "forest", "vintage_year": 2024}
        dac = {"registry": "verra", "project_type": "direct_air_capture", "vintage_year": 2024}
        assert calculate_price(dac) > calculate_price(regular)

    def test_vintage_depreciation(self):
        """Older vintage should be cheaper."""
        new = {"registry": "verra", "vintage_year": 2024}
        old = {"registry": "verra", "vintage_year": 2020}
        assert calculate_price(new) > calculate_price(old)


class TestValidateListing:
    """Test listing validation."""

    def test_clean_valid(self, valid_claim):
        """Clean claim should be valid for listing."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        is_valid, reason = validate_listing(valid_claim, fraud_receipt)
        assert is_valid is True
        assert reason == "valid"

    def test_fraud_invalid(self, valid_claim):
        """Fraud claim should be invalid."""
        fraud_receipt = {"fraud_level": "likely_fraud", "recommendation": "reject"}
        is_valid, reason = validate_listing(valid_claim, fraud_receipt)
        assert is_valid is False
        assert "fraud_level" in reason

    def test_suspect_may_be_invalid(self, valid_claim):
        """Suspect with reject recommendation should be invalid."""
        fraud_receipt = {"fraud_level": "suspect", "recommendation": "reject"}
        is_valid, reason = validate_listing(valid_claim, fraud_receipt)
        assert is_valid is False


class TestCreateListing:
    """Test listing creation."""

    def test_create_valid_listing(self, valid_claim):
        """Should create listing for valid claim."""
        fraud_receipt = {
            "fraud_level": "clean",
            "recommendation": "approve",
            "payload_hash": "test-hash",
        }
        receipt = create_listing(valid_claim, fraud_receipt)

        assert receipt["receipt_type"] == "listing"
        assert receipt["status"] == "active"
        assert receipt["quantity_tco2e"] == valid_claim["quantity_tco2e"]
        assert "listing_id" in receipt

    def test_create_invalid_raises(self, valid_claim):
        """Should raise StopRule for invalid claim."""
        fraud_receipt = {"fraud_level": "confirmed_fraud", "recommendation": "reject"}
        with pytest.raises(StopRule):
            create_listing(valid_claim, fraud_receipt)

    def test_listing_stored(self, valid_claim):
        """Listing should be stored in state."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)
        state = get_trading_state()
        assert len(state["listings"]) == 1


class TestMatchOrder:
    """Test order matching."""

    def test_match_finds_listing(self, valid_claim):
        """Should find matching listing."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        bid = {
            "quantity_tco2e": 500,  # Less than listing
            "max_price_per_tco2e": 100.0,  # Higher than listing price
        }
        match = match_order(bid)
        assert match is not None
        assert match["quantity_tco2e"] >= bid["quantity_tco2e"]

    def test_no_match_insufficient_quantity(self, valid_claim):
        """Should not match if quantity insufficient."""
        valid_claim["quantity_tco2e"] = 100
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        bid = {"quantity_tco2e": 500, "max_price_per_tco2e": 100.0}
        match = match_order(bid)
        assert match is None

    def test_no_match_price_too_low(self, valid_claim):
        """Should not match if max price too low."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        bid = {"quantity_tco2e": 100, "max_price_per_tco2e": 0.01}
        match = match_order(bid)
        assert match is None


class TestExecuteTrade:
    """Test trade execution."""

    def test_execute_trade(self, valid_claim):
        """Should execute trade and emit receipt."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        # Get the listing
        state = get_trading_state()
        listing = list(state["listings"].values())[0]

        bid = {"quantity_tco2e": 500, "max_price_per_tco2e": 100.0}
        trade_receipt = execute_trade(bid, listing, buyer="test_buyer")

        assert trade_receipt["receipt_type"] == "trade"
        assert trade_receipt["buyer"] == "test_buyer"
        assert trade_receipt["settlement_status"] == "settled"
        assert "custody_receipt_hash" in trade_receipt

    def test_trade_updates_listing(self, valid_claim):
        """Trade should update listing quantity."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        state = get_trading_state()
        listing = list(state["listings"].values())[0]
        original_qty = listing["quantity_tco2e"]

        bid = {"quantity_tco2e": 500, "max_price_per_tco2e": 100.0}
        execute_trade(bid, listing)

        state = get_trading_state()
        updated_listing = list(state["listings"].values())[0]
        assert updated_listing["quantity_tco2e"] < original_qty


class TestRetireCredit:
    """Test credit retirement."""

    def test_retire_credit(self, valid_claim):
        """Should retire credit and emit receipt."""
        receipt = retire_credit(valid_claim["claim_id"], "Test Beneficiary")

        assert receipt["receipt_type"] == "retirement"
        assert receipt["status"] == "retired"
        assert receipt["beneficiary"] == "Test Beneficiary"

    def test_double_retirement_raises(self, valid_claim):
        """Double retirement should raise StopRule."""
        retire_credit(valid_claim["claim_id"], "First")

        with pytest.raises(StopRule):
            retire_credit(valid_claim["claim_id"], "Second")

    def test_retirement_delists(self, valid_claim):
        """Retirement should delist active listings."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        retire_credit(valid_claim["claim_id"], "Beneficiary")

        state = get_trading_state()
        listing = list(state["listings"].values())[0]
        assert listing["status"] == "retired"


class TestMarketStats:
    """Test market statistics."""

    def test_empty_market(self):
        """Empty market should show zeros."""
        stats = get_market_stats()
        assert stats["active_listings"] == 0
        assert stats["total_volume_tco2e"] == 0

    def test_with_listings(self, valid_claim):
        """Should calculate stats correctly."""
        fraud_receipt = {"fraud_level": "clean", "recommendation": "approve"}
        create_listing(valid_claim, fraud_receipt)

        stats = get_market_stats()
        assert stats["active_listings"] == 1
        assert stats["total_volume_tco2e"] == valid_claim["quantity_tco2e"]


class TestFullTradingFlow:
    """Test complete trading flow."""

    def test_full_flow(self, valid_claim):
        """Test claim -> listing -> trade -> retirement."""
        # 1. Verify claim
        comp_receipt = compress_claim(valid_claim)
        reg_receipt = register_claim(valid_claim)
        fraud_receipt = detect_fraud(valid_claim, comp_receipt, reg_receipt)

        # Should be clean
        assert fraud_receipt["fraud_level"] in ("clean", "suspect")

        # 2. List (only if clean)
        if fraud_receipt["fraud_level"] == "clean":
            listing_receipt = create_listing(valid_claim, fraud_receipt)
            assert listing_receipt["status"] == "active"

            # 3. Match and trade
            bid = {"quantity_tco2e": 500, "max_price_per_tco2e": 100.0}
            match = match_order(bid)
            if match:
                trade = execute_trade(bid, match)
                assert trade["settlement_status"] == "settled"

            # 4. Retire
            retire = retire_credit(valid_claim["claim_id"], "Test Corp")
            assert retire["status"] == "retired"
