"""Core validation and truth layer for advanced-vision.

This module provides the foundation for reliable packet processing:
- PacketValidator: JSON Schema validation with fast-path optimization
- TruthWriter: Append-only event logging with atomic writes
- SchemaRegistry: Centralized schema loading and caching
- Governor: Constitutional gate between reviewers and execution
- GovernorVerdict: Structured decision output from the Governor
- ExecutionPrecondition: Validates verdicts before execution
- ExecutionGate: Gate between reviewers and execution

Key Pattern:
    # Truth-first write
    truth_writer.write_event(event)
    truth_writer.write_artifact(manifest)
    
    # Then validate and fanout
    if packet_validator.validate(packet, 'ui_packet'):
        wss_publisher.publish(packet)

    # Governor evaluates before execution
    verdict = governor.evaluate(recommendation, context, policy_class)
    
    # ExecutionGate enforces preconditions
    decision = execution_gate.process(reviewer_output, context)
    if decision.can_execute:
        execute_action()

Always write truth before fanout. No execution without a verdict.
"""

# New validation layer
from .packet_validator import PacketValidator, PacketValidationError
from .truth_writer import TruthWriter

# Existing schema registry (backward compatibility)
from .schema_registry import SchemaRegistry, get_registry, get_cached_schema

# Governor system
from .governor_verdict import (
    Decision,
    GovernorVerdict,
    Lineage,
    PolicyClass,
    RiskLevel,
    create_verdict,
    validate_verdict_dict,
    GOVERNOR_VERDICT_SCHEMA,
)
from .governor import (
    Governor,
    PolicyContext,
    PolicyRule,
    ReviewerResult,
    quick_evaluate,
)

# Execution preconditions (AD-010 fix)
from .precondition_result import PreconditionResult
from .execution_precondition import (
    ExecutionPrecondition,
    ValidationResult,
    GateResult,
)
from .execution_gate import ExecutionGate, GateDecision

__all__ = [
    # New validation layer
    "PacketValidator",
    "PacketValidationError",
    "TruthWriter",
    # Existing schema registry (backward compatibility)
    "SchemaRegistry",
    "get_registry",
    "get_cached_schema",
    # Governor system
    "Governor",
    "GovernorVerdict",
    "Decision",
    "Lineage",
    "PolicyClass",
    "PolicyContext",
    "PolicyRule",
    "ReviewerResult",
    "RiskLevel",
    "create_verdict",
    "quick_evaluate",
    "validate_verdict_dict",
    "GOVERNOR_VERDICT_SCHEMA",
    # Execution preconditions (AD-010 fix)
    "ExecutionPrecondition",
    "ExecutionGate",
    "GateDecision",
    "PreconditionResult",
    "ValidationResult",
    "GateResult",
]
