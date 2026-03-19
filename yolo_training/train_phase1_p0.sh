#!/bin/bash
# YOLO Training Script — Phase 1 P0 Narrow Class Set
# 6 classes: chart_panel, order_ticket, primary_action_button, confirm_modal, alert_indicator, position_panel

set -e

DATA_CONFIG="yolo_training/data_phase1_p0.yaml"
EPOCHS=100
IMG_SIZE=640
BATCH_SIZE=16

echo "=========================================="
echo "YOLO Phase 1 Training — P0 Narrow Classes"
echo "=========================================="
echo ""
echo "Config: $DATA_CONFIG"
echo "Epochs: $EPOCHS"
echo "Image size: $IMG_SIZE"
echo "Batch size: $BATCH_SIZE"
echo ""
echo "Classes:"
echo "  0: chart_panel"
echo "  1: order_ticket"
echo "  2: primary_action_button"
echo "  3: confirm_modal"
echo "  4: alert_indicator"
echo "  5: position_panel"
echo ""
echo "Goal: Reliable ROI boxing for scout/reviewer loop"
echo "Target: mAP@0.5 > 0.75, inference < 50ms"
echo ""

# Check data exists
if [ ! -f "$DATA_CONFIG" ]; then
    echo "❌ Data config not found: $DATA_CONFIG"
    exit 1
fi

# Check images exist
TRAIN_IMAGES=$(find yolo_training/data/images/train -name "*.png" 2>/dev/null | wc -l)
VAL_IMAGES=$(find yolo_training/data/images/val -name "*.png" 2>/dev/null | wc -l)

echo "Dataset:"
echo "  Train images: $TRAIN_IMAGES"
echo "  Val images: $VAL_IMAGES"
echo ""

if [ "$TRAIN_IMAGES" -eq 0 ]; then
    echo "❌ No training images found!"
    echo "   Run: labelImg yolo_training/annotations/raw_images"
    echo "   Then split into train/val/test by SESSION"
    exit 1
fi

# Train YOLOv8n (fast)
echo "Training YOLOv8n (nano) — fastest..."
yolo detect train \
    data=$DATA_CONFIG \
    model=yolov8n.pt \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    project=yolo_training/runs \
    name=phase1_p0_nano \
    device=0

# Train YOLOv8s (more accurate)
echo ""
echo "Training YOLOv8s (small) — more accurate..."
yolo detect train \
    data=$DATA_CONFIG \
    model=yolov8s.pt \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    project=yolo_training/runs \
    name=phase1_p0_small \
    device=0

echo ""
echo "=========================================="
echo "Training Complete!"
echo "=========================================="
echo ""
echo "Results:"
echo "  Nano: yolo_training/runs/phase1_p0_nano/"
echo "  Small: yolo_training/runs/phase1_p0_small/"
echo ""
echo "Evaluate:"
echo "  yolo detect val model=yolo_training/runs/phase1_p0_nano/weights/best.pt"
echo ""
echo "Test on image:"
echo "  yolo detect predict model=yolo_training/runs/phase1_p0_nano/weights/best.pt source=test_image.png"
echo ""
echo "Export:"
echo "  yolo export model=yolo_training/runs/phase1_p0_nano/weights/best.pt format=tensorrt"
