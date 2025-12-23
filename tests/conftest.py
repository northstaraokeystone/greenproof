"""
GreenProof Tests - Shared fixtures for pytest.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import RECEIPTS_FILE
from src.registry import reset_registry
from src.trading import reset_trading


@pytest.fixture(autouse=True)
def clean_receipts():
    """Clean receipts.jsonl before each test."""
    if RECEIPTS_FILE.exists():
        RECEIPTS_FILE.unlink()
    yield
    # Clean up after test
    if RECEIPTS_FILE.exists():
        RECEIPTS_FILE.unlink()


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    reset_registry()
    reset_trading()
    yield


@pytest.fixture
def valid_claim():
    """Generate a valid carbon claim for testing."""
    return {
        "claim_id": "test-valid-001",
        "registry": "verra",
        "project_id": "VCS-2023-12345",
        "vintage_year": 2023,
        "quantity_tco2e": 1000.0,
        "project_type": "forest_conservation",
        "methodology": "VM0007",
        "location": {
            "lat": -3.4653,
            "lon": -62.2159,
            "country": "BR",
        },
        "verification_body": "SCS Global Services",
        "issuance_date": "2023-06-15T00:00:00Z",
        "retirement_date": None,
        "beneficiary": None,
    }


@pytest.fixture
def fraudulent_claim():
    """Generate a fraudulent carbon claim for testing."""
    return {
        "claim_id": "test-fraud-001",
        "registry": "verra",
        "project_id": "FAKE-12345",
        "vintage_year": 2023,
        "quantity_tco2e": 999999.99,  # Unrealistic
        "project_type": "unknown_type_xyz",
        "methodology": "FAKE-METH",
        "location": {
            "lat": 0.0,
            "lon": 0.0,
            "country": "XX",
        },
        "verification_body": "Fake Verifier LLC",
        "issuance_date": "2023-01-01T00:00:00Z",
        "retirement_date": None,
        "beneficiary": None,
        # Extra random fields to increase entropy
        "random_field_1": 0.12345678901234567890,
        "random_field_2": "abc" * 100,
    }


@pytest.fixture
def valid_energy_claim():
    """Generate a valid energy production claim."""
    return {
        "claim_id": "energy-valid-001",
        "energy_type": "nuclear",
        "capacity_mw": 1000.0,
        "production_mwh": 7884000.0,  # 90% capacity factor
        "capacity_factor": 0.90,
        "claimed_avoided_tco2e": 3000000.0,
        "location": {"country": "US"},
        "lifetime_years": 40,
    }


@pytest.fixture
def valid_ev_claim():
    """Generate a valid EV credit claim."""
    return {
        "claim_id": "ev-valid-001",
        "vehicle_count": 100,
        "total_miles": 1200000.0,  # 12k miles per vehicle
        "claimed_credits": 680.0,  # Close to verified value (~691)
        "state": "CA",
    }


@pytest.fixture
def valid_vehicle_data():
    """Generate valid vehicle data for EV verification."""
    vehicles = []
    for i in range(100):
        vehicles.append({
            "id": f"VEH-{i:04d}",
            "miles": 12000.0,
            "state": "CA",
            "charging_source": "grid",
            "charging_data": {
                "source": "grid",
                "kwh": 3600.0,  # 12000 * 0.3 kWh/mile
            },
        })
    return vehicles


@pytest.fixture
def sample_receipts():
    """Generate sample receipts for testing."""
    return [
        {
            "receipt_type": "compression",
            "tenant_id": "greenproof-climate",
            "claim_id": "test-001",
            "compression_ratio": 0.87,
            "classification": "verified",
            "payload_hash": "SHA256:abc123:BLAKE3:def456",
        },
        {
            "receipt_type": "registry",
            "tenant_id": "greenproof-climate",
            "claim_id": "test-001",
            "duplicates_found": 0,
            "overlap_percentage": 0.0,
            "payload_hash": "SHA256:ghi789:BLAKE3:jkl012",
        },
        {
            "receipt_type": "fraud",
            "tenant_id": "greenproof-climate",
            "claim_id": "test-001",
            "fraud_score": 0.05,
            "fraud_level": "clean",
            "recommendation": "approve",
            "payload_hash": "SHA256:mno345:BLAKE3:pqr678",
        },
    ]


def load_receipts():
    """Load receipts from file for assertions."""
    receipts = []
    if RECEIPTS_FILE.exists():
        with open(RECEIPTS_FILE) as f:
            for line in f:
                if line.strip():
                    receipts.append(json.loads(line))
    return receipts
