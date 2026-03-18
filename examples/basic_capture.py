#!/usr/bin/env python3
"""
Basic Screenshot Capture Example

Verified on: RTX 5070 Ti
VRAM Usage: 0 GB (no model inference)
Timing: ~100-200ms per capture

Usage:
    python examples/basic_capture.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from advanced_vision.tools import screenshot_full, screenshot_active_window


def main():
    print("=" * 60)
    print("Basic Screenshot Capture Example")
    print("=" * 60)
    
    # Example 1: Full screen capture
    print("\n[1/2] Capturing full screen...")
    start = time.time()
    artifact = screenshot_full()
    elapsed = (time.time() - start) * 1000
    
    print(f"  ✓ Screenshot saved: {artifact.path}")
    print(f"    Size: {artifact.width}x{artifact.height}")
    print(f"    Time: {elapsed:.1f}ms")
    
    # Verify file exists
    path = Path(artifact.path)
    if path.exists():
        size_kb = path.stat().st_size / 1024
        print(f"    File size: {size_kb:.1f} KB")
    
    # Example 2: Active window capture
    print("\n[2/2] Capturing active window...")
    start = time.time()
    artifact = screenshot_active_window()
    elapsed = (time.time() - start) * 1000
    
    print(f"  ✓ Window screenshot saved: {artifact.path}")
    print(f"    Size: {artifact.width}x{artifact.height}")
    print(f"    Time: {elapsed:.1f}ms")
    
    # Note about fallback
    if artifact.width == 1280 and artifact.height == 720:
        print("    Note: Using placeholder (headless/GUI unavailable)")
    
    print("\n" + "=" * 60)
    print("Done! Check artifacts/screens/ for saved images.")
    print("=" * 60)


if __name__ == "__main__":
    main()
