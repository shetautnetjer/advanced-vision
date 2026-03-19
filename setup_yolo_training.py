#!/usr/bin/env python3
"""
Custom YOLO Training Pipeline for Advanced Vision
Train specialized models:
- UI Model: Detect buttons, forms, modals, charts, ticket panels
- Trading Model: Detect patterns, support/resistance, candlesticks
- OR Combined Model: Both in one

Based on: VINS dataset methodology + YOLOv5R7s (94.7% mAP)
"""

import os
import sys
import json
import shutil
from pathlib import Path

def setup_project_structure():
    """Create YOLO training project structure."""
    print("="*60)
    print("SETTING UP YOLO TRAINING PROJECT")
    print("="*60)
    print()
    
    # Create directory structure
    dirs = [
        'yolo_training/data/images/train',
        'yolo_training/data/images/val',
        'yolo_training/data/images/test',
        'yolo_training/data/labels/train',
        'yolo_training/data/labels/val',
        'yolo_training/data/labels/test',
        'yolo_training/models',
        'yolo_training/runs',
        'yolo_training/annotations',
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"✅ Created: {d}")
    
    print()
    return True

def copy_screenshots_for_annotation():
    """Copy existing screenshots to annotation folder."""
    print("="*60)
    print("COPYING SCREENSHOTS FOR ANNOTATION")
    print("="*60)
    print()
    
    source_dir = 'artifacts/screens'
    target_dir = 'yolo_training/annotations/raw_images'
    
    if not os.path.exists(source_dir):
        print(f"❌ Source directory not found: {source_dir}")
        return False
    
    os.makedirs(target_dir, exist_ok=True)
    
    # Get large screenshots (real captures)
    screenshots = [
        f for f in os.listdir(source_dir)
        if f.endswith('.png') and os.path.getsize(os.path.join(source_dir, f)) > 100000
    ]
    
    print(f"Found {len(screenshots)} real screenshots")
    print()
    
    # Copy for annotation
    copied = 0
    for f in screenshots[:50]:  # First 50 for initial training
        src = os.path.join(source_dir, f)
        dst = os.path.join(target_dir, f)
        shutil.copy2(src, dst)
        copied += 1
    
    print(f"✅ Copied {copied} images to {target_dir}")
    print()
    print("Next steps:")
    print("  1. Install labelImg: pip install labelImg")
    print("  2. Run: labelImg yolo_training/annotations/raw_images")
    print("  3. Annotate UI elements and trading patterns")
    print()
    
    return True

def create_data_yaml(model_type='combined'):
    """Create data.yaml configuration for YOLO training."""
    
    if model_type == 'ui':
        classes = {
            0: 'button',
            1: 'text_input',
            2: 'checkbox',
            3: 'dropdown',
            4: 'modal',
            5: 'chart_area',
            6: 'ticket_panel',
            7: 'alert',
            8: 'menu',
            9: 'tab',
        }
    elif model_type == 'trading':
        classes = {
            0: 'candlestick',
            1: 'support_line',
            2: 'resistance_line',
            3: 'trend_line',
            4: ' breakout_pattern',
            5: 'consolidation',
            6: 'indicator',
            7: 'order_button',
        }
    else:  # combined
        classes = {
            0: 'button',
            1: 'text_input',
            2: 'modal',
            3: 'chart_area',
            4: 'ticket_panel',
            5: 'candlestick',
            6: 'support_resistance',
            7: 'indicator',
        }
    
    config = {
        'path': '../data',
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': len(classes),
        'names': classes,
    }
    
    yaml_path = f'yolo_training/data_{model_type}.yaml'
    with open(yaml_path, 'w') as f:
        f.write(f"# YOLO Training Configuration\n")
        f.write(f"# Model Type: {model_type}\n")
        f.write(f"path: {config['path']}\n")
        f.write(f"train: {config['train']}\n")
        f.write(f"val: {config['val']}\n")
        f.write(f"test: {config['test']}\n")
        f.write(f"\n")
        f.write(f"# Classes\n")
        f.write(f"nc: {config['nc']}\n")
        f.write(f"names:\n")
        for idx, name in classes.items():
            f.write(f"  {idx}: {name}\n")
    
    print(f"✅ Created: {yaml_path}")
    print(f"   Classes: {list(classes.values())}")
    print()
    
    return yaml_path

