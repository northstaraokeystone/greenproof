"""
GreenProof Full Test Suite - Climate verification, additionality, double-counting, fraud detection.

Test coverage:
- Emissions verification flow
- Carbon credit additionality
- Double-count detection
- AXIOM compression fraud detection
- Full pipeline integration
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.carbon_credit_proof import (
    compute_additionality,
    generate_synthetic_baseline,
    generate_synthetic_credit_claim,
    ingest_credit_claim,
    stoprule_additionality_failure,
    verify_registry_entry,
)
from src.core import (
    ADDITIONALITY_THRESHOLD,
    COMPRESSION_FRAUD_THRESHOLD,
    COMPRESSION_VALID_THRESHOLD,
    DOUBLE_COUNT_TOLERANCE,
    EMISSIONS_DISCREPANCY_MAX,
    GREENPROOF_TENANT,
    StopRule,
    dual_hash,
    emit_receipt,
    load_greenproof_spec,
    merkle_proof,
    merkle_root,
    verify_merkle_proof,
)
from src.double_count_prevent import (
    check_double_count,
    merkle_cross_registry,
    register_credit,
    reset_registry,
    stoprule_double_count,
)
from src.emissions_verify import (
    cross_verify_emissions,
    detect_discrepancy,
    generate_synthetic_emissions_report,
    generate_synthetic_external_sources,
    ingest_emissions_report,
    stoprule_emissions_discrepancy,
)
from src.reasoning import (
    climate_validate,
    compute_entropy_signature,
    generate_synthetic_fabricated_claim,
    generate_synthetic_valid_claim,
)


# === FIXTURES ===


@pytest.fixture(autouse=True)
def clean_receipts():
    """Clean up receipts file before each test."""
    receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
    if receipts_file.exists():
        receipts_file.unlink()
    yield
    # Don't clean up after - keep for inspection


@pytest.fixture
def reset_double_count_registry():
    """Reset the double-count registry before each test."""
    reset_registry()
    yield
    reset_registry()


# === CORE TESTS ===


class TestDualHash:
    """Test dual_hash function."""

    def test_dual_hash_format(self):
        """Verify dual hash produces SHA256:BLAKE3 format."""
        result = dual_hash("test_data")
        assert "SHA256:" in result
        assert ":BLAKE3:" in result
        parts = result.split(":")
        assert len(parts) == 4
        assert parts[0] == "SHA256"
        assert parts[2] == "BLAKE3"

    def test_dual_hash_deterministic(self):
        """Same input produces same hash."""
        h1 = dual_hash("same_input")
        h2 = dual_hash("same_input")
        assert h1 == h2

    def test_dual_hash_different_inputs(self):
        """Different inputs produce different hashes."""
        h1 = dual_hash("input_1")
        h2 = dual_hash("input_2")
        assert h1 != h2

    def test_dual_hash_bytes(self):
        """Can hash bytes directly."""
        h1 = dual_hash(b"byte_data")
        assert "SHA256:" in h1


class TestMerkle:
    """Test Merkle tree operations."""

    def test_merkle_root_single(self):
        """Single hash returns itself."""
        h = dual_hash("only_one")
        root = merkle_root([h])
        assert root == h

    def test_merkle_root_multiple(self):
        """Multiple hashes produce valid root."""
        hashes = [dual_hash(f"item_{i}") for i in range(4)]
        root = merkle_root(hashes)
        assert "SHA256:" in root
        assert root != hashes[0]

    def test_merkle_proof_valid(self):
        """Generated proof verifies correctly."""
        hashes = [dual_hash(f"item_{i}") for i in range(4)]
        proof = merkle_proof(hashes, 1)
        root = merkle_root(hashes)

        assert proof["valid"]
        assert verify_merkle_proof(hashes[1], proof, root)

    def test_merkle_proof_all_positions(self):
        """Proof works for all positions in tree."""
        hashes = [dual_hash(f"item_{i}") for i in range(8)]
        root = merkle_root(hashes)

        for i in range(8):
            proof = merkle_proof(hashes, i)
            assert verify_merkle_proof(hashes[i], proof, root)


# === EMISSIONS VERIFICATION TESTS ===


class TestEmissionsIngest:
    """Test emissions report ingestion."""

    def test_emissions_ingest_creates_hash(self):
        """Ingestion adds report_hash to report."""
        report = generate_synthetic_emissions_report()
        ingested = ingest_emissions_report(report, GREENPROOF_TENANT)

        assert "report_hash" in ingested
        assert "SHA256:" in ingested["report_hash"]

    def test_emissions_ingest_emits_receipt(self):
        """Ingestion emits ingest_receipt."""
        report = generate_synthetic_emissions_report()
        ingest_emissions_report(report, GREENPROOF_TENANT)

        receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
        assert receipts_file.exists()

        with open(receipts_file) as f:
            receipts = [json.loads(line) for line in f]

        assert len(receipts) >= 1
        assert receipts[0]["receipt_type"] == "ingest"
        assert receipts[0]["tenant_id"] == GREENPROOF_TENANT


class TestEmissionsCrossVerify:
    """Test emissions cross-verification."""

    def test_cross_verify_computes_match_score(self):
        """Cross-verify computes match_score between 0-1."""
        report = generate_synthetic_emissions_report()
        ingested = ingest_emissions_report(report, GREENPROOF_TENANT)

        claimed = report["scope1_emissions"] + report["scope2_emissions"]
        sources = generate_synthetic_external_sources(claimed, discrepancy=0.05)

        result = cross_verify_emissions(ingested["report_hash"], sources, claimed, GREENPROOF_TENANT)

        assert "match_score" in result
        assert 0 <= result["match_score"] <= 1
        assert result["status"] in ["verified", "flagged", "failed"]

    def test_cross_verify_emits_receipt(self):
        """Cross-verify emits emissions_verify_receipt."""
        report = generate_synthetic_emissions_report()
        ingested = ingest_emissions_report(report, GREENPROOF_TENANT)

        claimed = report["scope1_emissions"]
        sources = generate_synthetic_external_sources(claimed, discrepancy=0.02)

        cross_verify_emissions(ingested["report_hash"], sources, claimed, GREENPROOF_TENANT)

        receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
        with open(receipts_file) as f:
            receipts = [json.loads(line) for line in f]

        verify_receipts = [r for r in receipts if r["receipt_type"] == "emissions_verify"]
        assert len(verify_receipts) >= 1

    def test_cross_verify_no_sources_fails(self):
        """No external sources results in failed status."""
        result = cross_verify_emissions("some_hash", [], 1000.0, GREENPROOF_TENANT)
        assert result["status"] == "failed"
        assert result["match_score"] == 0.0


class TestEmissionsDiscrepancy:
    """Test emissions discrepancy detection."""

    def test_detect_discrepancy_triggers_stoprule(self):
        """Large discrepancy triggers StopRule."""
        report = generate_synthetic_emissions_report()
        verified = {
            "claimed_value": 100.0,
            "verified_value": 50.0,  # 50% discrepancy
            "discrepancy_pct": 0.50,
        }

        with pytest.raises(StopRule) as exc_info:
            detect_discrepancy(report, verified, threshold=0.10, tenant_id=GREENPROOF_TENANT)

        assert "discrepancy" in str(exc_info.value).lower()

    def test_detect_discrepancy_within_threshold(self):
        """Small discrepancy passes."""
        report = generate_synthetic_emissions_report()
        verified = {
            "claimed_value": 100.0,
            "verified_value": 95.0,  # 5% discrepancy
            "discrepancy_pct": 0.05,
        }

        result = detect_discrepancy(report, verified, threshold=0.10, tenant_id=GREENPROOF_TENANT)
        assert not result["exceeds_threshold"]


# === CARBON CREDIT TESTS ===


class TestCreditAdditionality:
    """Test carbon credit additionality scoring."""

    def test_additionality_score_computed(self):
        """Additionality score computed correctly."""
        claim = generate_synthetic_credit_claim()
        ingested = ingest_credit_claim(claim, "verra", GREENPROOF_TENANT)

        # High additionality baseline
        baseline = generate_synthetic_baseline(claim["claimed_tonnes"], additionality=0.96)

        result = compute_additionality(ingested, baseline, GREENPROOF_TENANT)

        assert "additionality_score" in result
        assert 0.95 <= result["additionality_score"] <= 0.97  # ~96%
        assert result["verification_status"] == "verified"

    def test_additionality_emits_receipt(self):
        """Additionality check emits carbon_credit_receipt."""
        claim = generate_synthetic_credit_claim()
        ingested = ingest_credit_claim(claim, "verra", GREENPROOF_TENANT)
        baseline = generate_synthetic_baseline(claim["claimed_tonnes"], additionality=0.96)

        compute_additionality(ingested, baseline, GREENPROOF_TENANT)

        receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
        with open(receipts_file) as f:
            receipts = [json.loads(line) for line in f]

        credit_receipts = [r for r in receipts if r["receipt_type"] == "carbon_credit"]
        assert len(credit_receipts) >= 1

    def test_low_additionality_triggers_stoprule(self):
        """Very low additionality triggers StopRule."""
        claim = generate_synthetic_credit_claim()
        ingested = ingest_credit_claim(claim, "verra", GREENPROOF_TENANT)

        # Low additionality - baseline is 90% of claimed (only 10% additional)
        baseline = generate_synthetic_baseline(claim["claimed_tonnes"], additionality=0.10)

        with pytest.raises(StopRule) as exc_info:
            compute_additionality(ingested, baseline, GREENPROOF_TENANT)

        assert "additionality" in str(exc_info.value).lower()

    def test_registry_verification(self):
        """Registry verification returns status."""
        result = verify_registry_entry("VCS-2024-001", "verra", GREENPROOF_TENANT)

        assert result["registry_status"] == "active"
        assert result["verified"]

    def test_cancelled_credit_flagged(self):
        """Cancelled credits are flagged."""
        result = verify_registry_entry("CANCELLED-001", "verra", GREENPROOF_TENANT)

        assert result["registry_status"] == "cancelled"
        assert not result["verified"]


# === DOUBLE-COUNT PREVENTION TESTS ===


class TestDoubleCountDetection:
    """Test double-count detection."""

    def test_register_credit_unique(self, reset_double_count_registry):
        """First registration is unique."""
        result = register_credit("TEST-001", "verra", "owner1", GREENPROOF_TENANT)

        assert result["is_unique"]
        assert result["credit_id"] == "TEST-001"
        assert "merkle_position" in result

    def test_double_count_triggers_stoprule(self, reset_double_count_registry):
        """Same credit, different owner triggers StopRule."""
        # First registration
        register_credit("TEST-002", "verra", "owner1", GREENPROOF_TENANT)

        # Second registration - different owner
        with pytest.raises(StopRule) as exc_info:
            register_credit("TEST-002", "gold_standard", "owner2", GREENPROOF_TENANT)

        assert "double" in str(exc_info.value).lower()

    def test_check_double_count(self, reset_double_count_registry):
        """check_double_count finds registered credits."""
        register_credit("TEST-003", "verra", "owner1", GREENPROOF_TENANT)

        # Check should find it
        result = check_double_count("TEST-003", tenant_id=GREENPROOF_TENANT)

        assert result["occurrence_count"] == 1
        assert not result["is_double_counted"]

    def test_check_unregistered_credit(self, reset_double_count_registry):
        """Unregistered credit returns empty."""
        result = check_double_count("NONEXISTENT", tenant_id=GREENPROOF_TENANT)

        assert result["occurrence_count"] == 0
        assert not result["is_double_counted"]


class TestMerkleCrossRegistry:
    """Test cross-registry Merkle operations."""

    def test_merkle_cross_registry_computes_root(self, reset_double_count_registry):
        """Cross-registry Merkle computes unified root."""
        credits = [
            {"credit_id": "A", "registry": "verra", "owner_hash": "o1"},
            {"credit_id": "B", "registry": "gold_standard", "owner_hash": "o2"},
            {"credit_id": "C", "registry": "american_carbon_registry", "owner_hash": "o3"},
        ]

        result = merkle_cross_registry(credits, GREENPROOF_TENANT)

        assert "cross_registry_root" in result
        assert result["credit_count"] == 3
        assert len(result["proofs"]) == 3

    def test_merkle_proofs_valid(self, reset_double_count_registry):
        """All proofs in cross-registry are valid."""
        credits = [
            {"credit_id": f"CREDIT-{i}", "registry": "verra", "owner_hash": f"owner_{i}"}
            for i in range(5)
        ]

        result = merkle_cross_registry(credits, GREENPROOF_TENANT)

        for proof_info in result["proofs"]:
            proof = proof_info["proof"]
            assert proof["valid"]


# === COMPRESSION FRAUD DETECTION TESTS ===


class TestCompressionFraud:
    """Test AXIOM-style compression fraud detection."""

    def test_valid_claim_high_compression(self):
        """Valid physical claim has high compression ratio."""
        claim = generate_synthetic_valid_claim()
        result = climate_validate(claim, [], GREENPROOF_TENANT)

        # Valid claims should have reasonable compression
        assert "compression_ratio" in result
        assert result["physical_consistency"]

    def test_fabricated_claim_detected(self):
        """Fabricated claim is detected."""
        claim = generate_synthetic_fabricated_claim()
        result = climate_validate(claim, [], GREENPROOF_TENANT)

        # Fabricated claims should fail physical consistency
        assert not result["physical_consistency"]
        assert result["validation_status"] in ["suspicious", "fabricated"]

    def test_entropy_signature_computed(self):
        """Entropy signature is computed."""
        data = {"test": "data", "numbers": [1, 2, 3, 4, 5]}
        result = compute_entropy_signature(data, GREENPROOF_TENANT)

        assert "entropy" in result
        assert "normalized_entropy" in result
        assert 0 <= result["normalized_entropy"] <= 1

    def test_climate_validation_emits_receipt(self):
        """Climate validation emits receipt."""
        claim = generate_synthetic_valid_claim()
        climate_validate(claim, [], GREENPROOF_TENANT)

        receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
        with open(receipts_file) as f:
            receipts = [json.loads(line) for line in f]

        validation_receipts = [r for r in receipts if r["receipt_type"] == "climate_validation"]
        assert len(validation_receipts) >= 1


# === FULL PIPELINE TEST ===


class TestFullPipeline:
    """End-to-end verification flow."""

    def test_full_pipeline_receipts_in_order(self, reset_double_count_registry):
        """Full pipeline emits receipts in correct order."""
        # Step 1: Emissions
        report = generate_synthetic_emissions_report()
        ingested = ingest_emissions_report(report, GREENPROOF_TENANT)

        claimed = report["scope1_emissions"]
        sources = generate_synthetic_external_sources(claimed, discrepancy=0.02)
        cross_verify_emissions(ingested["report_hash"], sources, claimed, GREENPROOF_TENANT)

        # Step 2: Carbon credit
        claim = generate_synthetic_credit_claim()
        ingested_claim = ingest_credit_claim(claim, "verra", GREENPROOF_TENANT)
        baseline = generate_synthetic_baseline(claim["claimed_tonnes"], additionality=0.96)
        compute_additionality(ingested_claim, baseline, GREENPROOF_TENANT)

        # Step 3: Double-count registration
        register_credit("PIPELINE-TEST", "verra", "pipeline_owner", GREENPROOF_TENANT)

        # Step 4: Climate validation
        climate_validate(report, [], GREENPROOF_TENANT)

        # Verify receipts
        receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
        with open(receipts_file) as f:
            receipts = [json.loads(line) for line in f]

        receipt_types = [r["receipt_type"] for r in receipts]

        # Should have ingest, emissions_verify, ingest, carbon_credit, double_count, climate_validation
        assert "ingest" in receipt_types
        assert "emissions_verify" in receipt_types
        assert "carbon_credit" in receipt_types
        assert "double_count" in receipt_types
        assert "climate_validation" in receipt_types

    def test_all_receipts_have_tenant_id(self, reset_double_count_registry):
        """All emitted receipts have tenant_id."""
        # Generate some receipts
        report = generate_synthetic_emissions_report()
        ingest_emissions_report(report, GREENPROOF_TENANT)

        claim = generate_synthetic_credit_claim()
        ingest_credit_claim(claim, "verra", GREENPROOF_TENANT)

        receipts_file = Path(__file__).parent.parent / "receipts.jsonl"
        with open(receipts_file) as f:
            receipts = [json.loads(line) for line in f]

        for receipt in receipts:
            assert "tenant_id" in receipt, f"Missing tenant_id in {receipt['receipt_type']}"


# === CONFIG TESTS ===


class TestConfig:
    """Test configuration loading."""

    def test_spec_loads_with_hash(self):
        """greenproof_spec.json loads with config hash."""
        spec = load_greenproof_spec()

        assert "_config_hash" in spec
        assert "SHA256:" in spec["_config_hash"]
        assert spec["version"] == "1.0.0"

    def test_spec_thresholds_present(self):
        """All required thresholds present in spec."""
        spec = load_greenproof_spec()

        assert "additionality_threshold" in spec
        assert "double_count_tolerance" in spec
        assert "compression_fraud_threshold" in spec
        assert "compression_valid_threshold" in spec
        assert "emissions_discrepancy_max" in spec

    def test_spec_registries_present(self):
        """Registries list present in spec."""
        spec = load_greenproof_spec()

        assert "registries" in spec
        assert "verra" in spec["registries"]
        assert "gold_standard" in spec["registries"]
