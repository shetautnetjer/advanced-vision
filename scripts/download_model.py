#!/usr/bin/env python3
"""
Individual Model Download Scripts
Use these for granular control over model downloads
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

def get_models_dir() -> Path:
    """Get the models directory."""
    return Path(__file__).parent.parent / "models"

def download_eagle2(cache_dir: Optional[Path] = None) -> Path:
    """
    Download Eagle2-2B scout model.
    Size: ~4GB
    Purpose: Fast scout classification of ROI crops
    """
    from huggingface_hub import snapshot_download
    
    models_dir = get_models_dir()
    target_dir = models_dir / "Eagle2-2B"
    
    if target_dir.exists():
        print(f"✓ Eagle2-2B already exists at {target_dir}")
        return target_dir
    
    print("Downloading Eagle2-2B (~4GB)...")
    print("URL: https://huggingface.co/nvidia/Eagle2-2B")
    
    snapshot_download(
        repo_id="nvidia/Eagle2-2B",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        resume_download=True
    )
    
    print(f"✓ Eagle2-2B downloaded to {target_dir}")
    return target_dir

def download_eagle3(cache_dir: Optional[Path] = None) -> Path:
    """
    Download Eagle3 (alternative to Eagle2-2B).
    Faster with 0.26B head, but may have different capabilities.
    """
    from huggingface_hub import snapshot_download
    
    models_dir = get_models_dir()
    target_dir = models_dir / "Eagle3"
    
    if target_dir.exists():
        print(f"✓ Eagle3 already exists at {target_dir}")
        return target_dir
    
    print("Downloading Eagle3...")
    print("URL: https://huggingface.co/nvidia/Eagle3")
    
    try:
        snapshot_download(
            repo_id="nvidia/Eagle3",
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print(f"✓ Eagle3 downloaded to {target_dir}")
        return target_dir
    except Exception as e:
        print(f"⚠️ Eagle3 download failed: {e}")
        print("   Eagle3 may not be publicly available yet.")
        print("   Falling back to Eagle2-2B...")
        return download_eagle2(cache_dir)

def download_yolov8(variant: str = "n") -> Path:
    """
    Download YOLOv8 model.
    Variants: n (nano), s (small), m (medium), l (large), x (xlarge)
    
    For trading pipeline, recommended:
    - yolov8n.pt: Always-on, fast detection (~6MB)
    - yolov8s.pt: Higher accuracy when needed (~23MB)
    """
    from ultralytics import YOLO
    import shutil
    
    models_dir = get_models_dir() / "yolov8"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = models_dir / f"yolov8{variant}.pt"
    
    if target_path.exists():
        print(f"✓ yolov8{variant}.pt already exists")
        return target_path
    
    print(f"Downloading yolov8{variant}.pt...")
    model = YOLO(f"yolov8{variant}.pt")
    
    # Move from current directory to models
    source = Path(f"yolov8{variant}.pt")
    if source.exists():
        shutil.move(str(source), str(target_path))
    
    print(f"✓ yolov8{variant}.pt ready at {target_path}")
    return target_path

def download_sam3() -> Optional[Path]:
    """
    Download SAM3 (Segment Anything Model 3).
    Size: ~2.4GB
    Purpose: Pixel-precision segmentation on demand
    
    Note: Gated model - requires HF access approval
    """
    from huggingface_hub import snapshot_download, HfApi
    from huggingface_hub.utils import GatedRepoError
    
    models_dir = get_models_dir()
    target_dir = models_dir / "sam3"
    
    if target_dir.exists():
        print(f"✓ SAM3 already exists at {target_dir}")
        return target_dir
    
    print("Downloading SAM3 (~2.4GB)...")
    print("URL: https://huggingface.co/facebook/sam3")
    print("⚠️  This is a gated model - requires HF access approval")
    
    try:
        snapshot_download(
            repo_id="facebook/sam3",
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print(f"✓ SAM3 downloaded to {target_dir}")
        return target_dir
    except GatedRepoError:
        print("❌ SAM3 access denied. You need to:")
        print("   1. Visit https://huggingface.co/facebook/sam3")
        print("   2. Accept the license agreement")
        print("   3. Run: huggingface-cli login")
        print("")
        print("   See download_sam2_tiny() or download_mobilesam() for alternatives")
        return None
    except Exception as e:
        print(f"❌ SAM3 download failed: {e}")
        return None

def download_sam2_tiny() -> Path:
    """
    Download SAM2-tiny as lightweight alternative to SAM3.
    Much smaller, faster, but less precise.
    """
    from huggingface_hub import snapshot_download
    
    models_dir = get_models_dir()
    target_dir = models_dir / "sam2-tiny"
    
    if target_dir.exists():
        print(f"✓ SAM2-tiny already exists at {target_dir}")
        return target_dir
    
    print("Downloading SAM2-tiny (lightweight alternative)...")
    
    snapshot_download(
        repo_id="facebook/sam2-hiera-tiny",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        resume_download=True
    )
    
    print(f"✓ SAM2-tiny downloaded to {target_dir}")
    return target_dir

def download_mobilesam() -> Path:
    """
    Download MobileSAM for mobile/edge deployment.
    Extremely lightweight segmentation.
    """
    from huggingface_hub import snapshot_download
    
    models_dir = get_models_dir()
    target_dir = models_dir / "mobilesam"
    
    if target_dir.exists():
        print(f"✓ MobileSAM already exists at {target_dir}")
        return target_dir
    
    print("Downloading MobileSAM...")
    
    snapshot_download(
        repo_id="chaoningzhang/mobilesam",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        resume_download=True
    )
    
    print(f"✓ MobileSAM downloaded to {target_dir}")
    return target_dir

def download_stock_pattern_yolo() -> Path:
    """
    Download specialized stock pattern detection model.
    Purpose: Detect Head & Shoulders, triangles, W-bottom patterns
    """
    from huggingface_hub import snapshot_download
    
    models_dir = get_models_dir()
    target_dir = models_dir / "stock-pattern-yolo"
    
    if target_dir.exists():
        print(f"✓ Stock Pattern YOLO already exists at {target_dir}")
        return target_dir
    
    print("Downloading Stock Pattern YOLO...")
    print("URL: https://huggingface.co/foduucom/stockmarket-pattern-detection-yolov8")
    print("Purpose: Detect H&S, triangles, W-bottom in charts")
    
    snapshot_download(
        repo_id="foduucom/stockmarket-pattern-detection-yolov8",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        resume_download=True
    )
    
    print(f"✓ Stock Pattern YOLO downloaded to {target_dir}")
    return target_dir

def main():
    parser = argparse.ArgumentParser(description="Download vision models for trading pipeline")
    parser.add_argument(
        "model",
        choices=["eagle2", "eagle3", "yolov8n", "yolov8s", "sam3", "sam2-tiny", "mobilesam", "stock-pattern", "all"],
        help="Model to download"
    )
    parser.add_argument("--priority", action="store_true", help="Download priority models only (Qwen, MobileSAM, Eagle2, YOLO)")
    parser.add_argument("--check-only", action="store_true", help="Check if model exists without downloading")
    
    args = parser.parse_args()
    
    if args.check_only:
        models_dir = get_models_dir()
        print(f"Checking models in: {models_dir}")
        if models_dir.exists():
            for item in models_dir.iterdir():
                if item.is_dir():
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    print(f"  {item.name}: {size / 1e9:.2f} GB")
        return
    
    # Download requested model
    if args.model == "eagle2":
        download_eagle2()
    elif args.model == "eagle3":
        download_eagle3()
    elif args.model == "yolov8n":
        download_yolov8("n")
    elif args.model == "yolov8s":
        download_yolov8("s")
    elif args.model == "sam3":
        download_sam3()
    elif args.model == "sam2-tiny":
        download_sam2_tiny()
    elif args.model == "mobilesam":
        download_mobilesam()
    elif args.model == "stock-pattern":
        download_stock_pattern_yolo()
    elif args.model == "all":
        print("Downloading all models...")
        download_eagle2()
        download_yolov8("n")
        download_yolov8("s")
        result = download_sam3()
        if result is None:
            print("Falling back to SAM2-tiny...")
            download_sam2_tiny()
        download_stock_pattern_yolo()
        print("\n✓ All models downloaded!")

if __name__ == "__main__":
    main()