def create_training_script(model_type='combined'):
    """Create training script for the model."""
    
    script_content = f'''#!/bin/bash
# YOLO Training Script for {model_type.upper()} Model

# Configuration
MODEL_TYPE="{model_type}"
DATA_CONFIG="yolo_training/data_{model_type}.yaml"
EPOCHS=100
IMG_SIZE=640
BATCH_SIZE=16

# Create model config (YOLOv8n for speed, YOLOv8s for accuracy)
echo "Training {model_type} detection model..."
echo "Config: $DATA_CONFIG"
echo "Epochs: $EPOCHS"
echo "Image size: $IMG_SIZE"
echo "Batch size: $BATCH_SIZE"
echo ""

# Option 1: YOLOv8n (nano) - Fast, lightweight
echo "Option 1: Training YOLOv8n (fast)..."
yolo detect train \\
    data=$DATA_CONFIG \\
    model=yolov8n.pt \\
    epochs=$EPOCHS \\
    imgsz=$IMG_SIZE \\
    batch=$BATCH_SIZE \\
    project=yolo_training/runs \\
    name={model_type}_nano \\
    device=0

# Option 2: YOLOv8s (small) - Better accuracy
echo "Option 2: Training YOLOv8s (accurate)..."
yolo detect train \\
    data=$DATA_CONFIG \\
    model=yolov8s.pt \\
    epochs=$EPOCHS \\
    imgsz=$IMG_SIZE \\
    batch=$BATCH_SIZE \\
    project=yolo_training/runs \\
    name={model_type}_small \\
    device=0

echo ""
echo "Training complete!"
echo "Results in: yolo_training/runs/"
'''
    
    script_path = f'yolo_training/train_{model_type}.sh'
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"✅ Created: {script_path}")
    
    return script_path

def create_annotation_guide():
    """Create annotation guidelines document."""
    
    guide = """# YOLO Annotation Guide for Advanced Vision

## Setup

```bash
# Install labelImg
pip install labelImg

# Run annotation tool
labelImg yolo_training/annotations/raw_images
```

## Annotation Format

YOLO format: `class_id center_x center_y width height` (all normalized 0-1)

## UI Element Classes

| Class ID | Class Name | Description | Example |
|----------|------------|-------------|---------|
| 0 | button | Clickable buttons | "Submit", "OK", "Cancel" |
| 1 | text_input | Text entry fields | Email, password inputs |
| 2 | checkbox | Checkable boxes | Remember me, agree to terms |
| 3 | dropdown | Dropdown menus | Country selector, timeframes |
| 4 | modal | Modal dialogs | Confirmation dialogs, alerts |
| 5 | chart_area | Chart display area | Price chart, indicator chart |
| 6 | ticket_panel | Order/position panel | Buy/Sell ticket, position list |
| 7 | alert | Alert/notification | Price alerts, margin calls |
| 8 | menu | Menu/navigation | Top menu, sidebar |
| 9 | tab | Tab navigation | Chart tabs, timeframes |

## Trading Pattern Classes

| Class ID | Class Name | Description | Annotation Tips |
|----------|------------|-------------|-----------------|
| 0 | candlestick | Individual candles | Box around each candle |
| 1 | support_line | Support level line | Line annotation or tight box |
| 2 | resistance_line | Resistance level line | Line annotation or tight box |
| 3 | trend_line | Trend direction | Line following trend |
| 4 | breakout_pattern | Breakout formation | Box around breakout area |
| 5 | consolidation | Sideways movement | Box around consolidation zone |
| 6 | indicator | Technical indicator | RSI, MACD, Moving Average boxes |
| 7 | order_button | Buy/Sell buttons | "Buy", "Sell", "Close" buttons |

## Best Practices

1. **Tight bounding boxes**: Edges should touch object boundaries
2. **Occlusion**: If object is 50%+ visible, annotate. If less, skip.
3. **Multiple instances**: Annotate all visible instances
4. **Small objects**: Minimum 10x10 pixels for reliable detection
5. **Consistency**: Same object type = same class every time

## Workflow

1. Open labelImg
2. Set save format to YOLO (Ctrl+Shift+Y)
3. Load images from `yolo_training/annotations/raw_images`
4. Create bounding boxes for each object
5. Save annotations (Ctrl+S)
6. Annotations saved as `.txt` files with same name as image

## Data Split

- Training: 70% (35 images)
- Validation: 20% (10 images)
- Test: 10% (5 images)

## Expected Training Time

- YOLOv8n: ~30 minutes for 100 epochs (RTX 5070 Ti)
- YOLOv8s: ~1 hour for 100 epochs

## Target Performance

- mAP@0.5: > 0.80 (80% detection accuracy)
- Inference: < 50ms per frame (20+ FPS)
- Small object mAP: > 0.60
"""
    
    guide_path = 'yolo_training/ANNOTATION_GUIDE.md'
    with open(guide_path, 'w') as f:
        f.write(guide)
    
    print(f"✅ Created: {guide_path}")
    
    return guide_path

