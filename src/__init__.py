"""
GreenProof v3.0 - Government Waste Elimination Engine.

Same unbreakable physics. Now a sharpened weapon for energy dominance,
waste elimination, and American competitiveness.

Modules:
- core: Foundation (dual_hash, emit_receipt, merkle, StopRule)
- compress: AXIOM-style compression engine
- registry: US-only registry integration (Gold Standard KILLED)
- detect: Waste and fraud detection
- trading: Trading layer infrastructure
- energy: LNG, nuclear, pipeline verification
- vehicles: Tesla + legacy automaker exposure
- prove: Receipt chain, merkle proof
- sim: Monte Carlo harness (8 scenarios)
- doge: DOGE fraud audit integration
- cbam: CBAM reciprocal defense
- permit: Permitting acceleration templates
- spacex: SpaceX/Starlink net benefit
- expose: Competitor exposure scanner
"""

__version__ = "3.0.0"

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

# New v3 modules
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
from . import expose

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
    # Modules
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
    "expose",
]
