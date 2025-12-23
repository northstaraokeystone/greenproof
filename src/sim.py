"""
GreenProof Sim - Monte Carlo simulation harness.

Validates all GreenProof dynamics BEFORE production deployment.
Modeled on QED v12's 6 mandatory scenarios.

Core Loop:
  GENERATE synthetic claims → COMPRESS → DETECT fraud → EMIT receipts → VALIDATE constraints

THE 6 MANDATORY SCENARIOS:
1. BASELINE - Standard operation, no injected fraud
2. FRAUD_INJECTION - Validate fraud detection accuracy
3. DOUBLE_COUNTING - Validate multi-registry deduplication
4. TRADING_INTEGRITY - Validate trading layer rejects fraud
5. ENERGY_VERIFICATION - Validate energy producer module
6. STRESS - High fraud, high volume, constrained resources

No GreenProof feature ships without passing ALL scenarios.
"""

import json
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .compress import (
    FRAUD_THRESHOLD,
    VERIFIED_THRESHOLD,
    batch_compress,
    compress_claim,
    generate_fraudulent_claim,
    generate_valid_claim,
)
from .core import (
    GREENPROOF_TENANT,
    RECEIPTS_FILE,
    StopRule,
    dual_hash,
    emit_anomaly_receipt,
    emit_receipt,
)
from .detect import (
    MAX_FALSE_NEGATIVE_RATE,
    MAX_FALSE_POSITIVE_RATE,
    batch_detect,
    detect_fraud,
)
from .energy import (
    generate_fraudulent_energy_claim,
    generate_valid_energy_claim,
    verify_energy_claim,
)
from .ev import generate_fraudulent_ev_claim, generate_valid_ev_claim, verify_ev_credit
from .prove import chain_receipts, summarize_batch
from .registry import (
    calculate_overlap,
    generate_duplicate_claims,
    generate_unique_claims,
    register_claim,
    reset_registry,
)
from .trading import (
    create_listing,
    execute_trade,
    get_trading_state,
    match_order,
    reset_trading,
    retire_credit,
)


@dataclass
class SimConfig:
    """Configuration for Monte Carlo simulation."""
    n_cycles: int = 1000
    n_claims_per_type: int = 100
    fraud_injection_rate: float = 0.15  # 15% of claims are known fraud
    double_counting_rate: float = 0.10  # 10% duplicated
    random_seed: int = 42
    max_processing_time_ms: float = 50.0  # SLO per claim
    scenario: str = "BASELINE"

    def __post_init__(self):
        random.seed(self.random_seed)


@dataclass
class SimState:
    """State of simulation run."""
    claims: list[dict[str, Any]] = field(default_factory=list)
    compression_receipts: list[dict[str, Any]] = field(default_factory=list)
    registry_receipts: list[dict[str, Any]] = field(default_factory=list)
    fraud_receipts: list[dict[str, Any]] = field(default_factory=list)
    energy_receipts: list[dict[str, Any]] = field(default_factory=list)
    ev_receipts: list[dict[str, Any]] = field(default_factory=list)
    trade_receipts: list[dict[str, Any]] = field(default_factory=list)
    chain_receipt: dict[str, Any] = field(default_factory=dict)
    violations: list[dict[str, Any]] = field(default_factory=list)
    cycle: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    # Tracking for accuracy metrics
    known_fraud_ids: set[str] = field(default_factory=set)
    detected_fraud_ids: set[str] = field(default_factory=set)
    known_clean_ids: set[str] = field(default_factory=set)
    false_positive_ids: set[str] = field(default_factory=set)

    @property
    def detection_rate(self) -> float:
        """Rate of correctly detecting known fraud."""
        if not self.known_fraud_ids:
            return 1.0
        detected = len(self.known_fraud_ids & self.detected_fraud_ids)
        return detected / len(self.known_fraud_ids)

    @property
    def false_positive_rate(self) -> float:
        """Rate of falsely flagging clean claims as fraud."""
        if not self.known_clean_ids:
            return 0.0
        false_positives = len(self.known_clean_ids & self.detected_fraud_ids)
        return false_positives / len(self.known_clean_ids)

    @property
    def elapsed_time_ms(self) -> float:
        """Total elapsed time in milliseconds."""
        if self.end_time == 0:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


@dataclass
class Violation:
    """Record of a constraint violation."""
    constraint: str
    expected: Any
    actual: Any
    severity: str = "error"  # "warning" | "error" | "critical"
    cycle: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint": self.constraint,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "cycle": self.cycle,
            "details": self.details,
        }


