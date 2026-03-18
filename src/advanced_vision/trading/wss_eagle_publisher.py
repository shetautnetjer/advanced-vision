"""Eagle Vision WebSocket Publisher for classification feed.

Publishes Eagle2-2B classification results to ws://localhost:8004.
Runs after Eagle inference (~300-500ms per image).
Supports classification caching and schema tagging.
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
from typing import Any

import websockets
from PIL.Image import Image
from pydantic import BaseModel

from advanced_vision.trading.events import (
    DetectionSource,
    RiskLevel,
    TradingEventType,
    UIElementType,
)

logger = logging.getLogger(__name__)


class EagleWSSPublisher:
    """WebSocket publisher for Eagle2-2B classification results.
    
    Features:
    - Async WebSocket connection to ws://localhost:8004
    - Thread-safe queue for classification results
    - Optimized for ~300-500ms inference time
    - Classification deduplication/caching
    - Schema tagging: "ui" or "trading"
    
    Usage:
        publisher = EagleWSSPublisher()
        publisher.start()
        
        # After Eagle inference:
        publisher.publish_classification(
            roi_id="roi_001",
            frame_id="frame_001",
            classification="order_ticket",
            confidence=0.95,
        )
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8004"
    DEFAULT_INFERENCE_MS = 400  # Target inference time
    CACHE_SIZE = 100  # Number of recent classifications to cache
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        schema: str = "trading",
        enable_caching: bool = True,
        cache_ttl_seconds: float = 30.0,
        min_confidence: float = 0.5,
    ):
        self.uri = uri
        self.schema = schema
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.min_confidence = min_confidence
        
        # Threading
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        self._loop: asyncio.AbstractEventLoop | None = None
        
        # State
        self._connected = False
        self._classification_counter = 0
        self._inference_times_ms: list[float] = []
        
        # Cache: roi_id + hash -> (timestamp, classification)
        self._classification_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Batch buffer for related classifications
        self._batch_buffer: list[dict[str, Any]] = []
        self._batch_timeout_ms = 100.0
        self._last_batch_time = 0.0
    
    def start(self) -> None:
        """Start the publisher in a background thread."""
        if self._thread is not None:
            logger.warning("Eagle publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"Eagle publisher started (URI: {self.uri})")
    
    def stop(self) -> None:
        """Stop the publisher and close connections."""
        if self._thread is None:
            return
        
        self._stop_event.set()
        
        # Flush remaining batch
        if self._loop and self._batch_buffer:
            asyncio.run_coroutine_threadsafe(
                self._flush_batch(), self._loop
            )
        
        self._thread.join(timeout=5.0)
        self._thread = None
        self._connected = False
        
        avg_inference = (
            sum(self._inference_times_ms) / len(self._inference_times_ms)
            if self._inference_times_ms else 0
        )
        logger.info(f"Eagle publisher stopped (avg inference: {avg_inference:.1f}ms)")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"Eagle publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.uri) as websocket:
                    self._connected = True
                    logger.info(f"Eagle publisher connected to {self.uri}")
                    
                    while not self._stop_event.is_set():
                        try:
                            # Wait for message with timeout
                            message = await asyncio.wait_for(
                                self._queue.get(),
                                timeout=0.05
                            )
                            await websocket.send(json.dumps(message))
                        except asyncio.TimeoutError:
                            # Check batch timeout
                            await self._check_batch_timeout()
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("Eagle WebSocket closed, reconnecting...")
                            break
                        except Exception as e:
                            logger.error(f"Eagle send error: {e}")
                            
            except websockets.exceptions.ConnectionRefusedError:
                logger.warning(f"Eagle WebSocket refused, retrying in 2s...")
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"Eagle WebSocket error: {e}")
                await asyncio.sleep(2.0)
            finally:
                self._connected = False
    
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
        
        batch_message = {
            "type": "classification_batch",
            "schema": self.schema,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(self._batch_buffer),
            "classifications": self._batch_buffer,
        }
        
        try:
            self._queue.put_nowait(batch_message)
        except asyncio.QueueFull:
            logger.warning("Eagle publish queue full, dropping batch")
        
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
                # Expired
                del self._classification_cache[cache_key]
        
        self._cache_misses += 1
        return None
    
    def _cache_classification(self, cache_key: str, classification: dict[str, Any]) -> None:
        """Cache classification result."""
        if not self.enable_caching:
            return
        
        # Clean old entries if cache full
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
        classification: str | TradingEventType,
        confidence: float,
        inference_time_ms: float | None = None,
        reasoning: str | None = None,
        features: dict[str, Any] | None = None,
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
            # Keep last 100 measurements
            if len(self._inference_times_ms) > 100:
                self._inference_times_ms = self._inference_times_ms[-100:]
        
        # Normalize classification
        if isinstance(classification, TradingEventType):
            classification = classification.value
        
        # Build message
        message = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "roi_id": roi_id,
            "classification": classification,
            "confidence": round(confidence, 4),
            "schema": self.schema,
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
    
    def publish_eagle_result(
        self,
        roi_id: str,
        frame_id: str,
        eagle_output: dict[str, Any],
    ) -> bool:
        """Publish raw Eagle model output.
        
        Args:
            roi_id: ROI identifier
            frame_id: Frame identifier
            eagle_output: Raw output from Eagle model
        """
        # Extract classification from Eagle output
        # Eagle typically outputs event type and confidence
        classification = eagle_output.get("event_type", "unknown")
        confidence = eagle_output.get("confidence", 0.0)
        inference_time = eagle_output.get("inference_time_ms")
        
        return self.publish_classification(
            roi_id=roi_id,
            frame_id=frame_id,
            classification=classification,
            confidence=confidence,
            inference_time_ms=inference_time,
        )
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected
    
    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
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
            "connected": self._connected,
            "classifications_published": self._classification_counter,
            "avg_inference_time_ms": round(self.avg_inference_time_ms, 2),
            "queue_size": self.queue_size,
            "batch_buffer_size": len(self._batch_buffer),
            "cache_size": len(self._classification_cache),
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "uri": self.uri,
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_eagle_publisher(
    schema: str = "trading",
    enable_caching: bool = True,
) -> "EagleWSSPublisher":
    """Factory function to create Eagle WebSocket publisher."""
    return EagleWSSPublisher(
        schema=schema,
        enable_caching=enable_caching,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_eagle_publisher()
    publisher.start()
    
    try:
        # Simulate Eagle classifications
        test_classifications = [
            ("order_ticket", 0.92),
            ("chart_update", 0.78),
            ("confirm_dialog", 0.95),
            ("order_ticket", 0.91),  # Should hit cache
            ("warning_dialog", 0.88),
        ]
        
        for i, (event_type, confidence) in enumerate(test_classifications):
            inference_time = 300 + (i % 5) * 50  # 300-500ms variation
            
            published = publisher.publish_classification(
                roi_id=f"roi_{i % 3}",  # Reuse some ROI IDs
                frame_id=f"frame_{i:04d}",
                classification=event_type,
                confidence=confidence,
                inference_time_ms=inference_time,
                reasoning=f"Detected {event_type} based on UI patterns",
            )
            
            status = "PUBLISHED" if published else "CACHED"
            print(f"Frame {i}: {event_type} ({status})")
            
            # Simulate inference time
            time.sleep(inference_time / 1000)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
        print("Publisher stats:", publisher.stats)
