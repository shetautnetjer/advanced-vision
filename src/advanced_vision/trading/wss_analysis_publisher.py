"""Chronos/Kimi Analysis Results WebSocket Publisher.

Publishes analysis results from Chronos/Kimi to ws://localhost:8005.
Supports risk assessment, recommendations, and trading signals.

DEPRECATED: Use wss_analysis_publisher_v2.py instead (v2 uses single port 8000 with topic routing)
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import websockets

# Deprecation warning
warnings.warn(
    "wss_analysis_publisher.py (v1) is deprecated. Use wss_analysis_publisher_v2.py instead. "
    "v2 uses single port 8000 with topic routing (vision.analysis.qwen).",
    DeprecationWarning,
    stacklevel=2
)

from advanced_vision.trading.events import (
    ActionRecommendation,
    ReviewerAssessment,
    RiskLevel,
    OverseerResponse,
)

logger = logging.getLogger(__name__)


class AnalysisWSSPublisher:
    """WebSocket publisher for Chronos/Kimi analysis results.
    
    Features:
    - Async WebSocket connection to ws://localhost:8005
    - Thread-safe queue for analysis results
    - Publishes risk levels, recommendations, and trading signals
    - Supports both local reviewer (Chronos/Qwen) and overseer (Kimi) results
    - Schema tagging: "ui" or "trading"
    
    Message Format:
        {
            timestamp: ISO8601,
            frame_id: str,
            analysis: str,
            risk_level: "none" | "low" | "medium" | "high" | "critical",
            recommendation: "continue" | "note" | "warn" | "hold" | "pause" | "escalate"
        }
    
    Usage:
        publisher = AnalysisWSSPublisher()
        publisher.start()
        
        # After reviewer analysis:
        publisher.publish_reviewer_assessment(assessment, frame_id)
        
        # After overseer (Kimi) response:
        publisher.publish_overseer_response(response, frame_id)
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8005"
    HIGH_PRIORITY_RISKS = {RiskLevel.HIGH, RiskLevel.CRITICAL}
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        schema: str = "trading",
        enable_priority_queue: bool = True,
        alert_on_critical: bool = True,
    ):
        self.uri = uri
        self.schema = schema
        self.enable_priority_queue = enable_priority_queue
        self.alert_on_critical = alert_on_critical
        
        # Threading
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._priority_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        self._loop: asyncio.AbstractEventLoop | None = None
        
        # State
        self._connected = False
        self._analysis_counter = 0
        self._critical_alerts = 0
        self._high_risk_count = 0
        
        # Stats tracking
        self._risk_distribution: dict[str, int] = {
            "none": 0, "low": 0, "medium": 0, "high": 0, "critical": 0
        }
        self._recommendation_distribution: dict[str, int] = {}
    
    def start(self) -> None:
        """Start the publisher in a background thread."""
        if self._thread is not None:
            logger.warning("Analysis publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"Analysis publisher started (URI: {self.uri})")
    
    def stop(self) -> None:
        """Stop the publisher and close connections."""
        if self._thread is None:
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        self._connected = False
        logger.info("Analysis publisher stopped")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"Analysis publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.uri) as websocket:
                    self._connected = True
                    logger.info(f"Analysis publisher connected to {self.uri}")
                    
                    while not self._stop_event.is_set():
                        # Check priority queue first
                        try:
                            message = self._priority_queue.get_nowait()
                            await websocket.send(json.dumps(message))
                            continue
                        except asyncio.QueueEmpty:
                            pass
                        
                        # Then check normal queue
                        try:
                            message = await asyncio.wait_for(
                                self._queue.get(),
                                timeout=0.1
                            )
                            await websocket.send(json.dumps(message))
                        except asyncio.TimeoutError:
                            pass
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("Analysis WebSocket closed, reconnecting...")
                            break
                        except Exception as e:
                            logger.error(f"Analysis send error: {e}")
                            
            except websockets.exceptions.ConnectionRefusedError:
                logger.warning(f"Analysis WebSocket refused, retrying in 2s...")
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"Analysis WebSocket error: {e}")
                await asyncio.sleep(2.0)
            finally:
                self._connected = False
    
    def _enqueue_message(
        self,
        message: dict[str, Any],
        priority: bool = False,
    ) -> None:
        """Enqueue message to appropriate queue."""
        if priority and self.enable_priority_queue:
            try:
                self._priority_queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Priority queue full, using normal queue")
                try:
                    self._queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.error("Both queues full, dropping message")
        else:
            try:
                self._queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Analysis queue full, dropping message")
    
    def _update_stats(self, risk_level: RiskLevel, recommendation: ActionRecommendation) -> None:
        """Update statistics."""
        self._risk_distribution[risk_level.value] += 1
        
        rec_key = recommendation.value
        self._recommendation_distribution[rec_key] = (
            self._recommendation_distribution.get(rec_key, 0) + 1
        )
        
        if risk_level in self.HIGH_PRIORITY_RISKS:
            self._high_risk_count += 1
    
    def publish_analysis(
        self,
        frame_id: str,
        analysis: str,
        risk_level: RiskLevel | str,
        recommendation: ActionRecommendation | str,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish generic analysis result.
        
        Args:
            frame_id: Frame identifier
            analysis: Analysis text/summary
            risk_level: Risk assessment level
            recommendation: Recommended action
            confidence: Optional confidence score
            metadata: Optional additional metadata
        """
        self._analysis_counter += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Normalize inputs
        if isinstance(risk_level, RiskLevel):
            risk_level = risk_level.value
        if isinstance(recommendation, ActionRecommendation):
            recommendation = recommendation.value
        
        # Update stats
        self._update_stats(RiskLevel(risk_level), ActionRecommendation(recommendation))
        
        # Determine priority
        is_priority = RiskLevel(risk_level) in self.HIGH_PRIORITY_RISKS
        
        message = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "analysis": analysis,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "schema": self.schema,
        }
        
        if confidence is not None:
            message["confidence"] = round(confidence, 4)
        if metadata:
            message["metadata"] = metadata
        
        # Critical alert handling
        if self.alert_on_critical and risk_level == RiskLevel.CRITICAL.value:
            self._critical_alerts += 1
            message["alert"] = True
            message["alert_type"] = "critical"
            logger.critical(f"CRITICAL ALERT: Frame {frame_id} - {analysis[:100]}")
        
        self._enqueue_message(message, priority=is_priority)
    
    def publish_reviewer_assessment(
        self,
        assessment: ReviewerAssessment,
        frame_id: str,
    ) -> None:
        """Publish local reviewer (Chronos/Qwen) assessment.
        
        Args:
            assessment: ReviewerAssessment from local model
            frame_id: Frame identifier
        """
        metadata = {
            "source": "local_reviewer",
            "reviewer_model": assessment.reviewer_model,
            "is_uncertain": assessment.is_uncertain,
        }
        
        if assessment.uncertainty_reason:
            metadata["uncertainty_reason"] = assessment.uncertainty_reason
        
        if assessment.evidence_links:
            metadata["evidence_links"] = assessment.evidence_links
        
        self.publish_analysis(
            frame_id=frame_id,
            analysis=assessment.reasoning,
            risk_level=assessment.risk_level,
            recommendation=assessment.recommendation,
            confidence=assessment.confidence,
            metadata=metadata,
        )
    
    def publish_overseer_response(
        self,
        response: OverseerResponse,
        frame_id: str,
        escalated_from: ReviewerAssessment | None = None,
    ) -> None:
        """Publish overseer (Kimi) response.
        
        Args:
            response: OverseerResponse from cloud model
            frame_id: Frame identifier
            escalated_from: Original reviewer assessment if escalation
        """
        metadata = {
            "source": "overseer",
            "model": response.model,
            "request_id": response.request_id,
            "agrees_with_reviewer": response.agrees_with_reviewer,
        }
        
        if response.additional_observations:
            metadata["additional_observations"] = response.additional_observations
        
        if escalated_from:
            metadata["escalation"] = {
                "from_reviewer": escalated_from.reviewer_model,
                "original_risk": escalated_from.risk_level.value,
                "original_recommendation": escalated_from.recommendation.value,
            }
        
        self.publish_analysis(
            frame_id=frame_id,
            analysis=response.reasoning,
            risk_level=response.risk_level,
            recommendation=response.recommendation,
            confidence=response.confidence,
            metadata=metadata,
        )
    
    def publish_trading_signal(
        self,
        frame_id: str,
        signal_type: str,
        symbol: str | None = None,
        direction: str | None = None,  # "buy", "sell", "hold"
        price: float | None = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        analysis: str = "",
    ) -> None:
        """Publish trading signal.
        
        Args:
            frame_id: Frame identifier
            signal_type: Type of trading signal
            symbol: Trading symbol (e.g., "AAPL")
            direction: Signal direction
            price: Current/target price
            risk_level: Associated risk
            analysis: Signal analysis
        """
        metadata = {
            "source": "trading_signal",
            "signal_type": signal_type,
        }
        
        if symbol:
            metadata["symbol"] = symbol
        if direction:
            metadata["direction"] = direction
        if price:
            metadata["price"] = price
        
        # Map direction to recommendation
        direction_map = {
            "buy": ActionRecommendation.CONTINUE,
            "sell": ActionRecommendation.WARN,
            "hold": ActionRecommendation.NOTE,
        }
        recommendation = direction_map.get(direction, ActionRecommendation.NOTE)
        
        self.publish_analysis(
            frame_id=frame_id,
            analysis=analysis or f"Trading signal: {signal_type}",
            risk_level=risk_level,
            recommendation=recommendation,
            metadata=metadata,
        )
    
    def publish_error(
        self,
        frame_id: str,
        error_message: str,
        error_type: str = "analysis_error",
    ) -> None:
        """Publish analysis error.
        
        Args:
            frame_id: Frame identifier
            error_message: Error description
            error_type: Type of error
        """
        message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "frame_id": frame_id,
            "type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "risk_level": RiskLevel.HIGH.value,  # Errors are high risk
            "recommendation": ActionRecommendation.HOLD.value,
            "schema": self.schema,
        }
        
        self._enqueue_message(message, priority=True)
        logger.error(f"Analysis error for {frame_id}: {error_message}")
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected
    
    @property
    def queue_size(self) -> int:
        """Get current normal queue size."""
        return self._queue.qsize()
    
    @property
    def priority_queue_size(self) -> int:
        """Get current priority queue size."""
        return self._priority_queue.qsize()
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        return {
            "connected": self._connected,
            "analyses_published": self._analysis_counter,
            "critical_alerts": self._critical_alerts,
            "high_risk_count": self._high_risk_count,
            "queue_size": self.queue_size,
            "priority_queue_size": self.priority_queue_size,
            "risk_distribution": self._risk_distribution.copy(),
            "recommendation_distribution": self._recommendation_distribution.copy(),
            "uri": self.uri,
        }
    
    def get_risk_summary(self) -> dict[str, Any]:
        """Get risk distribution summary."""
        total = sum(self._risk_distribution.values())
        if total == 0:
            return {"total": 0, "percentages": {}}
        
        percentages = {
            k: round(v / total * 100, 2)
            for k, v in self._risk_distribution.items()
        }
        
        return {
            "total": total,
            "percentages": percentages,
            "high_risk_rate": round(
                (self._risk_distribution["high"] + self._risk_distribution["critical"]) / total * 100,
                2
            ),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_analysis_publisher(
    schema: str = "trading",
    alert_on_critical: bool = True,
) -> AnalysisWSSPublisher:
    """Factory function to create Analysis WebSocket publisher."""
    return AnalysisWSSPublisher(
        schema=schema,
        alert_on_critical=alert_on_critical,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_analysis_publisher()
    publisher.start()
    
    try:
        # Simulate various analysis results
        for i in range(10):
            frame_id = f"frame_{i:04d}"
            
            # Rotate through risk levels
            risk_levels = [
                RiskLevel.NONE,
                RiskLevel.LOW,
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.CRITICAL,
            ]
            risk = risk_levels[i % 5]
            
            if risk == RiskLevel.CRITICAL:
                publisher.publish_analysis(
                    frame_id=frame_id,
                    analysis=f"CRITICAL: Margin call imminent on position",
                    risk_level=risk,
                    recommendation=ActionRecommendation.PAUSE,
                    confidence=0.95,
                )
            elif risk == RiskLevel.HIGH:
                publisher.publish_analysis(
                    frame_id=frame_id,
                    analysis=f"High volatility detected in chart pattern",
                    risk_level=risk,
                    recommendation=ActionRecommendation.HOLD,
                    confidence=0.82,
                )
            else:
                publisher.publish_analysis(
                    frame_id=frame_id,
                    analysis=f"Normal trading conditions observed",
                    risk_level=risk,
                    recommendation=ActionRecommendation.CONTINUE,
                    confidence=0.75 + (i % 3) * 0.05,
                )
            
            print(f"Published analysis for {frame_id} (Risk: {risk.value})")
            time.sleep(0.5)
        
        # Print stats
        print("\n--- Stats ---")
        print(json.dumps(publisher.stats, indent=2))
        print("\n--- Risk Summary ---")
        print(json.dumps(publisher.get_risk_summary(), indent=2))
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