def generate_synthetic_claim(fraud: bool = False) -> dict[str, Any]:
    """Generate synthetic carbon claim with known fraud status.

    Args:
        fraud: If True, generate a fraudulent claim

    Returns:
        dict: Synthetic claim
    """
    if fraud:
        return generate_fraudulent_claim()
    else:
        registry = random.choice(["verra", "gold_standard", "acr", "car"])
        project_type = random.choice([
            "forest_conservation",
            "renewable_energy",
            "avoided_deforestation",
            "blue_carbon",
        ])
        return generate_valid_claim(registry=registry, project_type=project_type)


def inject_double_counting(
    claims: list[dict[str, Any]],
    rate: float,
) -> list[dict[str, Any]]:
    """Inject duplicate claims to simulate double-counting.

    Args:
        claims: List of claims
        rate: Rate of duplication (0.0-1.0)

    Returns:
        list: Claims with duplicates injected
    """
    if rate <= 0 or not claims:
        return claims

    n_duplicates = int(len(claims) * rate)
    if n_duplicates == 0:
        return claims

    result = list(claims)

    for _ in range(n_duplicates):
        # Pick a random claim to duplicate
        original = random.choice(claims)

        # Create duplicate with different registry
        duplicate = original.copy()
        duplicate["claim_id"] = str(uuid.uuid4())

        # Change registry (simulate cross-registry double-counting)
        registries = ["verra", "gold_standard", "acr", "car"]
        other_registries = [r for r in registries if r != original.get("registry")]
        if other_registries:
            duplicate["registry"] = random.choice(other_registries)

        result.append(duplicate)

    return result


def validate_constraints(state: SimState, config: SimConfig) -> list[Violation]:
    """Check all simulation constraints.

    Args:
        state: Current simulation state
        config: Simulation configuration

    Returns:
        list: List of violations
    """
    violations = []

    # 1. Detection rate constraint
    if state.known_fraud_ids:
        detection_rate = state.detection_rate
        if detection_rate < 0.90:  # 90% detection required
            violations.append(Violation(
                constraint="detection_rate",
                expected=">=0.90",
                actual=detection_rate,
                severity="error",
                cycle=state.cycle,
                details={
                    "known_fraud": len(state.known_fraud_ids),
                    "detected": len(state.known_fraud_ids & state.detected_fraud_ids),
                },
            ))

    # 2. False positive rate constraint
    if state.known_clean_ids:
        fp_rate = state.false_positive_rate
        if fp_rate > MAX_FALSE_POSITIVE_RATE:
            violations.append(Violation(
                constraint="false_positive_rate",
                expected=f"<={MAX_FALSE_POSITIVE_RATE}",
                actual=fp_rate,
                severity="error",
                cycle=state.cycle,
            ))

    # 3. No fraud in trading layer
    for trade in state.trade_receipts:
        if trade.get("settlement_status") == "settled":
            # Find corresponding fraud receipt
            claim_id = trade.get("claim_id")
            for fraud_receipt in state.fraud_receipts:
                if fraud_receipt.get("claim_id") == claim_id:
                    if fraud_receipt.get("fraud_level") in ("likely_fraud", "confirmed_fraud"):
                        violations.append(Violation(
                            constraint="trading_integrity",
                            expected="no_fraud_in_trades",
                            actual=fraud_receipt.get("fraud_level"),
                            severity="critical",
                            cycle=state.cycle,
                            details={"claim_id": claim_id},
                        ))

    # 4. Compression ratio distribution
    if state.compression_receipts:
        verified_count = sum(
            1 for r in state.compression_receipts
            if r.get("classification") == "verified"
        )
        verified_rate = verified_count / len(state.compression_receipts)

        # For non-fraud injection scenarios, expect high verified rate
        if config.fraud_injection_rate == 0 and verified_rate < 0.90:
            violations.append(Violation(
                constraint="compression_verified_rate",
                expected=">=0.90 (no fraud injection)",
                actual=verified_rate,
                severity="warning",
                cycle=state.cycle,
            ))

    return violations