def print_next_steps():
    """Print next steps for the user."""
    print("="*60)
    print("NEXT STEPS TO TRAIN CUSTOM YOLO MODELS")
    print("="*60)
    print()
    print("1. ANNOTATE IMAGES")
    print("   pip install labelImg")
    print("   labelImg yolo_training/annotations/raw_images")
    print()
    print("2. SPLIT DATA")
    print("   - Copy 70% to yolo_training/data/images/train")
    print("   - Copy 20% to yolo_training/data/images/val")
    print("   - Copy 10% to yolo_training/data/images/test")
    print("   - Copy corresponding .txt labels to labels/ directories")
    print()
    print("3. TRAIN MODELS")
    print("   # UI Detection Model")
    print("   ./yolo_training/train_ui.sh")
    print()
    print("   # Trading Pattern Model")
    print("   ./yolo_training/train_trading.sh")
    print()
    print("   # Combined Model")
    print("   ./yolo_training/train_combined.sh")
    print()
    print("4. EVALUATE")
    print("   yolo detect val model=yolo_training/runs/ui_nano/weights/best.pt")
    print()
    print("5. EXPORT")
    print("   yolo export model=best.pt format=onnx")
    print("   yolo export model=best.pt format=tensorrt")
    print()
    print("Files created:")
    print("   - yolo_training/data_ui.yaml")
    print("   - yolo_training/data_trading.yaml")
    print("   - yolo_training/data_combined.yaml")
    print("   - yolo_training/train_ui.sh")
    print("   - yolo_training/train_trading.sh")
    print("   - yolo_training/train_combined.sh")
    print("   - yolo_training/ANNOTATION_GUIDE.md")
    print()

def main():
    print("="*60)
    print("CUSTOM YOLO TRAINING PIPELINE SETUP")
    print("="*60)
    print()
    print("This will set up training for:")
    print("  - UI Detection Model (buttons, forms, charts)")
    print("  - Trading Pattern Model (candlesticks, support/resistance)")
    print("  - Combined Model (both in one)")
    print()
    
    # Setup structure
    setup_project_structure()
    
    # Copy screenshots
    copy_screenshots_for_annotation()
    
    # Create configs
    print("="*60)
    print("CREATING TRAINING CONFIGURATIONS")
    print("="*60)
    print()
    
    create_data_yaml('ui')
    create_data_yaml('trading')
    create_data_yaml('combined')
    
    # Create training scripts
    print("="*60)
    print("CREATING TRAINING SCRIPTS")
    print("="*60)
    print()
    
    create_training_script('ui')
    create_training_script('trading')
    create_training_script('combined')
    
    # Create annotation guide
    create_annotation_guide()
    
    # Print next steps
    print_next_steps()
    
    print("✅ Setup complete!")

if __name__ == "__main__":
    main()
