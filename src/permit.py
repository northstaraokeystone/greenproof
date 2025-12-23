"""
GreenProof Permit - Permitting acceleration templates.

Government Waste Elimination Engine v3.0

Create pre-verified 'American Energy' project templates that bypass NEPA delays.
Accelerate LNG terminals, pipelines, nuclear SMRs, refineries.

Receipt: permit_receipt
SLO: Template verification ≤ 500ms, NEPA bypass accuracy ≥ 95%
"""

import json
import time
from datetime import datetime, timezone
from typing import Any

from .core import (
    TENANT_ID,
    dual_hash,
    emit_receipt,
)
from .compress import compress_test


# === PERMIT CONSTANTS ===
NEPA_BYPASS_THRESHOLD = 0.90  # Above this = pre-verified compliance
PROJECT_TYPES = ["lng_terminal", "pipeline", "nuclear_smr", "refinery"]
TEMPLATE_VALIDITY_YEARS = 5

# Standard timelines (days)
STANDARD_TIMELINES = {
    "lng_terminal": 1825,  # 5 years
    "pipeline": 1460,      # 4 years
    "nuclear_smr": 2190,   # 6 years
    "refinery": 1095,      # 3 years
}

# Expedited timelines with template (days)
EXPEDITED_TIMELINES = {
    "lng_terminal": 365,   # 1 year
    "pipeline": 270,       # 9 months
    "nuclear_smr": 545,    # 18 months
    "refinery": 180,       # 6 months
}

# Pre-verified templates
_TEMPLATES: dict[str, dict[str, Any]] = {}


