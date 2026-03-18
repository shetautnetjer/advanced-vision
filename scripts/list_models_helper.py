#!/usr/bin/env python3
"""Helper script to list models from registry for start_vllm.sh"""

import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage: list_models_helper.py <registry_file> <project_root>")
        sys.exit(1)
    
    registry_file = Path(sys.argv[1])
    project_root = Path(sys.argv[2])
    
    try:
        with open(registry_file) as f:
            registry = json.load(f)
    except Exception as e:
        print(f"Error reading registry: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Colors
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    NC = '\033[0m'
    
    for model_id, model in registry.get('models', {}).items():
        name = model.get('name', model_id)
        vram = model.get('vram', {})
        vram_gb = vram.get('nvfp4_gb') or vram.get('tensorrt_gb') or vram.get('fp16_gb', 0)
        role = model.get('role', 'unknown')
        quant = model.get('quantization', 'fp16')
        
        # Check if model exists
        checkpoint_rel = model.get('files', {}).get('checkpoint', '')
        checkpoint_path = project_root / checkpoint_rel
        
        if checkpoint_path.is_dir():
            has_weights = (
                (checkpoint_path / 'model.safetensors').exists() or
                (checkpoint_path / 'pytorch_model.bin').exists() or
                any(checkpoint_path.glob('*.safetensors'))
            )
        else:
            has_weights = checkpoint_path.exists()
        
        status = "✓" if has_weights else "✗"
        color = GREEN if has_weights else RED
        
        print(f"{color}{status}{NC} {model_id}")
        print(f"   Name: {name}")
        print(f"   Role: {role}, VRAM: ~{vram_gb:.1f}GB, Quant: {quant}")
        print(f"   Path: {checkpoint_path}")
        print()

if __name__ == "__main__":
    main()
