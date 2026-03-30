# YOLO Training Data Policy - UI Navigation Screenshots

**Date:** 2026-03-19  
**Source:** Computer Vision Session Screenshots  
**Purpose:** Training UI Navigation Models

## Screenshot Collection

### Source Location
```
/home/netjer/Projects/AI Frame/optical.nerves/advanced-vision/artifacts/screens/
```

### Files Generated Today
- `full_2026-03-20T00-XX-XX.XXXXXX+00-00.png` (20+ screenshots)
- Captured during: Screen unlock, Settings navigation, Terminal usage

### Content Categories

| Category | Count | Elements |
|----------|-------|----------|
| Lock Screens | 3 | Password prompt, time display, unlock UI |
| Desktop Overview | 4 | App switcher, window management, dock |
| Settings App | 8 | GNOME Settings pages, sidebar navigation |
| Terminal Windows | 3 | Command execution, terminal UI |
| Browser/OpenClaw | 5 | Web UI elements, navigation bars |
| IDE (VS Code) | 4 | Code editor, file explorer, panels |
| File Manager | 2 | File browsing, directory structure |
| Notifications | 2 | System notifications, alerts |

## Annotation Strategy

### Primary Labels

```yaml
ui_elements:
  - button: [clickable buttons, icons]
  - text_field: [input boxes, password fields]
  - sidebar: [navigation panels, menus]
  - window: [application windows, dialogs]
  - menu: [dropdowns, context menus]
  - icon: [app icons, system icons]
  - notification: [alerts, toasts]
  - terminal: [terminal windows, prompts]
  - search_bar: [search inputs, filters]
  - settings_page: [settings panels, options]
```

### Navigation-Specific Labels

```yaml
navigation_elements:
  - settings_icon: [gear/cog icons]
  - power_menu: [power options, shutdown]
  - window_controls: [minimize, maximize, close]
  - dock_item: [sidebar icons, launchers]
  - search_result: [app listings, files]
  - active_window: [focused window indicator]
```

## Training Approaches

### Option 1: YOLOv8/v9 for UI Element Detection

**Pros:**
- Fast inference (real-time)
- Good for bounding box detection
- Works on edge devices

**Cons:**
- Limited semantic understanding
- Doesn't understand hierarchy

**Use Case:** Find all clickable elements on screen

### Option 2: SAM (Segment Anything Model)

**Pros:**
- Precise segmentation masks
- Can segment any UI element
- Good for irregular shapes

**Cons:**
- Needs prompts (point/box)
- Slower than YOLO

**Use Case:** Precise element boundaries for clicking

### Option 3: BART/BORT for UI Understanding

**Pros:**
- Natural language understanding
- Can parse UI structure
- Context-aware reasoning

**Cons:**
- Not visual (needs OCR)
- Slower inference

**Use Case:** "Click on the Settings icon in the sidebar"

### Option 4: Multi-Modal (CLIP + SAM + LLM)

**Architecture:**
```
Screenshot → CLIP (understand content) → 
SAM (segment elements) → 
LLM (reason about actions) → 
Coordinates for click/type
```

**Pros:**
- Best accuracy
- Natural language commands
- Understands context

**Cons:**
- Complex pipeline
- Higher latency

## Recommended Hybrid Approach

### Phase 1: YOLO Element Detection
```python
# Detect all interactive elements
elements = yolo_model(image)
# Returns: [{class: 'button', bbox: [x1,y1,x2,y2], confidence: 0.95}, ...]
```

### Phase 2: SAM Refinement
```python
# Get precise mask for click target
mask = sam_model(image, point=(cx, cy))
# Returns: segmentation mask for accurate clicking
```

### Phase 3: LLM for Reasoning
```python
# Understand what to do with detected elements
action = llm_model(
    elements=elements,
    instruction="Open Settings and disable screen lock"
)
# Returns: {action: 'click', target: 'Settings icon', coordinates: [x,y]}
```

## Labeling Guidelines

### Bounding Box Rules
1. **Tight fit:** Box should touch element edges
2. **No overlap:** Separate boxes for each element
3. **Confidence:** Tag uncertain elements as `occluded` or `truncated`
4. **Hierarchy:** Label parent containers (window) and children (button)

### Text Annotation
- OCR all text fields for BART/BORT training
- Link text to bounding boxes
- Tag placeholder text vs user input

### Action Labels
```yaml
actions:
  - click: [buttons, icons, links]
  - type: [text fields, search bars]
  - scroll: [scrollable areas]
  - drag: [sliders, window resize]
  - wait: [loading states]
```

## Dataset Organization

```
yolo_training/
├── images/
│   ├── train/
│   │   ├── full_2026-03-20T00-33-05.png
│   │   └── ...
│   └── val/
│       └── ...
├── labels/
│   ├── train/
│   │   ├── full_2026-03-20T00-33-05.txt  # YOLO format
│   │   └── ...
│   └── val/
│       └── ...
├── annotations/  # SAM masks
│   ├── train/
│   └── val/
├── captions/  # BART training
│   └── descriptions.json
└── data.yaml  # YOLO config
```

## Training Pipeline

### Step 1: YOLO Training
```bash
yolo detect train \
  data=data.yaml \
  model=yolov8n.pt \
  epochs=100 \
  imgsz=1920x1080 \
  batch=16 \
  name=ui_navigation
```

### Step 2: SAM Fine-tuning
```bash
# Use YOLO detections as prompts
python train_sam.py \
  --images images/train/ \
  --masks annotations/train/ \
  --model vit_h \
  --epochs=10
```

### Step 3: LLM Integration
```python
# Fine-tune on UI action sequences
from transformers import BartForConditionalGeneration

model = BartForConditionalGeneration.from_pretrained('facebook/bart-large')
# Train on (screenshot_description, action_sequence) pairs
```

## Validation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| mAP@50 | >0.85 | Element detection accuracy |
| Click Accuracy | >95% | Correct element targeted |
| Navigation Success | >90% | Complete task completion |
| Latency | <500ms | End-to-end action time |

## Next Steps

1. **Label existing screenshots** (20+ images ready)
2. **Collect more diverse UI states**
   - Different applications
   - Error states
   - Loading screens
   - Notifications
3. **Train YOLO baseline**
4. **Integrate with SAM for refinement**
5. **Test on live system**

## Tools

- **Labeling:** labelImg, CVAT, Roboflow
- **YOLO:** Ultralytics YOLOv8
- **SAM:** Meta Segment Anything
- **LLM:** Hugging Face Transformers
- **Validation:** Custom test suite

---

**Status:** Dataset collected, ready for annotation
**Estimated Training Time:** 2-4 hours (YOLO), 8-12 hours (full pipeline)
