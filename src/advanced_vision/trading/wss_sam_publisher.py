"""MobileSAM WebSocket Publisher for segmentation feed.

Publishes MobileSAM segmentation results to ws://localhost:8003 on-demand.
Supports mask persistence, ROI tracking, and schema tagging.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import websockets
from PIL.Image import Image

from advanced_vision.trading.events import ROI, BoundingBox

logger = logging.getLogger(__name__)


class MobileSAMWSSPublisher:
    """WebSocket publisher for MobileSAM segmentation results.
    
    Features:
    - Async WebSocket connection to ws://localhost:8003
    - Thread-safe queue for segmentation results
    - On-demand publishing (when precision needed)
    - Mask persistence: saves masks to disk, sends path
    - ROI tracking with unique IDs
    - Schema tagging: "ui" or "trading"
    
    Usage:
        publisher = MobileSAMWSSPublisher(mask_save_dir="/tmp/masks")
        publisher.start()
        
        # When precision segmentation needed:
        publisher.publish_segmentation(
            roi_id="roi_001",
            mask=mask_array,
            bbox=bbox,
            frame_id="frame_001",
            frame_image=frame,
        )
        
        publisher.stop()
    """
    
    DEFAULT_URI = "ws://localhost:8003"
    BATCH_TIMEOUT_MS = 100.0  # Batch timeout for grouping related segmentations
    
    def __init__(
        self,
        uri: str = DEFAULT_URI,
        mask_save_dir: str | Path = "/tmp/advanced_vision/masks",
        schema: str = "trading",
        enable_mask_save: bool = True,
        batch_window_ms: float = 50.0,
        min_mask_area: int = 100,  # Minimum mask area to publish
    ):
        self.uri = uri
        self.mask_save_dir = Path(mask_save_dir)
        self.schema = schema
        self.enable_mask_save = enable_mask_save
        self.batch_window_ms = batch_window_ms
        self.min_mask_area = min_mask_area
        
        # Threading
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        self._loop: asyncio.AbstractEventLoop | None = None
        
        # State
        self._connected = False
        self._segmentation_counter = 0
        self._batch_buffer: list[dict[str, Any]] = []
        self._batch_start_time: float = 0.0
        self._roi_history: dict[str, dict[str, Any]] = {}  # Track ROI changes
        
        # Ensure mask save directory exists
        if self.enable_mask_save:
            self.mask_save_dir.mkdir(parents=True, exist_ok=True)
    
    def start(self) -> None:
        """Start the publisher in a background thread."""
        if self._thread is not None:
            logger.warning("MobileSAM publisher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info(f"MobileSAM publisher started (URI: {self.uri})")
    
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
        logger.info("MobileSAM publisher stopped")
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._publish_loop())
        except Exception as e:
            logger.error(f"MobileSAM publisher loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _publish_loop(self) -> None:
        """Main WebSocket publish loop with reconnection."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.uri) as websocket:
                    self._connected = True
                    logger.info(f"MobileSAM publisher connected to {self.uri}")
                    
                    while not self._stop_event.is_set():
                        try:
                            # Wait for message with timeout
                            message = await asyncio.wait_for(
                                self._queue.get(),
                                timeout=0.05
                            )
                            await websocket.send(json.dumps(message))
                        except asyncio.TimeoutError:
                            # Check batch window
                            await self._check_batch_window()
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("MobileSAM WebSocket closed, reconnecting...")
                            break
                        except Exception as e:
                            logger.error(f"MobileSAM send error: {e}")
                            
            except websockets.exceptions.ConnectionRefusedError:
                logger.warning(f"MobileSAM WebSocket refused, retrying in 2s...")
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"MobileSAM WebSocket error: {e}")
                await asyncio.sleep(2.0)
            finally:
                self._connected = False
    
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
        
        batch_message = {
            "type": "segmentation_batch",
            "schema": self.schema,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(self._batch_buffer),
            "masks": self._batch_buffer,
        }
        
        try:
            self._queue.put_nowait(batch_message)
        except asyncio.QueueFull:
            logger.warning("MobileSAM publish queue full, dropping batch")
        
        self._batch_buffer = []
    
    def publish_segmentation(
        self,
        roi_id: str,
        mask: np.ndarray,
        bbox: BoundingBox,
        frame_id: str,
        frame_image: Image | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Publish segmentation result to WebSocket.
        
        Args:
            roi_id: Unique ROI identifier
            mask: Binary mask array (H, W) with True for segmented pixels
            bbox: Bounding box of the ROI
            frame_id: Frame identifier
            frame_image: Optional frame image for context
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
        
        # Save mask if enabled
        mask_path: str | None = None
        if self.enable_mask_save:
            mask_path = self._save_mask(mask, roi_id, frame_id)
        
        # Save context frame if provided
        frame_path: str | None = None
        if frame_image is not None and self.enable_mask_save:
            frame_path = self._save_frame(frame_image, frame_id)
        
        # Build mask entry
        mask_entry = {
            "roi_id": roi_id,
            "mask_path": mask_path,
            "area": mask_area,
            "bbox": {
                "x": bbox.x,
                "y": bbox.y,
                "w": bbox.width,
                "h": bbox.height,
            },
            "confidence": round(confidence, 4),
        }
        
        # Build message
        message = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "segmentation_id": f"seg_{self._segmentation_counter:08d}",
            "masks": [mask_entry],
            "schema": self.schema,
        }
        
        if frame_path:
            message["frame_path"] = frame_path
        
        # Track ROI history
        self._roi_history[roi_id] = {
            "last_seen": timestamp,
            "area": mask_area,
            "frame_id": frame_id,
        }
        
        # Add to batch
        if not self._batch_buffer:
            self._batch_start_time = time.time()
        self._batch_buffer.append(message)
        
        # Check if we should flush (batch window or size)
        batch_elapsed = (time.time() - self._batch_start_time) * 1000
        if batch_elapsed >= self.batch_window_ms or len(self._batch_buffer) >= 5:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._flush_batch(), self._loop
                )
    
    def publish_roi_segmentation(
        self,
        roi: ROI,
        frame_id: str,
        frame_image: Image | None = None,
    ) -> None:
        """Publish segmentation from ROI object.
        
        Args:
            roi: ROI object with segmentation data
            frame_id: Frame identifier
            frame_image: Optional frame image
        """
        # Convert segmentation mask points to numpy array if needed
        if roi.segmentation_mask:
            # Create binary mask from polygon points
            # This is a simplified version - production would use proper polygon rasterization
            mask = np.zeros((roi.bbox.height, roi.bbox.width), dtype=bool)
            for px, py in roi.segmentation_mask:
                rx = px - roi.bbox.x
                ry = py - roi.bbox.y
                if 0 <= rx < roi.bbox.width and 0 <= ry < roi.bbox.height:
                    mask[ry, rx] = True
        else:
            # Full bbox mask
            mask = np.ones((roi.bbox.height, roi.bbox.width), dtype=bool)
        
        self.publish_segmentation(
            roi_id=roi.roi_id,
            mask=mask,
            bbox=roi.bbox,
            frame_id=frame_id,
            frame_image=frame_image,
            confidence=roi.confidence,
        )
    
    def _save_mask(self, mask: np.ndarray, roi_id: str, frame_id: str) -> str:
        """Save mask to disk and return path."""
        filename = f"{frame_id}_{roi_id}_mask_{int(time.time() * 1000)}.png"
        filepath = self.mask_save_dir / filename
        
        try:
            # Convert bool/np array to uint8 image
            if isinstance(mask, np.ndarray):
                mask_img = (mask.astype(np.uint8) * 255)
            else:
                mask_img = np.array(mask, dtype=np.uint8) * 255
            
            # Save as PNG for lossless mask storage
            from PIL import Image as PILImage
            img = PILImage.fromarray(mask_img, mode='L')
            img.save(filepath, "PNG")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save mask: {e}")
            return ""
    
    def _save_frame(self, frame: Image, frame_id: str) -> str:
        """Save context frame to disk."""
        filename = f"{frame_id}_context_{int(time.time() * 1000)}.jpg"
        filepath = self.mask_save_dir / filename
        
        try:
            # Resize for efficiency
            max_dim = 1280
            if frame.width > max_dim or frame.height > max_dim:
                ratio = max_dim / max(frame.width, frame.height)
                new_size = (int(frame.width * ratio), int(frame.height * ratio))
                frame = frame.resize(new_size, Image.Resampling.LANCZOS)
            
            frame.save(filepath, "JPEG", quality=80)
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
            "segmentations_published": self._segmentation_counter,
            "queue_size": self.queue_size,
            "batch_buffer_size": len(self._batch_buffer),
            "tracked_rois": len(self._roi_history),
            "uri": self.uri,
        }
    
    def get_roi_history(self, roi_id: str) -> dict[str, Any] | None:
        """Get history for a specific ROI."""
        return self._roi_history.get(roi_id)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_sam_publisher(
    mask_save_dir: str = "/tmp/advanced_vision/masks",
    schema: str = "trading",
) -> MobileSAMWSSPublisher:
    """Factory function to create MobileSAM WebSocket publisher."""
    return MobileSAMWSSPublisher(
        mask_save_dir=mask_save_dir,
        schema=schema,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test the publisher
    logging.basicConfig(level=logging.INFO)
    
    publisher = create_sam_publisher()
    publisher.start()
    
    try:
        # Simulate segmentations
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
                roi_id=f"roi_{i % 5}",  # Reuse some ROI IDs
                mask=mask,
                bbox=bbox,
                frame_id=f"frame_{i:04d}",
                confidence=0.92,
            )
            
            # Simulate on-demand rate (variable timing)
            time.sleep(0.3 + (i % 3) * 0.2)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        publisher.stop()
        print("Publisher stats:", publisher.stats)
