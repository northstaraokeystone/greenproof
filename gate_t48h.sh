#!/bin/bash
# GreenProof Gate T+48h - Full verification gate
# All checks must pass before shipping

set -e

echo "=========================================="
echo "GREENPROOF GATE T+48h"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS="${GREEN}PASS${NC}"
FAIL="${RED}FAIL${NC}"

GATE_PASSED=true

# Function to run a gate check
check_gate() {
    local name="$1"
    local command="$2"

    echo -n "Checking $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "$PASS"
        return 0
    else
        echo -e "$FAIL"
        GATE_PASSED=false
        return 1
    fi
}

echo ""
echo "--- GATE 1: Foundation ---"

check_gate "greenproof_spec.json exists" "test -f data/greenproof_spec.json"
check_gate "spec has dual_hash on load" "python -c \"from src.core import load_greenproof_spec; s=load_greenproof_spec(); assert ':' in s['_config_hash']\""
check_gate "core.py has dual_hash" "python -c \"from src.core import dual_hash; h=dual_hash('test'); assert 'SHA256:' in h and 'BLAKE3:' in h\""
check_gate "core.py has emit_receipt" "python -c \"from src.core import emit_receipt\""
check_gate "core.py has merkle functions" "python -c \"from src.core import merkle_root, merkle_proof\""
check_gate "core.py has StopRule" "python -c \"from src.core import StopRule\""

echo ""
echo "--- GATE 2: Emissions Verification ---"

check_gate "emissions_verify.py exists" "python -c \"from src.emissions_verify import ingest_emissions_report\""
check_gate "cross_verify_emissions exists" "python -c \"from src.emissions_verify import cross_verify_emissions\""
check_gate "detect_discrepancy exists" "python -c \"from src.emissions_verify import detect_discrepancy\""
check_gate "stoprule_emissions_discrepancy exists" "python -c \"from src.emissions_verify import stoprule_emissions_discrepancy\""

echo ""
echo "--- GATE 3: Carbon Credit Proof ---"

check_gate "carbon_credit_proof.py exists" "python -c \"from src.carbon_credit_proof import ingest_credit_claim\""
check_gate "compute_additionality exists" "python -c \"from src.carbon_credit_proof import compute_additionality\""
check_gate "verify_registry_entry exists" "python -c \"from src.carbon_credit_proof import verify_registry_entry\""
check_gate "stoprule_additionality_failure exists" "python -c \"from src.carbon_credit_proof import stoprule_additionality_failure\""

echo ""
echo "--- GATE 4: Double-Count Prevention ---"

check_gate "double_count_prevent.py exists" "python -c \"from src.double_count_prevent import register_credit\""
check_gate "check_double_count exists" "python -c \"from src.double_count_prevent import check_double_count\""
check_gate "merkle_cross_registry exists" "python -c \"from src.double_count_prevent import merkle_cross_registry\""
check_gate "stoprule_double_count exists" "python -c \"from src.double_count_prevent import stoprule_double_count\""
check_gate "register_credit works" "python -c \"from src.double_count_prevent import register_credit, reset_registry; reset_registry(); r=register_credit('TEST','verra','o1','t'); assert r['is_unique']\""

echo ""
echo "--- GATE 5: Compression Fraud Detection ---"

check_gate "reasoning.py has climate_validate" "python -c \"from src.reasoning import climate_validate\""
check_gate "compute_entropy_signature exists" "python -c \"from src.reasoning import compute_entropy_signature\""
check_gate "climate_validate returns ratio" "python -c \"from src.reasoning import climate_validate; r=climate_validate({'test':'data'},[],'t'); assert 'compression_ratio' in r\""

echo ""
echo "--- GATE 6: CLI & Tests ---"

check_gate "cli.py exists and imports" "python -c \"import cli\""
check_gate "cli --greenproof_mode --help works" "python cli.py --greenproof_mode --test"
check_gate "test file exists" "test -f tests/test_greenproof_carbon.py"

echo ""
echo "--- GATE 7: Test Execution ---"

echo "Running pytest..."
if pytest tests/test_greenproof_carbon.py -v --tb=short; then
    echo -e "pytest: $PASS"
else
    echo -e "pytest: $FAIL"
    GATE_PASSED=false
fi

echo ""
echo "=========================================="
if [ "$GATE_PASSED" = true ]; then
    echo -e "${GREEN}ALL GATES PASSED${NC}"
    echo "GreenProof v1.0 ready to ship!"
    exit 0
else
    echo -e "${RED}GATE FAILURE${NC}"
    echo "Fix issues before shipping."
    exit 1
fi
