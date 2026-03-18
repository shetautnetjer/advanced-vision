"""YOLO Detector WebSocket Publisher v2 for real-time detection feed.

Publishes YOLO detection results to ws://localhost:8000 with topic routing.
Uses typed topic: vision.detection.yolo

This is the v2 refactor - uses single port (8000) with typed topics instead
of dedicated port (8002) from v1.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import websockets

from advanced_vision.wss_client_v2 import (
    WSSPublisherV2,
    ClientConfigV2,
    create_publisher_v2,
)
from advanced_vision.wss_server_v2 import (
    TransportEnvelope,
    SchemaFamily,
    Topic,
)

logger = logging.getLogger(__name__)


class YOLOWSSPublisherV2:
    """WebSocket v2 publisher for YOLO detection results.
    
    Features:
    - Single port connection to ws://localhost:8000
    - Publishes to topic: vision.detection.yolo
    - Uses TransportEnvelope with event_id, trace_id, etc.
    - Thread-safe queue for detection results
    - Configurable FPS (10-30)
    - Batching: multiple detections per frame
    - Frame persistence: saves to disk, sends path
    
    Usage:
        publisher = YOLOWSSPublisherV2(fps=15, frame_save_dir="/tmp/frames")
        publisher.start()
        
        # In detection loop:
        publisher.publish_detection(result, frame_image, frame_id="frame_001")
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8000"
    DEFAULT_TOPIC = Topic.VISION_DETECTION_YOLO.value
    DEFAULT_FPS = 15
    MIN_FPS = 10
    MAX_FPS = 30
    BATCH_SIZE = 10  # Max detections per message
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        fps: int = DEFAULT_FPS,
        frame_save_dir: str | Path = "/tmp/advanced_vision/frames",
        enable_frame_save: bool = True,
        batch_timeout_ms: float = 50.0,
        auth_token: Optional[str] = None,
    ):
        self.uri = uri
        self.fps = max(self.MIN_FPS, min(self.MAX_FPS, fps))
        self.frame_interval = 1.0 / self.fps
        self.frame_save_dir = Path(frame_save_dir)
        self.enable_frame_save = enable_frame_save
        self.batch_timeout_ms = batch_timeout_ms
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
        self._frame_counter = 0
        self._batch_buffer: list[dict[str, Any]] = []
        self._last_batch_time = 0.0
        self._trace_id: Optional[str] = None
        
        # Ensure frame save directory exists
        if self.enable_frame_save:
            self.frame_save_dir.mkdir(parents=True, exist_ok=True)
    
    def _parse_uri(self, uri: str) -> tuple[str, int]:
        """Parse WebSocket URI into host and port."""
        # Handle ws://host:port format
        uri = uri.replace("ws://", "").replace("wss://", "")
        parts = uri.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8000
        return host, port
    
    def start(self) -> None:
        """Start the publisher in a background thread."""
        if self._thread is not None:
            logger.warning("YOLO v2 publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"YOLO v2 publisher started (FPS: {self.fps}, URI: {self.uri}, Topic: {self.DEFAULT_TOPIC})")
    
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
        logger.info("YOLO v2 publisher stopped")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"YOLO v2 publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                await self._publisher.connect()
                logger.info(f"YOLO v2 publisher connected to {self.uri}")
                
                while not self._stop_event.is_set() and self._publisher.is_connected:
                    await asyncio.sleep(0.1)
                    
                    # Check batch timeout
                    await self._check_batch_timeout()
                    
            except Exception as e:
                logger.error(f"YOLO v2 publisher error: {e}")
                await asyncio.sleep(2.0)
    
    async def _check_batch_timeout(self) -> None:
        """Flush batch if timeout reached."""
        if self._batch_buffer:
            elapsed = (time.time() - self._last_batch_time) * 1000
            if elapsed >= self.batch_timeout_ms:
                await self._flush_batch()
    
    async def _flush_batch(self) -> None:
        """Send batched detections."""
        if not self._batch_buffer:
            return
        
        envelope = TransportEnvelope(
            event_type="detection_batch",
            schema_family=SchemaFamily.DETECTION,
            source="yolo",
            trace_id=self._trace_id,
            payload={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(self._batch_buffer),
                "detections": self._batch_buffer,
            }
        )
        
        if self._publisher.is_connected:
            await self._publisher.publish(envelope, self.DEFAULT_TOPIC)
        
        self._batch_buffer = []
    
    def publish_detection(
        self,
        boxes: list[dict],
        frame_id: str | None = None,
        inference_time_ms: float = 0.0,
        **kwargs
    ) -> None:
        """Publish detection result to WebSocket.
        
        Args:
            boxes: List of detection boxes with keys: x, y, w, h, class, confidence
            frame_id: Optional frame identifier
            inference_time_ms: Inference time in milliseconds
            **kwargs: Additional metadata
        """
        self._frame_counter += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if frame_id is None:
            frame_id = f"frame_{self._frame_counter:08d}"
        
        # Build message
        message = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "boxes": boxes,
            "inference_time_ms": round(inference_time_ms, 2),
            **kwargs
        }
        
        # Add to batch
        self._batch_buffer.append(message)
        self._last_batch_time = time.time()
        
        # Flush if batch full
        if len(self._batch_buffer) >= self.BATCH_SIZE:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._flush_batch(), self._loop
                )
    
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
            "frames_published": self._frame_counter,
            "batch_buffer_size": len(self._batch_buffer),
            "fps_configured": self.fps,
            "uri": self.uri,
            "topic": self.DEFAULT_TOPIC,
            **self._publisher.get_client_stats()
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_yolo_publisher_v2(
    fps: int = 15,
    frame_save_dir: str = "/tmp/advanced_vision/frames",
    auth_token: Optional[str] = None,
) -> YOLOWSSPublisherV2:
    """Factory function to create YOLO v2 WebSocket publisher."""
    return YOLOWSSPublisherV2(
        fps=fps,
        frame_save_dir=frame_save_dir,
        auth_token=auth_token,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the v2 publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_yolo_publisher_v2(fps=10)
    publisher.start()
    
    # Set a trace ID for this batch
    import uuid
    publisher.set_trace_id(str(uuid.uuid4()))
    
    try:
        for i in range(100):
            # Simulate detections
            boxes = [{
                "x": 100 + i * 2,
                "y": 100 + i,
                "w": 400,
                "h": 300,
                "class": "chart_panel",
                "confidence": 0.95 - (i % 5) * 0.01,
            }]
            
            publisher.publish_detection(
                boxes=boxes,
                frame_id=f"frame_{i:04d}",
                inference_time_ms=15.5
            )
            
            time.sleep(0.1)  # 10 FPS
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
        print("Publisher stats:", publisher.stats)
