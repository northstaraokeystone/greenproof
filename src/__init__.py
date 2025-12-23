"""
GreenProof v3.1 - Government Waste Elimination Engine (General Counsel Edition).

Same unbreakable physics. Now with 100% legal compliance, liability isolation,
and explicit simulation boundaries.

v3.1 LEGAL COMPLIANCE FEATURES:
- SimulationContext: Sandbox wrapper for all external API calls
- LegalDisclaimer: Standardized disclaimers for all outputs
- US_Code_Filter: Jurisdictional fencing (GDPR-safe)
- EvidentiaryLog: Safe harbor logging infrastructure
- ProbabilisticModel: No binary "fraud" labels
- Compression Anomaly Scores: Neutral statistical language

Modules:
- core: Foundation (dual_hash, emit_receipt, merkle, StopRule)
- compliance: Legal compliance infrastructure (NEW v3.1)
- benchmark: Market data benchmark analysis (REFACTORED from expose)
- compress: AXIOM-style compression engine
- registry: US-only registry integration
- detect: Waste and anomaly detection
- trading: Trading layer infrastructure
- energy: LNG, nuclear, pipeline verification
- vehicles: Tesla + legacy automaker analysis
- prove: Receipt chain, merkle proof
- sim: Monte Carlo harness (8 scenarios)
- doge: DOGE efficiency audit integration
- cbam: CBAM reciprocal defense
- permit: Permitting acceleration templates
- spacex: SpaceX/Starlink net benefit
- expose: DEPRECATED - use benchmark module
"""

__version__ = "3.1.0"

# Core exports
from .core import (
    TENANT_ID,
    SYSTEM_NAME,
    GREENPROOF_TENANT,  # Backwards compatibility
    SUPPORTED_REGISTRIES,
    StopRule,
    dual_hash,
    emit_receipt,
    merkle_root,
    merkle_proof,
    verify_merkle_proof,
    emit_anomaly_receipt,
)

# v3 modules
from . import compress
from . import registry
from . import detect
from . import trading
from . import energy
from . import vehicles
from . import prove
from . import sim
from . import doge
from . import cbam
from . import permit
from . import spacex
from . import expose  # DEPRECATED - maintained for backwards compatibility

# v3.1 Legal Compliance modules
from . import compliance
from . import benchmark
from . import legal  # jurisdiction and logging extensions

__all__ = [
    # Version
    "__version__",
    # Constants
    "TENANT_ID",
    "SYSTEM_NAME",
    "GREENPROOF_TENANT",
    "SUPPORTED_REGISTRIES",
    # Core
    "StopRule",
    "dual_hash",
    "emit_receipt",
    "merkle_root",
    "merkle_proof",
    "verify_merkle_proof",
    "emit_anomaly_receipt",
    # v3 Modules
    "compress",
    "registry",
    "detect",
    "trading",
    "energy",
    "vehicles",
    "prove",
    "sim",
    "doge",
    "cbam",
    "permit",
    "spacex",
    "expose",  # DEPRECATED
    # v3.1 Legal Compliance
    "compliance",
    "benchmark",
    "legal",
]
