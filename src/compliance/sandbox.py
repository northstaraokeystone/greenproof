"""
GreenProof Simulation Sandbox - Legal isolation for external operations.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

LEGAL SAFEGUARD: All external API calls (EPA, DOE, scraping) are intercepted
unless --live_authorized flag is explicitly present and confirmed.

DEFAULT BEHAVIOR:
- Intercept all external calls
- Return synthetic_waste_data
- Inject "SIMULATION_ONLY" watermark into every receipt

This proves you were running a test, not an attack.
"""

import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

# Thread-local storage for simulation context state
_context_state = threading.local()

# Environment variable for live authorization
LIVE_AUTHORIZED_ENV = "GREENPROOF_LIVE_AUTHORIZED"
LIVE_AUTHORIZED_FLAG = "--live_authorized"

# Simulation watermark
SIMULATION_WATERMARK = "SIMULATION_ONLY"
SIMULATION_VERSION = "v3.1-sandbox"


def is_live_authorized() -> bool:
    """Check if live mode is authorized.

    Live mode requires BOTH:
    1. Environment variable GREENPROOF_LIVE_AUTHORIZED=true
    2. Explicit confirmation via context manager

    Returns:
        bool: True only if live mode is explicitly authorized
    """
    env_authorized = os.environ.get(LIVE_AUTHORIZED_ENV, "").lower() == "true"
    context_authorized = getattr(_context_state, "live_authorized", False)
    return env_authorized and context_authorized


def get_simulation_metadata() -> dict[str, Any]:
    """Generate simulation metadata for watermarking.

    Returns:
        dict: Simulation metadata including watermark and timestamp
    """
    return {
        "simulation_mode": not is_live_authorized(),
        "watermark": SIMULATION_WATERMARK,
        "sandbox_version": SIMULATION_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "This output is from a simulation environment. "
                      "No real external systems were contacted.",
    }


def synthetic_waste_data(
    source: str = "epa",
    count: int = 5,
) -> list[dict[str, Any]]:
    """Generate synthetic waste data for simulation.

    Args:
        source: Data source type ("epa", "doe", "registry")
        count: Number of synthetic records to generate

    Returns:
        list: Synthetic data with SIMULATION_ONLY watermark
    """
    import random
    random.seed(42)  # Reproducible synthetic data

    data = []
    for i in range(count):
        if source == "epa":
            record = {
                "grant_id": f"SIM-EPA-{i+1:04d}",
                "amount": random.randint(1_000_000, 100_000_000),
                "program": "epa",
                "third_party_audit": random.choice([True, False]),
                "site_visit_completed": random.choice([True, False]),
                "outcome_metrics": {"reduction_pct": random.randint(5, 50)},
                "_simulation": True,
                "_watermark": SIMULATION_WATERMARK,
            }
        elif source == "doe":
            record = {
                "loan_id": f"SIM-DOE-{i+1:04d}",
                "amount": random.randint(10_000_000, 500_000_000),
                "program": "doe",
                "third_party_audit": random.choice([True, False]),
                "financial_audit": random.choice([True, False]),
                "_simulation": True,
                "_watermark": SIMULATION_WATERMARK,
            }
        else:
            record = {
                "record_id": f"SIM-REG-{i+1:04d}",
                "source": source,
                "value": random.randint(1000, 100000),
                "_simulation": True,
                "_watermark": SIMULATION_WATERMARK,
            }
        data.append(record)

    return data


def wrap_external_call(
    call_fn: Callable[..., Any],
    synthetic_response: Any = None,
    endpoint_name: str = "unknown",
) -> Callable[..., Any]:
    """Wrap an external API call with simulation interception.

    Args:
        call_fn: The actual external call function
        synthetic_response: Response to return in simulation mode
        endpoint_name: Name of the endpoint for logging

    Returns:
        Callable: Wrapped function that respects simulation context
    """
    def wrapped(*args, **kwargs) -> Any:
        if is_live_authorized():
            # Live mode - execute real call
            return call_fn(*args, **kwargs)
        else:
            # Simulation mode - return synthetic data
            if synthetic_response is not None:
                response = synthetic_response
            else:
                response = {
                    "endpoint": endpoint_name,
                    "status": "simulated",
                    "data": None,
                    "_watermark": SIMULATION_WATERMARK,
                }

            # Inject simulation metadata
            if isinstance(response, dict):
                response["_simulation_metadata"] = get_simulation_metadata()

            return response

    return wrapped