def create_template(
    project_type: str,
    parameters: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Create pre-verified project template.

    Args:
        project_type: Type of project (lng_terminal, pipeline, etc.)
        parameters: Template parameters

    Returns:
        dict: Created template
    """
    if project_type not in PROJECT_TYPES:
        return {
            "error": f"Unsupported project type: {project_type}",
            "supported": PROJECT_TYPES,
        }

    template_id = f"TEMPLATE-{project_type.upper()}-{len(_TEMPLATES) + 1:04d}"

    template = {
        "template_id": template_id,
        "project_type": project_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "valid_until": _calculate_validity(),
        "parameters": parameters,
        "compliance_requirements": _get_compliance_requirements(project_type),
        "pre_verified_sections": _get_preverified_sections(project_type),
        "expedited_timeline_days": EXPEDITED_TIMELINES[project_type],
        "standard_timeline_days": STANDARD_TIMELINES[project_type],
        "time_saved_days": STANDARD_TIMELINES[project_type] - EXPEDITED_TIMELINES[project_type],
    }

    # Store template
    _TEMPLATES[template_id] = template

    # Emit template creation receipt
    receipt = {
        "receipt_type": "template_created",
        "tenant_id": tenant_id,
        "payload_hash": dual_hash(json.dumps(template, sort_keys=True)),
        "template_id": template_id,
        "project_type": project_type,
        "time_saved_days": template["time_saved_days"],
    }
    emit_receipt(receipt)

    return template


def verify_project(
    project: dict[str, Any],
    template_id: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Verify project against pre-verified template.

    Args:
        project: Project data to verify
        template_id: Template to verify against
        tenant_id: Tenant identifier

    Returns:
        dict: permit_receipt with verification result
    """
    start_time = time.time()

    template = _TEMPLATES.get(template_id)
    if not template:
        return {"error": f"Template not found: {template_id}"}

    project_id = project.get("project_id", "UNKNOWN")
    project_type = template["project_type"]

    # Calculate template coverage
    coverage_pct = template_coverage(project, template)

    # Calculate compliance ratio
    compliance_ratio = _calculate_compliance_ratio(project, template)

    # Check NEPA bypass eligibility
    nepa_bypass = check_nepa_bypass(compliance_ratio)

    result = {
        "receipt_type": "permit",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "project_id": project_id,
        "project_type": project_type,
        "template_used": template_id,
        "template_coverage_pct": round(coverage_pct, 4),
        "compliance_ratio": round(compliance_ratio, 4),
        "nepa_bypass_eligible": nepa_bypass,
        "expedited_timeline_days": template["expedited_timeline_days"] if nepa_bypass else None,
        "standard_timeline_days": template["standard_timeline_days"],
        "time_saved_days": template["time_saved_days"] if nepa_bypass else 0,
        "verification_time_ms": round((time.time() - start_time) * 1000, 2),
        "payload_hash": "",
    }

    result["payload_hash"] = dual_hash(json.dumps(result, sort_keys=True))

    # Emit permit receipt (CLAUDEME LAW_1)
    emit_receipt(result)

    return result


def check_nepa_bypass(compliance_ratio: float) -> bool:
    """Check if project qualifies for NEPA bypass.

    Args:
        compliance_ratio: Project compliance ratio

    Returns:
        bool: True if bypass eligible
    """
    return compliance_ratio >= NEPA_BYPASS_THRESHOLD


def generate_compliance_receipt(
    project: dict[str, Any],
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    """Generate compliance receipt for project.

    Args:
        project: Project data
        tenant_id: Tenant identifier

    Returns:
        dict: permit_receipt
    """
    # Find best matching template
    project_type = project.get("project_type", "pipeline")

    matching_templates = [
        t for t in _TEMPLATES.values()
        if t["project_type"] == project_type
    ]

    if not matching_templates:
        # Create default template
        template = create_template(project_type, {}, tenant_id)
        template_id = template["template_id"]
    else:
        template_id = matching_templates[0]["template_id"]

    return verify_project(project, template_id, tenant_id)


def list_templates() -> list[dict[str, Any]]:
    """List all available pre-verified templates.

    Returns:
        list: Available templates
    """
    return [
        {
            "template_id": t["template_id"],
            "project_type": t["project_type"],
            "created_at": t["created_at"],
            "valid_until": t["valid_until"],
            "time_saved_days": t["time_saved_days"],
        }
        for t in _TEMPLATES.values()
    ]


def template_coverage(
    project: dict[str, Any],
    template: dict[str, Any] | str,
) -> float:
    """Calculate how much of project is template-covered.

    Args:
        project: Project data
        template: Template dict or ID

    Returns:
        float: Coverage percentage (0-1)
    """
    if isinstance(template, str):
        template = _TEMPLATES.get(template, {})

    if not template:
        return 0.0

    preverified = template.get("pre_verified_sections", [])
    requirements = template.get("compliance_requirements", [])

    if not requirements:
        return 1.0

    covered = 0
    for req in requirements:
        req_name = req.get("name", req) if isinstance(req, dict) else req
        if req_name in preverified:
            covered += 1
        elif project.get(req_name):
            covered += 0.5  # Partial credit for project-provided

    return covered / len(requirements)


def _calculate_validity() -> str:
    """Calculate template validity end date."""
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(days=365 * TEMPLATE_VALIDITY_YEARS)).isoformat()


def _calculate_compliance_ratio(project: dict[str, Any], template: dict[str, Any]) -> float:
    """Calculate project compliance with template."""
    # Run compression test for data quality
    compression = compress_test(project)

    # Check required fields
    requirements = template.get("compliance_requirements", [])
    met = 0

    for req in requirements:
        req_name = req.get("name", req) if isinstance(req, dict) else req
        if project.get(req_name):
            met += 1

    field_ratio = met / len(requirements) if requirements else 1.0

    # Combine compression quality and field completion
    return (compression["compression_ratio"] * 0.3 + field_ratio * 0.7)


def _get_compliance_requirements(project_type: str) -> list[dict[str, Any]]:
    """Get compliance requirements for project type."""
    base_requirements = [
        {"name": "environmental_assessment", "weight": 1.0},
        {"name": "safety_analysis", "weight": 1.0},
        {"name": "community_impact", "weight": 0.8},
        {"name": "water_usage", "weight": 0.7},
        {"name": "air_quality", "weight": 0.9},
    ]

    type_specific = {
        "lng_terminal": [
            {"name": "marine_assessment", "weight": 1.0},
            {"name": "export_license", "weight": 1.0},
        ],
        "pipeline": [
            {"name": "right_of_way", "weight": 1.0},
            {"name": "crossing_permits", "weight": 0.9},
        ],
        "nuclear_smr": [
            {"name": "nrc_license", "weight": 1.0},
            {"name": "emergency_planning", "weight": 1.0},
        ],
        "refinery": [
            {"name": "epa_permit", "weight": 1.0},
            {"name": "storage_certification", "weight": 0.9},
        ],
    }

    return base_requirements + type_specific.get(project_type, [])


def _get_preverified_sections(project_type: str) -> list[str]:
    """Get pre-verified sections for template."""
    return [
        "environmental_assessment",
        "safety_analysis",
        "air_quality",
    ]


# Initialize default templates
def _init_default_templates():
    """Initialize default templates for all project types."""
    for ptype in PROJECT_TYPES:
        create_template(ptype, {"default": True}, TENANT_ID)


# Initialize on module load
_init_default_templates()
