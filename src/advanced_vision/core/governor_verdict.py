"""Governor Verdict - Structured decision output from the Governor.

This module defines the GovernorVerdict dataclass and Lineage dataclass
for tracking decisions made by the Governor system.

The Governor acts as a constitutional gate between reviewers and execution,
ensuring no execution candidate proceeds without a structured verdict.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4, UUID


class RiskLevel(str, Enum):
    """Risk levels for governor decisions."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    """Decision outcomes from governor evaluation."""
    CONTINUE = "continue"
    WARN = "warn"
    RECHECK = "recheck"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class PolicyClass(str, Enum):
    """Policy classes for categorizing recommendations."""
    OBSERVE = "observe"
    INFORM = "inform"
    INTERNAL_STATE_UPDATE = "internal_state_update"
    EXTERNAL_REVIEW = "external_review"
    TRADING_ANALYSIS = "trading_analysis"
    TRADING_EXECUTION_CANDIDATE = "trading_execution_candidate"
    UI_INTERACTION_CANDIDATE = "ui_interaction_candidate"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    PROMOTION_CANDIDATE = "promotion_candidate"


@dataclass(frozen=True)
class Lineage:
    """Lineage information tracking the source of a verdict.
    
    Attributes:
        source_event: UUID of the original event that triggered evaluation
        reviewer: Name of the reviewer that produced the recommendation
        trace_id: UUID for tracing the decision through the system
    """
    source_event: str
    reviewer: str
    trace_id: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert lineage to dictionary."""
        return {
            "source_event": self.source_event,
            "reviewer": self.reviewer,
            "trace_id": self.trace_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lineage:
        """Create Lineage from dictionary."""
        return cls(
            source_event=data["source_event"],
            reviewer=data["reviewer"],
            trace_id=data["trace_id"],
        )


@dataclass(frozen=True)
class GovernorVerdict:
    """Structured verdict emitted by the Governor.
    
    This is the authoritative output of the Governor evaluation process.
    Every path through the Governor returns a GovernorVerdict - no execution
    candidate proceeds without one.
    
    Attributes:
        verdict_id: Unique identifier for this verdict
        timestamp: ISO8601 timestamp when the verdict was created
        risk_level: Assessed risk level (none, low, medium, high, critical)
        decision: The governor's decision (continue, warn, recheck, require_approval, block)
        policy_class: The policy class that was applied
        rationale: Human-readable explanation for the decision
        lineage: Source tracking information
        tags: Derived tags for filtering and categorization
        overrides_applied: List of override rules that were triggered
    """
    verdict_id: str
    timestamp: str
    risk_level: RiskLevel
    decision: Decision
    policy_class: PolicyClass
    rationale: str
    lineage: Lineage
    tags: list[str] = field(default_factory=list)
    overrides_applied: list[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate the verdict structure after creation."""
        # Ensure risk_level is a RiskLevel enum
        if isinstance(self.risk_level, str):
            object.__setattr__(self, 'risk_level', RiskLevel(self.risk_level))
        # Ensure decision is a Decision enum
        if isinstance(self.decision, str):
            object.__setattr__(self, 'decision', Decision(self.decision))
        # Ensure policy_class is a PolicyClass enum
        if isinstance(self.policy_class, str):
            object.__setattr__(self, 'policy_class', PolicyClass(self.policy_class))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert verdict to dictionary for serialization.
        
        Returns:
            Dictionary representation of the verdict with all fields.
        """
        return {
            "verdict_id": self.verdict_id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level.value,
            "decision": self.decision.value,
            "policy_class": self.policy_class.value,
            "rationale": self.rationale,
            "lineage": self.lineage.to_dict(),
            "tags": self.tags.copy(),
            "overrides_applied": self.overrides_applied.copy(),
        }
    
    def to_json(self) -> str:
        """Serialize verdict to JSON string.
        
        Returns:
            JSON string representation of the verdict.
        """
        return json.dumps(self.to_dict(), separators=(',', ':'))
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GovernorVerdict:
        """Create GovernorVerdict from dictionary.
        
        Args:
            data: Dictionary containing verdict fields
            
        Returns:
            GovernorVerdict instance
        """
        return cls(
            verdict_id=data["verdict_id"],
            timestamp=data["timestamp"],
            risk_level=RiskLevel(data["risk_level"]),
            decision=Decision(data["decision"]),
            policy_class=PolicyClass(data["policy_class"]),
            rationale=data["rationale"],
            lineage=Lineage.from_dict(data["lineage"]),
            tags=data.get("tags", []),
            overrides_applied=data.get("overrides_applied", []),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> GovernorVerdict:
        """Deserialize verdict from JSON string.
        
        Args:
            json_str: JSON string containing verdict data
            
        Returns:
            GovernorVerdict instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_execution_allowed(self) -> bool:
        """Check if this verdict allows execution to proceed.
        
        Returns:
            True if decision is continue or warn, False otherwise.
        """
        return self.decision in (Decision.CONTINUE, Decision.WARN)
    
    def is_blocked(self) -> bool:
        """Check if this verdict blocks execution.
        
        Returns:
            True if decision is block, False otherwise.
        """
        return self.decision == Decision.BLOCK
    
    def requires_approval(self) -> bool:
        """Check if this verdict requires external approval.
        
        Returns:
            True if decision is require_approval, False otherwise.
        """
        return self.decision == Decision.REQUIRE_APPROVAL


def create_verdict(
    risk_level: RiskLevel,
    decision: Decision,
    policy_class: PolicyClass,
    rationale: str,
    source_event: str,
    reviewer: str,
    trace_id: str | None = None,
    tags: list[str] | None = None,
    overrides_applied: list[str] | None = None,
) -> GovernorVerdict:
    """Factory function to create a GovernorVerdict with auto-generated fields.
    
    Args:
        risk_level: Assessed risk level
        decision: The governor's decision
        policy_class: The policy class applied
        rationale: Human-readable explanation
        source_event: UUID of the source event
        reviewer: Name of the reviewer
        trace_id: Optional trace ID (generated if not provided)
        tags: Optional list of tags
        overrides_applied: Optional list of override rules triggered
        
    Returns:
        GovernorVerdict with generated verdict_id and timestamp
    """
    return GovernorVerdict(
        verdict_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        risk_level=risk_level,
        decision=decision,
        policy_class=policy_class,
        rationale=rationale,
        lineage=Lineage(
            source_event=source_event,
            reviewer=reviewer,
            trace_id=trace_id or str(uuid4()),
        ),
        tags=tags or [],
        overrides_applied=overrides_applied or [],
    )


# Schema validation compatibility - JSON Schema for GovernorVerdict
GOVERNOR_VERDICT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://advanced-vision.ai/schemas/governor_verdict.schema.json",
    "title": "GovernorVerdict",
    "description": "Structured verdict emitted by the Governor system",
    "type": "object",
    "required": [
        "verdict_id",
        "timestamp",
        "risk_level",
        "decision",
        "policy_class",
        "rationale",
        "lineage",
    ],
    "properties": {
        "verdict_id": {
            "type": "string",
            "format": "uuid",
            "description": "Unique identifier for this verdict",
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "ISO8601 timestamp when the verdict was created",
        },
        "risk_level": {
            "type": "string",
            "enum": ["none", "low", "medium", "high", "critical"],
            "description": "Assessed risk level",
        },
        "decision": {
            "type": "string",
            "enum": ["continue", "warn", "recheck", "require_approval", "block"],
            "description": "The governor's decision",
        },
        "policy_class": {
            "type": "string",
            "enum": [
                "observe",
                "inform",
                "internal_state_update",
                "external_review",
                "trading_analysis",
                "trading_execution_candidate",
                "ui_interaction_candidate",
                "sensitive_data_access",
                "promotion_candidate",
            ],
            "description": "The policy class that was applied",
        },
        "rationale": {
            "type": "string",
            "minLength": 1,
            "description": "Human-readable explanation for the decision",
        },
        "lineage": {
            "type": "object",
            "required": ["source_event", "reviewer", "trace_id"],
            "properties": {
                "source_event": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of the original event",
                },
                "reviewer": {
                    "type": "string",
                    "description": "Name of the reviewer",
                },
                "trace_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Trace ID for system-wide tracking",
                },
            },
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Derived tags for filtering",
        },
        "overrides_applied": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of override rules triggered",
        },
    },
}


def validate_verdict_dict(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a dictionary against the GovernorVerdict schema.
    
    Args:
        data: Dictionary to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check required fields
    for field in GOVERNOR_VERDICT_SCHEMA["required"]:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors
    
    # Validate risk_level enum
    valid_risk_levels = GOVERNOR_VERDICT_SCHEMA["properties"]["risk_level"]["enum"]
    if data["risk_level"] not in valid_risk_levels:
        errors.append(f"Invalid risk_level: {data['risk_level']}")
    
    # Validate decision enum
    valid_decisions = GOVERNOR_VERDICT_SCHEMA["properties"]["decision"]["enum"]
    if data["decision"] not in valid_decisions:
        errors.append(f"Invalid decision: {data['decision']}")
    
    # Validate policy_class enum
    valid_policy_classes = GOVERNOR_VERDICT_SCHEMA["properties"]["policy_class"]["enum"]
    if data["policy_class"] not in valid_policy_classes:
        errors.append(f"Invalid policy_class: {data['policy_class']}")
    
    # Validate lineage structure
    lineage = data.get("lineage", {})
    for field in GOVERNOR_VERDICT_SCHEMA["properties"]["lineage"]["required"]:
        if field not in lineage:
            errors.append(f"Missing required lineage field: {field}")
    
    return len(errors) == 0, errors
