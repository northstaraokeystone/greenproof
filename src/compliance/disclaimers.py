"""
GreenProof Legal Disclaimers - Standardized legal text for all outputs.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

LEGAL REQUIREMENT: All reports, outputs, and analyses MUST include
appropriate disclaimers to limit liability exposure.

Disclaimer Types:
- SIMULATION_DISCLAIMER: For simulation/test outputs
- MARKET_ANALYSIS_DISCLAIMER: For trading/market data
- BENCHMARK_DISCLAIMER: For anomaly scoring (replaces "fraud" language)
- NO_FINANCIAL_ADVICE_DISCLAIMER: SEC compliance
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


# === STANDARD DISCLAIMERS ===

SIMULATION_DISCLAIMER = (
    "SIMULATION ONLY: This output was generated in a simulation environment. "
    "No real government systems, APIs, or databases were accessed. "
    "All data shown is synthetic and for demonstration purposes only."
)

MARKET_ANALYSIS_DISCLAIMER = (
    "MARKET DATA ANALYSIS: This analysis is for informational and simulation "
    "purposes only. It does not constitute financial advice, investment "
    "recommendations, or trading signals. Past performance does not guarantee "
    "future results. Consult qualified professionals before making investment decisions."
)

BENCHMARK_DISCLAIMER = (
    "BENCHMARK ANALYSIS: Compression Anomaly Scores (CAS) represent statistical "
    "deviations from expected data patterns. A high anomaly score indicates data "
    "that may warrant further review by qualified professionals. Scores do not "
    "constitute accusations of wrongdoing or conclusions about data authenticity."
)

NO_FINANCIAL_ADVICE_DISCLAIMER = (
    "NOT FINANCIAL ADVICE: Nothing in this output should be construed as "
    "financial, legal, tax, or investment advice. This tool is for analytical "
    "and educational purposes only. Users should consult qualified professionals "
    "for specific financial decisions."
)

GOVERNMENT_AUDIT_DISCLAIMER = (
    "AUDIT SIMULATION: This analysis simulates efficiency audit methodology. "
    "Results represent probabilistic indicators, not definitive findings. "
    "Actual government audits require proper authorization and formal processes. "
    "This tool does not access live government systems without explicit authorization."
)

DEFAMATION_SAFE_HARBOR = (
    "STATISTICAL ANALYSIS: All classifications and scores are derived from "
    "mathematical analysis of publicly available or provided data. No statement "
    "herein should be interpreted as an accusation of fraud, misconduct, or "
    "illegal activity. Anomaly detection indicates statistical deviation only."
)


@dataclass
class LegalDisclaimer:
    """Structured legal disclaimer for reports and outputs."""

    disclaimer_type: str
    text: str
    applicable_to: list[str]
    version: str = "3.1"
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for inclusion in reports."""
        return {
            "disclaimer_type": self.disclaimer_type,
            "text": self.text,
            "applicable_to": self.applicable_to,
            "version": self.version,
            "generated_at": self.generated_at,
        }

    def to_header(self) -> str:
        """Generate header string for report inclusion."""
        border = "=" * 70
        return f"\n{border}\nLEGAL DISCLAIMER ({self.disclaimer_type})\n{border}\n{self.text}\n{border}\n"


# === PRE-CONFIGURED DISCLAIMERS ===

