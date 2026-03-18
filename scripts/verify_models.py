#!/usr/bin/env python3
"""
Verify model downloads and create status report.
"""

import json
from pathlib import Path
from typing import Dict, List
import sys

def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent

def load_registry() -> Dict:
    """Load model registry."""
    registry_path = get_project_root() / "config" / "model_registry.json"
    with open(registry_path) as f:
        return json.load(f)

def check_model_files(model_id: str, model_data: Dict) -> Dict:
    """Check if model files exist."""
    project_root = get_project_root()
    models_dir = project_root / "models"
    
    checkpoint_rel = model_data["files"]["checkpoint"]
    checkpoint_path = project_root / checkpoint_rel
    
    tensorrt_rel = model_data["files"].get("tensorrt")
    tensorrt_path = project_root / tensorrt_rel if tensorrt_rel else None
    
    result = {
        "id": model_id,
        "name": model_data["name"],
        "checkpoint_exists": checkpoint_path.exists(),
        "checkpoint_path": str(checkpoint_path),
        "tensorrt_exists": tensorrt_path.exists() if tensorrt_path else False,
        "tensorrt_path": str(tensorrt_path) if tensorrt_path else None,
        "vram_gb": model_data["vram"]["tensorrt_gb"],
        "residency": model_data["residency"]
    }
    
    # Calculate size if exists
    if checkpoint_path.exists():
        if checkpoint_path.is_dir():
            size = sum(f.stat().st_size for f in checkpoint_path.rglob("*") if f.is_file())
        else:
            size = checkpoint_path.stat().st_size
        result["size_gb"] = size / 1e9
    else:
        result["size_gb"] = 0
        
    return result

def print_report(results: List[Dict]):
    """Print verification report."""
    print("\n" + "="*70)
    print("MODEL VERIFICATION REPORT")
    print("="*70)
    
    available = []
    missing = []
    
    for result in results:
        if result["checkpoint_exists"]:
            available.append(result)
        else:
            missing.append(result)
    
    print(f"\n✓ AVAILABLE MODELS ({len(available)}):")
    print("-"*70)
    for r in available:
        size_str = f"{r['size_gb']:.2f} GB" if r['size_gb'] > 0 else "N/A"
        tensorrt_status = "[TRT]" if r["tensorrt_exists"] else "[pt]"
        print(f"  {tensorrt_status} {r['id']:20s} {size_str:10s} {r['name']}")
    
    if missing:
        print(f"\n✗ MISSING MODELS ({len(missing)}):")
        print("-"*70)
        for r in missing:
            print(f"  {r['id']:20s} {r['name']}")
            print(f"    Expected: {r['checkpoint_path']}")
    
    # VRAM calculation
    print(f"\nVRAM ANALYSIS:")
    print("-"*70)
    
    resident_vram = sum(r["vram_gb"] for r in available if r["residency"] == "resident")
    ondemand_vram = sum(r["vram_gb"] for r in available if r["residency"] == "on_demand")
    
    print(f"  Resident models VRAM:  {resident_vram:.1f} GB")
    print(f"  On-demand models VRAM: {ondemand_vram:.1f} GB (max single load)")
    print(f"  Total if all loaded:   {resident_vram + ondemand_vram:.1f} GB")
    print(f"  Budget (14 GB):        {'✓ OK' if resident_vram <= 14 else '✗ EXCEEDED'}")
    
    # Disk usage
    total_size = sum(r["size_gb"] for r in available)
    print(f"\nDISK USAGE:")
    print("-"*70)
    print(f"  Total model size: {total_size:.2f} GB")
    
    print("\n" + "="*70)
    
    # Return exit code
    return len(missing) == 0

def main():
    """Main verification function."""
    registry = load_registry()
    
    results = []
    for model_id, model_data in registry["models"].items():
        result = check_model_files(model_id, model_data)
        results.append(result)
    
    all_ok = print_report(results)
    
    if not all_ok:
        print("\nTo download missing models:")
        print("  bash scripts/download_models.sh")
        print("  # or")
        print("  python scripts/download_model.py all")
        sys.exit(1)
    else:
        print("\n✓ All models verified!")
        print("\nNext steps:")
        print("  1. Convert to TensorRT: bash scripts/optimize_tensorrt.sh")
        print("  2. Load standard session: python scripts/load_models.py strategy --strategy standard_trading")
        sys.exit(0)

if __name__ == "__main__":
    main()
