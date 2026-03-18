"""PreconditionResult - Result type for execution precondition checks.

This module defines the PreconditionResult dataclass used to communicate
the outcome of execution precondition checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PreconditionResult:
    """Result of an execution precondition check.
    
    This dataclass encapsulates the outcome of checking whether an execution
candidate packet is allowed to proceed based on governor verdict validation.
    
    Attributes:
        allowed: Whether execution is allowed to proceed
        reason: Human-readable explanation of the result
        verdict_id: Optional ID of the verdict that was checked
        violation_type: Optional classification of the violation if blocked
        """
    allowed: bool
    reason: str
    verdict_id: Optional[str] = None
    violation_type: Optional[str] = None
    
    @classmethod
    def allowed_result(
        cls,
        reason: str,
        verdict_id: Optional[str] = None,
    ) -> PreconditionResult:
        """Create an allowed result.
        
        Args:
            reason: Explanation for why execution is allowed
            verdict_id: Optional verdict ID
            
        Returns:
            PreconditionResult with allowed=True
        """
        return cls(
            allowed=True,
            reason=reason,
            verdict_id=verdict_id,
            violation_type=None,
        )
    
    @classmethod
    def blocked_result(
        cls,
        reason: str,
        violation_type: str,
        verdict_id: Optional[str] = None,
    ) -> PreconditionResult:
        """Create a blocked result.
        
        Args:
            reason: Explanation for why execution is blocked
            violation_type: Classification of the violation
            verdict_id: Optional verdict ID (may be None if verdict was missing)
            
        Returns:
            PreconditionResult with allowed=False
        """
        return cls(
            allowed=False,
            reason=reason,
            verdict_id=verdict_id,
            violation_type=violation_type,
        )
    
    @classmethod
    def recheck_result(
        cls,
        reason: str,
        verdict_id: Optional[str] = None,
    ) -> PreconditionResult:
        """Create a recheck result - execution blocked, route back for review.
        
        Args:
            reason: Explanation for why recheck is needed
            verdict_id: Optional verdict ID
            
        Returns:
            PreconditionResult with allowed=False and violation_type='recheck_required'
        """
        return cls(
            allowed=False,
            reason=reason,
            verdict_id=verdict_id,
            violation_type="recheck_required",
        )
    
    @classmethod
    def approval_required_result(
        cls,
        reason: str,
        verdict_id: Optional[str] = None,
    ) -> PreconditionResult:
        """Create an approval required result - execution blocked pending approval.
        
        Args:
            reason: Explanation for why approval is required
            verdict_id: Optional verdict ID
            
        Returns:
            PreconditionResult with allowed=False and violation_type='approval_required'
        """
        return cls(
            allowed=False,
            reason=reason,
            verdict_id=verdict_id,
            violation_type="approval_required",
        )
