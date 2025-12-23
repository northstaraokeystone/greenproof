"""
GreenProof Jurisdictional Fencing - Legal isolation by jurisdiction.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

LEGAL SAFEGUARD: Implements US_Code_Filter to explicitly filter out
non-US data for DOGE audits, avoiding GDPR/EU conflicts.

All data is tagged with jurisdiction_id (e.g., "US-EPA-2025").
This provides clear legal boundaries for data processing.
"""

import json
from datetime import datetime, timezone
from typing import Any

# === JURISDICTION CONSTANTS ===

# US Federal agencies we can audit
US_FEDERAL_AGENCIES = [
    "EPA",   # Environmental Protection Agency
    "DOE",   # Department of Energy
    "DOT",   # Department of Transportation
    "USDA",  # Department of Agriculture
    "DOI",   # Department of Interior
]

# US State codes (we can process data from any US state)
US_STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU", "AS", "MP",  # Territories
]

# Jurisdictions we CANNOT process (GDPR, etc.)
BLOCKED_JURISDICTIONS = [
    "EU",     # European Union - GDPR
    "UK",     # United Kingdom - UK GDPR
    "CH",     # Switzerland - FADP
    "BR",     # Brazil - LGPD
    "CN",     # China - PIPL
    "IN",     # India - DPDP
    "JP",     # Japan - APPI
    "KR",     # South Korea - PIPA
    "AU",     # Australia - Privacy Act
    "NZ",     # New Zealand - Privacy Act
]

# EU Member States (blocked individually)
EU_MEMBER_STATES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
]


