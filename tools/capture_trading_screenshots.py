#!/usr/bin/env python3
"""
Baseline Computer Use Capture Tool
Simplified approach: Just capture + basic YOLO, no heavy model stack
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

class BaselineCaptureTool:
    """Minimal capture tool for collecting trading platform screenshots."""
    
    def __init__(self, output_dir="yolo_training/annotations/raw_images"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.capture_count = 0
        
    def check_dependencies(self):
        """Check what's available for screen capture."""
        print("Checking capture capabilities...")
        
        # Check for different capture methods
        methods = {}
        
        # 1. Check if we're in OpenClaw with screen access
        if os.path.exists('/dev/video0'):
            methods['v4l2'] = True
            print("  ✅ v4l2 video device available")
        else:
            methods['v4l2'] = False
            
        # 2. Check for gnome-screenshot
        try:
            subprocess.run(['gnome-screenshot', '--help'], 
                          capture_output=True, check=True)
            methods['gnome-screenshot'] = True
            print("  ✅ gnome-screenshot available")
        except:
            methods['gnome-screenshot'] = False
            
        # 3. Check for import (ImageMagick)
        try:
            subprocess.run(['import', '--help'], 
                          capture_output=True, check=True)
            methods['imagemagick'] = True
            print("  ✅ ImageMagick import available")
        except:
            methods['imagemagick'] = False
            
        # 4. Check for PIL/Pillow
        try:
            from PIL import Image
            methods['pillow'] = True
            print("  ✅ PIL/Pillow available")
        except:
            methods['pillow'] = False
            
        # 5. Check for mss (multi-screen shot)
        try:
            import mss
            methods['mss'] = True
            print("  ✅ mss available")
        except:
            methods['mss'] = False
            
        return methods
    
    def capture_screen_pillow(self, filename):
        """Capture screen using PIL/Pillow."""
        try:
            from PIL import Image
            import pyscreenshot as ImageGrab
            
            # Capture
            screenshot = ImageGrab.grab()
            
            # Save
            filepath = os.path.join(self.output_dir, filename)
            screenshot.save(filepath)
            
            return True, filepath
        except Exception as e:
            return False, str(e)
    
    def capture_screen_mss(self, filename):
        """Capture screen using mss (fastest)."""
        try:
            import mss
            import numpy as np
            from PIL import Image
            
            with mss.mss() as sct:
                # Capture primary monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                
                # Convert to PIL
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Save
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
                
                return True, filepath
        except Exception as e:
            return False, str(e)
    
    def capture_screen_gnome(self, filename):
        """Capture using gnome-screenshot."""
        try:
            filepath = os.path.join(self.output_dir, filename)
            subprocess.run([
                'gnome-screenshot', 
                '-f', filepath
            ], check=True, capture_output=True)
            return True, filepath
        except Exception as e:
            return False, str(e)
    
    def capture_screen_imagemagick(self, filename):
        """Capture using ImageMagick import."""
        try:
            filepath = os.path.join(self.output_dir, filename)
            subprocess.run([
                'import', '-window', 'root', filepath
            ], check=True, capture_output=True)
            return True, filepath
        except Exception as e:
            return False, str(e)
    
    def capture(self, label=""):
        """Capture a screenshot using best available method."""
        timestamp = time.strftime('%Y-%m-%dT%H-%M-%S')
        if label:
            filename = f"capture_{label}_{timestamp}.png"
        else:
            filename = f"capture_{timestamp}.png"
        
        # Try methods in order of preference
        methods = [
            ('mss', self.capture_screen_mss),
            ('pillow', self.capture_screen_pillow),
            ('gnome-screenshot', self.capture_screen_gnome),
            ('imagemagick', self.capture_screen_imagemagick),
        ]
        
        for name, method in methods:
            success, result = method(filename)
            if success:
                self.capture_count += 1
                print(f"✅ Captured: {result}")
                return result
        
        print("❌ All capture methods failed")
        return None
    
    def capture_sequence(self, count=10, delay=2, label="trading"):
        """Capture multiple screenshots with delay."""
        print(f"\nCapturing {count} screenshots with {delay}s delay...")
        print("Switch to your trading platform now!")
        print("Starting in 5 seconds...\n")
        
        time.sleep(5)
        
        captured = []
        for i in range(count):
            print(f"Capture {i+1}/{count}...")
            filepath = self.capture(f"{label}_{i+1:02d}")
            if filepath:
                captured.append(filepath)
            
            if i < count - 1:
                time.sleep(delay)
        
        return captured
    
    def interactive_capture(self):
        """Interactive capture session."""
        print("="*60)
        print("BASELINE COMPUTER USE CAPTURE TOOL")
        print("="*60)
        print()
        print("This tool captures screenshots for YOLO training.")
        print("You'll need to manually navigate to your trading platform.")
        print()
        
        # Check what we have
        methods = self.check_dependencies()
        available = [k for k, v in methods.items() if v]
        
        if not available:
            print("❌ No capture methods available!")
            print("Install one of:")
            print("  pip install mss pillow")
            print("  sudo apt install gnome-screenshot")
            print("  sudo apt install imagemagick")
            return
        
        print(f"\nAvailable methods: {', '.join(available)}")
        print()
        
        while True:
            print("\nOptions:")
            print("  1. Single capture")
            print("  2. Capture sequence (multiple with delay)")
            print("  3. Capture with state labels (buy, sell, alert, etc.)")
            print("  4. Exit")
            
            choice = input("\nSelect: ").strip()
            
            if choice == '1':
                label = input("Label (optional): ").strip()
                self.capture(label if label else "manual")
                
            elif choice == '2':
                count = int(input("Number of captures: ") or "10")
                delay = int(input("Delay between captures (seconds): ") or "2")
                label = input("Label prefix: ").strip() or "sequence"
                self.capture_sequence(count, delay, label)
                
            elif choice == '3':
                print("\nState capture mode:")
                print("Navigate to different states and capture:")
                print("  - Normal view")
                print("  - Buy order screen")
                print("  - Sell order screen")
                print("  - Position open")
                print("  - Alert/warning showing")
                print("  - Confirmation modal")
                print()
                
                states = [
                    "normal", "buy_screen", "sell_screen", 
                    "position_open", "alert_showing", "confirm_modal"
                ]
                
                for state in states:
                    input(f"\nNavigate to '{state}' state and press Enter...")
                    self.capture(state)
                    
            elif choice == '4':
                break
        
        print(f"\n✅ Total captured: {self.capture_count}")
        print(f"Output directory: {self.output_dir}")

def main():
    tool = BaselineCaptureTool()
    tool.interactive_capture()

if __name__ == "__main__":
    main()
