"""Truth writer for advanced-vision.

Provides append-only event logging and artifact manifest writing with:
- Atomic writes (write temp, then rename)
- Timestamp ordering guarantees
- Automatic directory creation
- JSON Lines format for events
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TruthWriter:
    """Append-only event log and artifact manifest writer.
    
    The truth layer writes BEFORE any WSS fanout. This ensures that even
    if downstream systems fail, the audit trail is preserved.
    
    Usage:
        writer = TruthWriter("/var/log/advanced-vision")
        
        # Write event (truth-first)
        writer.write_event(event)
        
        # Write artifact manifest
        writer.write_artifact(manifest)
        
        # Then validate and fanout
        if validator.validate(packet, 'ui_packet'):
            wss_publisher.publish(packet)
    
    File Structure:
        truth_dir/
        ├── events/
        │   ├── 2026-03-18.jsonl      # Daily event logs
        │   └── 2026-03-19.jsonl
        └── artifacts/
            └── manifests.jsonl       # All artifact manifests
    
    Atomic Write Strategy:
        1. Write to temp file in same directory
        2. fsync to ensure durability
        3. atomic rename to target
    """
    
    def __init__(
        self,
        truth_dir: str | Path,
        *,
        fsync: bool = True,
        utc_timestamps: bool = True
    ):
        """Initialize the truth writer.
        
        Args:
            truth_dir: Root directory for truth logs
            fsync: Whether to fsync after writes for durability
            utc_timestamps: Use UTC timestamps (recommended)
        """
        self.truth_dir = Path(truth_dir)
        self.fsync = fsync
        self.utc_timestamps = utc_timestamps
        
        # Subdirectories
        self.events_dir = self.truth_dir / "events"
        self.artifacts_dir = self.truth_dir / "artifacts"
        
        # Ensure directories exist
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Manifest file path (single append-only file)
        self.manifest_path = self.artifacts_dir / "manifests.jsonl"
        
        logger.info(f"TruthWriter initialized: {self.truth_dir}")
    
    def _now(self) -> datetime:
        """Get current timestamp."""
        if self.utc_timestamps:
            return datetime.now(timezone.utc)
        return datetime.now()
    
    def _atomic_write(self, filepath: Path, data: str) -> None:
        """Write data atomically using temp file + rename.
        
        Args:
            filepath: Target file path
            data: String data to write
        """
        # Create temp file in same directory for atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=filepath.parent,
            prefix=f".{filepath.name}.tmp."
        )
        
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(data)
                f.write('\n')
                
                if self.fsync:
                    f.flush()
                    os.fsync(fd)
            
            # Atomic rename
            os.rename(temp_path, filepath)
            
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def _atomic_append(self, filepath: Path, data: str) -> None:
        """Append data atomically to a file.
        
        Uses write-to-temp then append pattern for line-by-line atomicity.
        
        Args:
            filepath: Target file path
            data: String data to append (single line)
        """
        # For append operations, we write to a temp file first, then append
        # the content. This ensures each line is a complete JSON object.
        fd, temp_path = tempfile.mkstemp(
            dir=filepath.parent,
            prefix=f".{filepath.name}.tmp."
        )
        
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(data)
                if self.fsync:
                    f.flush()
                    os.fsync(fd)
            
            # Read temp content and append to target
            with open(temp_path, 'r') as f:
                line = f.read()
            
            # Append to actual file
            with open(filepath, 'a') as f:
                f.write(line)
                if not line.endswith('\n'):
                    f.write('\n')
                if self.fsync:
                    f.flush()
                    os.fsync(f.fileno())
            
            # Clean up temp
            os.unlink(temp_path)
            
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def write_event(self, event: dict[str, Any]) -> Path:
        """Write an event to the daily log file.
        
        Events are written to JSON Lines files organized by date.
        Timestamp ordering is guaranteed within a file.
        
        Args:
            event: Event dictionary (must include timestamp field)
            
        Returns:
            Path to the log file written
            
        Note:
            Adds 'ingestion_timestamp' field for when event was logged
        """
        now = self._now()
        
        # Add ingestion timestamp if not present
        if "ingestion_timestamp" not in event:
            event = dict(event)  # Copy to avoid mutating input
            event["ingestion_timestamp"] = now.isoformat()
        
        # Daily file path
        date_str = now.strftime("%Y-%m-%d")
        log_file = self.events_dir / f"{date_str}.jsonl"
        
        # Serialize and append
        line = json.dumps(event, separators=(',', ':'))
        self._atomic_append(log_file, line)
        
        logger.debug(f"Event written: {event.get('event_id', 'unknown')} -> {log_file}")
        return log_file
    
    def write_artifact(self, manifest: dict[str, Any]) -> Path:
        """Write an artifact manifest to the append-only manifest log.
        
        Artifacts are tracked in a single manifests.jsonl file with
        strict timestamp ordering for replay/audit.
        
        Args:
            manifest: Artifact manifest dict (must match artifact_manifest schema)
            
        Returns:
            Path to the manifest file
            
        Note:
            Generates manifest_id and timestamp if not provided
        """
        now = self._now()
        
        # Ensure required fields
        manifest = dict(manifest)  # Copy to avoid mutating input
        
        if "manifest_id" not in manifest:
            manifest["manifest_id"] = str(uuid4())
        
        if "timestamp" not in manifest:
            manifest["timestamp"] = now.isoformat()
        
        # Serialize and append
        line = json.dumps(manifest, separators=(',', ':'))
        self._atomic_append(self.manifest_path, line)
        
        logger.debug(f"Artifact manifest written: {manifest['manifest_id']}")
        return self.manifest_path
    
    def write_artifact_atomic(
        self,
        manifest: dict[str, Any],
        artifact_data: bytes | str,
        artifact_path: str | Path
    ) -> tuple[Path, Path]:
        """Write artifact file and manifest atomically.
        
        This ensures the artifact file exists before its manifest is logged.
        
        Args:
            manifest: Artifact manifest
            artifact_data: Binary or text data for the artifact
            artifact_path: Where to write the artifact (relative to truth_dir)
            
        Returns:
            Tuple of (artifact_path, manifest_path)
        """
        full_artifact_path = self.truth_dir / artifact_path
        full_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write artifact file atomically
        if isinstance(artifact_data, str):
            self._atomic_write(full_artifact_path, artifact_data)
        else:
            fd, temp_path = tempfile.mkstemp(
                dir=full_artifact_path.parent,
                prefix=f".{full_artifact_path.name}.tmp."
            )
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(artifact_data)
                    if self.fsync:
                        f.flush()
                        os.fsync(fd)
                os.rename(temp_path, full_artifact_path)
            except Exception:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        
        # Update manifest with final path and write
        manifest = dict(manifest)
        manifest["path"] = str(artifact_path)
        manifest_path = self.write_artifact(manifest)
        
        return full_artifact_path, manifest_path
    
    def get_events_for_date(self, date: str | datetime) -> list[dict]:
        """Read all events for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD) or datetime object
            
        Returns:
            List of event dictionaries
        """
        if isinstance(date, datetime):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = date
        
        log_file = self.events_dir / f"{date_str}.jsonl"
        
        if not log_file.exists():
            return []
        
        events = []
        with open(log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        
        return events
    
    def get_all_manifests(self) -> list[dict]:
        """Read all artifact manifests.
        
        Returns:
            List of manifest dictionaries in timestamp order
        """
        if not self.manifest_path.exists():
            return []
        
        manifests = []
        with open(self.manifest_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    manifests.append(json.loads(line))
        
        return manifests
    
    def rotate_event_log(self, date: str | datetime | None = None) -> Path | None:
        """Rotate (close) an event log file by renaming it.
        
        Args:
            date: Date to rotate (defaults to today)
            
        Returns:
            Path to rotated file or None if file doesn't exist
        """
        if date is None:
            date = self._now()
        
        if isinstance(date, datetime):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = date
        
        log_file = self.events_dir / f"{date_str}.jsonl"
        
        if not log_file.exists():
            return None
        
        rotated = self.events_dir / f"{date_str}.jsonl.closed"
        
        # Atomic rename
        os.rename(log_file, rotated)
        
        logger.info(f"Rotated event log: {log_file} -> {rotated}")
        return rotated
