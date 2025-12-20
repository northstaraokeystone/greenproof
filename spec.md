# GreenProof v1.0 Specification

## Overview

GreenProof is a receipts-native climate claim verification infrastructure that brings cryptographic proof to the $40T+ ESG market where 90%+ of claims are currently unverifiable.

## Paradigm Inversion

**OLD**: Trust corporate self-reporting. Spot-check occasionally. Hope registries don't double-sell.

**NEW**: Every climate claim produces a receipt. Receipts cross-verify against physics. Double-counting is mathematically impossible. Greenwashing patterns detected by compression failure.

## Core Principles

1. **No Receipt → Not Real**: Every function that modifies state MUST emit a receipt
2. **Dual-Hash Lineage**: All data uses SHA256:BLAKE3 format for audit trails
3. **Physics-Based Validation**: Real emissions follow thermodynamic constraints
4. **Zero Tolerance**: Double-counting triggers immediate halt

## Modules

### emissions_verify.py
- **Purpose**: Cross-verify corporate emissions against external sources
- **Inputs**: Corporate emissions report (scope 1/2/3)
- **Outputs**: `emissions_verify_receipt` with match_score
- **SLO**: discrepancy_pct ≤ 10%

### carbon_credit_proof.py
- **Purpose**: Verify carbon offset additionality
- **Inputs**: Credit claim, baseline data
- **Outputs**: `carbon_credit_receipt` with additionality_score
- **SLO**: additionality_score ≥ 95%

### double_count_prevent.py
- **Purpose**: Cross-registry deduplication via Merkle tree
- **Inputs**: Credit ID, registry, owner
- **Outputs**: `double_count_receipt` with merkle_proof
- **SLO**: double_count_tolerance = 0.0

### reasoning.py (climate_validate)
- **Purpose**: AXIOM-style compression fraud detection
- **Inputs**: Climate claim, evidence
- **Outputs**: `climate_validation_receipt` with compression_ratio
- **SLO**: compression_ratio ≥ 0.85 for valid claims

## Receipt Types

| Type | Purpose | Key Fields |
|------|---------|------------|
| ingest | Data ingestion tracking | source, record_count |
| emissions_verify | Emissions verification | match_score, discrepancy_pct |
| carbon_credit | Credit additionality | additionality_score, registry_status |
| double_count | Deduplication check | is_unique, merkle_proof |
| climate_validation | Fraud detection | compression_ratio, physical_consistency |
| anomaly | Violation tracking | classification, action |
| anchor | Merkle root anchoring | merkle_root, leaf_count |

## Thresholds

```python
UNVERIFIABLE_TARGET = 0.90        # 90% of market is unverifiable (our target)
ADDITIONALITY_THRESHOLD = 0.95    # Claims must prove 95% additionality
DOUBLE_COUNT_TOLERANCE = 0.0      # Zero tolerance for double-counting
COMPRESSION_FRAUD_THRESHOLD = 0.70  # Below 70% compression = flag
COMPRESSION_VALID_THRESHOLD = 0.85  # Above 85% = valid physical pattern
EMISSIONS_DISCREPANCY_MAX = 0.10  # Max 10% discrepancy
```

## Verification Flow

```
Corporate Report → ingest_receipt
       ↓
External Sources → emissions_verify_receipt
       ↓
Carbon Credits → carbon_credit_receipt
       ↓
Registry Check → double_count_receipt
       ↓
Physics Check → climate_validation_receipt
       ↓
Merkle Anchor → anchor_receipt
```

## Stop Rules

- **emissions_discrepancy**: Triggers when discrepancy > threshold
- **additionality_failure**: Triggers when score < threshold × 0.5
- **double_count**: Triggers on ANY duplicate detection

All stop rules emit `anomaly_receipt` BEFORE raising exception.

## CLI Usage

```bash
# Basic test
python cli.py --greenproof_mode --test

# Simulate emissions verification
python cli.py --greenproof_mode --simulate_emissions

# Test carbon additionality
python cli.py --carbon_additionality_test

# Check for double-counting
python cli.py --double_count_check VCS-2024-001

# Full pipeline
python cli.py --full_pipeline
```

## v2.0 Roadmap (Not Implemented)

- Live Verra/Gold Standard API integration
- Real satellite data ingestion
- Multi-tenant isolation
- ZK proofs for proprietary data
- Blockchain anchoring
