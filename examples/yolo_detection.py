#!/usr/bin/env python3
"""
YOLO Detection on Screenshot Example

Verified on: RTX 5070 Ti
VRAM Usage: ~0.4 GB (YOLOv8n)
Timing: ~10-15ms per detection

Usage:
    python examples/yolo_detection.py

Requirements:
    - models/yolov8n.pt must exist
    - ultralytics package installed
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from advanced_vision.tools import screenshot_full


def main():
    print("=" * 60)
    print("YOLO Detection Example")
    print("=" * 60)
    
    # Import YOLO
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics not installed")
        print("Install with: pip install ultralytics")
        sys.exit(1)
    
    # Check model exists
    model_path = Path("models/yolov8n.pt")
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Download with: python scripts/download_yolo.py")
        sys.exit(1)
    
    # Load model
    print(f"\nLoading YOLOv8n from {model_path}...")
    start = time.time()
    model = YOLO(str(model_path))
    load_time = (time.time() - start) * 1000
    print(f"  ✓ Model loaded in {load_time:.1f}ms")
    
    # Capture screen
    print("\nCapturing screenshot...")
    artifact = screenshot_full()
    print(f"  ✓ Screenshot: {artifact.width}x{artifact.height}")
    
    # Run detection
    print("\nRunning YOLO detection...")
    start = time.time()
    results = model(artifact.path, verbose=False)
    elapsed = (time.time() - start) * 1000
    
    # Process results
    print(f"  ✓ Detection complete in {elapsed:.1f}ms")
    print()
    
    for r in results:
        boxes = r.boxes
        if len(boxes) == 0:
            print("  No objects detected")
        else:
            print(f"  Found {len(boxes)} objects:")
            print()
            print(f"  {'Class':<15} {'Confidence':>12} {'Box':>20}")
            print(f"  {'-' * 15} {'-' * 12} {'-' * 20}")
            
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                name = model.names[cls]
                xyxy = box.xyxy[0].tolist()
                box_str = f"({xyxy[0]:.0f}, {xyxy[1]:.0f}, {xyxy[2]:.0f}, {xyxy[3]:.0f})"
                
                print(f"  {name:<15} {conf:>11.1%} {box_str:>20}")
    
    # Summary
    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Model load:   {load_time:.1f}ms")
    print(f"  Inference:    {elapsed:.1f}ms")
    print(f"  VRAM used:    ~0.4 GB")
    print("=" * 60)


if __name__ == "__main__":
    main()
