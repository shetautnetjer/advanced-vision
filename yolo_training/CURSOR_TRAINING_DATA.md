# Cursor Training Data for YOLO

**Purpose:** Train YOLO to detect mouse cursor position and state
**Date:** 2026-03-18  
**Total Images:** 25 cursor captures

## Why Cursor Detection Matters

1. **Cursor-only movement detection** — Identify when only cursor moved (noise suppression)
2. **Click localization** — Know exactly where clicks happen
3. **Hover states** — Detect what UI element cursor is over
4. **Action correlation** — Link cursor position to UI changes

## Dataset Contents

### Location
`yolo_training/annotations/raw_images/cursor_training/`

### Files (25 total)

**Position Variations (9):**
- cursor_top_left_100_100.png
- cursor_center_960_540.png
- cursor_top_right_1800_100.png
- cursor_bottom_left_100_1000.png
- cursor_bottom_right_1800_1000.png
- cursor_top_center_960_100.png
- cursor_bottom_center_960_1000.png
- cursor_left_center_100_540.png
- cursor_right_center_1800_540.png

**Cursor States (3):**
- cursor_text_400_400.png — I-beam text cursor
- cursor_pointer_100_100.png — Hand/pointer cursor
- cursor_resize_1919_540.png — Resize cursor

**Movement Trail (10):**
- cursor_move_00_200_500.png through cursor_move_09_1100_500.png
- Shows cursor at different positions

**UI Context (2):**
- cursor_context_chart.png — Cursor over chart area
- cursor_context_sidebar.png — Cursor over sidebar

## Image Specifications

- **Size:** 64x64 pixels (small region around cursor)
- **Format:** PNG
- **Content:** Cursor + small surrounding context
- **Labels:** Single bounding box around cursor

## YOLO Label Format

```
# cursor_top_left.txt
0 0.5 0.5 0.3 0.5
```

Where:
- Class 0: cursor_default
- Class 1: cursor_pointer
- Class 2: cursor_text
- Class 3: cursor_resize
- x_center, y_center: Center of cursor in 64x64 box (normalized 0-1)
- width, height: Cursor size (typically ~10-20 pixels = ~0.15-0.30)

## Use Cases

### 1. Noise Suppression
```
Current frame: Cursor at (500, 300)
Previous frame: Cursor at (200, 200)
Change detected: Only cursor moved
Action: Suppress (cursor-only = noise)
```

### 2. Click Localization
```
Click event detected
Cursor position: (750, 450)
UI element at that position: primary_action_button
Action: Trigger button click logic
```

### 3. Hover Detection
```
Cursor at (800, 600) for 2 seconds
UI element: chart_panel
Action: Show tooltip/enable zoom
```

## Integration with Main Training

**Combined dataset:**
- TradingView: 18 images (charts)
- DEX sites: 12 images (swap interfaces)
- Antigravity: 7 images (IDE)
- ChatGPT: 10 images (chat UI)
- ChatGPT projects: 4 images (project lists)
- **Cursor: 25 images (mouse cursor)**
- **Total: 76 images**

## Labeling Instructions

```bash
labelImg yolo_training/annotations/raw_images/cursor_training/

# Draw tight boxes around cursor arrow/pointer
# Class: cursor_default (0), cursor_pointer (1), cursor_text (2), cursor_resize (3)
# The cursor is small - box should tightly fit the arrow tip
```

## Why Small Regions (64x64)

- Cursor itself is only ~12-20 pixels
- Small region = focused training on cursor shape
- Reduces background noise
- Faster inference (smaller input)
- Can be overlaid on full screenshot for position detection

## Training Strategy

**Phase 1:** Train on cursor-only images (25 samples)  
**Phase 2:** Train on full UI images where cursor is labeled (76 samples)  
**Combined:** Full model detects both UI elements AND cursor position

This enables:
- Cursor tracking
- Click-to-element mapping
- Noise filtering
- Precise interaction localization
