#!/bin/bash
# YOLO Training Script for TRADING Model

# Configuration
MODEL_TYPE="trading"
DATA_CONFIG="yolo_training/data_trading.yaml"
EPOCHS=100
IMG_SIZE=640
BATCH_SIZE=16

# Create model config (YOLOv8n for speed, YOLOv8s for accuracy)
echo "Training trading detection model..."
echo "Config: $DATA_CONFIG"
echo "Epochs: $EPOCHS"
echo "Image size: $IMG_SIZE"
echo "Batch size: $BATCH_SIZE"
echo ""

# Option 1: YOLOv8n (nano) - Fast, lightweight
echo "Option 1: Training YOLOv8n (fast)..."
yolo detect train \
    data=$DATA_CONFIG \
    model=yolov8n.pt \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    project=yolo_training/runs \
    name=trading_nano \
    device=0

# Option 2: YOLOv8s (small) - Better accuracy
echo "Option 2: Training YOLOv8s (accurate)..."
yolo detect train \
    data=$DATA_CONFIG \
    model=yolov8s.pt \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    project=yolo_training/runs \
    name=trading_small \
    device=0

echo ""
echo "Training complete!"
echo "Results in: yolo_training/runs/"
