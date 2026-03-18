#!/bin/bash
# =============================================================================
# Advanced Vision Trading Pipeline - Model Download Script
# =============================================================================
# Downloads all required vision models for the trading pipeline
# Target: RTX 5070 Ti 16GB (keep under 14GB concurrent)
# =============================================================================

set -e

# Configuration
MODELS_DIR="${1:-./models}"
HF_CACHE_DIR="${2:-$HOME/.cache/huggingface}"
mkdir -p "$MODELS_DIR"

echo "============================================================"
echo "Advanced Vision Trading Pipeline - Model Downloader"
echo "============================================================"
echo "Models directory: $MODELS_DIR"
echo "HuggingFace cache: $HF_CACHE_DIR"
echo ""

# Check for huggingface-cli
if ! command -v huggingface-cli &> /dev/null; then
    echo "⚠️  huggingface-cli not found. Installing..."
    pip install -q huggingface-hub
fi

# Check for git-lfs (required for large models)
if ! command -v git-lfs &> /dev/null; then
    echo "⚠️  git-lfs not found. Large model downloads may fail."
    echo "   Install: apt-get install git-lfs  (Ubuntu/Debian)"
    echo "            brew install git-lfs     (macOS)"
fi

echo ""
echo "============================================================"
echo "1/4: Downloading Eagle2-2B (Scout Model) ~4GB"
echo "============================================================"
echo "Purpose: Fast scout classification of ROI crops"
echo "URL: https://huggingface.co/nvidia/Eagle2-2B"
echo ""

if [ -d "$MODELS_DIR/Eagle2-2B" ]; then
    echo "✓ Eagle2-2B already exists, skipping..."
else
    huggingface-cli download nvidia/Eagle2-2B \
        --local-dir "$MODELS_DIR/Eagle2-2B" \
        --local-dir-use-symlinks False \
        --resume-download
    echo "✓ Eagle2-2B downloaded"
fi

echo ""
echo "============================================================"
echo "2/4: Downloading YOLOv8 Models (Detection Backbone)"
echo "============================================================"
echo "Purpose: Tripwire detection, UI element detection"
echo "Models: yolov8n.pt (nano, fast) + yolov8s.pt (small, balanced)"
echo ""

# Create YOLO directory
mkdir -p "$MODELS_DIR/yolov8"

# Download via Python (ultralytics auto-downloads)
python3 << 'PYTHON_EOF'
import os
from pathlib import Path

models_dir = Path(os.environ.get("MODELS_DIR", "./models")) / "yolov8"
models_dir.mkdir(parents=True, exist_ok=True)

try:
    from ultralytics import YOLO
    print("Using ultralytics to download YOLOv8 models...")
    
    # Download nano (fastest)
    print("Downloading yolov8n.pt...")
    model_n = YOLO("yolov8n.pt")
    # Move to our models directory
    import shutil
    src = Path("yolov8n.pt")
    if src.exists():
        shutil.move(str(src), str(models_dir / "yolov8n.pt"))
    print("✓ yolov8n.pt ready")
    
    # Download small (balanced)
    print("Downloading yolov8s.pt...")
    model_s = YOLO("yolov8s.pt")
    src = Path("yolov8s.pt")
    if src.exists():
        shutil.move(str(src), str(models_dir / "yolov8s.pt"))
    print("✓ yolov8s.pt ready")
    
except ImportError:
    print("⚠️  ultralytics not installed. Attempting manual download...")
    import urllib.request
    
    base_url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/"
    
    for model in ["yolov8n.pt", "yolov8s.pt"]:
        target = models_dir / model
        if target.exists():
            print(f"✓ {model} already exists")
            continue
        print(f"Downloading {model}...")
        urllib.request.urlretrieve(base_url + model, str(target))
        print(f"✓ {model} downloaded")

print("✓ YOLOv8 models ready")
PYTHON_EOF

echo ""
echo "============================================================"
echo "3/5: Downloading MobileSAM (Lightweight Segmentation) ~10MB"
echo "============================================================"
echo "Purpose: Fast segmentation - CAN STAY RESIDENT"
echo "URL: https://huggingface.co/chaoningzhang/mobilesam"
echo "Speed: ~12ms/image | VRAM: ~500MB"
echo "Note: Same mask decoder as SAM, TinyViT encoder (5M params)"
echo ""

if [ -d "$MODELS_DIR/mobilesam" ]; then
    echo "✓ MobileSAM already exists, skipping..."
else
    huggingface-cli download chaoningzhang/mobilesam \
        --local-dir "$MODELS_DIR/mobilesam" \
        --local-dir-use-symlinks False \
        --resume-download
    echo "✓ MobileSAM downloaded"
fi

echo ""
echo "============================================================"
echo "4/5: Downloading SAM3 (Segmentation - Precision Mode) ~2.4GB"
echo "============================================================"
echo "Purpose: Pixel-precision segmentation on demand (fallback)"
echo "URL: https://huggingface.co/facebook/sam3"
echo "Note: Gated model - may require HF access approval"
echo "      MobileSAM preferred for resident use"
echo ""

if [ -d "$MODELS_DIR/sam3" ]; then
    echo "✓ SAM3 already exists, skipping..."
else
    echo "⚠️  SAM3 is a gated model. Checking access..."
    if huggingface-cli download facebook/sam3 --include "config.json" --local-dir /tmp/sam3_test 2>/dev/null; then
        rm -rf /tmp/sam3_test
        huggingface-cli download facebook/sam3 \
            --local-dir "$MODELS_DIR/sam3" \
            --local-dir-use-symlinks False \
            --resume-download
        echo "✓ SAM3 downloaded"
    else
        echo "❌ SAM3 access denied. You need to:"
        echo "   1. Visit https://huggingface.co/facebook/sam3"
        echo "   2. Accept the license agreement"
        echo "   3. Run: huggingface-cli login"
        echo ""
        echo "   ✓ MobileSAM already available as resident alternative"
    fi
fi

echo ""
echo "============================================================"
echo "5/5: Downloading Stock Pattern YOLO (Specialized)"
echo "============================================================"
echo "Purpose: Detect H&S, triangles, W-bottom in charts"
echo "URL: https://huggingface.co/foduucom/stockmarket-pattern-detection-yolov8"
echo ""

if [ -d "$MODELS_DIR/stock-pattern-yolo" ]; then
    echo "✓ Stock Pattern YOLO already exists, skipping..."
else
    huggingface-cli download foduucom/stockmarket-pattern-detection-yolov8 \
        --local-dir "$MODELS_DIR/stock-pattern-yolo" \
        --local-dir-use-symlinks False \
        --resume-download
    echo "✓ Stock Pattern YOLO downloaded"
fi

echo ""
echo "============================================================"
echo "Download Summary"
echo "============================================================"
echo ""
echo "Installed models in: $MODELS_DIR"
du -sh "$MODELS_DIR"/* 2>/dev/null || echo "(directory listing failed)"
echo ""
echo "Next steps:"
echo "  1. Verify models: python scripts/verify_models.py"
echo "  2. Check VRAM: python scripts/check_vram.py"
echo "  3. Optimize for TensorRT: bash scripts/optimize_tensorrt.sh"
echo ""
echo "============================================================"
