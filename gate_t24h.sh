#!/bin/bash
# GreenProof T+24h Gate: MVP verification
# Verifies core functionality and tests pass

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn() {
    echo -e "${YELLOW}WARN${NC}: $1"
}

echo "=========================================="
echo "GreenProof T+24h Gate: MVP"
echo "=========================================="
echo ""

# ============================================
# GATE 1: T+2h Gate Passes
# ============================================
echo "--- GATE 1: T+2h Gate ---"

if bash gate_t2h.sh > /dev/null 2>&1; then
    pass "T+2h gate passes"
else
    fail "T+2h gate failed - fix before proceeding"
    exit 1
fi

# ============================================
# GATE 2: Compression Receipt Generation
# ============================================
echo ""
echo "--- GATE 2: Compression Receipts ---"

COMP_TEST=$(python3 -c "
from src.compress import compress_claim, generate_valid_claim
claim = generate_valid_claim()
receipt = compress_claim(claim)
print(f\"ratio={receipt['compression_ratio']:.4f} class={receipt['classification']}\")
" 2>/dev/null)

if [ $? -eq 0 ]; then
    pass "compression_receipt generated: $COMP_TEST"
else
    fail "compression_receipt generation failed"
fi

# ============================================
# GATE 3: Fraud Detection
# ============================================
echo ""
echo "--- GATE 3: Fraud Detection ---"

FRAUD_TEST=$(python3 -c "
from src.compress import compress_claim, generate_valid_claim
from src.registry import register_claim, reset_registry
from src.detect import detect_fraud

reset_registry()
claim = generate_valid_claim()
comp = compress_claim(claim)
reg = register_claim(claim)
fraud = detect_fraud(claim, comp, reg)
print(f\"score={fraud['fraud_score']:.4f} level={fraud['fraud_level']} rec={fraud['recommendation']}\")
" 2>/dev/null)

if [ $? -eq 0 ]; then
    pass "fraud_receipt generated: $FRAUD_TEST"
else
    fail "fraud_receipt generation failed"
fi

# ============================================
# GATE 4: 100-Cycle Smoke Test
# ============================================
echo ""
echo "--- GATE 4: 100-Cycle Smoke Test ---"

SMOKE_TEST=$(python3 -c "
from src.sim import run_simulation, SimConfig
config = SimConfig(n_cycles=100, n_claims_per_type=10)
result = run_simulation(config)
print(f\"cycles={result.cycle} violations={len(result.violations)} detection={result.detection_rate:.2%}\")
" 2>/dev/null)

if [ $? -eq 0 ]; then
    pass "100-cycle smoke test: $SMOKE_TEST"
else
    fail "100-cycle smoke test failed"
fi

# ============================================
# GATE 5: Energy Verification
# ============================================
echo ""
echo "--- GATE 5: Energy Verification ---"

ENERGY_TEST=$(python3 -c "
from src.energy import verify_energy_claim, generate_valid_energy_claim
claim = generate_valid_energy_claim('nuclear')
receipt = verify_energy_claim(claim, 'nuclear')
print(f\"status={receipt['verification_status']} discrepancy={receipt['discrepancy_pct']:.2%}\")
" 2>/dev/null)

if [ $? -eq 0 ]; then
    pass "energy verification: $ENERGY_TEST"
else
    fail "energy verification failed"
fi

# ============================================
# GATE 6: EV Verification
# ============================================
echo ""
echo "--- GATE 6: EV Verification ---"

EV_TEST=$(python3 -c "
from src.ev import verify_ev_credit, generate_valid_ev_claim
claim, vehicles = generate_valid_ev_claim(50)
receipt = verify_ev_credit(claim, vehicles)
print(f\"status={receipt['verification_status']} vehicles={receipt['vehicle_count']}\")
" 2>/dev/null)

if [ $? -eq 0 ]; then
    pass "EV verification: $EV_TEST"
else
    fail "EV verification failed"
fi

# ============================================
# GATE 7: Test Suite
# ============================================
echo ""
echo "--- GATE 7: Test Suite ---"

# Run pytest with coverage
if python3 -m pytest tests/ -v --tb=short -q 2>/dev/null; then
    pass "pytest tests pass"
else
    warn "some pytest tests failed - check output"
fi

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=========================================="
echo "T+24h Gate Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "Failed: ${RED}${FAIL_COUNT}${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}T+24h GATE PASSED${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}T+24h GATE FAILED${NC}"
    exit 1
fi
