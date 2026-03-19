# YOLO Annotation Guide for Advanced Vision

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
