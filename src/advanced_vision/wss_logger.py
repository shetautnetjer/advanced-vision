#!/usr/bin/env python3
"""
WebSocket Logger for Advanced Vision
Logs text, JSON, and image references from WSS feeds
"""

import json
import logging
import base64
from typing import Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path
import sys
from dataclasses import dataclass, asdict
import threading


@dataclass
class LogEntry:
    """Base log entry"""
    timestamp: str
    feed: str
    event_type: str
    data: Dict[str, Any]


class WSSLogger:
    """Logger for WebSocket feed data"""
    
    def __init__(self, 
                 log_dir: Optional[str] = None,
                 text_log_file: str = "wss-feed-text.log",
                 json_log_file: str = "wss-feed-classifications.json",
                 image_dir: str = "frames"):
        """
        Initialize WSS Logger
        
        Args:
            log_dir: Directory for logs (default: project_root/logs)
            text_log_file: Text log filename
            json_log_file: JSON log filename  
            image_dir: Directory to save frame images
        """
        # Determine log directory
        if log_dir is None:
            # Find project root
            current = Path(__file__).parent.parent.parent
            self.log_dir = current / "logs"
        else:
            self.log_dir = Path(log_dir)
            
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.text_log_path = self.log_dir / text_log_file
        self.json_log_path = self.log_dir / json_log_file
        self.image_dir = self.log_dir / image_dir
        self.image_dir.mkdir(exist_ok=True)
        
        # Setup text logger
        self.text_logger = logging.getLogger(f"wss_logger_{id(self)}")
        self.text_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.text_logger.handlers = []
        
        # File handler for text log
        file_handler = logging.FileHandler(self.text_log_path)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.text_logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.text_logger.addHandler(console_handler)
        
        # JSON log buffer
        self._json_entries: list = []
        self._json_buffer_size = 100
        self._json_lock = threading.Lock()
        
        # Frame counter per feed
        self._frame_counters: Dict[str, int] = {}
        
        self.text_logger.info("=" * 60)
        self.text_logger.info("WSS Logger Initialized")
        self.text_logger.info(f"Text log: {self.text_log_path}")
        self.text_logger.info(f"JSON log: {self.json_log_path}")
        self.text_logger.info(f"Image dir: {self.image_dir}")
        self.text_logger.info("=" * 60)
        
    def log_connection(self, feed: str, client_info: Dict[str, Any], event: str):
        """Log client connection/disconnection"""
        self.text_logger.info(f"[{feed}] Client {event}: {client_info}")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "feed": feed,
            "event_type": "connection",
            "event": event,
            "client_info": client_info
        }
        self._append_json(entry)
        
    def log_message(self, feed: str, data: Dict[str, Any], timestamp: str):
        """Log a JSON message"""
        # Text log (truncated for readability)
        data_str = json.dumps(data)
        if len(data_str) > 200:
            data_str = data_str[:200] + "..."
        self.text_logger.info(f"[{feed}] Message: {data_str}")
        
        # JSON log
        entry = {
            "timestamp": timestamp,
            "feed": feed,
            "event_type": "message",
            "data": data
        }
        self._append_json(entry)
        
    def log_frame(self, feed: str, size_bytes: int, timestamp: str) -> Optional[str]:
        """Log a binary frame received"""
        self.text_logger.info(f"[{feed}] Frame received: {size_bytes} bytes")
        
        # We don't save the actual binary data, just log the receipt
        # The actual frame saving should be done by the caller if needed
        entry = {
            "timestamp": timestamp,
            "feed": feed,
            "event_type": "frame",
            "size_bytes": size_bytes
        }
        self._append_json(entry)
        
        return None
        
    def save_frame(self, feed: str, frame_data: bytes, timestamp: str,
                   extension: str = "jpg") -> Optional[str]:
        """
        Save a frame image to disk and return the path
        
        Args:
            feed: Feed name
            frame_data: Binary image data
            timestamp: ISO timestamp
            extension: File extension
            
        Returns:
            Path to saved image relative to log_dir
        """
        # Get frame number for this feed
        if feed not in self._frame_counters:
            self._frame_counters[feed] = 0
        self._frame_counters[feed] += 1
        frame_num = self._frame_counters[feed]
        
        # Create filename
        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        filename = f"{feed}_{ts.strftime('%Y%m%d_%H%M%S')}_{frame_num:06d}.{extension}"
        filepath = self.image_dir / filename
        
        # Save image
        try:
            with open(filepath, 'wb') as f:
                f.write(frame_data)
                
            rel_path = f"frames/{filename}"
            
            # Log the save
            self.text_logger.info(f"[{feed}] Frame saved: {rel_path} ({len(frame_data)} bytes)")
            
            # Add to JSON log with image reference
            entry = {
                "timestamp": timestamp,
                "feed": feed,
                "event_type": "frame_saved",
                "image_ref": rel_path,
                "size_bytes": len(frame_data)
            }
            self._append_json(entry)
            
            return rel_path
            
        except Exception as e:
            self.text_logger.error(f"[{feed}] Failed to save frame: {e}")
            return None
            
    def log_classification(self, feed: str, label: str, confidence: float,
                          details: Dict[str, Any], timestamp: str,
                          image_ref: Optional[str] = None):
        """
        Log a classification result
        
        Args:
            feed: Feed name
            label: Classification label
            confidence: Confidence score (0-1)
            details: Additional classification details
            timestamp: ISO timestamp
            image_ref: Optional reference to saved frame image
        """
        self.text_logger.info(
            f"[{feed}] Classification: {label} (confidence: {confidence:.2%})"
        )
        
        entry = {
            "timestamp": timestamp,
            "feed": feed,
            "event_type": "classification",
            "label": label,
            "confidence": confidence,
            "details": details
        }
        
        if image_ref:
            entry["image_ref"] = image_ref
            
        self._append_json(entry)
        
    def log_detection(self, feed: str, boxes: list, classes: list,
                     scores: list, timestamp: str, image_ref: Optional[str] = None):
        """Log YOLO detection results"""
        num_detections = len(boxes)
        self.text_logger.info(
            f"[{feed}] Detection: {num_detections} objects - {classes}"
        )
        
        entry = {
            "timestamp": timestamp,
            "feed": feed,
            "event_type": "detection",
            "num_detections": num_detections,
            "boxes": boxes,
            "classes": classes,
            "scores": scores
        }
        
        if image_ref:
            entry["image_ref"] = image_ref
            
        self._append_json(entry)
        
    def log_segmentation(self, feed: str, masks: list, classes: list,
                        timestamp: str, image_ref: Optional[str] = None):
        """Log MobileSAM segmentation results"""
        num_masks = len(masks)
        self.text_logger.info(
            f"[{feed}] Segmentation: {num_masks} masks - {classes}"
        )
        
        entry = {
            "timestamp": timestamp,
            "feed": feed,
            "event_type": "segmentation",
            "num_masks": num_masks,
            "classes": classes
        }
        
        # Don't store full mask data in JSON log (too large)
        # Just log the count and reference
        if masks and len(masks) > 0:
            entry["mask_shape"] = list(masks[0].shape) if hasattr(masks[0], 'shape') else None
            
        if image_ref:
            entry["image_ref"] = image_ref
            
        self._append_json(entry)
        
    def log_analysis(self, feed: str, analysis_type: str, result: Dict[str, Any],
                    timestamp: str, image_ref: Optional[str] = None):
        """Log reviewer analysis results"""
        self.text_logger.info(
            f"[{feed}] Analysis ({analysis_type}): {json.dumps(result)[:100]}..."
        )
        
        entry = {
            "timestamp": timestamp,
            "feed": feed,
            "event_type": "analysis",
            "analysis_type": analysis_type,
            "result": result
        }
        
        if image_ref:
            entry["image_ref"] = image_ref
            
        self._append_json(entry)
        
    def log_server_event(self, server_name: str, event: str, details: Dict[str, Any]):
        """Log server-level events"""
        self.text_logger.info(f"[Server:{server_name}] {event}: {details}")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "feed": server_name,
            "event_type": "server_event",
            "event": event,
            "details": details
        }
        self._append_json(entry)
        
    def log_error(self, feed: str, error: str):
        """Log an error"""
        self.text_logger.error(f"[{feed}] Error: {error}")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "feed": feed,
            "event_type": "error",
            "error": error
        }
        self._append_json(entry)
        
    def _append_json(self, entry: Dict[str, Any]):
        """Append entry to JSON log buffer and flush if needed"""
        with self._json_lock:
            self._json_entries.append(entry)
            
            # Flush if buffer is full
            if len(self._json_entries) >= self._json_buffer_size:
                self._flush_json()
                
    def _flush_json(self):
        """Flush JSON entries to file"""
        if not self._json_entries:
            return
            
        try:
            # Read existing entries if file exists
            existing = []
            if self.json_log_path.exists():
                try:
                    with open(self.json_log_path, 'r') as f:
                        existing = json.load(f)
                except json.JSONDecodeError:
                    pass
                    
            # Append new entries
            all_entries = existing + self._json_entries
            
            # Write back
            with open(self.json_log_path, 'w') as f:
                json.dump(all_entries, f, indent=2)
                
            # Clear buffer
            self._json_entries = []
            
        except Exception as e:
            self.text_logger.error(f"Failed to flush JSON log: {e}")
            
    def flush(self):
        """Force flush all buffers"""
        with self._json_lock:
            self._flush_json()
        self.text_logger.info("WSS Logger flushed")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics"""
        return {
            "text_log_path": str(self.text_log_path),
            "json_log_path": str(self.json_log_path),
            "image_dir": str(self.image_dir),
            "json_buffer_size": len(self._json_entries),
            "frame_counters": self._frame_counters.copy()
        }
        
    def close(self):
        """Close logger and flush all buffers"""
        self.flush()
        for handler in self.text_logger.handlers:
            handler.close()
        self.text_logger.info("WSS Logger closed")


def demo_logging():
    """Demonstrate logging functionality"""
    logger = WSSLogger()
    
    # Simulate some events
    timestamp = datetime.utcnow().isoformat()
    
    # Log connection
    logger.log_connection("capture", {"remote_address": "127.0.0.1:12345"}, "connected")
    
    # Log a message
    logger.log_message("eagle", {"label": "button", "confidence": 0.95}, timestamp)
    
    # Log a classification
    logger.log_classification(
        "eagle",
        "submit_button",
        0.95,
        {"bbox": [100, 200, 150, 250]},
        timestamp,
        image_ref="frames/capture_20240101_120000_000001.jpg"
    )
    
    # Log detection
    logger.log_detection(
        "yolo",
        [[100, 200, 150, 250]],
        ["button"],
        [0.92],
        timestamp
    )
    
    # Log analysis
    logger.log_analysis(
        "reviewers",
        "ui_review",
        {"issues": [], "score": 0.95},
        timestamp
    )
    
    # Flush and show stats
    logger.flush()
    print(json.dumps(logger.get_stats(), indent=2))
    logger.close()


if __name__ == "__main__":
    demo_logging()
