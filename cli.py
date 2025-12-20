#!/usr/bin/env python3
"""
GreenProof CLI - Command-line interface for climate claim verification.

Usage:
    python cli.py --greenproof_mode --test
    python cli.py --greenproof_mode --simulate_emissions
    python cli.py --carbon_additionality_test
    python cli.py --double_count_check <credit_id>
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.carbon_credit_proof import (
    compute_additionality,
    generate_synthetic_baseline,
    generate_synthetic_credit_claim,
    ingest_credit_claim,
    verify_registry_entry,
)
from src.core import (
    GREENPROOF_TENANT,
    StopRule,
    dual_hash,
    emit_receipt,
    load_greenproof_spec,
)
from src.double_count_prevent import (
    check_double_count,
    get_registry_state,
    register_credit,
    reset_registry,
)
from src.emissions_verify import (
    cross_verify_emissions,
    detect_discrepancy,
    generate_synthetic_emissions_report,
    generate_synthetic_external_sources,
    ingest_emissions_report,
)
from src.reasoning import (
    climate_validate,
    generate_synthetic_fabricated_claim,
    generate_synthetic_valid_claim,
)


def run_greenproof_test() -> dict:
    """Run basic GreenProof test to verify setup."""
    print("Running GreenProof v1.0 test...")

    # Load and hash spec
    spec = load_greenproof_spec()
    config_hash = spec["_config_hash"]
    print(f"Config loaded, hash: {config_hash[:50]}...")

    # Emit test receipt
    test_receipt = {
        "receipt_type": "ingest",
        "tenant_id": GREENPROOF_TENANT,
        "payload_hash": dual_hash("test_payload"),
        "source": "cli_test",
        "record_count": 1,
    }
    receipt = emit_receipt(test_receipt)
    print(f"Test receipt emitted: {json.dumps(receipt, indent=2)}")

    return {"status": "ok", "receipt": receipt}


def run_simulate_emissions() -> dict:
    """Simulate corporate emissions verification flow."""
    print("Simulating emissions verification...")

    # Generate synthetic data
    report = generate_synthetic_emissions_report("DEMO-CORP-001")
    print(f"Generated emissions report for {report['company_id']}")

    # Ingest report
    ingested = ingest_emissions_report(report, GREENPROOF_TENANT)
    print(f"Ingested report, hash: {ingested['report_hash'][:50]}...")

    # Cross-verify with external sources
    total_claimed = (
        report["scope1_emissions"] + report["scope2_emissions"] + report.get("scope3_emissions", 0)
    )
    external_sources = generate_synthetic_external_sources(total_claimed, discrepancy=0.05)

    verified = cross_verify_emissions(
        ingested["report_hash"], external_sources, total_claimed, GREENPROOF_TENANT
    )

    print(f"Verification result: {json.dumps(verified, indent=2)}")

    # Check for discrepancy
    try:
        discrepancy = detect_discrepancy(report, verified, tenant_id=GREENPROOF_TENANT)
        print(f"Discrepancy check: {json.dumps(discrepancy, indent=2)}")
    except StopRule as e:
        print(f"StopRule triggered: {e}")
        return {"status": "stopped", "reason": str(e)}

    return {"status": "verified", "verification": verified}


def run_carbon_additionality_test() -> dict:
    """Test carbon credit additionality verification."""
    print("Testing carbon credit additionality...")

    # Generate synthetic credit claim
    claim = generate_synthetic_credit_claim("VCS-DEMO-001", "verra")
    print(f"Generated credit claim: {claim['credit_id']}")

    # Ingest claim
    ingested = ingest_credit_claim(claim, "verra", GREENPROOF_TENANT)
    print(f"Ingested claim, hash: {ingested['claim_hash'][:50]}...")

    # Generate baseline (high additionality = 96%)
    baseline = generate_synthetic_baseline(claim["claimed_tonnes"], additionality=0.96)
    print(f"Baseline tonnes: {baseline['baseline_tonnes']}")

    # Compute additionality
    try:
        result = compute_additionality(ingested, baseline, GREENPROOF_TENANT)
        print(f"Additionality result: {json.dumps(result, indent=2)}")
    except StopRule as e:
        print(f"StopRule triggered: {e}")
        return {"status": "stopped", "reason": str(e)}

    # Verify registry entry
    registry_result = verify_registry_entry(claim["credit_id"], "verra", GREENPROOF_TENANT)
    print(f"Registry verification: {json.dumps(registry_result, indent=2)}")

    return {"status": "verified", "additionality": result}


def run_double_count_check(credit_id: str) -> dict:
    """Check a credit for double-counting."""
    print(f"Checking credit {credit_id} for double-counting...")

    try:
        result = check_double_count(credit_id, tenant_id=GREENPROOF_TENANT)
        print(f"Double-count check result: {json.dumps(result, indent=2)}")
        return {"status": "checked", "result": result}
    except StopRule as e:
        print(f"StopRule triggered - double-counting detected: {e}")
        return {"status": "double_count_detected", "reason": str(e)}


def run_compression_fraud_test() -> dict:
    """Test AXIOM-style compression fraud detection."""
    print("Testing compression fraud detection...")

    # Test valid claim
    valid_claim = generate_synthetic_valid_claim()
    valid_result = climate_validate(valid_claim, [], GREENPROOF_TENANT)
    print(f"Valid claim result: {json.dumps(valid_result, indent=2)}")

    # Test fabricated claim
    fake_claim = generate_synthetic_fabricated_claim()
    fake_result = climate_validate(fake_claim, [], GREENPROOF_TENANT)
    print(f"Fabricated claim result: {json.dumps(fake_result, indent=2)}")

    return {
        "status": "tested",
        "valid_claim": valid_result,
        "fabricated_claim": fake_result,
    }


def run_full_pipeline() -> dict:
    """Run the complete GreenProof verification pipeline."""
    print("=" * 60)
    print("GREENPROOF v1.0 FULL PIPELINE")
    print("=" * 60)

    results = {}

    # Reset registry for clean run
    reset_registry()

    # Step 1: Emissions verification
    print("\n--- STEP 1: Emissions Verification ---")
    results["emissions"] = run_simulate_emissions()

    # Step 2: Carbon credit additionality
    print("\n--- STEP 2: Carbon Credit Additionality ---")
    results["additionality"] = run_carbon_additionality_test()

    # Step 3: Double-count prevention
    print("\n--- STEP 3: Double-Count Prevention ---")
    # Register a credit
    register_result = register_credit("PIPELINE-001", "verra", "owner_hash_1", GREENPROOF_TENANT)
    print(f"Registered credit: {json.dumps(register_result, indent=2)}")
    results["double_count"] = {"status": "registered", "result": register_result}

    # Step 4: Compression fraud detection
    print("\n--- STEP 4: Compression Fraud Detection ---")
    results["fraud_detection"] = run_compression_fraud_test()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="GreenProof v1.0 - Receipts-native climate claim verification"
    )

    parser.add_argument(
        "--greenproof_mode",
        action="store_true",
        help="Enable GreenProof verification pipeline",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run basic test to verify setup",
    )

    parser.add_argument(
        "--simulate_emissions",
        action="store_true",
        help="Generate synthetic emissions report and verify",
    )

    parser.add_argument(
        "--carbon_additionality_test",
        action="store_true",
        help="Run additionality verification on test credit",
    )

    parser.add_argument(
        "--double_count_check",
        type=str,
        metavar="CREDIT_ID",
        help="Check credit for double-counting",
    )

    parser.add_argument(
        "--compression_fraud_test",
        action="store_true",
        help="Test AXIOM compression fraud detection",
    )

    parser.add_argument(
        "--full_pipeline",
        action="store_true",
        help="Run complete verification pipeline",
    )

    args = parser.parse_args()

    # Handle greenproof_mode with sub-commands
    if args.greenproof_mode:
        if args.test:
            result = run_greenproof_test()
        elif args.simulate_emissions:
            result = run_simulate_emissions()
        elif args.full_pipeline:
            result = run_full_pipeline()
        else:
            print("GreenProof mode enabled. Use --test, --simulate_emissions, or --full_pipeline")
            parser.print_help()
            return 0

        return 0 if result.get("status") != "stopped" else 1

    # Handle standalone commands
    if args.carbon_additionality_test:
        result = run_carbon_additionality_test()
        return 0 if result.get("status") != "stopped" else 1

    if args.double_count_check:
        result = run_double_count_check(args.double_count_check)
        return 0 if result.get("status") != "double_count_detected" else 1

    if args.compression_fraud_test:
        result = run_compression_fraud_test()
        return 0

    if args.full_pipeline:
        result = run_full_pipeline()
        return 0

    # No arguments - show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