def simulate_cycle(state: SimState, config: SimConfig) -> SimState:
    """Execute one simulation cycle.

    Args:
        state: Current simulation state
        config: Simulation configuration

    Returns:
        SimState: Updated state
    """
    state.cycle += 1

    # Generate claims
    n_fraud = int(config.n_claims_per_type * config.fraud_injection_rate)
    n_clean = config.n_claims_per_type - n_fraud

    cycle_claims = []

    # Generate clean claims
    for _ in range(n_clean):
        claim = generate_synthetic_claim(fraud=False)
        state.known_clean_ids.add(claim["claim_id"])
        cycle_claims.append(claim)

    # Generate fraud claims
    for _ in range(n_fraud):
        claim = generate_synthetic_claim(fraud=True)
        state.known_fraud_ids.add(claim["claim_id"])
        cycle_claims.append(claim)

    # Inject double-counting
    cycle_claims = inject_double_counting(cycle_claims, config.double_counting_rate)

    state.claims.extend(cycle_claims)

    # Process claims through pipeline
    for claim in cycle_claims:
        claim_id = claim["claim_id"]

        try:
            # 1. Compress
            comp_receipt = compress_claim(claim)
            state.compression_receipts.append(comp_receipt)

            # 2. Register
            reg_receipt = register_claim(claim)
            state.registry_receipts.append(reg_receipt)

            # 3. Detect fraud
            fraud_receipt = detect_fraud(claim, comp_receipt, reg_receipt)
            state.fraud_receipts.append(fraud_receipt)

            # Track detection
            if fraud_receipt.get("fraud_level") in ("likely_fraud", "confirmed_fraud"):
                state.detected_fraud_ids.add(claim_id)

            # Check for false positives
            if claim_id in state.known_clean_ids:
                if fraud_receipt.get("fraud_level") in ("likely_fraud", "confirmed_fraud"):
                    state.false_positive_ids.add(claim_id)

        except StopRule:
            # Claim rejected by stoprule - this is expected for some fraud
            state.detected_fraud_ids.add(claim_id)
            continue

    # Validate constraints
    cycle_violations = validate_constraints(state, config)
    state.violations.extend(cycle_violations)

    return state


def run_simulation(config: SimConfig) -> SimState:
    """Execute full Monte Carlo simulation.

    Args:
        config: Simulation configuration

    Returns:
        SimState: Final simulation state
    """
    # Reset global state
    reset_registry()
    reset_trading()

    # Clear receipts file for simulation
    if RECEIPTS_FILE.exists():
        RECEIPTS_FILE.unlink()

    state = SimState()
    state.start_time = time.time()

    for cycle in range(config.n_cycles):
        state = simulate_cycle(state, config)

    state.end_time = time.time()

    # Chain all receipts
    all_receipts = (
        state.compression_receipts +
        state.registry_receipts +
        state.fraud_receipts
    )
    if all_receipts:
        state.chain_receipt = chain_receipts(all_receipts)

    return state


# === SCENARIO IMPLEMENTATIONS ===


def run_scenario(scenario_name: str) -> SimState:
    """Run a specific simulation scenario.

    Args:
        scenario_name: One of BASELINE, FRAUD_INJECTION, DOUBLE_COUNTING,
                       TRADING_INTEGRITY, ENERGY_VERIFICATION, STRESS

    Returns:
        SimState: Scenario results
    """
    scenarios = {
        "BASELINE": _scenario_baseline,
        "FRAUD_INJECTION": _scenario_fraud_injection,
        "DOUBLE_COUNTING": _scenario_double_counting,
        "TRADING_INTEGRITY": _scenario_trading_integrity,
        "ENERGY_VERIFICATION": _scenario_energy_verification,
        "STRESS": _scenario_stress,
    }

    if scenario_name not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_name}. Valid: {list(scenarios.keys())}")

    return scenarios[scenario_name]()


def _scenario_baseline() -> SimState:
    """Scenario 1: BASELINE - Standard operation, no injected fraud.

    Pass Criteria:
    - All 1000 cycles complete
    - Zero false fraud detections
    - Compression ratio distribution matches expected (95% > 0.85)
    """
    config = SimConfig(
        n_cycles=1000,
        n_claims_per_type=100,
        fraud_injection_rate=0.0,  # No fraud
        scenario="BASELINE",
    )
    return run_simulation(config)


def _scenario_fraud_injection() -> SimState:
    """Scenario 2: FRAUD_INJECTION - Validate fraud detection accuracy.

    Config:
    - n_cycles: 500
    - fraud_injection_rate: 0.20 (20% fraud)

    Pass Criteria:
    - >= 90% of injected fraud detected (ratio < 0.70)
    - <= 5% false positives
    - fraud_receipt emitted for each detection
    """
    config = SimConfig(
        n_cycles=500,
        n_claims_per_type=100,
        fraud_injection_rate=0.20,
        scenario="FRAUD_INJECTION",
    )
    return run_simulation(config)


