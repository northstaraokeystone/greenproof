"""
GreenProof Core Extensions - Jurisdiction and Logging.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

New core modules for legal compliance:
- jurisdiction: US_Code_Filter for GDPR-safe data processing
- logging: EvidentiaryLog for safe harbor protection
"""

from .jurisdiction import (
    US_Code_Filter,
    US_FEDERAL_AGENCIES,
    US_STATE_CODES,
    BLOCKED_JURISDICTIONS,
    generate_jurisdiction_id,
    is_us_jurisdiction,
    is_blocked_jurisdiction,
    tag_with_jurisdiction,
    ensure_us_only,
)

from .logging import (
    EvidentiaryLog,
    EvidentiaryLogEntry,
    get_evidentiary_log,
    log_event,
    ALGORITHM_VERSION,
)

__all__ = [
    # Jurisdiction
    "US_Code_Filter",
    "US_FEDERAL_AGENCIES",
    "US_STATE_CODES",
    "BLOCKED_JURISDICTIONS",
    "generate_jurisdiction_id",
    "is_us_jurisdiction",
    "is_blocked_jurisdiction",
    "tag_with_jurisdiction",
    "ensure_us_only",
    # Logging
    "EvidentiaryLog",
    "EvidentiaryLogEntry",
    "get_evidentiary_log",
    "log_event",
    "ALGORITHM_VERSION",
]
