"""
GreenProof Tests - Registry integration tests.

Tests multi-registry deduplication and double-counting detection.
"""

import pytest

from src.core import StopRule
from src.registry import (
    calculate_overlap,
    check_duplicate,
    cross_registry_scan,
    generate_duplicate_claims,
    generate_unique_claims,
    get_registry_state,
    hash_claim_identity,
    normalize_claim,
    register_claim,
    reset_registry,
    stoprule_duplicate_claim,
)


class TestNormalizeClaim:
    """Test claim normalization from registry-specific format."""

    def test_normalize_verra(self):
        """Should normalize Verra format."""
        raw = {
            "ID": "VCS-123",
            "Name": "Test Project",
            "Methodology": "VM0007",
            "Vintage": 2023,
            "Quantity": 1000,
        }
        normalized = normalize_claim(raw, "verra")
        assert normalized["registry"] == "verra"
        assert normalized["project_id"] == "VCS-123"
        assert normalized["quantity_tco2e"] == 1000

    def test_normalize_gold_standard(self):
        """Should normalize Gold Standard format."""
        raw = {
            "GS ID": "GS-456",
            "Project Name": "Gold Project",
            "VERs Issued": 2000,
        }
        normalized = normalize_claim(raw, "gold_standard")
        assert normalized["registry"] == "gold_standard"
        assert normalized["project_id"] == "GS-456"
        assert normalized["quantity_tco2e"] == 2000

    def test_normalize_unknown_registry(self):
        """Unknown registry should return claim with registry tag."""
        raw = {"project_id": "UNKNOWN-1", "quantity": 500}
        normalized = normalize_claim(raw, "unknown_registry")
        assert normalized["registry"] == "unknown_registry"

    def test_normalize_adds_claim_id(self):
        """Should generate claim_id if missing."""
        raw = {"ID": "VCS-789"}
        normalized = normalize_claim(raw, "verra")
        assert "claim_id" in normalized


class TestHashClaimIdentity:
    """Test identity hashing for deduplication."""

    def test_same_claim_same_hash(self):
        """Same claim should produce same hash."""
        claim = {
            "project_id": "VCS-123",
            "vintage_year": 2023,
            "quantity_tco2e": 1000,
            "location": {"country": "BR"},
        }
        hash1 = hash_claim_identity(claim)
        hash2 = hash_claim_identity(claim)
        assert hash1 == hash2

    def test_different_project_different_hash(self):
        """Different project_id should produce different hash."""
        claim1 = {"project_id": "VCS-123", "vintage_year": 2023, "quantity_tco2e": 1000}
        claim2 = {"project_id": "VCS-456", "vintage_year": 2023, "quantity_tco2e": 1000}
        assert hash_claim_identity(claim1) != hash_claim_identity(claim2)

    def test_different_vintage_different_hash(self):
        """Different vintage_year should produce different hash."""
        claim1 = {"project_id": "VCS-123", "vintage_year": 2023, "quantity_tco2e": 1000}
        claim2 = {"project_id": "VCS-123", "vintage_year": 2024, "quantity_tco2e": 1000}
        assert hash_claim_identity(claim1) != hash_claim_identity(claim2)

    def test_hash_format(self):
        """Hash should be in dual-hash format."""
        claim = {"project_id": "VCS-123"}
        h = hash_claim_identity(claim)
        assert "SHA256:" in h
        assert "BLAKE3:" in h


class TestRegisterClaim:
    """Test claim registration."""

    def test_register_new_claim(self, valid_claim):
        """Should register new claim and emit receipt."""
        receipt = register_claim(valid_claim)
        assert receipt["receipt_type"] == "registry"
        assert receipt["duplicates_found"] == 0
        assert receipt["overlap_percentage"] == 0.0

    def test_register_duplicate_detected(self, valid_claim):
        """Should detect duplicate on second registration."""
        # Register first time
        register_claim(valid_claim)

        # Create duplicate with same identity but different claim_id
        duplicate = valid_claim.copy()
        duplicate["claim_id"] = "different-id"
        duplicate["registry"] = "gold_standard"

        receipt = register_claim(duplicate)
        assert receipt["duplicates_found"] == 1
        assert "verra" in receipt["duplicate_registries"]

    def test_register_updates_state(self, valid_claim):
        """Registration should update global state."""
        register_claim(valid_claim)
        state = get_registry_state()
        assert len(state) > 0


class TestCheckDuplicate:
    """Test duplicate checking."""

    def test_no_duplicate(self, valid_claim):
        """Should return None for non-duplicate."""
        identity = hash_claim_identity(valid_claim)
        result = check_duplicate(identity)
        assert result is None

    def test_finds_duplicate(self, valid_claim):
        """Should find duplicate after registration."""
        register_claim(valid_claim)
        identity = hash_claim_identity(valid_claim)
        result = check_duplicate(identity)
        assert result is not None
        assert result["claim_id"] == valid_claim["claim_id"]


class TestCrossRegistryScan:
    """Test cross-registry scanning."""

    def test_scan_finds_matches(self, valid_claim):
        """Should find registered claims."""
        register_claim(valid_claim)

        matches = cross_registry_scan(valid_claim)
        assert len(matches) == 1

    def test_scan_empty_registry(self, valid_claim):
        """Should return empty for unregistered claim."""
        matches = cross_registry_scan(valid_claim)
        assert len(matches) == 0


class TestCalculateOverlap:
    """Test overlap calculation."""

    def test_no_overlap(self):
        """Unique claims should have 0 overlap."""
        claims = generate_unique_claims(10)
        overlap = calculate_overlap(claims)
        assert overlap == 0.0

    def test_with_duplicates(self):
        """Duplicate claims should show overlap."""
        claims = generate_duplicate_claims(5)
        # Each duplicate set has 2 claims with same identity
        overlap = calculate_overlap(claims)
        assert overlap > 0.0

    def test_empty_list(self):
        """Empty list should have 0 overlap."""
        assert calculate_overlap([]) == 0.0


class TestSyntheticGenerators:
    """Test synthetic data generators."""

    def test_unique_claims_unique(self):
        """Generated unique claims should have different identities."""
        claims = generate_unique_claims(10)
        hashes = [hash_claim_identity(c) for c in claims]
        # All should be unique
        assert len(set(hashes)) == 10

    def test_duplicate_claims_overlap(self):
        """Generated duplicate claims should have overlapping identities."""
        claims = generate_duplicate_claims(5)
        hashes = [hash_claim_identity(c) for c in claims]
        # 5 sets of 2 = 10 claims, 5 unique identities
        assert len(set(hashes)) < len(claims)


class TestStopruleDuplicate:
    """Test duplicate claim stoprule."""

    def test_emits_anomaly_and_raises(self, valid_claim):
        """Should emit anomaly and raise StopRule."""
        duplicates = [{"claim_id": "dup1", "registry": "verra"}]
        with pytest.raises(StopRule) as exc_info:
            stoprule_duplicate_claim(valid_claim["claim_id"], duplicates)
        assert "Duplicate" in str(exc_info.value)
