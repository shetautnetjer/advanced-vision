#!/usr/bin/env python3
"""
Mouse Cursor Training Data Capture
Captures cursor at various positions and states for YOLO training.
The cursor itself becomes a detectable UI element.
"""

import subprocess
import time
import os

os.environ['DISPLAY'] = ':1'

output_dir = "/home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision/yolo_training/annotations/raw_images/cursor_training"
os.makedirs(output_dir, exist_ok=True)

print("=== Mouse Cursor Training Data ===")
print()

# Function to get mouse position and capture around it
def capture_cursor_region(name, size=64):
    """Capture region around cursor."""
    # Get mouse position
    result = subprocess.run(
        ['xdotool', 'getmouselocation'],
        capture_output=True, text=True
    )
    pos = result.stdout.strip()
    # Parse "x:1234 y:5678 screen:0"
    x = int(pos.split()[0].split(':')[1])
    y = int(pos.split()[1].split(':')[1])
    
    # Calculate crop region (centered on cursor)
    half = size // 2
    left = max(0, x - half)
    top = max(0, y - half)
    
    # Capture region
    filename = f"{output_dir}/{name}_{x}_{y}.png"
    subprocess.run([
        'import', '-window', 'root',
        '-crop', f'{size}x{size}+{left}+{top}',
        filename
    ])
    print(f"  ✓ {name} at ({x}, {y})")
    return filename

print("1. Default cursor positions...")
positions = [
    (100, 100, "top_left"),
    (960, 540, "center"),
    (1800, 100, "top_right"),
    (100, 1000, "bottom_left"),
    (1800, 1000, "bottom_right"),
    (960, 100, "top_center"),
    (960, 1000, "bottom_center"),
    (100, 540, "left_center"),
    (1800, 540, "right_center"),
]

for x, y, name in positions:
    subprocess.run(['xdotool', 'mousemove', str(x), str(y)])
    time.sleep(0.5)
    capture_cursor_region(f"cursor_{name}", size=64)

print()
print("2. Cursor states...")

# Different cursor contexts
print("  Moving over text...")
subprocess.run(['xdotool', 'mousemove', '400', '400'])
subprocess.run(['xdotool', 'click', '1'])  # Click to get text cursor
time.sleep(0.5)
capture_cursor_region("cursor_text", size=64)

print("  Moving over buttons...")
subprocess.run(['xdotool', 'mousemove', '100', '100'])  # Top bar area
time.sleep(0.5)
capture_cursor_region("cursor_pointer", size=64)

print("  Moving over window edge...")
subprocess.run(['xdotool', 'mousemove', '1920', '540'])  # Right edge
time.sleep(0.5)
capture_cursor_region("cursor_resize", size=64)

print()
print("3. Cursor movement trail...")
# Capture cursor at intervals during movement
for i in range(10):
    x = 200 + (i * 100)
    y = 500 + (i % 3) * 50
    subprocess.run(['xdotool', 'mousemove', str(x), str(y)])
    time.sleep(0.3)
    capture_cursor_region(f"cursor_move_{i:02d}", size=64)

print()
print("4. Cursor with UI context...")
# Move over different UI elements and capture

print("  Over chart area...")
subprocess.run(['xdotool', 'mousemove', '600', '600'])
time.sleep(0.5)
subprocess.run([
    'import', '-window', 'root',
    '-crop', '128x128+568+568',
    f'{output_dir}/cursor_context_chart.png'
])

print("  Over sidebar...")
subprocess.run(['xdotool', 'mousemove', '50', '400'])
time.sleep(0.5)
subprocess.run([
    'import', '-window', 'root',
    '-crop', '128x128+18+368',
    f'{output_dir}/cursor_context_sidebar.png'
])

print()
print("=== Cursor Training Capture Complete ===")
print(f"Saved to: {output_dir}")
subprocess.run(['ls', '-la', output_dir])