DISCLAIMER_REGISTRY = {
    "simulation": LegalDisclaimer(
        disclaimer_type="SIMULATION",
        text=SIMULATION_DISCLAIMER,
        applicable_to=["demo", "test", "simulation", "synthetic"],
    ),
    "market": LegalDisclaimer(
        disclaimer_type="MARKET_ANALYSIS",
        text=MARKET_ANALYSIS_DISCLAIMER,
        applicable_to=["trading", "listing", "market", "price"],
    ),
    "benchmark": LegalDisclaimer(
        disclaimer_type="BENCHMARK",
        text=BENCHMARK_DISCLAIMER,
        applicable_to=["benchmark", "anomaly", "compression", "scan"],
    ),
    "financial": LegalDisclaimer(
        disclaimer_type="NO_FINANCIAL_ADVICE",
        text=NO_FINANCIAL_ADVICE_DISCLAIMER,
        applicable_to=["investment", "financial", "advice", "recommendation"],
    ),
    "audit": LegalDisclaimer(
        disclaimer_type="GOVERNMENT_AUDIT",
        text=GOVERNMENT_AUDIT_DISCLAIMER,
        applicable_to=["doge", "epa", "doe", "grant", "loan", "waste"],
    ),
    "defamation": LegalDisclaimer(
        disclaimer_type="DEFAMATION_SAFE_HARBOR",
        text=DEFAMATION_SAFE_HARBOR,
        applicable_to=["exposure", "company", "fraud", "investigation"],
    ),
}


def get_disclaimer_header(
    *disclaimer_types: str,
    custom_text: str | None = None,
) -> str:
    """Generate combined disclaimer header for reports.

    Args:
        *disclaimer_types: Types of disclaimers to include
        custom_text: Optional custom disclaimer text

    Returns:
        str: Formatted disclaimer header
    """
    headers = []

    for dtype in disclaimer_types:
        if dtype in DISCLAIMER_REGISTRY:
            headers.append(DISCLAIMER_REGISTRY[dtype].to_header())

    if custom_text:
        custom = LegalDisclaimer(
            disclaimer_type="CUSTOM",
            text=custom_text,
            applicable_to=["custom"],
        )
        headers.append(custom.to_header())

    if not headers:
        # Default to simulation disclaimer
        headers.append(DISCLAIMER_REGISTRY["simulation"].to_header())

    return "\n".join(headers)


def inject_disclaimer(
    report: dict[str, Any],
    *disclaimer_types: str,
) -> dict[str, Any]:
    """Inject disclaimers into a report dictionary.

    Args:
        report: Report to inject disclaimers into
        *disclaimer_types: Types of disclaimers to include

    Returns:
        dict: Report with disclaimers injected
    """
    report = report.copy()

    disclaimers = []
    for dtype in disclaimer_types:
        if dtype in DISCLAIMER_REGISTRY:
            disclaimers.append(DISCLAIMER_REGISTRY[dtype].to_dict())

    if not disclaimers:
        # Default to simulation disclaimer
        disclaimers.append(DISCLAIMER_REGISTRY["simulation"].to_dict())

    report["_legal_disclaimers"] = disclaimers
    report["_disclaimer_version"] = "3.1"
    report["_disclaimer_generated_at"] = datetime.now(timezone.utc).isoformat()

    return report


def get_disclaimers_for_context(context: str) -> list[str]:
    """Determine which disclaimers apply to a given context.

    Args:
        context: Context string (e.g., "doge_audit", "trading", "benchmark")

    Returns:
        list: Disclaimer types that apply to this context
    """
    applicable = []
    context_lower = context.lower()

    for dtype, disclaimer in DISCLAIMER_REGISTRY.items():
        for keyword in disclaimer.applicable_to:
            if keyword in context_lower:
                applicable.append(dtype)
                break

    # Always include simulation in simulation mode
    if "simulation" not in applicable:
        applicable.insert(0, "simulation")

    return applicable


def generate_compliance_report() -> dict[str, Any]:
    """Generate a legal compliance report at startup.

    Returns:
        dict: Compliance report with all active disclaimers
    """
    return {
        "report_type": "legal_compliance",
        "version": "3.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "compliance_features": {
            "simulation_sandbox": True,
            "legal_disclaimers": True,
            "jurisdictional_fencing": True,
            "evidentiary_logging": True,
            "probabilistic_scoring": True,
            "defamation_protection": True,
        },
        "active_disclaimers": list(DISCLAIMER_REGISTRY.keys()),
        "disclaimer_registry": {
            k: v.to_dict() for k, v in DISCLAIMER_REGISTRY.items()
        },
    }
