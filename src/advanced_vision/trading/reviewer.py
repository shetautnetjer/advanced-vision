"""Local reviewer lane for Track B: Trading-Watch Intelligence.

This module implements the local reviewer layer per Dad's findings:
- Qwen3.5-2B/4B-NVFP4 as primary reviewer candidates
- Consumes ROI crops, parser structure, and scout notes
- Produces structured judgment with confidence and uncertainty
- Escalates to Kimi overseer when uncertain

The reviewer answers:
- What does this event likely mean?
- How risky is it?
- Should we continue, warn, hold, or escalate?
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from advanced_vision.trading.events import (
    ActionRecommendation,
    RiskLevel,
    ReviewerAssessment,
    ROI,
    TradingEvent,
    TradingEventType,
    UIElement,
    should_escalate_to_overseer,
)
from advanced_vision.trading.roi import EvidenceBundle, UIStructure


# =============================================================================
# Reviewer Configuration
# =============================================================================

class ReviewerModel(str, Enum):
    """Available local reviewer models."""
    # Per Dad's findings: Qwen NVFP4 variants are strong candidates
    QWEN_2B_NVFP4 = "qwen3.5-2b-nvfp4"
    QWEN_4B_NVFP4 = "qwen3.5-4b-nvfp4"
    QWEN_7B = "qwen3.5-7b"
    
    # Alternative/placeholder models
    EAGLE_SCOUT = "eagle2-2b"  # Can double as light reviewer
    LLAVA = "llava-v1.5"
    
    # Stub mode for testing
    STUB = "stub"


class ReviewerConfig(BaseModel):
    """Configuration for local reviewer behavior."""
    
    # Model selection
    model: ReviewerModel = ReviewerModel.QWEN_4B_NVFP4
    model_path: str | None = None  # Custom model path
    
    # Inference settings
    device: str = "auto"  # "cuda", "cpu", "auto"
    max_tokens: int = 512
    temperature: float = 0.3  # Lower for more consistent judgments
    
    # Confidence thresholds
    min_confidence: float = 0.6  # Below this = uncertain
    high_confidence: float = 0.85  # Above this = skip escalation
    
    # Risk auto-escalation
    auto_escalate_risk: set[RiskLevel] = Field(default_factory=lambda: {
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    })
    
    # Uncertainty handling
    escalate_on_low_confidence: bool = True
    escalate_on_unknown_event: bool = True
    
    # Safety
    dry_run: bool = True  # Stub mode by default


# =============================================================================
# Reviewer Prompts
# =============================================================================

REVIEWER_SYSTEM_PROMPT = """You are a careful trading assistant reviewing screen captures.

Your job is to assess trading-related UI events and provide structured judgment.

Respond with a JSON object containing:
- risk_level: "none" | "low" | "medium" | "high" | "critical"
- recommendation: "continue" | "note" | "warn" | "hold" | "pause" | "escalate"
- confidence: float between 0 and 1
- reasoning: brief explanation of your assessment
- is_uncertain: boolean, true if you need a second opinion

Event types and how to handle them:
- NOISE/CURSOR_ONLY: low risk, continue
- CHART_UPDATE: low risk, note
- PRICE_CHANGE: low risk, note
- ORDER_TICKET: medium risk, warn if values look unusual
- CONFIRM_DIALOG: medium risk, verify details
- WARNING_DIALOG: high risk, hold for review
- ERROR_DIALOG: critical risk, pause
- SLIPPAGE/MARGIN warnings: high risk, pause

Be conservative with money at risk. When in doubt, flag uncertainty."""


REVIEWER_PROMPT_TEMPLATE = """Review this trading interface event:

Event Type: {event_type}
Event Summary: {summary}
Detected UI Elements: {ui_elements}
Extracted Text: {text_content}

