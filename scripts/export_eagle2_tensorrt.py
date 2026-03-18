#!/usr/bin/env python3
"""
Export Eagle2-2B to TensorRT format.
"""

import torch
from pathlib import Path
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_eagle2_tensorrt(models_dir: Path):
    """Export Eagle2-2B vision encoder to TensorRT."""
    
    eagle_dir = models_dir / "Eagle2-2B"
    if not eagle_dir.exists():
        logger.error(f"Eagle2-2B not found at {eagle_dir}")
        return False
    
    logger.info("Loading Eagle2-2B...")
    
    try:
        from transformers import AutoModelForVision2Seq, AutoProcessor
        
        model = AutoModelForVision2Seq.from_pretrained(
            str(eagle_dir),
            torch_dtype=torch.float16,
            device_map="cuda:0"
        )
        
        # Export vision tower to ONNX
        logger.info("Exporting vision tower to ONNX...")
        vision_tower = model.vision_tower
        vision_tower.eval()
        
        dummy_input = torch.randn(1, 3, 384, 384).half().cuda()
        onnx_path = eagle_dir / "eagle2_vision.onnx"
        
        torch.onnx.export(
            vision_tower,
            dummy_input,
            str(onnx_path),
            input_names=["images"],
            output_names=["features"],
            dynamic_axes={"images": {0: "batch"}, "features": {0: "batch"}},
            opset_version=17
        )
        
        logger.info(f"ONNX exported to {onnx_path}")
        
        # Convert to TensorRT using trtexec
        logger.info("Converting to TensorRT (this may take a few minutes)...")
        
        import subprocess
        engine_path = eagle_dir / "tensorrt" / "eagle2_vision.engine"
        engine_path.parent.mkdir(exist_ok=True)
        
        cmd = [
            "trtexec",
            f"--onnx={onnx_path}",
            f"--saveEngine={engine_path}",
            "--fp16",
            "--workspace=4096",
            "--minShapes=images:1x3x384x384",
            "--optShapes=images:4x3x384x384",
            "--maxShapes=images:8x3x384x384"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✓ TensorRT engine saved to {engine_path}")
            return True
        else:
            logger.error(f"TensorRT conversion failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", type=Path, default=Path("./models"))
    args = parser.parse_args()
    
    success = export_eagle2_tensorrt(args.models_dir)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    import sys
    main()
