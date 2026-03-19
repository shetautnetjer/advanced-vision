#!/bin/bash
# Quick Capture Script for Trading Platform Screenshots
# Usage: ./quick_capture.sh [count] [delay]

COUNT=${1:-10}
DELAY=${2:-2}

echo "======================================"
echo "Quick Trading Screenshot Capture"
echo "======================================"
echo ""
echo "Will capture $COUNT screenshots with ${DELAY}s delay"
echo "Output: yolo_training/annotations/raw_images/"
echo ""
echo "Switch to your trading platform NOW!"
echo "Starting in 5 seconds..."
echo ""

sleep 5

mkdir -p yolo_training/annotations/raw_images

for i in $(seq 1 $COUNT); do
    TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)
    FILENAME="trading_${i}_${TIMESTAMP}.png"
    OUTPUT="yolo_training/annotations/raw_images/$FILENAME"
    
    echo "Capturing $i/$COUNT: $FILENAME"
    
    # Try different capture methods
    if command -v gnome-screenshot &> /dev/null; then
        gnome-screenshot -f "$OUTPUT" 2>/dev/null
    elif command -v import &> /dev/null; then
        import -window root "$OUTPUT" 2>/dev/null
    else
        echo "❌ No screenshot tool found. Install gnome-screenshot or ImageMagick."
        exit 1
    fi
    
    if [ -f "$OUTPUT" ]; then
        echo "  ✅ Saved: $OUTPUT"
    else
        echo "  ❌ Failed to capture"
    fi
    
    if [ $i -lt $COUNT ]; then
        sleep $DELAY
    fi
done

echo ""
echo "======================================"
echo "Capture Complete!"
echo "======================================"
echo "Next steps:"
echo "  1. Label images: labelImg yolo_training/annotations/raw_images/"
echo "  2. Split by session"
echo "  3. Train: ./yolo_training/train_phase1_p0.sh"