Provide your structured assessment following the system format."""


# =============================================================================
# Local Reviewer
# =============================================================================

class ReviewerInput(BaseModel):
    """Input to the reviewer model."""
    event: TradingEvent
    roi_crops: list[Path] = Field(default_factory=list)
    ui_structure: UIStructure | None = None
    scout_notes: str | None = None


class ReviewerOutput(BaseModel):
    """Output from the reviewer model."""
    assessment: ReviewerAssessment
    raw_response: str | None = None
    inference_time_ms: float = 0.0
    model_used: str


class LocalReviewer:
    """Local reviewer model for trading event assessment.
    
    Per Dad's architecture:
    - Consumes: ROI crops, UI structure, scout notes
    - Produces: Structured judgment with risk level and recommendation
    - Escalates: When uncertain or high risk
    """
    
    def __init__(self, config: ReviewerConfig | None = None):
        self.config = config or ReviewerConfig()
        self._model: Any | None = None
        self._model_loaded = False
        self._inference_count = 0
    
    def _load_model(self) -> bool:
        """Load reviewer model. Stub - model not downloaded per constraints."""
        if self._model_loaded:
            return True
        
        if self.config.dry_run or self.config.model == ReviewerModel.STUB:
            return False
        
        # Production would load actual model:
        # from transformers import AutoModelForVision2Seq, AutoProcessor
        # self._model = AutoModelForVision2Seq.from_pretrained(...)
        # self._processor = AutoProcessor.from_pretrained(...)
        
        return False
    
    def review(
        self,
        input_data: ReviewerInput,
        dry_run: bool | None = None,
    ) -> ReviewerOutput:
        """Review a trading event and produce structured assessment.
        
        Args:
            input_data: ReviewerInput with event and evidence
            dry_run: Override config dry_run setting
            
        Returns:
            ReviewerOutput with assessment and metadata
        """
        use_dry_run = dry_run if dry_run is not None else self.config.dry_run
        
        if use_dry_run or not self._load_model():
            return self._stub_review(input_data)
        
        # Production implementation would:
        # 1. Prepare prompt with ROIs and context
        # 2. Run model inference
        # 3. Parse structured output
        # 4. Create ReviewerAssessment
        
        return self._stub_review(input_data)
    
    def _stub_review(self, input_data: ReviewerInput) -> ReviewerOutput:
        """Generate stub review for testing (safe mode)."""
        import time
        start_time = time.time()
        
        event = input_data.event
        
        # Rule-based stub assessment
        assessment = self._rule_based_assessment(event)
        
        inference_time = (time.time() - start_time) * 1000
        self._inference_count += 1
        
        return ReviewerOutput(
            assessment=assessment,
            raw_response="stub_mode",
            inference_time_ms=inference_time,
            model_used=self.config.model.value,
        )
    
    def _rule_based_assessment(self, event: TradingEvent) -> ReviewerAssessment:
        """Generate rule-based assessment for stub mode.
        
        Mimics what a trained model would learn.
        """
        import datetime
        
        now = datetime.datetime.now().isoformat()
        
        # Default values
        risk_level = RiskLevel.LOW
        recommendation = ActionRecommendation.CONTINUE
        confidence = 0.75
        reasoning = "Default assessment"
        is_uncertain = False
        
        # Event type based rules
        event_rules: dict[TradingEventType, tuple[RiskLevel, ActionRecommendation, str]] = {
            TradingEventType.NOISE: (RiskLevel.NONE, ActionRecommendation.CONTINUE, "Just noise"),
            TradingEventType.CURSOR_ONLY: (RiskLevel.NONE, ActionRecommendation.CONTINUE, "Cursor movement only"),
            TradingEventType.ANIMATION: (RiskLevel.NONE, ActionRecommendation.CONTINUE, "Visual animation"),
            TradingEventType.CHART_UPDATE: (RiskLevel.LOW, ActionRecommendation.NOTE, "Chart updated"),
            TradingEventType.PRICE_CHANGE: (RiskLevel.LOW, ActionRecommendation.NOTE, "Price changed"),
            TradingEventType.ORDER_TICKET: (RiskLevel.MEDIUM, ActionRecommendation.WARN, "Order form active - verify details"),
            TradingEventType.CONFIRM_DIALOG: (RiskLevel.MEDIUM, ActionRecommendation.WARN, "Confirmation required"),
            TradingEventType.WARNING_DIALOG: (RiskLevel.HIGH, ActionRecommendation.HOLD, "Warning dialog - review before proceeding"),
            TradingEventType.ERROR_DIALOG: (RiskLevel.CRITICAL, ActionRecommendation.PAUSE, "Error dialog - stop and review"),
            TradingEventType.SLIPPAGE_WARNING: (RiskLevel.HIGH, ActionRecommendation.HOLD, "Slippage warning"),
            TradingEventType.MARGIN_WARNING: (RiskLevel.CRITICAL, ActionRecommendation.PAUSE, "Margin warning - immediate attention"),
            TradingEventType.ROUTE_WARNING: (RiskLevel.MEDIUM, ActionRecommendation.WARN, "Order routing warning"),
            TradingEventType.SYMBOL_MISMATCH: (RiskLevel.HIGH, ActionRecommendation.HOLD, "Symbol mismatch detected"),
        }
        
        if event.event_type in event_rules:
            risk_level, recommendation, reasoning = event_rules[event.event_type]
        else:
            is_uncertain = True
            reasoning = f"Unknown event type: {event.event_type.value}"
        
        # Adjust confidence based on event confidence
        confidence = min(event.confidence + 0.2, 0.95)
        
        # Check for uncertainty triggers
        if event.event_type == TradingEventType.UNKNOWN:
            is_uncertain = True
            confidence = 0.4
        
        # Build assessment
        assessment = ReviewerAssessment(
            reviewer_model=self.config.model.value,
            timestamp=now,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            evidence_links=[roi.crop_path for roi in event.rois if roi.crop_path],
            is_uncertain=is_uncertain,
            uncertainty_reason="Unknown event type" if is_uncertain else None,
        )
        
        # Check escalation rules
        if risk_level in self.config.auto_escalate_risk:
            assessment.is_uncertain = True
            assessment.uncertainty_reason = f"Risk level {risk_level.value} requires escalation"
        elif confidence < self.config.min_confidence and self.config.escalate_on_low_confidence:
            assessment.is_uncertain = True
            assessment.uncertainty_reason = f"Low confidence: {confidence:.2f}"
        
        return assessment
    
    def should_escalate(self, assessment: ReviewerAssessment) -> bool:
        """Determine if assessment warrants escalation to overseer."""
        return should_escalate_to_overseer(assessment)
    
    def get_stats(self) -> dict[str, Any]:
        """Get reviewer statistics."""
        return {
            "inference_count": self._inference_count,
            "model": self.config.model.value,
            "dry_run": self.config.dry_run,
        }


# =============================================================================
# Reviewer Lane Orchestrator
# =============================================================================

class ReviewerLane:
    """Orchestrates the reviewer lane processing.
    
    Integrates:
    - Scout input (pre-classified event)
    - ROI evidence
    - Reviewer judgment
    - Escalation decision
    """
    
    def __init__(self, config: ReviewerConfig | None = None):
        self.config = config or ReviewerConfig()
        self.reviewer = LocalReviewer(config)
        self._processed_count = 0
        self._escalated_count = 0
    
    def process_event(
        self,
        event: TradingEvent,
        roi_crops: list[Path] | None = None,
        ui_structure: UIStructure | None = None,
        dry_run: bool = True,
    ) -> TradingEvent:
        """Process trading event through reviewer lane.
        
        Args:
            event: Trading event from scout
            roi_crops: Paths to ROI images
            ui_structure: Parsed UI structure
            dry_run: Safe mode
            
        Returns:
            Updated event with reviewer assessment
        """
        self._processed_count += 1
        
        # Skip reviewer for noise events
        if event.event_type in {
            TradingEventType.NOISE,
            TradingEventType.CURSOR_ONLY,
            TradingEventType.ANIMATION,
        }:
            event.reviewer_assessment = ReviewerAssessment(
                reviewer_model=self.config.model.value,
                timestamp=event.timestamp,
                risk_level=RiskLevel.NONE,
                recommendation=ActionRecommendation.CONTINUE,
                confidence=0.95,
                reasoning="Noise event - no review needed",
                is_uncertain=False,
            )
            return event
        
        # Run reviewer
        input_data = ReviewerInput(
            event=event,
            roi_crops=roi_crops or [],
            ui_structure=ui_structure,
        )
        
        output = self.reviewer.review(input_data, dry_run=dry_run)
        event.reviewer_assessment = output.assessment
        
        # Check escalation
        if self.reviewer.should_escalate(output.assessment):
            event.escalated_to_overseer = True
            self._escalated_count += 1
        
        return event
    
    def get_stats(self) -> dict[str, Any]:
        """Get lane statistics."""
        return {
            "processed_count": self._processed_count,
            "escalated_count": self._escalated_count,
            "escalation_rate": self._escalated_count / max(self._processed_count, 1),
            **self.reviewer.get_stats(),
        }


# =============================================================================
# Escalation Preparation
# =============================================================================

class EscalationPreparer:
    """Prepare events for escalation to Kimi overseer.
    
    Per Dad's findings: escalate only minimal, sanitized evidence.
    """
    
    def __init__(self):
        self._escalation_count = 0
    
    def prepare_escalation(
        self,
        event: TradingEvent,
        include_full_context: bool = False,
    ) -> EvidenceBundle:
        """Prepare minimal evidence bundle for Kimi escalation.
        
        Args:
            event: Trading event with reviewer assessment
            include_full_context: If True, include more context (use sparingly)
            
        Returns:
            EvidenceBundle with redacted/sanitized content
        """
        self._escalation_count += 1
        
        assessment = event.reviewer_assessment
        
        # Build minimal summary
        conf_str = f"{assessment.confidence:.2f}" if assessment else "0"
        summary_parts = [
            f"Event: {event.event_type.value}",
            f"Local reviewer risk: {assessment.risk_level.value if assessment else 'unknown'}",
            f"Local confidence: {conf_str}",
        ]
        
        if event.summary:
            summary_parts.append(f"Context: {event.summary}")
        
        # Risk indicators
        risk_indicators = []
        if assessment:
            if assessment.is_uncertain:
                risk_indicators.append("local_uncertain")
            risk_indicators.append(f"risk_{assessment.risk_level.value}")
            if assessment.recommendation in {ActionRecommendation.PAUSE, ActionRecommendation.HOLD}:
                risk_indicators.append("blocking_recommended")
        
        # Redact sensitive content
        redacted_text = None
        if event.raw_text_extracted:
            redacted_text = self._redact_for_escalation(event.raw_text_extracted)
        
        return EvidenceBundle(
            event_id=event.event_id,
            timestamp=event.timestamp,
            event_summary=" | ".join(summary_parts),
            risk_indicators=risk_indicators,
            roi_crop_paths=[roi.crop_path for roi in event.rois if roi.crop_path],
            reviewer_confidence=assessment.confidence if assessment else None,
            reviewer_reasoning=assessment.reasoning if assessment else None,
            redacted_text=redacted_text,
        )
    
    def _redact_for_escalation(self, text: str) -> str:
        """Redact sensitive content before cloud escalation."""
        import re
        
        redacted = text
        
        # API keys
        redacted = re.sub(
            r'\b(sk-[a-zA-Z0-9]{20,}|key_[a-zA-Z0-9]{16,})\b',
            '[KEY_REDACTED]',
            redacted
        )
        
        # Wallet addresses
        redacted = re.sub(
            r'\b(0x[a-fA-F0-9]{40}|[13][a-zA-Z0-9]{24,33})\b',
            '[WALLET_REDACTED]',
            redacted
        )
        
        # Account numbers (keep last 4)
        redacted = re.sub(
            r'\b\d{8,}\b',
            lambda m: '[ACCT-' + m.group()[-4:] + ']',
            redacted
        )
        
        return redacted


# =============================================================================
# Factory Functions
# =============================================================================

def create_reviewer(
    model: ReviewerModel = ReviewerModel.QWEN_4B_NVFP4,
    dry_run: bool = True,
) -> LocalReviewer:
    """Factory function to create configured reviewer."""
    config = ReviewerConfig(model=model, dry_run=dry_run)
    return LocalReviewer(config)


def create_reviewer_lane(
    model: ReviewerModel = ReviewerModel.QWEN_4B_NVFP4,
    dry_run: bool = True,
) -> ReviewerLane:
    """Factory function to create reviewer lane."""
    config = ReviewerConfig(model=model, dry_run=dry_run)
    return ReviewerLane(config)