T = TypeVar("T")


class SimulationContext:
    """Context manager for simulation sandbox.

    Usage:
        # Simulation mode (default)
        with SimulationContext():
            result = audit_epa_grant(grant)  # Uses synthetic data

        # Live mode (requires explicit authorization)
        with SimulationContext(live_authorized=True):
            result = audit_epa_grant(grant)  # Uses real API

    All receipts emitted within context include simulation metadata.
    """

    def __init__(
        self,
        live_authorized: bool = False,
        synthetic_source: str = "epa",
        inject_watermark: bool = True,
    ):
        """Initialize simulation context.

        Args:
            live_authorized: If True AND env var set, allow live calls
            synthetic_source: Default source for synthetic data
            inject_watermark: If True, inject watermark into all outputs
        """
        self.live_authorized = live_authorized
        self.synthetic_source = synthetic_source
        self.inject_watermark = inject_watermark
        self._previous_state = None
        self._receipts_emitted = []

    def __enter__(self) -> "SimulationContext":
        """Enter simulation context."""
        # Save previous state
        self._previous_state = getattr(_context_state, "live_authorized", False)

        # Set new state (requires both flag AND env var for live mode)
        _context_state.live_authorized = self.live_authorized

        # Log context entry
        self._log_context_entry()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit simulation context."""
        # Restore previous state
        _context_state.live_authorized = self._previous_state

        # Log context exit
        self._log_context_exit()

        return False  # Don't suppress exceptions

    def _log_context_entry(self) -> None:
        """Log entry into simulation context."""
        from src.core import emit_receipt, dual_hash

        metadata = get_simulation_metadata()

        receipt = {
            "receipt_type": "simulation_context_entry",
            "tenant_id": "greenproof-compliance",
            "payload_hash": dual_hash(json.dumps(metadata, sort_keys=True)),
            "simulation_mode": metadata["simulation_mode"],
            "watermark": metadata["watermark"],
            "sandbox_version": metadata["sandbox_version"],
        }

        emitted = emit_receipt(receipt)
        self._receipts_emitted.append(emitted)

    def _log_context_exit(self) -> None:
        """Log exit from simulation context."""
        from src.core import emit_receipt, dual_hash

        metadata = {
            "context_exit": True,
            "receipts_in_context": len(self._receipts_emitted),
            "simulation_mode": not is_live_authorized(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        receipt = {
            "receipt_type": "simulation_context_exit",
            "tenant_id": "greenproof-compliance",
            "payload_hash": dual_hash(json.dumps(metadata, sort_keys=True)),
            "receipts_emitted_count": len(self._receipts_emitted),
        }

        emit_receipt(receipt)

    def get_synthetic_data(self, count: int = 5) -> list[dict[str, Any]]:
        """Get synthetic data for current context.

        Args:
            count: Number of records to generate

        Returns:
            list: Synthetic data with watermarks
        """
        return synthetic_waste_data(self.synthetic_source, count)

    def inject_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inject simulation metadata into data.

        Args:
            data: Data to inject metadata into

        Returns:
            dict: Data with simulation metadata injected
        """
        if self.inject_watermark and not is_live_authorized():
            data = data.copy()
            data["_simulation"] = True
            data["_watermark"] = SIMULATION_WATERMARK
            data["_simulation_metadata"] = get_simulation_metadata()
        return data


@contextmanager
def simulation_sandbox(
    live_authorized: bool = False,
    synthetic_source: str = "epa",
):
    """Alternative context manager for simulation sandbox.

    Usage:
        with simulation_sandbox():
            # All external calls intercepted
            pass

        with simulation_sandbox(live_authorized=True):
            # Real external calls (if env var also set)
            pass
    """
    ctx = SimulationContext(
        live_authorized=live_authorized,
        synthetic_source=synthetic_source,
    )
    with ctx:
        yield ctx
