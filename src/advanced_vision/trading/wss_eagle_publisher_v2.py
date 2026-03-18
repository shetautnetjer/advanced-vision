"""Eagle Vision WebSocket Publisher v2 for classification feed.

Publishes Eagle2-2B classification results to ws://localhost:8000 with topic routing.
Uses typed topic: vision.classification.eagle

This is the v2 refactor - uses single port (8000) with typed topics instead
of dedicated port (8004) from v1.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
import time
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

logger = logging.getLogger(__name__)


class EagleWSSPublisherV2:
    """WebSocket v2 publisher for Eagle2-2B classification results.
    
    Features:
    - Single port connection to ws://localhost:8000
    - Publishes to topic: vision.classification.eagle
    - Uses TransportEnvelope with event_id, trace_id, etc.
    - Thread-safe queue for classification results
    - Classification deduplication/caching
    
    Usage:
        publisher = EagleWSSPublisherV2()
        publisher.start()
        
        publisher.publish_classification(
            roi_id="roi_001",
            frame_id="frame_001",
            classification="order_ticket",
            confidence=0.95,
        )
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8000"
    DEFAULT_TOPIC = Topic.VISION_CLASSIFICATION_EAGLE.value
    CACHE_SIZE = 100
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        enable_caching: bool = True,
        cache_ttl_seconds: float = 30.0,
        min_confidence: float = 0.5,
        auth_token: Optional[str] = None,
    ):
        self.uri = uri
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.min_confidence = min_confidence
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
        self._classification_counter = 0
        self._inference_times_ms: list[float] = []
        self._classification_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._batch_buffer: list[dict[str, Any]] = []
        self._batch_timeout_ms = 100.0
        self._last_batch_time: float = 0.0
        self._trace_id: Optional[str] = None
    
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
            logger.warning("Eagle v2 publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"Eagle v2 publisher started (URI: {self.uri}, Topic: {self.DEFAULT_TOPIC})")
    
    def stop(self) -> None:
        """Stop the publisher and close connections."""
        if self._thread is None:
            return
        
        self._stop_event.set()
        
        # Flush remaining batch
        if self._loop and self._batch_buffer:
            future = asyncio.run_coroutine_threadsafe(
                self._flush_batch(), self._loop
            )
            try:
                future.result(timeout=5.0)
            except Exception:
                pass
        
        self._thread.join(timeout=5.0)
        self._thread = None
        
        avg_inference = (
            sum(self._inference_times_ms) / len(self._inference_times_ms)
            if self._inference_times_ms else 0
        )
        logger.info(f"Eagle v2 publisher stopped (avg inference: {avg_inference:.1f}ms)")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"Eagle v2 publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                await self._publisher.connect()
                logger.info(f"Eagle v2 publisher connected to {self.uri}")
                
                while not self._stop_event.is_set() and self._publisher.is_connected:
                    await asyncio.sleep(0.05)
                    
                    # Check batch timeout
                    await self._check_batch_timeout()
                    
            except Exception as e:
                logger.error(f"Eagle v2 publisher error: {e}")
                await asyncio.sleep(2.0)
    
    async def _check_batch_timeout(self) -> None:
        """Flush batch if timeout reached."""
        if self._batch_buffer:
            elapsed = (time.time() - self._last_batch_time) * 1000
            if elapsed >= self._batch_timeout_ms:
                await self._flush_batch()
    
    async def _flush_batch(self) -> None:
        """Send batched classifications."""
        if not self._batch_buffer:
            return
        
        envelope = TransportEnvelope(
            event_type="classification_batch",
            schema_family=SchemaFamily.CLASSIFICATION,
            source="eagle",
            trace_id=self._trace_id,
            payload={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(self._batch_buffer),
                "classifications": self._batch_buffer,
            }
        )
        
        if self._publisher.is_connected:
            await self._publisher.publish(envelope, self.DEFAULT_TOPIC)
        
        self._batch_buffer = []
    
    def _compute_cache_key(self, roi_id: str, features: dict[str, Any] | None = None) -> str:
        """Compute cache key for classification."""
        key_data = f"{roi_id}:{json.dumps(features, sort_keys=True) if features else ''}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_classification(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached classification if still valid."""
        if not self.enable_caching:
            return None
        
        if cache_key in self._classification_cache:
            timestamp, classification = self._classification_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl_seconds:
                self._cache_hits += 1
                return classification
            else:
                del self._classification_cache[cache_key]
        
        self._cache_misses += 1
        return None
    
    def _cache_classification(self, cache_key: str, classification: dict[str, Any]) -> None:
        """Cache classification result."""
        if not self.enable_caching:
            return
        
        if len(self._classification_cache) >= self.CACHE_SIZE:
            oldest_key = min(
                self._classification_cache.keys(),
                key=lambda k: self._classification_cache[k][0]
            )
            del self._classification_cache[oldest_key]
        
        self._classification_cache[cache_key] = (time.time(), classification)
    
    def publish_classification(
        self,
        roi_id: str,
        frame_id: str,
        classification: str,
        confidence: float,
        inference_time_ms: Optional[float] = None,
        reasoning: Optional[str] = None,
        features: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Publish classification result to WebSocket.
        
        Args:
            roi_id: ROI identifier that was classified
            frame_id: Frame identifier
            classification: Event type classification
            confidence: Classification confidence (0-1)
            inference_time_ms: Time taken for inference
            reasoning: Optional reasoning text
            features: Optional feature dict for caching
            
        Returns:
            True if published, False if cached/duplicated
        """
        # Check confidence threshold
        if confidence < self.min_confidence:
            logger.debug(f"Skipping low confidence classification: {confidence}")
            return False
        
        # Check cache
        cache_key = self._compute_cache_key(roi_id, features)
        cached = self._get_cached_classification(cache_key)
        if cached:
            logger.debug(f"Using cached classification for {roi_id}")
            return False
        
        self._classification_counter += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Track inference time
        if inference_time_ms:
            self._inference_times_ms.append(inference_time_ms)
            if len(self._inference_times_ms) > 100:
                self._inference_times_ms = self._inference_times_ms[-100:]
        
        # Build message
        message = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "roi_id": roi_id,
            "classification": classification,
            "confidence": round(confidence, 4),
        }
        
        if inference_time_ms:
            message["inference_time_ms"] = round(inference_time_ms, 2)
        if reasoning:
            message["reasoning"] = reasoning
        
        # Cache the classification
        self._cache_classification(cache_key, message)
        
        # Add to batch
        if not self._batch_buffer:
            self._last_batch_time = time.time()
        self._batch_buffer.append(message)
        
        # Flush if batch has multiple items or timeout
        batch_elapsed = (time.time() - self._last_batch_time) * 1000
        if len(self._batch_buffer) >= 3 or batch_elapsed >= self._batch_timeout_ms:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._flush_batch(), self._loop
                )
        
        return True
    
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
    def avg_inference_time_ms(self) -> float:
        """Get average inference time."""
        if not self._inference_times_ms:
            return 0.0
        return sum(self._inference_times_ms) / len(self._inference_times_ms)
    
    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        return {
            "connected": self.is_connected,
            "classifications_published": self._classification_counter,
            "avg_inference_time_ms": round(self.avg_inference_time_ms, 2),
            "batch_buffer_size": len(self._batch_buffer),
            "cache_size": len(self._classification_cache),
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "uri": self.uri,
            "topic": self.DEFAULT_TOPIC,
            **self._publisher.get_client_stats()
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_eagle_publisher_v2(
    enable_caching: bool = True,
    auth_token: Optional[str] = None,
) -> EagleWSSPublisherV2:
    """Factory function to create Eagle v2 WebSocket publisher."""
    return EagleWSSPublisherV2(
        enable_caching=enable_caching,
        auth_token=auth_token,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the v2 publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_eagle_publisher_v2()
    publisher.start()
    
    import uuid
    publisher.set_trace_id(str(uuid.uuid4()))
    
    try:
        test_classifications = [
            ("order_ticket", 0.92),
            ("chart_update", 0.78),
            ("confirm_dialog", 0.95),
            ("order_ticket", 0.91),  # Should hit cache
            ("warning_dialog", 0.88),
        ]
        
        for i, (event_type, confidence) in enumerate(test_classifications):
            inference_time = 300 + (i % 5) * 50
            
            published = publisher.publish_classification(
                roi_id=f"roi_{i % 3}",
                frame_id=f"frame_{i:04d}",
                classification=event_type,
                confidence=confidence,
                inference_time_ms=inference_time,
                reasoning=f"Detected {event_type} based on UI patterns",
            )
            
            status = "PUBLISHED" if published else "CACHED"
            print(f"Frame {i}: {event_type} ({status})")
            
            time.sleep(inference_time / 1000)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
        print("Publisher stats:", publisher.stats)
