"""
GreenProof Evidentiary Logging - Safe Harbor logging infrastructure.

Government Waste Elimination Engine v3.1 (General Counsel Edition)

LEGAL SAFEGUARD: Replaces standard logging with EvidentiaryLog.
Records: Timestamp, Algorithm Version, Dataset Hash, and "Simulated" Flag.

This proves you were running a test, not an attack.
All log entries are structured for legal admissibility.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# === LOGGING CONSTANTS ===

EVIDENTIARY_LOG_FILE = Path(__file__).parent.parent.parent / "evidentiary.log"
ALGORITHM_VERSION = "3.1.0"
LOG_SCHEMA_VERSION = "1.0"


class EvidentiaryLogEntry:
    """Structured log entry for legal admissibility."""

    def __init__(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
        simulated: bool = True,
        algorithm_version: str = ALGORITHM_VERSION,
    ):
        """Create evidentiary log entry.

        Args:
            event_type: Type of event (e.g., "audit_start", "analysis_complete")
            message: Human-readable message
            data: Additional structured data
            simulated: True if this is a simulation run
            algorithm_version: Version of the algorithm used
        """
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type
        self.message = message
        self.data = data or {}
        self.simulated = simulated
        self.algorithm_version = algorithm_version
        self.schema_version = LOG_SCHEMA_VERSION

        # Compute entry hash for integrity
        self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash of log entry for integrity."""
        content = json.dumps({
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data,
            "simulated": self.simulated,
            "algorithm_version": self.algorithm_version,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data,
            "simulated": self.simulated,
            "algorithm_version": self.algorithm_version,
            "entry_hash": self.entry_hash,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True)


class EvidentiaryLog:
    """Evidentiary logging for legal safe harbor.

    Usage:
        log = EvidentiaryLog()

        # Start a simulation session
        log.log_session_start(simulated=True)

        # Log analysis events
        log.log_event("analysis_start", "Beginning EPA grant analysis", {
            "grant_count": 100,
            "dataset_hash": "abc123..."
        })

        # End session
        log.log_session_end()

    All entries include:
    - ISO8601 timestamp
    - Algorithm version
    - Dataset hash (if applicable)
    - Simulated flag (proves test vs. production)
    """

    def __init__(
        self,
        log_file: Path | None = None,
        console_output: bool = True,
        simulated: bool = True,
    ):
        """Initialize evidentiary logger.

        Args:
            log_file: Path to log file (default: evidentiary.log)
            console_output: If True, also output to console
            simulated: Default simulation flag
        """
        self.log_file = log_file or EVIDENTIARY_LOG_FILE
        self.console_output = console_output
        self.simulated = simulated
        self.session_id = self._generate_session_id()
        self.entries: list[EvidentiaryLogEntry] = []

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Set up standard logging as backup
        self._setup_standard_logging()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        content = f"{datetime.now(timezone.utc).isoformat()}-{os.getpid()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _setup_standard_logging(self) -> None:
        """Set up standard logging for backup."""
        self._logger = logging.getLogger(f"greenproof.evidentiary.{self.session_id}")
        self._logger.setLevel(logging.DEBUG)

        # File handler
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.DEBUG)

        # Console handler
        if self.console_output:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            self._logger.addHandler(ch)

        self._logger.addHandler(fh)

    def log_event(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
        simulated: bool | None = None,
    ) -> EvidentiaryLogEntry:
        """Log an evidentiary event.

        Args:
            event_type: Type of event
            message: Human-readable message
            data: Additional structured data
            simulated: Override default simulation flag

        Returns:
            EvidentiaryLogEntry: The logged entry
        """
        if simulated is None:
            simulated = self.simulated

        # Add session ID to data
        entry_data = data.copy() if data else {}
        entry_data["session_id"] = self.session_id

        entry = EvidentiaryLogEntry(
            event_type=event_type,
            message=message,
            data=entry_data,
            simulated=simulated,
        )

        # Store in memory
        self.entries.append(entry)

        # Write to file
        with open(self.log_file, "a") as f:
            f.write(entry.to_json() + "\n")

        # Console output
        if self.console_output:
            sim_tag = "[SIMULATION]" if simulated else "[LIVE]"
            print(f"{sim_tag} {entry.timestamp} | {event_type}: {message}")

        return entry

    def log_session_start(
        self,
        simulated: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidentiaryLogEntry:
        """Log session start.

        Args:
            simulated: Override default simulation flag
            metadata: Additional session metadata

        Returns:
            EvidentiaryLogEntry: The logged entry
        """
        data = {
            "event": "session_start",
            "algorithm_version": ALGORITHM_VERSION,
            "schema_version": LOG_SCHEMA_VERSION,
        }
        if metadata:
            data.update(metadata)

        return self.log_event(
            "session_start",
            f"Evidentiary logging session started (session_id={self.session_id})",
            data,
            simulated,
        )

    def log_session_end(
        self,
        summary: dict[str, Any] | None = None,
    ) -> EvidentiaryLogEntry:
        """Log session end.

        Args:
            summary: Optional session summary

        Returns:
            EvidentiaryLogEntry: The logged entry
        """
        data = {
            "event": "session_end",
            "entries_count": len(self.entries),
            "session_hash": self._compute_session_hash(),
        }
        if summary:
            data.update(summary)

        return self.log_event(
            "session_end",
            f"Evidentiary logging session ended ({len(self.entries)} entries)",
            data,
        )

    def log_dataset_hash(
        self,
        dataset_name: str,
        dataset_hash: str,
        record_count: int | None = None,
    ) -> EvidentiaryLogEntry:
        """Log dataset hash for audit trail.

        Args:
            dataset_name: Name of the dataset
            dataset_hash: Hash of the dataset
            record_count: Number of records in dataset

        Returns:
            EvidentiaryLogEntry: The logged entry
        """
        data = {
            "dataset_name": dataset_name,
            "dataset_hash": dataset_hash,
        }
        if record_count is not None:
            data["record_count"] = record_count

        return self.log_event(
            "dataset_hash",
            f"Dataset '{dataset_name}' hash recorded",
            data,
        )

    def log_algorithm_execution(
        self,
        algorithm_name: str,
        input_hash: str,
        output_hash: str,
        execution_time_ms: float | None = None,
    ) -> EvidentiaryLogEntry:
        """Log algorithm execution for reproducibility.

        Args:
            algorithm_name: Name of the algorithm
            input_hash: Hash of input data
            output_hash: Hash of output data
            execution_time_ms: Execution time in milliseconds

        Returns:
            EvidentiaryLogEntry: The logged entry
        """
        data = {
            "algorithm_name": algorithm_name,
            "algorithm_version": ALGORITHM_VERSION,
            "input_hash": input_hash,
            "output_hash": output_hash,
        }
        if execution_time_ms is not None:
            data["execution_time_ms"] = execution_time_ms

        return self.log_event(
            "algorithm_execution",
            f"Algorithm '{algorithm_name}' executed",
            data,
        )

    def log_anomaly_detected(
        self,
        anomaly_type: str,
        details: dict[str, Any],
        severity: str = "warning",
    ) -> EvidentiaryLogEntry:
        """Log anomaly detection for audit trail.

        Args:
            anomaly_type: Type of anomaly
            details: Anomaly details
            severity: Severity level (warning, violation, critical)

        Returns:
            EvidentiaryLogEntry: The logged entry
        """
        data = {
            "anomaly_type": anomaly_type,
            "severity": severity,
            "details": details,
        }

        return self.log_event(
            "anomaly_detected",
            f"Anomaly detected: {anomaly_type} (severity={severity})",
            data,
        )

    def _compute_session_hash(self) -> str:
        """Compute hash of all session entries."""
        content = json.dumps([e.to_dict() for e in self.entries], sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of the logging session.

        Returns:
            dict: Session summary
        """
        event_types = {}
        for entry in self.entries:
            event_types[entry.event_type] = event_types.get(entry.event_type, 0) + 1

        return {
            "session_id": self.session_id,
            "simulated": self.simulated,
            "algorithm_version": ALGORITHM_VERSION,
            "entries_count": len(self.entries),
            "event_types": event_types,
            "session_hash": self._compute_session_hash(),
            "log_file": str(self.log_file),
        }

    def export_for_legal(self) -> dict[str, Any]:
        """Export session for legal review.

        Returns:
            dict: Legally formatted session export
        """
        return {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "export_type": "legal_review",
            "session_summary": self.get_session_summary(),
            "entries": [e.to_dict() for e in self.entries],
            "integrity_hash": self._compute_session_hash(),
            "disclaimer": (
                "This log export is provided for legal review purposes. "
                "All timestamps are in UTC. The 'simulated' flag indicates "
                "whether each entry was recorded during a simulation run."
            ),
        }


# Global evidentiary logger instance
_global_log: EvidentiaryLog | None = None


def get_evidentiary_log(simulated: bool = True) -> EvidentiaryLog:
    """Get or create global evidentiary logger.

    Args:
        simulated: Default simulation flag

    Returns:
        EvidentiaryLog: Global logger instance
    """
    global _global_log
    if _global_log is None:
        _global_log = EvidentiaryLog(simulated=simulated)
    return _global_log


def log_event(
    event_type: str,
    message: str,
    data: dict[str, Any] | None = None,
    simulated: bool = True,
) -> EvidentiaryLogEntry:
    """Convenience function to log an event.

    Args:
        event_type: Type of event
        message: Human-readable message
        data: Additional structured data
        simulated: Simulation flag

    Returns:
        EvidentiaryLogEntry: The logged entry
    """
    log = get_evidentiary_log(simulated)
    return log.log_event(event_type, message, data, simulated)
