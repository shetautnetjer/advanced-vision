"""Chronos/Kimi Analysis Results WebSocket Publisher v2.

Publishes analysis results from Chronos/Kimi to ws://localhost:8000 with topic routing.
Uses typed topic: vision.analysis.qwen

This is the v2 refactor - uses single port (8000) with typed topics instead
of dedicated port (8005) from v1.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from advanced_vision.wss_client_v2 import (
    WSSPublisherV2,
    ClientConfigV2,
)
from advanced_vision.wss_server_v2 import (
    TransportEnvelope,
    SchemaFamily,
    Topic,
)
from advanced_vision.trading.events import (
    RiskLevel,
    ActionRecommendation,
)

logger = logging.getLogger(__name__)


class AnalysisWSSPublisherV2:
    """WebSocket v2 publisher for Chronos/Kimi analysis results.
    
    Features:
    - Single port connection to ws://localhost:8000
    - Publishes to topic: vision.analysis.qwen
    - Uses TransportEnvelope with event_id, trace_id, etc.
    - Thread-safe queue for analysis results
    - Publishes risk levels, recommendations, and trading signals
    - Supports priority queue for high-risk events
    
    Usage:
        publisher = AnalysisWSSPublisherV2()
        publisher.start()
        
        publisher.publish_analysis(
            frame_id="frame_001",
            analysis="Potential margin call detected",
            risk_level=RiskLevel.HIGH,
            recommendation=ActionRecommendation.PAUSE,
            confidence=0.85,
        )
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8000"
    DEFAULT_TOPIC = Topic.VISION_ANALYSIS_QWEN.value
    HIGH_PRIORITY_RISKS = {RiskLevel.HIGH, RiskLevel.CRITICAL}
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        enable_priority_queue: bool = True,
        alert_on_critical: bool = True,
        auth_token: Optional[str] = None,
    ):
        self.uri = uri
        self.enable_priority_queue = enable_priority_queue
        self.alert_on_critical = alert_on_critical
        self.auth_token = auth_token
        
        # Create v2 publisher
        host, port = self._parse_uri(uri)
        config = ClientConfigV2(
            host=host,
            port=port,
            auth_token=auth_token,
            auto_reconnect=True,
        )
        self._publisher = WSSPublisherV2(config, default_topic=self.DEFAULT_TOPIC)
        
        # Threading
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        
        # State
        self._analysis_counter = 0
        self._critical_alerts = 0
        self._high_risk_count = 0
        self._trace_id: Optional[str] = None
        
        # Stats tracking
        self._risk_distribution: dict[str, int] = {
            "none": 0, "low": 0, "medium": 0, "high": 0, "critical": 0
        }
        self._recommendation_distribution: dict[str, int] = {}
    
    def _parse_uri(self, uri: str) -> tuple[str, int]:
        """Parse WebSocket URI into host and port."""
        uri = uri.replace("ws://", "").replace("wss://", "")
        parts = uri.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8000
        return host, port
    
    def start(self) -> None:
        """Start the publisher in a background thread."""
        if self._thread is not None:
            logger.warning("Analysis v2 publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"Analysis v2 publisher started (URI: {self.uri}, Topic: {self.DEFAULT_TOPIC})")
    
    def stop(self) -> None:
        """Stop the publisher and close connections."""
        if self._thread is None:
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        logger.info("Analysis v2 publisher stopped")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"Analysis v2 publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                await self._publisher.connect()
                logger.info(f"Analysis v2 publisher connected to {self.uri}")
                
                while not self._stop_event.is_set() and self._publisher.is_connected:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Analysis v2 publisher error: {e}")
                await asyncio.sleep(2.0)
    
    def _update_stats(self, risk_level: RiskLevel, recommendation: ActionRecommendation) -> None:
        """Update statistics."""
        self._risk_distribution[risk_level.value] += 1
        
        rec_key = recommendation.value
        self._recommendation_distribution[rec_key] = (
            self._recommendation_distribution.get(rec_key, 0) + 1
        )
        
        if risk_level in self.HIGH_PRIORITY_RISKS:
            self._high_risk_count += 1
    
    async def _publish_envelope(self, envelope: TransportEnvelope, priority: bool = False) -> None:
        """Publish envelope, optionally with priority."""
        if self._publisher.is_connected:
            await self._publisher.publish(envelope, self.DEFAULT_TOPIC)
    
    def publish_analysis(
        self,
        frame_id: str,
        analysis: str,
        risk_level: RiskLevel | str,
        recommendation: ActionRecommendation | str,
        confidence: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
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
        
        payload = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "analysis": analysis,
            "risk_level": risk_level,
            "recommendation": recommendation,
        }
        
        if confidence is not None:
            payload["confidence"] = round(confidence, 4)
        if metadata:
            payload["metadata"] = metadata
        
        # Critical alert handling
        if self.alert_on_critical and risk_level == RiskLevel.CRITICAL.value:
            self._critical_alerts += 1
            payload["alert"] = True
            payload["alert_type"] = "critical"
            logger.critical(f"CRITICAL ALERT: Frame {frame_id} - {analysis[:100]}")
        
        envelope = TransportEnvelope(
            event_type="analysis",
            schema_family=SchemaFamily.ANALYSIS,
            source="qwen",
            frame_ref=frame_id,
            trace_id=self._trace_id,
            payload=payload
        )
        
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._publish_envelope(envelope, priority=is_priority),
                self._loop
            )
    
    def publish_trading_signal(
        self,
        frame_id: str,
        signal_type: str,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        price: Optional[float] = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        analysis: str = "",
    ) -> None:
        """Publish trading signal.
        
        Args:
            frame_id: Frame identifier
            signal_type: Type of trading signal
            symbol: Trading symbol (e.g., "AAPL")
            direction: Signal direction (buy, sell, hold)
            price: Current/target price
            risk_level: Associated risk
            analysis: Signal analysis
        """
        metadata = {
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
        timestamp = datetime.now(timezone.utc).isoformat()
        
        envelope = TransportEnvelope(
            event_type="error",
            schema_family=SchemaFamily.SYSTEM,
            source="qwen",
            frame_ref=frame_id,
            trace_id=self._trace_id,
            payload={
                "timestamp": timestamp,
                "frame_id": frame_id,
                "error_type": error_type,
                "error_message": error_message,
                "risk_level": RiskLevel.HIGH.value,
                "recommendation": ActionRecommendation.HOLD.value,
            }
        )
        
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._publish_envelope(envelope, priority=True),
                self._loop
            )
        
        logger.error(f"Analysis error for {frame_id}: {error_message}")
    
    def set_trace_id(self, trace_id: str) -> None:
        """Set trace ID for distributed tracing."""
        self._trace_id = trace_id
        self._publisher.set_trace_id(trace_id)
    
    def clear_trace_id(self) -> None:
        """Clear trace ID."""
        self._trace_id = None
        self._publisher.clear_trace_id()
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._publisher.is_connected
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        return {
            "connected": self.is_connected,
            "analyses_published": self._analysis_counter,
            "critical_alerts": self._critical_alerts,
            "high_risk_count": self._high_risk_count,
            "risk_distribution": self._risk_distribution.copy(),
            "recommendation_distribution": self._recommendation_distribution.copy(),
            "uri": self.uri,
            "topic": self.DEFAULT_TOPIC,
            **self._publisher.get_client_stats()
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

def create_analysis_publisher_v2(
    alert_on_critical: bool = True,
    auth_token: Optional[str] = None,
) -> AnalysisWSSPublisherV2:
    """Factory function to create Analysis v2 WebSocket publisher."""
    return AnalysisWSSPublisherV2(
        alert_on_critical=alert_on_critical,
        auth_token=auth_token,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the v2 publisher
    import time
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_analysis_publisher_v2()
    publisher.start()
    
    import uuid
    publisher.set_trace_id(str(uuid.uuid4()))
    
    try:
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
        
        print("\n--- Stats ---")
        print(publisher.stats)
        print("\n--- Risk Summary ---")
        print(publisher.get_risk_summary())
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