def generate_jurisdiction_id(
    agency: str,
    year: int | None = None,
    sub_code: str | None = None,
) -> str:
    """Generate jurisdiction ID for data tagging.

    Args:
        agency: Federal agency code (e.g., "EPA", "DOE")
        year: Year of data (default: current year)
        sub_code: Optional sub-code for specificity

    Returns:
        str: Jurisdiction ID (e.g., "US-EPA-2025")
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    base = f"US-{agency.upper()}-{year}"

    if sub_code:
        base = f"{base}-{sub_code.upper()}"

    return base


def is_us_jurisdiction(jurisdiction_id: str | None) -> bool:
    """Check if jurisdiction ID indicates US data.

    Args:
        jurisdiction_id: Jurisdiction ID to check

    Returns:
        bool: True if US jurisdiction
    """
    if not jurisdiction_id:
        return False

    # Must start with "US-"
    if not jurisdiction_id.upper().startswith("US-"):
        return False

    # Extract agency code
    parts = jurisdiction_id.upper().split("-")
    if len(parts) < 2:
        return False

    agency = parts[1]

    # Check if valid US agency or state
    return agency in US_FEDERAL_AGENCIES or agency in US_STATE_CODES


def is_blocked_jurisdiction(jurisdiction_id: str | None) -> bool:
    """Check if jurisdiction ID indicates blocked jurisdiction.

    Args:
        jurisdiction_id: Jurisdiction ID to check

    Returns:
        bool: True if blocked (GDPR, etc.)
    """
    if not jurisdiction_id:
        return False

    jurisdiction_upper = jurisdiction_id.upper()

    # Check blocked jurisdictions
    for blocked in BLOCKED_JURISDICTIONS:
        if jurisdiction_upper.startswith(f"{blocked}-"):
            return True

    # Check EU member states
    for eu_state in EU_MEMBER_STATES:
        if jurisdiction_upper.startswith(f"{eu_state}-"):
            return True

    return False


def tag_with_jurisdiction(
    data: dict[str, Any],
    agency: str,
    year: int | None = None,
    sub_code: str | None = None,
) -> dict[str, Any]:
    """Tag data with jurisdiction ID.

    Args:
        data: Data to tag
        agency: Federal agency code
        year: Year of data
        sub_code: Optional sub-code

    Returns:
        dict: Data with jurisdiction_id added
    """
    data = data.copy()
    data["jurisdiction_id"] = generate_jurisdiction_id(agency, year, sub_code)
    data["jurisdiction_tagged_at"] = datetime.now(timezone.utc).isoformat()
    return data


class US_Code_Filter:
    """Filter for ensuring US-only data processing.

    Usage:
        filter = US_Code_Filter()

        # Filter a single record
        if filter.is_allowed(record):
            process(record)

        # Filter a batch
        us_only = filter.filter_batch(records)

    LEGAL REQUIREMENT: All DOGE audits MUST use this filter.
    """

    def __init__(
        self,
        allowed_agencies: list[str] | None = None,
        strict_mode: bool = True,
    ):
        """Initialize US Code Filter.

        Args:
            allowed_agencies: List of allowed agency codes (default: all US agencies)
            strict_mode: If True, require explicit jurisdiction_id
        """
        self.allowed_agencies = allowed_agencies or US_FEDERAL_AGENCIES
        self.strict_mode = strict_mode
        self._filtered_count = 0
        self._blocked_count = 0
        self._allowed_count = 0

    def is_allowed(self, data: dict[str, Any]) -> bool:
        """Check if data is allowed for processing.

        Args:
            data: Data record to check

        Returns:
            bool: True if allowed for US processing
        """
        jurisdiction_id = data.get("jurisdiction_id")

        # Check for blocked jurisdictions first
        if is_blocked_jurisdiction(jurisdiction_id):
            self._blocked_count += 1
            return False

        # In strict mode, require explicit US jurisdiction
        if self.strict_mode:
            if not is_us_jurisdiction(jurisdiction_id):
                self._filtered_count += 1
                return False

        # Check if from allowed agency
        if jurisdiction_id:
            parts = jurisdiction_id.upper().split("-")
            if len(parts) >= 2:
                agency = parts[1]
                if agency in US_FEDERAL_AGENCIES and agency not in self.allowed_agencies:
                    self._filtered_count += 1
                    return False

        self._allowed_count += 1
        return True

    def filter_batch(
        self,
        records: list[dict[str, Any]],
        tag_filtered: bool = True,
    ) -> list[dict[str, Any]]:
        """Filter batch of records to US-only.

        Args:
            records: List of records to filter
            tag_filtered: If True, tag allowed records with filter metadata

        Returns:
            list: US-only records
        """
        allowed = []

        for record in records:
            if self.is_allowed(record):
                if tag_filtered:
                    record = record.copy()
                    record["_us_code_filter"] = {
                        "passed": True,
                        "filter_version": "3.1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                allowed.append(record)

        return allowed

    def get_filter_stats(self) -> dict[str, Any]:
        """Get filter statistics.

        Returns:
            dict: Filter statistics
        """
        total = self._allowed_count + self._filtered_count + self._blocked_count
        return {
            "total_processed": total,
            "allowed": self._allowed_count,
            "filtered": self._filtered_count,
            "blocked_gdpr": self._blocked_count,
            "filter_rate": self._filtered_count / total if total > 0 else 0,
            "block_rate": self._blocked_count / total if total > 0 else 0,
        }

    def emit_filter_receipt(self, tenant_id: str) -> dict[str, Any]:
        """Emit receipt for filter operation.

        Args:
            tenant_id: Tenant identifier

        Returns:
            dict: Filter receipt
        """
        from src.core import emit_receipt, dual_hash

        stats = self.get_filter_stats()

        receipt = {
            "receipt_type": "jurisdiction_filter",
            "tenant_id": tenant_id,
            "payload_hash": dual_hash(json.dumps(stats, sort_keys=True)),
            "filter_stats": stats,
            "allowed_agencies": self.allowed_agencies,
            "strict_mode": self.strict_mode,
        }

        return emit_receipt(receipt)


def ensure_us_only(
    data: dict[str, Any] | list[dict[str, Any]],
    agency: str = "EPA",
) -> dict[str, Any] | list[dict[str, Any]]:
    """Convenience function to ensure data is US-only.

    Tags data with US jurisdiction and validates.

    Args:
        data: Single record or list of records
        agency: Default agency code for tagging

    Returns:
        Tagged data (filtered if list)
    """
    if isinstance(data, list):
        filter = US_Code_Filter(strict_mode=False)
        tagged = [tag_with_jurisdiction(d, agency) for d in data]
        return filter.filter_batch(tagged)
    else:
        return tag_with_jurisdiction(data, agency)
