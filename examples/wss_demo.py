#!/usr/bin/env python3
"""
WSS Demo: Full Pipeline - Capture → YOLO → WSS → Display

This demo shows the complete Advanced Vision pipeline with WebSocket broadcasting:
1. Screen capture (screenshot)
2. YOLO detection (UI element detection)
3. Eagle2 classification (scout lane)
4. WSS publishing (broadcast to subscribers)
5. Latency measurement for each component
6. Console and file logging

Usage:
    # Run with dry-run (safe, no actual inference)
    python examples/wss_demo.py --dry-run
    
    # Run with actual models (requires setup)
    python examples/wss_demo.py --mode trading
    
    # Run for specific duration
    python examples/wss_demo.py --duration 60

Requirements:
    - websockets package: pip install websockets
    - Running WSS server (starts automatically)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import websockets
    from websockets.client import connect as ws_connect
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Error: websockets package not installed.")
    print("Install with: pip install websockets")
    sys.exit(1)

from advanced_vision.wss_server import (
    WSSServer,
    WSSServerConfig,
    DetectionMessage,
    ClassificationMessage,
    TradingSignalMessage,
    UIUpdateMessage,
)
from advanced_vision.tools.screen import screenshot_full
from advanced_vision.trading.detector import create_detector, DetectorMode
from advanced_vision.trading.events import (
    TradingEventType,
    RiskLevel,
    ActionRecommendation,
)


# =============================================================================
# Latency Tracker
# =============================================================================

@dataclass
class LatencyMetrics:
    """Track latency for each pipeline component."""
    capture_ms: float = 0.0
    detection_ms: float = 0.0
    classification_ms: float = 0.0
    wss_publish_ms: float = 0.0
    total_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "capture_ms": round(self.capture_ms, 2),
            "detection_ms": round(self.detection_ms, 2),
            "classification_ms": round(self.classification_ms, 2),
            "wss_publish_ms": round(self.wss_publish_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


# =============================================================================
# Demo Logger
# =============================================================================

class DemoLogger:
    """Logs demo output to console and file."""
    
    def __init__(self, log_dir: Path = Path("logs/demo")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.console_log = self.log_dir / f"demo_{timestamp}.log"
        self.latency_log = self.log_dir / f"latency_{timestamp}.jsonl"
        
        print(f"📝 Logs will be saved to: {self.log_dir.absolute()}")
        print(f"   Console: {self.console_log.name}")
        print(f"   Latency: {self.latency_log.name}")
    
    def log(self, message: str, level: str = "INFO") -> None:
        """Log message to console and file."""
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level}] {message}"
        
        # Console output
        print(formatted)
        
        # File output
        with open(self.console_log, "a") as f:
            f.write(formatted + "\n")
    
    def log_latency(self, metrics: LatencyMetrics) -> None:
        """Log latency metrics to JSONL file."""
        with open(self.latency_log, "a") as f:
            f.write(json.dumps(metrics.to_dict()) + "\n")
    
    def log_summary(self, metrics_list: list[LatencyMetrics]) -> None:
        """Log summary statistics."""
        if not metrics_list:
            self.log("No metrics to summarize", "WARN")
            return
        
        capture_times = [m.capture_ms for m in metrics_list]
        detection_times = [m.detection_ms for m in metrics_list]
        classification_times = [m.classification_ms for m in metrics_list]
        wss_times = [m.wss_publish_ms for m in metrics_list]
        total_times = [m.total_ms for m in metrics_list]
        
        summary = f"""
{'='*60}
📊 LATENCY SUMMARY ({len(metrics_list)} frames)
{'='*60}
  Screenshot Capture:
    Average: {sum(capture_times)/len(capture_times):.2f} ms
    Min: {min(capture_times):.2f} ms
    Max: {max(capture_times):.2f} ms
  
  YOLO Detection:
    Average: {sum(detection_times)/len(detection_times):.2f} ms
    Min: {min(detection_times):.2f} ms
    Max: {max(detection_times):.2f} ms
  
  Eagle2 Classification:
    Average: {sum(classification_times)/len(classification_times):.2f} ms
    Min: {min(classification_times):.2f} ms
    Max: {max(classification_times):.2f} ms
  
  WSS Publish:
    Average: {sum(wss_times)/len(wss_times):.2f} ms
    Min: {min(wss_times):.2f} ms
    Max: {max(wss_times):.2f} ms
  
  TOTAL PIPELINE:
    Average: {sum(total_times)/len(total_times):.2f} ms
    Min: {min(total_times):.2f} ms
    Max: {max(total_times):.2f} ms
{'='*60}
"""
        self.log(summary, "SUMMARY")


# =============================================================================
# Demo Pipeline
# =============================================================================

class WSSDemoPipeline:
    """Full WSS demo pipeline."""
    
    def __init__(
        self,
        wss_server: WSSServer,
        mode: DetectorMode = DetectorMode.DESKTOP_SCOUT,
        dry_run: bool = True,
        logger: DemoLogger | None = None,
    ):
        self.wss_server = wss_server
        self.mode = mode
        self.dry_run = dry_run
        self.logger = logger or DemoLogger()
        self.detector = create_detector(mode=mode)
        self.metrics: list[LatencyMetrics] = []
        self.frame_count = 0
        self.running = False
    
    async def run_single_cycle(self) -> LatencyMetrics:
        """Run one complete pipeline cycle."""
        metrics = LatencyMetrics()
        self.frame_count += 1
        frame_id = f"demo_{self.frame_count:04d}"
        
        self.logger.log(f"\n{'─'*60}")
        self.logger.log(f"🔄 Processing frame {self.frame_id} - {frame_id}")
        self.logger.log(f"{'─'*60}")
        
        # 1. Screenshot Capture
        self.logger.log("📸 Capturing screenshot...")
        start = time.perf_counter()
        
        try:
            screenshot = screenshot_full()
            capture_time = (time.perf_counter() - start) * 1000
            metrics.capture_ms = capture_time
            self.logger.log(f"   ✓ Screenshot saved: {screenshot.path}")
            self.logger.log(f"   ⏱️  Capture time: {capture_time:.2f} ms")
        except Exception as e:
            self.logger.log(f"   ✗ Capture failed: {e}", "ERROR")
            capture_time = (time.perf_counter() - start) * 1000
            metrics.capture_ms = capture_time
            return metrics
        
        # 2. YOLO Detection
        self.logger.log("🔍 Running YOLO detection...")
        start = time.perf_counter()
        
        try:
            from PIL import Image
            with Image.open(screenshot.path) as img:
                detection_result = self.detector.process_frame(
                    screenshot=img,
                    timestamp=datetime.utcnow().isoformat(),
                    dry_run=self.dry_run,
                )
            
            detection_time = (time.perf_counter() - start) * 1000
            metrics.detection_ms = detection_time
            
            if detection_result:
                self.logger.log(f"   ✓ Detected {len(detection_result.elements)} elements")
                for elem in detection_result.elements:
                    self.logger.log(f"     - {elem.element_type.value}: {elem.confidence:.2f} confidence")
                self.logger.log(f"   ⏱️  Detection time: {detection_time:.2f} ms")
            else:
                self.logger.log("   ℹ No detections")
                
        except Exception as e:
            self.logger.log(f"   ✗ Detection failed: {e}", "ERROR")
            detection_time = (time.perf_counter() - start) * 1000
            metrics.detection_ms = detection_time
        
        # 3. Eagle2 Classification (simulated)
        self.logger.log("🦅 Eagle2 classification...")
        start = time.perf_counter()
        
        # Simulate classification based on detections
        if detection_result and detection_result.elements:
            # Classify based on detected elements
            element_types = {e.element_type.value for e in detection_result.elements}
            
            if "warning_modal" in element_types or "error_modal" in element_types:
                event_type = TradingEventType.WARNING_DIALOG
                is_relevant = True
                confidence = 0.92
            elif "order_ticket_panel" in element_types:
                event_type = TradingEventType.ORDER_TICKET
                is_relevant = True
                confidence = 0.88
            elif "chart_panel" in element_types:
                event_type = TradingEventType.CHART_UPDATE
                is_relevant = True
                confidence = 0.85
            else:
                event_type = TradingEventType.UI_CHANGE
                is_relevant = False
                confidence = 0.65
        else:
            event_type = TradingEventType.NOISE
            is_relevant = False
            confidence = 0.45
        
        # Add some simulated inference time
        if not self.dry_run:
            await asyncio.sleep(0.3)  # Simulate model inference
        
        classification_time = (time.perf_counter() - start) * 1000
        metrics.classification_ms = classification_time
        
        self.logger.log(f"   ✓ Classified as: {event_type.value}")
        self.logger.log(f"   ✓ Trading relevant: {is_relevant}")
        self.logger.log(f"   ✓ Confidence: {confidence:.2f}")
        self.logger.log(f"   ⏱️  Classification time: {classification_time:.2f} ms")
        
        # 4. Publish to WSS
        self.logger.log("📡 Publishing to WebSocket...")
        start = time.perf_counter()
        
        try:
            # Publish detection
            if detection_result:
                detection_msg = DetectionMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="yolo_detector",
                    msg_type="detection",
                    payload={
                        "frame_id": frame_id,
                        "inference_time_ms": metrics.detection_ms,
                        "detections": [
                            {
                                "element_type": e.element_type.value,
                                "confidence": e.confidence,
                                "bbox": e.bbox.model_dump() if e.bbox else None,
                            }
                            for e in detection_result.elements
                        ],
                    }
                )
                await self.wss_server.publish(8002, detection_msg)
            
            # Publish classification
            class_msg = ClassificationMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="eagle2_scout",
                msg_type="classification",
                payload={
                    "frame_id": frame_id,
                    "event_type": event_type.value,
                    "is_trading_relevant": is_relevant,
                    "confidence": confidence,
                    "inference_time_ms": metrics.classification_ms,
                }
            )
            await self.wss_server.publish(8004, class_msg)
            
            # Publish UI update
            ui_msg = UIUpdateMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="demo_pipeline",
                msg_type="ui_update",
                payload={
                    "update_type": "frame_processed",
                    "frame_id": frame_id,
                    "screenshot_path": screenshot.path,
                    "detection_count": len(detection_result.elements) if detection_result else 0,
                    "event_type": event_type.value,
                }
            )
            await self.wss_server.publish(8001, ui_msg)
            
            # If trading relevant, publish signal
            if is_relevant and confidence > 0.8:
                risk = RiskLevel.MEDIUM if confidence > 0.9 else RiskLevel.LOW
                signal_msg = TradingSignalMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="demo_pipeline",
                    msg_type="trading_signal",
                    payload={
                        "frame_id": frame_id,
                        "signal_type": "ANALYSIS_COMPLETE",
                        "risk_level": risk.value,
                        "recommendation": ActionRecommendation.NOTE.value,
                        "confidence": confidence,
                    }
                )
                await self.wss_server.publish(8005, signal_msg)
            
            wss_time = (time.perf_counter() - start) * 1000
            metrics.wss_publish_ms = wss_time
            
            self.logger.log(f"   ✓ Published to all channels")
            self.logger.log(f"   ⏱️  WSS publish time: {wss_time:.2f} ms")
            
        except Exception as e:
            self.logger.log(f"   ✗ WSS publish failed: {e}", "ERROR")
            wss_time = (time.perf_counter() - start) * 1000
            metrics.wss_publish_ms = wss_time
        
        # Calculate total
        metrics.total_ms = (
            metrics.capture_ms +
            metrics.detection_ms +
            metrics.classification_ms +
            metrics.wss_publish_ms
        )
        
        self.logger.log(f"\n📊 TOTAL CYCLE TIME: {metrics.total_ms:.2f} ms")
        
        return metrics
    
    async def run(self, duration_seconds: float = 10.0, interval_seconds: float = 2.0) -> None:
        """Run demo for specified duration."""
        self.running = True
        start_time = time.time()
        
        self.logger.log(f"\n{'='*60}")
        self.logger.log("🚀 WSS DEMO PIPELINE STARTED")
        self.logger.log(f"{'='*60}")
        self.logger.log(f"Duration: {duration_seconds}s")
        self.logger.log(f"Interval: {interval_seconds}s")
        self.logger.log(f"Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")
        self.logger.log(f"{'='*60}\n")
        
        while self.running and (time.time() - start_time) < duration_seconds:
            metrics = await self.run_single_cycle()
            self.metrics.append(metrics)
            self.logger.log_latency(metrics)
            
            # Wait for next cycle
            if self.running:
                await asyncio.sleep(interval_seconds)
        
        self.running = False
        
        # Print summary
        self.logger.log_summary(self.metrics)


# =============================================================================
# Display Subscriber
# =============================================================================

class DisplaySubscriber:
    """Simple subscriber that displays received messages."""
    
    def __init__(self, port: int, name: str):
        self.port = port
        self.name = name
        self.message_count = 0
        self.running = False
    
    async def run(self) -> None:
        """Run subscriber loop."""
        self.running = True
        uri = f"ws://localhost:{self.port}"
        
        print(f"👁️  [{self.name}] Connecting to {uri}...")
        
        try:
            async with ws_connect(uri) as websocket:
                print(f"✓ [{self.name}] Connected!")
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        self.message_count += 1
                        data = json.loads(message)
                        
                        # Pretty print based on message type
                        msg_type = data.get("msg_type", "unknown")
                        source = data.get("source", "unknown")
                        
                        if msg_type == "detection":
                            detections = data.get("payload", {}).get("detections", [])
                            print(f"🔍 [{self.name}] Detection from {source}: {len(detections)} elements")
                        elif msg_type == "classification":
                            event = data.get("payload", {}).get("event_type", "unknown")
                            relevant = data.get("payload", {}).get("is_trading_relevant", False)
                            print(f"🦅 [{self.name}] Classification: {event} (relevant: {relevant})")
                        elif msg_type == "trading_signal":
                            signal = data.get("payload", {}).get("signal_type", "unknown")
                            risk = data.get("payload", {}).get("risk_level", "unknown")
                            print(f"📈 [{self.name}] Trading Signal: {signal} (risk: {risk})")
                        elif msg_type == "ui_update":
                            update_type = data.get("payload", {}).get("update_type", "unknown")
                            print(f"🖥️  [{self.name}] UI Update: {update_type}")
                        elif msg_type == "system_event":
                            event = data.get("payload", {}).get("event_type", "unknown")
                            if event == "heartbeat":
                                pass  # Silently ignore heartbeats
                            else:
                                print(f"⚙️  [{self.name}] System: {event}")
                        
                    except asyncio.TimeoutError:
                        continue
                        
        except Exception as e:
            print(f"✗ [{self.name}] Error: {e}")
    
    def stop(self) -> None:
        """Stop subscriber."""
        self.running = False


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main demo entry point."""
    parser = argparse.ArgumentParser(description="WSS Demo Pipeline")
    parser.add_argument(
        "--mode",
        choices=["desktop", "trading"],
        default="desktop",
        help="Detection mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (safe, no actual inference)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Demo duration in seconds"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Interval between cycles in seconds"
    )
    parser.add_argument(
        "--no-subscribers",
        action="store_true",
        help="Don't spawn display subscribers"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/demo",
        help="Log directory"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_dir = Path(args.log_dir)
    logger = DemoLogger(log_dir)
    
    # Create and start WSS server
    wss_config = WSSServerConfig(
        log_dir=log_dir / "wss",
        log_format="json",
        heartbeat_interval=30.0,
    )
    
    wss_server = WSSServer(wss_config)
    server_task = asyncio.create_task(wss_server.start())
    
    # Wait for server startup
    await asyncio.sleep(0.5)
    
    # Start display subscribers
    subscriber_tasks = []
    if not args.no_subscribers:
        subscribers = [
            DisplaySubscriber(8001, "UI"),
            DisplaySubscriber(8002, "Detection"),
            DisplaySubscriber(8004, "Classification"),
            DisplaySubscriber(8005, "Trading"),
        ]
        
        for sub in subscribers:
            task = asyncio.create_task(sub.run())
            subscriber_tasks.append((sub, task))
        
        # Give subscribers time to connect
        await asyncio.sleep(0.5)
    
    # Create and run demo pipeline
    detector_mode = DetectorMode.TRADING_WATCH if args.mode == "trading" else DetectorMode.DESKTOP_SCOUT
    
    pipeline = WSSDemoPipeline(
        wss_server=wss_server,
        mode=detector_mode,
        dry_run=args.dry_run,
        logger=logger,
    )
    
    try:
        await pipeline.run(
            duration_seconds=args.duration,
            interval_seconds=args.interval
        )
    except KeyboardInterrupt:
        logger.log("\n⚠️ Interrupted by user", "WARN")
    
    # Cleanup
    logger.log("\n🛑 Shutting down...")
    
    # Stop subscribers
    for sub, task in subscriber_tasks:
        sub.stop()
        task.cancel()
    
    # Stop server
    await wss_server.stop()
    server_task.cancel()
    
    # Wait for cleanup
    for sub, task in subscriber_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    try:
        await server_task
    except asyncio.CancelledError:
        pass
    
    logger.log("✓ Demo complete!")
    print(f"\n📁 Logs saved to: {log_dir.absolute()}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye!")
        sys.exit(0)