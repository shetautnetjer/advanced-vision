"""ExecutionPrecondition - Validates execution preconditions before allowing execution.

This module provides the ExecutionPrecondition class which enforces:
1. No execution candidate without a valid GovernorVerdict
2. No stale verdict reuse beyond freshness window
3. No malformed/missing verdict objects
4. No missing trace/lineage fields
5. Execution blocked based on verdict decision

Core doctrine: Reviewer outputs are advisory evidence, not executable authority.
A valid GovernorVerdict is required before any execution candidate proceeds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from .governor_verdict import (
    Decision,
    GovernorVerdict,
    validate_verdict_dict,
    GOVERNOR_VERDICT_SCHEMA,
)
from .precondition_result import PreconditionResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of verdict structure validation.
    
    Attributes:
        valid: Whether the verdict structure is valid
        errors: List of validation error messages
        missing_fields: List of required fields that are missing
    """
    valid: bool
    errors: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Convenience property for validity check."""
        return self.valid


@dataclass
class GateResult:
    """Result of decision gate enforcement.
    
    Attributes:
        can_proceed: Whether execution can proceed based on decision
        decision: The decision that was evaluated
        action_required: What action is required (halt, warn, proceed, recheck)
    """
    can_proceed: bool
    decision: Decision
    action_required: str


class ExecutionPrecondition:
    """Enforces execution preconditions for governor verdicts.
    
    This class validates that execution candidates have valid, fresh GovernorVerdicts
    before allowing execution to proceed. It blocks all direct reviewer → execution
    paths and requires proper verdict validation.
    
    Usage:
        precondition = ExecutionPrecondition()
        
        # Check if packet can execute
        result = precondition.check(packet, verdict)
        if result.allowed:
            execute_action()
        else:
            handle_blocked_execution(result)
    """
    
    # Default freshness window in seconds
    DEFAULT_FRESHNESS_SECONDS: int = 30
    
    # Violation type constants
    VIOLATION_MISSING_VERDICT = "missing_verdict"
    VIOLATION_MALFORMED_VERDICT = "malformed_verdict"
    VIOLATION_STALE_VERDICT = "stale_verdict"
    VIOLATION_MISSING_LINEAGE = "missing_lineage"
    VIOLATION_INVALID_LINEAGE = "invalid_lineage"
    VIOLATION_BLOCKED_DECISION = "blocked_decision"
    VIOLATION_APPROVAL_REQUIRED = "approval_required"
    VIOLATION_RECHECK_REQUIRED = "recheck_required"
    VIOLATION_NO_EXECUTION_FLAG = "not_execution_candidate"
    
    def __init__(self, default_freshness_seconds: int = DEFAULT_FRESHNESS_SECONDS):
        """Initialize ExecutionPrecondition.
        
        Args:
            default_freshness_seconds: Default max age for verdict freshness
        """
        self.default_freshness_seconds = default_freshness_seconds
        self._check_count = 0
        self._block_count = 0
        
        logger.info(
            "ExecutionPrecondition initialized with freshness_window=%ds",
            default_freshness_seconds
        )
    
    def check(
        self,
        packet: dict[str, Any],
        verdict: Optional[GovernorVerdict] = None,
    ) -> PreconditionResult:
        """Check if execution is allowed for a packet.
        
        This is the main entry point for precondition checking. It validates:
        1. Packet is an execution candidate (has execution_candidate flag)
        2. Verdict is present and valid
        3. Verdict is fresh (within freshness window)
        4. Verdict structure is complete
        5. Lineage fields are present
        6. Decision allows execution
        
        Args:
            packet: The packet to check (must have execution_candidate flag)
            verdict: Optional GovernorVerdict to validate (required for execution candidates)
            
        Returns:
            PreconditionResult indicating whether execution is allowed
        """
        self._check_count += 1
        
        # Check 1: Is this an execution candidate?
        is_execution_candidate = packet.get("execution_candidate", False)
        if not is_execution_candidate:
            # Not an execution candidate - no verdict required
            return PreconditionResult.allowed_result(
                reason="Packet is not an execution candidate - no verdict required",
                verdict_id=None,
            )
        
        # Check 2: Execution candidates MUST have a verdict
        if verdict is None:
            self._block_count += 1
            logger.warning(
                "Execution precondition BLOCKED: execution_candidate packet "
                "without GovernorVerdict"
            )
            return PreconditionResult.blocked_result(
                reason="Execution candidate packets require a valid GovernorVerdict. "
                       "Reviewer recommendation alone cannot trigger execution.",
                violation_type=self.VIOLATION_MISSING_VERDICT,
                verdict_id=None,
            )
        
        # Check 3: Validate verdict structure
        validation = self.validate_verdict_structure(verdict)
        if not validation.valid:
            self._block_count += 1
            logger.warning(
                "Execution precondition BLOCKED: malformed verdict - %s",
                "; ".join(validation.errors)
            )
            return PreconditionResult.blocked_result(
                reason=f"Malformed GovernorVerdict: {'; '.join(validation.errors)}",
                violation_type=self.VIOLATION_MALFORMED_VERDICT,
                verdict_id=getattr(verdict, 'verdict_id', None),
            )
        
        # Check 4: Validate verdict freshness
        if not self.check_verdict_freshness(verdict):
            self._block_count += 1
            logger.warning(
                "Execution precondition BLOCKED: stale verdict %s",
                verdict.verdict_id
            )
            return PreconditionResult.blocked_result(
                reason=f"GovernorVerdict {verdict.verdict_id} is stale "
                       f"(older than {self.default_freshness_seconds}s freshness window)",
                violation_type=self.VIOLATION_STALE_VERDICT,
                verdict_id=verdict.verdict_id,
            )
        
        # Check 5: Validate lineage fields
        lineage_validation = self._validate_lineage(verdict)
        if not lineage_validation.valid:
            self._block_count += 1
            logger.warning(
                "Execution precondition BLOCKED: invalid lineage - %s",
                "; ".join(lineage_validation.errors)
            )
            return PreconditionResult.blocked_result(
                reason=f"Invalid lineage: {'; '.join(lineage_validation.errors)}",
                violation_type=self.VIOLATION_INVALID_LINEAGE,
                verdict_id=verdict.verdict_id,
            )
        
        # Check 6: Enforce decision gate
        gate_result = self.enforce_decision_gate(verdict.decision)
        if not gate_result.can_proceed:
            self._block_count += 1
            logger.warning(
                "Execution precondition BLOCKED: decision=%s requires action=%s",
                verdict.decision.value,
                gate_result.action_required
            )
            
            if verdict.decision == Decision.BLOCK:
                return PreconditionResult.blocked_result(
                    reason=f"GovernorVerdict {verdict.verdict_id} decision is 'block' - "
                           "execution halted, violation attempt logged",
                    violation_type=self.VIOLATION_BLOCKED_DECISION,
                    verdict_id=verdict.verdict_id,
                )
            elif verdict.decision == Decision.REQUIRE_APPROVAL:
                return PreconditionResult.approval_required_result(
                    reason=f"GovernorVerdict {verdict.verdict_id} requires explicit approval "
                           "before execution can proceed",
                    verdict_id=verdict.verdict_id,
                )
            elif verdict.decision == Decision.RECHECK:
                return PreconditionResult.recheck_result(
                    reason=f"GovernorVerdict {verdict.verdict_id} requires recheck - "
                           "routing back for deeper review",
                    verdict_id=verdict.verdict_id,
                )
            else:
                # Unknown blocked state
                return PreconditionResult.blocked_result(
                    reason=f"GovernorVerdict {verdict.verdict_id} blocks execution",
                    violation_type=self.VIOLATION_BLOCKED_DECISION,
                    verdict_id=verdict.verdict_id,
                )
        
        # All checks passed - execution allowed
        logger.debug(
            "Execution precondition ALLOWED: verdict=%s decision=%s",
            verdict.verdict_id,
            verdict.decision.value
        )
        
        if verdict.decision == Decision.WARN:
            return PreconditionResult.allowed_result(
                reason=f"GovernorVerdict {verdict.verdict_id} allows execution with warning "
                       "(proceeding with caution)",
                verdict_id=verdict.verdict_id,
            )
        
        return PreconditionResult.allowed_result(
            reason=f"GovernorVerdict {verdict.verdict_id} allows execution",
            verdict_id=verdict.verdict_id,
        )
    
    def check_verdict_freshness(
        self,
        verdict: GovernorVerdict,
        max_age_seconds: Optional[int] = None,
    ) -> bool:
        """Check if a verdict is within the freshness window.
        
        Args:
            verdict: The GovernorVerdict to check
            max_age_seconds: Max age in seconds (uses default if not specified)
            
        Returns:
            True if verdict is fresh (within window), False if stale
        """
        max_age = max_age_seconds or self.default_freshness_seconds
        
        try:
            # Parse the verdict timestamp
            timestamp = datetime.fromisoformat(verdict.timestamp)
            
            # Ensure timezone-aware comparison
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age_seconds = (now - timestamp).total_seconds()
            
            return age_seconds <= max_age
            
        except (ValueError, TypeError) as e:
            logger.error("Failed to parse verdict timestamp: %s", e)
            return False
    
    def validate_verdict_structure(self, verdict: GovernorVerdict) -> ValidationResult:
        """Validate the structure of a GovernorVerdict.
        
        Checks that all required fields are present and valid according to
        the GovernorVerdict schema.
        
        Args:
            verdict: The GovernorVerdict to validate
            
        Returns:
            ValidationResult with validity status and any errors
        """
        errors = []
        missing_fields = []
        
        # Required fields per GOVERNOR_VERDICT_SCHEMA
        required_fields = GOVERNOR_VERDICT_SCHEMA["required"]
        
        # Check each required field
        for field in required_fields:
            if not hasattr(verdict, field):
                missing_fields.append(field)
                errors.append(f"Missing required field: {field}")
            elif getattr(verdict, field) is None:
                missing_fields.append(field)
                errors.append(f"Required field is None: {field}")
        
        if missing_fields:
            return ValidationResult(
                valid=False,
                errors=errors,
                missing_fields=missing_fields,
            )
        
        # Validate lineage structure
        lineage = verdict.lineage
        if lineage is None:
            errors.append("lineage is None")
            missing_fields.append("lineage")
        else:
            lineage_required = GOVERNOR_VERDICT_SCHEMA["properties"]["lineage"]["required"]
            for field in lineage_required:
                if not hasattr(lineage, field):
                    errors.append(f"Missing required lineage field: {field}")
                    missing_fields.append(f"lineage.{field}")
                elif getattr(lineage, field) is None or getattr(lineage, field) == "":
                    errors.append(f"Required lineage field is empty: {field}")
                    missing_fields.append(f"lineage.{field}")
        
        # Validate UUID fields are valid UUID strings
        uuid_fields = ["verdict_id"]
        if hasattr(verdict, 'lineage') and verdict.lineage:
            uuid_fields.extend(["source_event", "trace_id"])
        
        for field in uuid_fields:
            value = getattr(verdict if not field.startswith("lineage.") else verdict.lineage,
                           field.replace("lineage.", ""), None)
            if value:
                try:
                    UUID(value)
                except ValueError:
                    errors.append(f"Invalid UUID format for {field}: {value}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            missing_fields=missing_fields,
        )
    
    def enforce_decision_gate(self, decision: Decision) -> GateResult:
        """Enforce the decision gate based on verdict decision.
        
        Args:
            decision: The GovernorVerdict decision to enforce
            
        Returns:
            GateResult indicating whether execution can proceed
        """
        if decision == Decision.CONTINUE:
            return GateResult(
                can_proceed=True,
                decision=decision,
                action_required="proceed",
            )
        elif decision == Decision.WARN:
            return GateResult(
                can_proceed=True,
                decision=decision,
                action_required="proceed_with_caution",
            )
        elif decision == Decision.RECHECK:
            return GateResult(
                can_proceed=False,
                decision=decision,
                action_required="recheck",
            )
        elif decision == Decision.REQUIRE_APPROVAL:
            return GateResult(
                can_proceed=False,
                decision=decision,
                action_required="await_approval",
            )
        elif decision == Decision.BLOCK:
            return GateResult(
                can_proceed=False,
                decision=decision,
                action_required="halt",
            )
        else:
            # Unknown decision - block for safety
            return GateResult(
                can_proceed=False,
                decision=decision,
                action_required="halt",
            )
    
    def _validate_lineage(self, verdict: GovernorVerdict) -> ValidationResult:
        """Validate lineage fields specifically.
        
        Args:
            verdict: The GovernorVerdict with lineage to validate
            
        Returns:
            ValidationResult for lineage fields
        """
        errors = []
        missing_fields = []
        
        if verdict.lineage is None:
            return ValidationResult(
                valid=False,
                errors=["lineage is None"],
                missing_fields=["lineage"],
            )
        
        lineage = verdict.lineage
        
        # Check source_event is valid UUID
        if not lineage.source_event:
            errors.append("lineage.source_event is missing")
            missing_fields.append("lineage.source_event")
        else:
            try:
                UUID(lineage.source_event)
            except ValueError:
                errors.append(f"lineage.source_event is not a valid UUID: {lineage.source_event}")
        
        # Check reviewer is specified
        if not lineage.reviewer:
            errors.append("lineage.reviewer is missing")
            missing_fields.append("lineage.reviewer")
        elif not isinstance(lineage.reviewer, str) or lineage.reviewer.strip() == "":
            errors.append("lineage.reviewer must be a non-empty string")
        elif lineage.reviewer not in ("eagle", "qwen", "aya", "claude", "kimi", "gpt", "gemini"):
            # Reviewer should be a known reviewer type (warning only, not blocking)
            logger.debug("Unknown reviewer type: %s", lineage.reviewer)
        
        # Check trace_id is valid UUID
        if not lineage.trace_id:
            errors.append("lineage.trace_id is missing")
            missing_fields.append("lineage.trace_id")
        else:
            try:
                UUID(lineage.trace_id)
            except ValueError:
                errors.append(f"lineage.trace_id is not a valid UUID: {lineage.trace_id}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            missing_fields=missing_fields,
        )
    
    @property
    def check_count(self) -> int:
        """Total number of precondition checks performed."""
        return self._check_count
    
    @property
    def block_count(self) -> int:
        """Total number of executions blocked."""
        return self._block_count