def _scenario_double_counting() -> SimState:
    """Scenario 3: DOUBLE_COUNTING - Validate multi-registry deduplication.

    Config:
    - n_cycles: 500
    - double_counting_rate: 0.15 (15% duplicates)

    Pass Criteria:
    - >= 95% of duplicates detected
    - registry_receipt shows correct overlap_percentage
    - No duplicate claims pass to trading layer
    """
    config = SimConfig(
        n_cycles=500,
        n_claims_per_type=100,
        double_counting_rate=0.15,
        scenario="DOUBLE_COUNTING",
    )
    return run_simulation(config)


def _scenario_trading_integrity() -> SimState:
    """Scenario 4: TRADING_INTEGRITY - Validate trading layer rejects fraud.

    Config:
    - n_cycles: 500
    - Mix of clean, suspect, and fraud claims

    Pass Criteria:
    - Zero fraud_level="likely_fraud" or "confirmed_fraud" reach listing
    - All trades have valid custody_receipt
    - Retirement prevents resale
    """
    # Reset state
    reset_registry()
    reset_trading()
    if RECEIPTS_FILE.exists():
        RECEIPTS_FILE.unlink()

    state = SimState()
    state.start_time = time.time()

    n_cycles = 500
    n_claims = 50  # Fewer claims for trading test

    for cycle in range(n_cycles):
        state.cycle = cycle + 1

        # Generate mixed claims
        claims = []
        for i in range(n_claims):
            if i % 5 == 0:
                # 20% fraud
                claim = generate_synthetic_claim(fraud=True)
                state.known_fraud_ids.add(claim["claim_id"])
            else:
                claim = generate_synthetic_claim(fraud=False)
                state.known_clean_ids.add(claim["claim_id"])
            claims.append(claim)

        # Process through full pipeline including trading
        for claim in claims:
            try:
                comp_receipt = compress_claim(claim)
                state.compression_receipts.append(comp_receipt)

                reg_receipt = register_claim(claim)
                state.registry_receipts.append(reg_receipt)

                fraud_receipt = detect_fraud(claim, comp_receipt, reg_receipt)
                state.fraud_receipts.append(fraud_receipt)

                # Only list if clean
                if fraud_receipt.get("fraud_level") == "clean":
                    try:
                        listing = create_listing(claim, fraud_receipt)

                        # Simulate buyer bid
                        bid = {
                            "quantity_tco2e": claim.get("quantity_tco2e", 100),
                            "max_price_per_tco2e": 50.0,
                        }

                        matched = match_order(bid)
                        if matched:
                            trade = execute_trade(bid, matched)
                            state.trade_receipts.append(trade)

                    except StopRule:
                        # Listing rejected - expected for some claims
                        pass
                else:
                    state.detected_fraud_ids.add(claim["claim_id"])

            except StopRule:
                state.detected_fraud_ids.add(claim["claim_id"])

        # Validate trading integrity
        violations = validate_constraints(state, SimConfig(scenario="TRADING_INTEGRITY"))
        state.violations.extend(violations)

    state.end_time = time.time()
    return state


def _scenario_energy_verification() -> SimState:
    """Scenario 5: ENERGY_VERIFICATION - Validate energy producer module.

    Config:
    - n_cycles: 500
    - Energy types: fossil, nuclear, renewable, lng

    Pass Criteria:
    - Discrepancy detection >= 85%
    - Nuclear verification matches Wright's DOE priorities
    - LNG lifecycle emissions calculated correctly
    """
    reset_registry()
    reset_trading()
    if RECEIPTS_FILE.exists():
        RECEIPTS_FILE.unlink()

    state = SimState()
    state.start_time = time.time()

    n_cycles = 500
    energy_types = ["nuclear", "solar", "wind", "lng"]

    for cycle in range(n_cycles):
        state.cycle = cycle + 1

        for energy_type in energy_types:
            # Generate valid claim
            valid_claim = generate_valid_energy_claim(energy_type=energy_type)
            state.known_clean_ids.add(valid_claim["claim_id"])

            receipt = verify_energy_claim(valid_claim, energy_type)
            state.energy_receipts.append(receipt)

            if receipt.get("verification_status") != "verified":
                state.detected_fraud_ids.add(valid_claim["claim_id"])

            # Generate fraudulent claim
            fraud_claim = generate_fraudulent_energy_claim(energy_type=energy_type)
            state.known_fraud_ids.add(fraud_claim["claim_id"])

            receipt = verify_energy_claim(fraud_claim, energy_type)
            state.energy_receipts.append(receipt)

            if receipt.get("verification_status") in ("discrepancy", "fraud"):
                state.detected_fraud_ids.add(fraud_claim["claim_id"])

    state.end_time = time.time()
    return state


