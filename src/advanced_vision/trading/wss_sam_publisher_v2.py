"""MobileSAM WebSocket Publisher v2 for segmentation feed.

Publishes MobileSAM segmentation results to ws://localhost:8000 with topic routing.
Uses typed topic: vision.segmentation.sam

This is the v2 refactor - uses single port (8000) with typed topics instead
of dedicated port (8003) from v1.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

from advanced_vision.wss_client_v2 import (
    WSSPublisherV2,
    ClientConfigV2,
)
from advanced_vision.wss_server_v2 import (
    TransportEnvelope,
    SchemaFamily,
    Topic,
)
from advanced_vision.trading.events import BoundingBox

logger = logging.getLogger(__name__)


class MobileSAMWSSPublisherV2:
    """WebSocket v2 publisher for MobileSAM segmentation results.
    
    Features:
    - Single port connection to ws://localhost:8000
    - Publishes to topic: vision.segmentation.sam
    - Uses TransportEnvelope with event_id, trace_id, etc.
    - Thread-safe queue for segmentation results
    - On-demand publishing (when precision needed)
    - Mask persistence: saves masks to disk, sends path
    
    Usage:
        publisher = MobileSAMWSSPublisherV2(mask_save_dir="/tmp/masks")
        publisher.start()
        
        publisher.publish_segmentation(
            roi_id="roi_001",
            mask=mask_array,
            bbox=bbox,
            frame_id="frame_001",
        )
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8000"
    DEFAULT_TOPIC = Topic.VISION_SEGMENTATION_SAM.value
    BATCH_WINDOW_MS = 100.0
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        mask_save_dir: str | Path = "/tmp/advanced_vision/masks",
        enable_mask_save: bool = True,
        batch_window_ms: float = 50.0,
        min_mask_area: int = 100,
        auth_token: Optional[str] = None,
    ):
        self.uri = uri
        self.mask_save_dir = Path(mask_save_dir)
        self.enable_mask_save = enable_mask_save
        self.batch_window_ms = batch_window_ms
        self.min_mask_area = min_mask_area
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
        self._segmentation_counter = 0
        self._batch_buffer: list[dict[str, Any]] = []
        self._batch_start_time: float = 0.0
        self._trace_id: Optional[str] = None
        
        # Ensure mask save directory exists
        if self.enable_mask_save:
            self.mask_save_dir.mkdir(parents=True, exist_ok=True)
    
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
            logger.warning("MobileSAM v2 publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"MobileSAM v2 publisher started (URI: {self.uri}, Topic: {self.DEFAULT_TOPIC})")
    
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
        logger.info("MobileSAM v2 publisher stopped")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"MobileSAM v2 publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                await self._publisher.connect()
                logger.info(f"MobileSAM v2 publisher connected to {self.uri}")
                
                while not self._stop_event.is_set() and self._publisher.is_connected:
                    await asyncio.sleep(0.05)
                    
                    # Check batch window
                    await self._check_batch_window()
                    
            except Exception as e:
                logger.error(f"MobileSAM v2 publisher error: {e}")
                await asyncio.sleep(2.0)
    
    async def _check_batch_window(self) -> None:
        """Flush batch if window timeout reached."""
        if self._batch_buffer:
            elapsed = (time.time() - self._batch_start_time) * 1000
            if elapsed >= self.batch_window_ms:
                await self._flush_batch()
    
    async def _flush_batch(self) -> None:
        """Send batched segmentations."""
        if not self._batch_buffer:
            return
        
        envelope = TransportEnvelope(
            event_type="segmentation_batch",
            schema_family=SchemaFamily.SEGMENTATION,
            source="sam",
            trace_id=self._trace_id,
            payload={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(self._batch_buffer),
                "masks": self._batch_buffer,
            }
        )
        
        if self._publisher.is_connected:
            await self._publisher.publish(envelope, self.DEFAULT_TOPIC)
        
        self._batch_buffer = []
    
    def publish_segmentation(
        self,
        roi_id: str,
        mask: np.ndarray,
        bbox: BoundingBox,
        frame_id: str,
        confidence: float = 1.0,
    ) -> None:
        """Publish segmentation result to WebSocket.
        
        Args:
            roi_id: Unique ROI identifier
            mask: Binary mask array (H, W) with True for segmented pixels
            bbox: Bounding box of the ROI
            frame_id: Frame identifier
            confidence: Segmentation confidence
        """
        self._segmentation_counter += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Calculate mask area
        if isinstance(mask, np.ndarray):
            mask_area = int(np.sum(mask))
        else:
            mask_area = int(sum(mask))
        
        # Skip small masks
        if mask_area < self.min_mask_area:
            logger.debug(f"Skipping small mask for {roi_id}: area={mask_area}")
            return
        
        # Build mask entry
        mask_entry = {
            "roi_id": roi_id,
            "area": mask_area,
            "bbox": {
                "x": bbox.x,
                "y": bbox.y,
                "w": bbox.width,
                "h": bbox.height,
            },
            "confidence": round(confidence, 4),
            "timestamp": timestamp,
        }
        
        # Build message
        message = {
            "frame_id": frame_id,
            "segmentation_id": f"seg_{self._segmentation_counter:08d}",
            "mask": mask_entry,
        }
        
        # Add to batch
        if not self._batch_buffer:
            self._batch_start_time = time.time()
        self._batch_buffer.append(message)
        
        # Check if we should flush
        batch_elapsed = (time.time() - self._batch_start_time) * 1000
        if batch_elapsed >= self.batch_window_ms or len(self._batch_buffer) >= 5:
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
            "segmentations_published": self._segmentation_counter,
            "batch_buffer_size": len(self._batch_buffer),
            "uri": self.uri,
            "topic": self.DEFAULT_TOPIC,
            **self._publisher.get_client_stats()
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_sam_publisher_v2(
    mask_save_dir: str = "/tmp/advanced_vision/masks",
    auth_token: Optional[str] = None,
) -> MobileSAMWSSPublisherV2:
    """Factory function to create MobileSAM v2 WebSocket publisher."""
    return MobileSAMWSSPublisherV2(
        mask_save_dir=mask_save_dir,
        auth_token=auth_token,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the v2 publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_sam_publisher_v2()
    publisher.start()
    
    import uuid
    publisher.set_trace_id(str(uuid.uuid4()))
    
    try:
        for i in range(20):
            # Create mock mask
            mask = np.random.rand(200, 300) > 0.5
            
            bbox = BoundingBox(
                x=100 + i * 10,
                y=100 + i * 5,
                width=300,
                height=200,
            )
            
            publisher.publish_segmentation(
                roi_id=f"roi_{i % 5}",
                mask=mask,
                bbox=bbox,
                frame_id=f"frame_{i:04d}",
                confidence=0.92,
            )
            
            time.sleep(0.3 + (i % 3) * 0.2)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
        print("Publisher stats:", publisher.stats)
