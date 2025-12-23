#!/usr/bin/env python3
"""
GreenProof CLI - Government Waste Elimination Engine v3.0

Command-line interface for waste elimination verification.

Usage:
    python cli.py --test                    Run basic test
    python cli.py --doge_audit              Run DOGE fraud audit demo
    python cli.py --cbam_verify             Run CBAM defense demo
    python cli.py --permit_check            Run permitting acceleration demo
    python cli.py --spacex_verify           Run SpaceX net benefit demo
    python cli.py --expose_legacy           Expose legacy automaker claims
    python cli.py --full_pipeline           Run complete pipeline
    python cli.py --run_scenarios           Run all 8 scenarios
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    TENANT_ID,
    SYSTEM_NAME,
    StopRule,
    dual_hash,
    emit_receipt,
)
from src.core import load_greenproof_spec
from src.compress import waste_validate, compress_test
from src.detect import detect_waste, batch_detect, generate_waste_report
from src.doge import audit_epa_grant, batch_audit, generate_dashboard
from src.cbam import verify_us_export, generate_trade_brief
from src.permit import verify_project, list_templates
from src.spacex import verify_starlink_claim, generate_regulatory_brief
from src.expose import scan_company, batch_scan_industry, generate_exposure_report
from src.vehicles import verify_tesla_efficiency, compare_tesla_vs_legacy
from src.energy import verify_lng_export, verify_nuclear_smr, verify_pipeline
from src.sim import run_simulation, run_scenario, run_all_scenarios, SimConfig
from src.prove import anchor_chain, get_chain_state
from src.trading import create_listing, execute_trade, get_active_listings


def run_basic_test() -> dict:
    """Run basic test to verify setup."""
    print(f"Running {SYSTEM_NAME} v3.0 test...")
    print("=" * 60)

    # Load and hash spec
    spec = load_greenproof_spec()
    config_hash = spec["_config_hash"]
    print(f"Config loaded, hash: {config_hash[:50]}...")

    # Test compression
    test_claim = {"test": "data", "value": 12345}
    compression = compress_test(test_claim)
    print(f"Compression test: ratio={compression['compression_ratio']}")

    # Test waste detection
    waste_result = detect_waste(test_claim)
    print(f"Waste detection: {waste_result['validation_status']}")

    # Emit test receipt
    test_receipt = {
        "receipt_type": "test",
        "tenant_id": TENANT_ID,
        "payload_hash": dual_hash("test_payload"),
        "source": "cli_test",
    }
    receipt = emit_receipt(test_receipt)
    print(f"Test receipt emitted: ts={receipt['ts']}")

    print("=" * 60)
    print("All systems operational.")

    return {"status": "ok"}


def run_doge_audit_demo() -> dict:
    """Run DOGE fraud audit demo."""
    print("Running DOGE Fraud Audit Demo...")
    print("=" * 60)

    # Generate synthetic EPA grants
    grants = [
        {
            "grant_id": "EPA-2024-001",
            "amount": 50_000_000,
            "program": "epa",
            "third_party_audit": True,
            "outcome_metrics": {"reduction_pct": 25},
        },
        {
            "grant_id": "EPA-2024-002",
            "amount": 75_000_000,
            "program": "epa",
            # Missing verification = waste
        },
        {
            "grant_id": "EPA-2024-003",
            "amount": 100_000_000,
            "program": "epa",
            "third_party_audit": True,
            "site_visit_completed": True,
            "outcome_metrics": {"reduction_pct": 40},
            "financial_audit": True,
            "progress_reports": [{"q": 1}, {"q": 2}],
        },
    ]

    print(f"Auditing {len(grants)} EPA grants...")

    receipts = batch_audit(grants, "epa", TENANT_ID)

    for r in receipts:
        print(f"  {r['grant_id']}: {r['recommendation']} (waste: ${r['waste_amount_usd']:,.0f})")

    # Generate dashboard
    dashboard = generate_dashboard(receipts, TENANT_ID)
    print(f"\nDashboard Summary:")
    print(f"  Total Allocated: ${dashboard['total_allocated_usd']:,.0f}")
    print(f"  Total Waste: ${dashboard['total_waste_identified_usd']:,.0f}")
    print(f"  Waste Rate: {dashboard['waste_rate']:.1%}")

    return {"status": "ok", "dashboard": dashboard}


def run_cbam_verify_demo() -> dict:
    """Run CBAM defense demo."""
    print("Running CBAM Reciprocal Defense Demo...")
    print("=" * 60)

    exports = [
        {
            "export_id": "EXP-LNG-001",
            "sector": "lng",
            "quantity_mmbtu": 1_000_000,
            "eu_claimed_emissions": 60_000,  # EU overclaiming
        },
        {
            "export_id": "EXP-STEEL-001",
            "sector": "steel",
            "quantity": 50_000,
            "value_usd": 75_000_000,
            "eu_claimed_emissions": 100_000,  # EU overclaiming
        },
    ]

    print(f"Verifying {len(exports)} US exports...")

    receipts = []
    for export in exports:
        result = verify_us_export(export, TENANT_ID)
        receipts.append(result)
        print(f"  {result['export_id']}: {result['discrepancy_direction']} ({result['discrepancy_percentage']:.1%})")
        if result['reciprocal_tariff_justified']:
            print(f"    -> Reciprocal tariff JUSTIFIED")

    # Generate trade brief
    brief = generate_trade_brief(receipts, "lng", TENANT_ID)
    print(f"\nTrade Brief (LNG):")
    print(f"  Position: {brief.get('negotiation_position', 'N/A')}")

    return {"status": "ok", "receipts": receipts}


def run_permit_demo() -> dict:
    """Run permitting acceleration demo."""
    print("Running Permitting Acceleration Demo...")
    print("=" * 60)

    # List available templates
    templates = list_templates()
    print(f"Available templates: {len(templates)}")
    for t in templates[:4]:
        print(f"  {t['template_id']}: {t['project_type']} (saves {t['time_saved_days']} days)")

    # Verify a project
    project = {
        "project_id": "LNG-GULF-001",
        "project_type": "lng_terminal",
        "environmental_assessment": True,
        "safety_analysis": True,
        "marine_assessment": True,
        "export_license": "pending",
    }

    template_id = templates[0]["template_id"] if templates else None
    if template_id:
        result = verify_project(project, template_id, TENANT_ID)
        print(f"\nProject Verification:")
        print(f"  Compliance: {result['compliance_ratio']:.1%}")
        print(f"  NEPA Bypass: {'ELIGIBLE' if result['nepa_bypass_eligible'] else 'NOT ELIGIBLE'}")
        if result['nepa_bypass_eligible']:
            print(f"  Time Saved: {result['time_saved_days']} days")

    return {"status": "ok"}


def run_spacex_demo() -> dict:
    """Run SpaceX net benefit demo."""
    print("Running SpaceX/Starlink Net Benefit Demo...")
    print("=" * 60)

    missions = [
        {
            "mission_id": "STARLINK-6-32",
            "vehicle": "falcon9",
            "satellites_deployed": 60,
        },
        {
            "mission_id": "STARLINK-7-15",
            "vehicle": "falcon9",
            "satellites_deployed": 55,
        },
    ]

    print(f"Analyzing {len(missions)} Starlink missions...")

    receipts = []
    for mission in missions:
        result = verify_starlink_claim(mission, TENANT_ID)
        receipts.append(result)
        print(f"  {result['mission_id']}: {result['net_status']}")
        print(f"    Launch: {result['launch_emissions_kg_co2']:,.0f} kg CO2")
        print(f"    Avoided: {result['avoided_infrastructure']['avoided_emissions_kg_co2']:,.0f} kg CO2")
        print(f"    Net Benefit: {result['net_benefit_kg_co2']:,.0f} kg CO2")

    brief = generate_regulatory_brief(receipts, TENANT_ID)
    print(f"\nRegulatory Brief:")
    print(f"  Overall Status: {brief['overall_status']}")
    print(f"  Net Benefit: {brief['net_benefit_kg_co2']:,.0f} kg CO2")

    return {"status": "ok", "brief": brief}


def run_expose_legacy_demo() -> dict:
    """Run legacy automaker exposure demo."""
    print("Running Legacy Automaker Exposure Demo...")
    print("=" * 60)

    # Scan legacy automakers
    results = batch_scan_industry(tenant_id=TENANT_ID)

    print("ESG Claim Analysis:")
    for r in results:
        print(f"  {r['company'].upper()}: fraud_rate={r['fraud_rate']:.1%}, level={r['overall_fraud_level']}")

    # Generate exposure report
    report = generate_exposure_report(results, TENANT_ID)
    print(f"\nIndustry Exposure Report:")
    print(f"  Companies Scanned: {report['companies_scanned']}")
    print(f"  Companies with Fraud: {report['companies_with_fraud']}")
    print(f"  Industry Fraud Rate: {report['industry_fraud_rate']:.1%}")

    # Compare to Tesla
    tesla_data = verify_tesla_efficiency({
        "vehicle_id": "TESLA-M3-001",
        "model": "Model 3",
    }, TENANT_ID)

    comparison = compare_tesla_vs_legacy(tesla_data, tenant_id=TENANT_ID)
    print(f"\nTesla vs Legacy Comparison:")
    print(f"  Winner: {comparison['winner'].upper()}")
    print(f"  Tesla Fraud Level: {comparison['tesla']['fraud_level']}")
    print(f"  Legacy Avg Fraud Level: {comparison['legacy_average']['fraud_level']}")

    return {"status": "ok", "report": report}


def run_all_scenarios_demo() -> dict:
    """Run all 8 mandatory scenarios."""
    print("Running All 8 Mandatory Scenarios...")
    print("=" * 60)

    results = run_all_scenarios(TENANT_ID)

    passed = 0
    failed = 0

    for name, result in results.items():
        status = "PASS" if result.passed else "FAIL"
        if result.passed:
            passed += 1
        else:
            failed += 1
        print(f"  {name}: {status} (detection_rate={result.detection_rate:.1%})")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    return {
        "status": "ok" if failed == 0 else "failed",
        "passed": passed,
        "failed": failed,
    }


def run_full_pipeline() -> dict:
    """Run complete verification pipeline."""
    print("=" * 60)
    print(f"{SYSTEM_NAME} v3.0 FULL PIPELINE")
    print("=" * 60)

    results = {}

    # Step 1: Basic test
    print("\n--- STEP 1: System Check ---")
    results["system"] = run_basic_test()

    # Step 2: DOGE audit
    print("\n--- STEP 2: DOGE Audit ---")
    results["doge"] = run_doge_audit_demo()

    # Step 3: CBAM defense
    print("\n--- STEP 3: CBAM Defense ---")
    results["cbam"] = run_cbam_verify_demo()

    # Step 4: Permitting
    print("\n--- STEP 4: Permitting Acceleration ---")
    results["permit"] = run_permit_demo()

    # Step 5: SpaceX
    print("\n--- STEP 5: SpaceX Net Benefit ---")
    results["spacex"] = run_spacex_demo()

    # Step 6: Legacy exposure
    print("\n--- STEP 6: Legacy Automaker Exposure ---")
    results["expose"] = run_expose_legacy_demo()

    # Step 7: Anchor chain
    print("\n--- STEP 7: Anchor Proof Chain ---")
    anchor = anchor_chain("full_pipeline", TENANT_ID)
    print(f"Anchored at height {anchor['anchor_height']}")
    print(f"Merkle root: {anchor['merkle_root'][:50]}...")
    results["anchor"] = anchor

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description=f"{SYSTEM_NAME} v3.0 - Receipts-native waste elimination verification"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run basic test to verify setup",
    )

    parser.add_argument(
        "--doge_audit",
        action="store_true",
        help="Run DOGE fraud audit demo",
    )

    parser.add_argument(
        "--cbam_verify",
        action="store_true",
        help="Run CBAM reciprocal defense demo",
    )

    parser.add_argument(
        "--permit_check",
        action="store_true",
        help="Run permitting acceleration demo",
    )

    parser.add_argument(
        "--spacex_verify",
        action="store_true",
        help="Run SpaceX net benefit demo",
    )

    parser.add_argument(
        "--expose_legacy",
        action="store_true",
        help="Expose legacy automaker ESG claims",
    )

    parser.add_argument(
        "--run_scenarios",
        action="store_true",
        help="Run all 8 mandatory scenarios",
    )

    parser.add_argument(
        "--full_pipeline",
        action="store_true",
        help="Run complete verification pipeline",
    )

    # Legacy v1 commands (still supported)
    parser.add_argument(
        "--greenproof_mode",
        action="store_true",
        help="Enable GreenProof mode (legacy)",
    )

    parser.add_argument(
        "--simulate_emissions",
        action="store_true",
        help="Simulate emissions verification (legacy)",
    )

    args = parser.parse_args()

    # Handle commands
    if args.test or (args.greenproof_mode and not args.simulate_emissions):
        result = run_basic_test()
        return 0

    if args.doge_audit:
        result = run_doge_audit_demo()
        return 0

    if args.cbam_verify:
        result = run_cbam_verify_demo()
        return 0

    if args.permit_check:
        result = run_permit_demo()
        return 0

    if args.spacex_verify:
        result = run_spacex_demo()
        return 0

    if args.expose_legacy:
        result = run_expose_legacy_demo()
        return 0

    if args.run_scenarios:
        result = run_all_scenarios_demo()
        return 0 if result["status"] == "ok" else 1

    if args.full_pipeline:
        result = run_full_pipeline()
        return 0

    if args.greenproof_mode and args.simulate_emissions:
        # Legacy support
        from src.energy import verify_corporate_emissions
        print("Legacy emissions simulation - use --doge_audit for v3")
        return 0

    # No arguments - show help
    parser.print_help()
    print(f"\n{SYSTEM_NAME} v3.0")
    print("No receipt → not real. Ship at T+48h or kill.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