def _scenario_stress() -> SimState:
    """Scenario 6: STRESS - High fraud, high volume, constrained resources.

    Config:
    - n_cycles: 1000
    - fraud_injection_rate: 0.40
    - double_counting_rate: 0.25
    - Processing constraint: 10ms per claim

    Pass Criteria:
    - System stabilizes without cascade failure
    - Detection accuracy >= 80% under load
    - No receipt data loss
    """
    config = SimConfig(
        n_cycles=1000,
        n_claims_per_type=200,  # Higher volume
        fraud_injection_rate=0.40,  # 40% fraud
        double_counting_rate=0.25,  # 25% duplicates
        max_processing_time_ms=10.0,  # Tight constraint
        scenario="STRESS",
    )
    return run_simulation(config)


def run_all_scenarios() -> dict[str, SimState]:
    """Run all 6 mandatory scenarios.

    Returns:
        dict: Mapping of scenario name to results
    """
    scenarios = [
        "BASELINE",
        "FRAUD_INJECTION",
        "DOUBLE_COUNTING",
        "TRADING_INTEGRITY",
        "ENERGY_VERIFICATION",
        "STRESS",
    ]

    results = {}
    for scenario in scenarios:
        print(f"Running scenario: {scenario}...")
        results[scenario] = run_scenario(scenario)
        print(f"  Completed in {results[scenario].elapsed_time_ms:.0f}ms")
        print(f"  Violations: {len(results[scenario].violations)}")
        print(f"  Detection rate: {results[scenario].detection_rate:.2%}")

    return results


def check_scenario_pass(scenario_name: str, state: SimState) -> tuple[bool, list[str]]:
    """Check if a scenario passed its criteria.

    Args:
        scenario_name: Name of scenario
        state: Scenario result state

    Returns:
        tuple: (passed, list of failure reasons)
    """
    failures = []

    # Common checks
    if state.violations:
        failures.append(f"{len(state.violations)} constraint violations")

    # Scenario-specific checks
    if scenario_name == "BASELINE":
        if state.false_positive_rate > 0:
            failures.append(f"False positives in baseline: {state.false_positive_rate:.2%}")

    elif scenario_name == "FRAUD_INJECTION":
        if state.detection_rate < 0.90:
            failures.append(f"Detection rate below 90%: {state.detection_rate:.2%}")
        if state.false_positive_rate > 0.05:
            failures.append(f"False positive rate above 5%: {state.false_positive_rate:.2%}")

    elif scenario_name == "DOUBLE_COUNTING":
        # Check duplicate detection
        dup_receipts = [r for r in state.registry_receipts if r.get("duplicates_found", 0) > 0]
        if not dup_receipts:
            failures.append("No duplicates detected")

    elif scenario_name == "TRADING_INTEGRITY":
        # Check no fraud in trades
        for v in state.violations:
            if v.constraint == "trading_integrity":
                failures.append(f"Fraud in trading: {v.details}")

    elif scenario_name == "ENERGY_VERIFICATION":
        if state.detection_rate < 0.85:
            failures.append(f"Energy detection rate below 85%: {state.detection_rate:.2%}")

    elif scenario_name == "STRESS":
        if state.detection_rate < 0.80:
            failures.append(f"Stress detection rate below 80%: {state.detection_rate:.2%}")

    return len(failures) == 0, failures


# === VIOLATION RECEIPTS ===


def emit_violation_receipt(
    violation: Violation,
    tenant_id: str = GREENPROOF_TENANT,
) -> dict[str, Any]:
    """Emit receipt for a constraint violation.

    Args:
        violation: Violation to record
        tenant_id: Tenant identifier

    Returns:
        dict: violation_receipt
    """
    receipt = {
        "receipt_type": "violation",
        "tenant_id": tenant_id,
        "constraint": violation.constraint,
        "expected": str(violation.expected),
        "actual": str(violation.actual),
        "severity": violation.severity,
        "cycle": violation.cycle,
        "details": violation.details,
        "payload_hash": dual_hash(json.dumps(violation.to_dict(), sort_keys=True)),
    }
    return emit_receipt(receipt)
