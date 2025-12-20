"""
GreenProof Receipt Registry - All receipt type schemas for climate verification.

Receipt types:
- ingest_receipt: Data ingestion tracking
- emissions_verify_receipt: Corporate emissions verification
- carbon_credit_receipt: Offset additionality verification
- double_count_receipt: Cross-registry deduplication
- climate_validation_receipt: AXIOM compression fraud detection
- anomaly_receipt: Anomaly/violation tracking
- anchor_receipt: Merkle root anchoring
"""

from typing import Any

# === RECEIPT TYPE SCHEMAS ===

RECEIPT_SCHEMAS: dict[str, dict[str, Any]] = {
    "ingest": {
        "receipt_type": "ingest",
        "required_fields": ["ts", "tenant_id", "payload_hash", "source", "record_count"],
        "optional_fields": ["metadata"],
    },
    "emissions_verify": {
        "receipt_type": "emissions_verify",
        "required_fields": [
            "ts",
            "tenant_id",
            "payload_hash",
            "report_hash",
            "external_source_hashes",
            "match_score",
            "verified_value",
            "claimed_value",
            "discrepancy_pct",
            "status",
        ],
        "optional_fields": ["verification_method", "confidence_interval"],
    },
    "carbon_credit": {
        "receipt_type": "carbon_credit",
        "required_fields": [
            "ts",
            "tenant_id",
            "payload_hash",
            "credit_id",
            "registry",
            "project_type",
            "claimed_tonnes",
            "baseline_tonnes",
            "additionality_score",
            "vintage_year",
            "registry_status",
            "verification_status",
        ],
        "optional_fields": ["project_location", "methodology"],
    },
    "double_count": {
        "receipt_type": "double_count",
        "required_fields": [
            "ts",
            "tenant_id",
            "payload_hash",
            "credit_id",
            "registries_checked",
            "occurrences",
            "is_unique",
            "merkle_position",
            "merkle_proof",
            "cross_registry_root",
        ],
        "optional_fields": ["previous_owners"],
    },
    "climate_validation": {
        "receipt_type": "climate_validation",
        "required_fields": [
            "ts",
            "tenant_id",
            "payload_hash",
            "compression_ratio",
            "entropy_signature",
            "physical_consistency",
            "validation_status",
        ],
        "optional_fields": ["physical_model", "expected_entropy_range"],
    },
    "anomaly": {
        "receipt_type": "anomaly",
        "required_fields": [
            "ts",
            "tenant_id",
            "payload_hash",
            "anomaly_type",
            "classification",
            "action",
            "details",
        ],
        "optional_fields": ["related_receipts", "remediation"],
    },
    "anchor": {
        "receipt_type": "anchor",
        "required_fields": [
            "ts",
            "tenant_id",
            "payload_hash",
            "merkle_root",
            "leaf_count",
            "anchor_type",
        ],
        "optional_fields": ["previous_anchor", "chain_height"],
    },
}


def validate_receipt(receipt: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate receipt against its schema.

    Args:
        receipt: Receipt dict to validate

    Returns:
        tuple: (is_valid, list of missing/invalid fields)
    """
    receipt_type = receipt.get("receipt_type")
    if not receipt_type:
        return False, ["receipt_type missing"]

    schema = RECEIPT_SCHEMAS.get(receipt_type)
    if not schema:
        return False, [f"unknown receipt_type: {receipt_type}"]

    missing = []
    for field in schema["required_fields"]:
        if field not in receipt:
            missing.append(field)

    return len(missing) == 0, missing


def get_receipt_schema(receipt_type: str) -> dict[str, Any] | None:
    """Get schema for a receipt type.

    Args:
        receipt_type: Type of receipt

    Returns:
        dict or None: Schema if found
    """
    return RECEIPT_SCHEMAS.get(receipt_type)


# === STATUS ENUMS ===

VERIFICATION_STATUS = ["verified", "flagged", "failed"]
REGISTRY_STATUS = ["active", "retired", "cancelled"]
CLASSIFICATION = ["warning", "violation", "critical"]
VALIDATION_STATUS = ["valid", "suspicious", "fabricated"]
ACTION = ["flag", "halt", "review"]
