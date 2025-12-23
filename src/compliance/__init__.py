"""
GreenProof Compliance - Legal compliance infrastructure.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

Provides:
- SimulationContext: Sandbox wrapper for external API calls
- LegalDisclaimer: Standardized legal disclaimers for all outputs
- SyntheticDataGenerator: Safe synthetic data for simulation mode

All external operations MUST pass through the compliance layer.
Default behavior: SIMULATION_ONLY unless --live_authorized flag is present.
"""

__version__ = "3.1.0"

from .sandbox import (
    SimulationContext,
    is_live_authorized,
    get_simulation_metadata,
    synthetic_waste_data,
    wrap_external_call,
)

from .disclaimers import (
    LegalDisclaimer,
    SIMULATION_DISCLAIMER,
    MARKET_ANALYSIS_DISCLAIMER,
    BENCHMARK_DISCLAIMER,
    NO_FINANCIAL_ADVICE_DISCLAIMER,
    get_disclaimer_header,
    inject_disclaimer,
    generate_compliance_report,
)

__all__ = [
    # Version
    "__version__",
    # Sandbox
    "SimulationContext",
    "is_live_authorized",
    "get_simulation_metadata",
    "synthetic_waste_data",
    "wrap_external_call",
    # Disclaimers
    "LegalDisclaimer",
    "SIMULATION_DISCLAIMER",
    "MARKET_ANALYSIS_DISCLAIMER",
    "BENCHMARK_DISCLAIMER",
    "NO_FINANCIAL_ADVICE_DISCLAIMER",
    "get_disclaimer_header",
    "inject_disclaimer",
    "generate_compliance_report",
]
