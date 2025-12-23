#!/bin/bash
# GreenProof T+2h Gate: SKELETON verification
# Verifies foundational components are in place

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
echo "GreenProof T+2h Gate: SKELETON"
echo "=========================================="
echo ""

# ============================================
# GATE 1: Core Files Exist
# ============================================
echo "--- GATE 1: Core Files ---"

if [ -f "spec.md" ]; then
    pass "spec.md exists"
else
    fail "spec.md missing"
fi

if [ -f "ledger_schema.json" ]; then
    pass "ledger_schema.json exists"
else
    fail "ledger_schema.json missing"
fi

if [ -f "cli.py" ]; then
    pass "cli.py exists"
else
    fail "cli.py missing"
fi

if [ -f "data/greenproof_spec.json" ]; then
    pass "data/greenproof_spec.json exists"
else
    fail "data/greenproof_spec.json missing"
fi

# ============================================
# GATE 2: Core Module Functions
# ============================================
echo ""
echo "--- GATE 2: Core Module Functions ---"

# Check dual_hash
if python3 -c "from src.core import dual_hash; h=dual_hash('test'); assert 'SHA256:' in h and 'BLAKE3:' in h" 2>/dev/null; then
    pass "core.dual_hash works"
else
    fail "core.dual_hash failed"
fi

# Check emit_receipt
if python3 -c "from src.core import emit_receipt; r=emit_receipt({'receipt_type':'test'}); assert 'ts' in r" 2>/dev/null; then
    pass "core.emit_receipt works"
else
    fail "core.emit_receipt failed"
fi

# Check merkle
if python3 -c "from src.core import merkle_root; r=merkle_root(['a','b']); assert r" 2>/dev/null; then
    pass "core.merkle_root works"
else
    fail "core.merkle_root failed"
fi

# Check StopRule
if python3 -c "from src.core import StopRule; s=StopRule('test'); assert s.message=='test'" 2>/dev/null; then
    pass "core.StopRule works"
else
    fail "core.StopRule failed"
fi

# ============================================
# GATE 3: Compress Module
# ============================================
echo ""
echo "--- GATE 3: Compress Module ---"

# Check thresholds
if python3 -c "from src.compress import VERIFIED_THRESHOLD, FRAUD_THRESHOLD; assert VERIFIED_THRESHOLD == 0.85; assert FRAUD_THRESHOLD == 0.70" 2>/dev/null; then
    pass "compress thresholds correct (0.85/0.70)"
else
    fail "compress thresholds incorrect"
fi

# Check compress_claim
if python3 -c "from src.compress import compress_claim; r=compress_claim({'claim_id':'t','quantity_tco2e':100}); assert 'compression_ratio' in r" 2>/dev/null; then
    pass "compress.compress_claim works"
else
    fail "compress.compress_claim failed"
fi

# Check classify_claim (uses physics_consistent parameter)
if python3 -c "from src.compress import classify_claim; assert classify_claim(0.30, True)=='verified'; assert classify_claim(0.30, False)=='fraud_signal'" 2>/dev/null; then
    pass "compress.classify_claim works"
else
    fail "compress.classify_claim failed"
fi

# ============================================
# GATE 4: Registry Module
# ============================================
echo ""
echo "--- GATE 4: Registry Module ---"

if python3 -c "from src.registry import register_claim, hash_claim_identity, reset_registry; reset_registry()" 2>/dev/null; then
    pass "registry module imports"
else
    fail "registry module import failed"
fi

if python3 -c "from src.registry import hash_claim_identity; h=hash_claim_identity({'project_id':'t'}); assert 'SHA256:' in h" 2>/dev/null; then
    pass "registry.hash_claim_identity works"
else
    fail "registry.hash_claim_identity failed"
fi

# ============================================
# GATE 5: Detect Module
# ============================================
echo ""
echo "--- GATE 5: Detect Module ---"

if python3 -c "from src.detect import detect_fraud, check_compression_fraud" 2>/dev/null; then
    pass "detect module imports"
else
    fail "detect module import failed"
fi

if python3 -c "from src.detect import classify_fraud_level; assert classify_fraud_level(0.10)=='clean'; assert classify_fraud_level(0.90)=='confirmed_fraud'" 2>/dev/null; then
    pass "detect.classify_fraud_level works"
else
    fail "detect.classify_fraud_level failed"
fi

# ============================================
# GATE 6: Trading Module
# ============================================
echo ""
echo "--- GATE 6: Trading Module ---"

if python3 -c "from src.trading import create_listing, calculate_price, reset_trading; reset_trading()" 2>/dev/null; then
    pass "trading module imports"
else
    fail "trading module import failed"
fi

# ============================================
# GATE 7: Energy & EV Modules
# ============================================
echo ""
echo "--- GATE 7: Energy & EV Modules ---"

if python3 -c "from src.energy import verify_energy_claim, calculate_avoided_emissions" 2>/dev/null; then
    pass "energy module imports"
else
    fail "energy module import failed"
fi

if python3 -c "from src.ev import verify_ev_credit, compare_to_ice_baseline" 2>/dev/null; then
    pass "ev module imports"
else
    fail "ev module import failed"
fi

# ============================================
# GATE 8: Sim Module
# ============================================
echo ""
echo "--- GATE 8: Sim Module ---"

if python3 -c "from src.sim import SimConfig, run_simulation" 2>/dev/null; then
    pass "sim module imports"
else
    fail "sim module import failed"
fi

if python3 -c "from src.sim import SimConfig; c=SimConfig(n_cycles=1); assert c.n_cycles==1" 2>/dev/null; then
    pass "sim.SimConfig works"
else
    fail "sim.SimConfig failed"
fi

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=========================================="
echo "T+2h Gate Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "Failed: ${RED}${FAIL_COUNT}${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}T+2h GATE PASSED${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}T+2h GATE FAILED${NC}"
    exit 1
fi
