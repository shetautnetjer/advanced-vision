#!/usr/bin/env python3
"""
Crypto DEX Screenshot Capture
Capture UI from birdeye.so, Jupiter, and DEXScreener for YOLO training.
These have different UI patterns than TradingView.
"""

import subprocess
import time
import os
from pathlib import Path

os.environ['DISPLAY'] = ':1'

output_dir = Path(__file__).resolve().parents[1] / "yolo_training" / "annotations" / "raw_images" / "dex_sites"
os.makedirs(output_dir, exist_ok=True)

def capture(url, name, actions=None):
    """Open URL and capture screenshots."""
    print(f"\nCapturing {name}...")
    
    # Open browser
    subprocess.Popen([
        'google-chrome', '--new-window', url
    ])
    time.sleep(6)  # Wait for load
    
    # Initial capture
    subprocess.run([
        'import', '-window', 'root',
        f'{output_dir}/{name}_main.png'
    ])
    print(f"  ✓ Main view")
    
    # Optional interactions
    if actions:
        for action_name, x, y in actions:
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)])
            subprocess.run(['xdotool', 'click', '1'])
            time.sleep(2)
            subprocess.run([
                'import', '-window', 'root',
                f'{output_dir}/{name}_{action_name}.png'
            ])
            print(f"  ✓ {action_name}")
            subprocess.run(['xdotool', 'key', 'Escape'])
            time.sleep(1)
    
    # Close tab
    subprocess.run(['xdotool', 'key', 'Ctrl+w'])
    time.sleep(1)

# 1. Birdeye.so - Solana DEX tracker
print("="*50)
print("BIRDEYE.SO CAPTURE")
print("="*50)

birdeye_actions = [
    ('token_search', 800, 120),      # Search bar
    ('trending', 300, 400),          # Trending tokens
    ('chart_view', 960, 600),        # Chart area
]

capture('https://birdeye.so', 'birdeye', birdeye_actions)

# 2. Jupiter - DEX Aggregator
print("\n" + "="*50)
print("JUPITER CAPTURE")
print("="*50)

jupiter_actions = [
    ('swap_interface', 960, 500),    # Main swap box
    ('token_select', 1100, 450),     # Token dropdown
    ('settings', 1250, 400),         # Settings gear
]

capture('https://jup.ag', 'jupiter', jupiter_actions)

# 3. DEXScreener - Multi-chain DEX
print("\n" + "="*50)
print("DEXSCREENER CAPTURE")
print("="*50)

dexscreener_actions = [
    ('pair_search', 700, 120),       # Search
    ('trending_pairs', 400, 300),    # Trending
    ('chart_panel', 800, 600),       # Chart
]

capture('https://dexscreener.com', 'dexscreener', dexscreener_actions)

print("\n" + "="*50)
print("DEX SITE CAPTURE COMPLETE")
print("="*50)
print(f"\nScreenshots saved to: {output_dir}")
print(f"Files captured:")
for f in sorted(os.listdir(output_dir)):
    if f.startswith(('birdeye', 'jupiter', 'dexscreener')):
        print(f"  - {f}")
