"""YOLO Detector WebSocket Publisher for real-time detection feed.

Publishes YOLO detection results to ws://localhost:8002 at 10-30 FPS.
Supports batching, frame persistence, and schema tagging.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import websockets
from PIL.Image import Image

from advanced_vision.trading.detector import DetectionResult, YOLODetector
from advanced_vision.trading.events import BoundingBox, UIElement

logger = logging.getLogger(__name__)


class YOLOWSSPublisher:
    """WebSocket publisher for YOLO detection results.
    
    Features:
    - Async WebSocket connection to ws://localhost:8002
    - Thread-safe queue for detection results
    - Configurable FPS (10-30)
    - Batching: multiple detections per frame
    - Frame persistence: saves to disk, sends path
    - Schema tagging: "ui" or "trading"
    
    Usage:
        publisher = YOLOWSSPublisher(fps=15, frame_save_dir="/tmp/frames")
        publisher.start()
        
        # In detection loop:
        publisher.publish_detection(result, frame_image, frame_id="frame_001")
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8002"
    DEFAULT_FPS = 15
    MIN_FPS = 10
    MAX_FPS = 30
    BATCH_SIZE = 10  # Max detections per message
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        fps: int = DEFAULT_FPS,
        frame_save_dir: str | Path = "/tmp/advanced_vision/frames",
        schema: str = "trading",
        enable_frame_save: bool = True,
        batch_timeout_ms: float = 50.0,
    ):
        self.uri = uri
        self.fps = max(self.MIN_FPS, min(self.MAX_FPS, fps))
        self.frame_interval = 1.0 / self.fps
        self.frame_save_dir = Path(frame_save_dir)
        self.schema = schema
        self.enable_frame_save = enable_frame_save
        self.batch_timeout_ms = batch_timeout_ms
        
        # Threading
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._loop: asyncio.AbstractEventLoop | None = None
        
        # State
        self._connected = False
        self._frame_counter = 0
        self._batch_buffer: list[dict[str, Any]] = []
        self._last_batch_time = 0.0
        
        # Ensure frame save directory exists
        if self.enable_frame_save:
            self.frame_save_dir.mkdir(parents=True, exist_ok=True)
    
    def start(self) -> None:
        """Start the publisher in a background thread."""
        if self._thread is not None:
            logger.warning("YOLO publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"YOLO publisher started (FPS: {self.fps}, URI: {self.uri})")
    
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
        logger.info("YOLO publisher stopped")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"YOLO publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.uri) as websocket:
                    self._connected = True
                    logger.info(f"YOLO publisher connected to {self.uri}")
                    
                    while not self._stop_event.is_set():
                        try:
                            # Wait for message with timeout
                            message = await asyncio.wait_for(
                                self._queue.get(),
                                timeout=0.1
                            )
                            await websocket.send(json.dumps(message))
                        except asyncio.TimeoutError:
                            # Check batch timeout
                            await self._check_batch_timeout()
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("YOLO WebSocket closed, reconnecting...")
                            break
                        except Exception as e:
                            logger.error(f"YOLO send error: {e}")
                            
            except websockets.exceptions.ConnectionRefusedError:
                logger.warning(f"YOLO WebSocket refused, retrying in 2s...")
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"YOLO WebSocket error: {e}")
                await asyncio.sleep(2.0)
            finally:
                self._connected = False
    
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
        
        batch_message = {
            "type": "detection_batch",
            "schema": self.schema,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(self._batch_buffer),
            "detections": self._batch_buffer,
        }
        
        try:
            self._queue.put_nowait(batch_message)
        except asyncio.QueueFull:
            logger.warning("YOLO publish queue full, dropping batch")
        
        self._batch_buffer = []
    
    def publish_detection(
        self,
        result: DetectionResult,
        frame_image: Image | None = None,
        frame_id: str | None = None,
    ) -> None:
        """Publish detection result to WebSocket.
        
        Args:
            result: YOLO detection result
            frame_image: Optional frame image to save
            frame_id: Optional frame identifier
        """
        self._frame_counter += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if frame_id is None:
            frame_id = f"frame_{self._frame_counter:08d}"
        
        # Save frame if enabled
        frame_path: str | None = None
        if self.enable_frame_save and frame_image is not None:
            frame_path = self._save_frame(frame_image, frame_id)
        
        # Build detection boxes
        boxes = []
        for elem in result.elements:
            boxes.append({
                "x": elem.bbox.x,
                "y": elem.bbox.y,
                "w": elem.bbox.width,
                "h": elem.bbox.height,
                "class": elem.element_type.value,
                "confidence": round(elem.confidence, 4),
                "element_id": elem.element_id,
                "text": elem.text_content,
            })
        
        # Build message
        message = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "boxes": boxes,
            "inference_time_ms": round(result.inference_time_ms, 2),
            "source": result.source.value,
            "schema": self.schema,
        }
        
        if frame_path:
            message["frame_path"] = frame_path
        
        # Add to batch
        self._batch_buffer.append(message)
        self._last_batch_time = time.time()
        
        # Flush if batch full
        if len(self._batch_buffer) >= self.BATCH_SIZE:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._flush_batch(), self._loop
                )
    
    def _save_frame(self, frame: Image, frame_id: str) -> str:
        """Save frame to disk and return path."""
        filename = f"{frame_id}_{int(time.time() * 1000)}.jpg"
        filepath = self.frame_save_dir / filename
        
        try:
            # Resize if too large for network efficiency
            max_dim = 1920
            if frame.width > max_dim or frame.height > max_dim:
                ratio = max_dim / max(frame.width, frame.height)
                new_size = (int(frame.width * ratio), int(frame.height * ratio))
                frame = frame.resize(new_size, Image.Resampling.LANCZOS)
            
            frame.save(filepath, "JPEG", quality=85)
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return ""
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected
    
    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        return {
            "connected": self._connected,
            "frames_published": self._frame_counter,
            "queue_size": self.queue_size,
            "batch_buffer_size": len(self._batch_buffer),
            "fps_configured": self.fps,
            "uri": self.uri,
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_yolo_publisher(
    fps: int = 15,
    frame_save_dir: str = "/tmp/advanced_vision/frames",
    schema: str = "trading",
) -> YOLOWSSPublisher:
    """Factory function to create YOLO WebSocket publisher."""
    return YOLOWSSPublisher(
        fps=fps,
        frame_save_dir=frame_save_dir,
        schema=schema,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_yolo_publisher(fps=10)
    publisher.start()
    
    # Simulate detections
    from advanced_vision.trading.events import UIElementType, DetectionSource
    
    try:
        for i in range(100):
            # Create mock detection
            elem = UIElement(
                element_id=f"elem_{i}",
                element_type=UIElementType.CHART_PANEL,
                bbox=BoundingBox(x=100, y=100, width=400, height=300),
                confidence=0.85,
                source=DetectionSource.TRIPWIRE,
            )
            
            result = DetectionResult(
                elements=[elem],
                inference_time_ms=15.5,
                frame_timestamp=datetime.now(timezone.utc).isoformat(),
            )
            
            publisher.publish_detection(result, frame_id=f"frame_{i:04d}")
            time.sleep(0.1)  # 10 FPS
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
        print("Publisher stats:", publisher.stats)
