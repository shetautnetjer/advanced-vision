#!/usr/bin/env python3
"""
Verify model downloads and create status report.
Updated to work with NVFP4 quantized models.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def load_registry() -> Dict:
    """Load model registry."""
    registry_path = get_project_root() / "config" / "model_registry.json"
    try:
        with open(registry_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Registry file not found at {registry_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in registry file: {e}")
        sys.exit(1)


def check_model_files(model_id: str, model_data: Dict) -> Dict:
    """Check if model files exist."""
    project_root = get_project_root()
    models_dir = project_root / "models"
    
    checkpoint_rel = model_data["files"]["checkpoint"]
    checkpoint_path = project_root / checkpoint_rel
    
    tensorrt_rel = model_data["files"].get("tensorrt")
    tensorrt_path = project_root / tensorrt_rel if tensorrt_rel else None
    
    # Determine if model exists (handle both files and directories)
    if checkpoint_path.is_dir():
        # For directory models, check for model.safetensors or pytorch_model.bin
        has_weights = (
            (checkpoint_path / "model.safetensors").exists() or
            (checkpoint_path / "pytorch_model.bin").exists() or
            any(checkpoint_path.glob("*.safetensors"))
        )
        checkpoint_exists = has_weights
    else:
        checkpoint_exists = checkpoint_path.exists()
    
    result = {
        "id": model_id,
        "name": model_data["name"],
        "checkpoint_exists": checkpoint_exists,
        "checkpoint_path": str(checkpoint_path),
        "tensorrt_exists": tensorrt_path.exists() if tensorrt_path else False,
        "tensorrt_path": str(tensorrt_path) if tensorrt_path else None,
        "vram_gb": model_data["vram"].get("nvfp4_gb") or model_data["vram"].get("tensorrt_gb", 0),
        "residency": model_data["residency"],
        "quantization": model_data.get("quantization", "fp16"),
        "status": model_data.get("status", "unknown"),
    }
    
    # Calculate size if exists
    if checkpoint_path.exists():
        if checkpoint_path.is_dir():
            try:
                size = sum(f.stat().st_size for f in checkpoint_path.rglob("*") if f.is_file())
            except (OSError, PermissionError):
                size = 0
        else:
            try:
                size = checkpoint_path.stat().st_size
            except (OSError, PermissionError):
                size = 0
        result["size_gb"] = size / 1e9
    else:
        result["size_gb"] = 0
        
    return result


def print_report(results: List[Dict], registry: Dict):
    """Print verification report."""
    print("\n" + "="*70)
    print("MODEL VERIFICATION REPORT")
    print("="*70)
    
    available = []
    missing = []
    gated = []
    
    for result in results:
        if result["status"] == "gated":
            gated.append(result)
        elif result["checkpoint_exists"]:
            available.append(result)
        else:
            missing.append(result)
    
    # Available models
    print(f"\n✓ AVAILABLE MODELS ({len(available)}):")
    print("-"*70)
    if available:
        for r in available:
            size_str = f"{r['size_gb']:.2f} GB" if r['size_gb'] > 0 else "N/A"
            tensorrt_status = "[TRT]" if r["tensorrt_exists"] else "[pt]"
            quant_tag = f"[{r['quantization']}]" if r['quantization'] else ""
            print(f"  {tensorrt_status} {r['id']:<20} {size_str:<10} {quant_tag:<8} {r['name']}")
    else:
        print("  (none)")
    
    # Missing models
    if missing:
        print(f"\n✗ MISSING MODELS ({len(missing)}):")
        print("-"*70)
        for r in missing:
            print(f"  {r['id']:<20} {r['name']}")
            print(f"    Expected: {r['checkpoint_path']}")
    
    # Gated models
    if gated:
        print(f"\n🔒 GATED MODELS ({len(gated)}) - Requires Access:")
        print("-"*70)
        for r in gated:
            print(f"  {r['id']:<20} {r['name']}")
    
    # VRAM calculation
    print(f"\nVRAM ANALYSIS:")
    print("-"*70)
    
    resident_vram = sum(r["vram_gb"] for r in available if r["residency"] == "resident")
    ondemand_vram = sum(r["vram_gb"] for r in available if r["residency"] == "on_demand")
    
    # Get hardware target from registry
    hw_target = registry.get("hardware_target", {})
    vram_budget = hw_target.get("vram_budget_gb", 14.0)
    
    print(f"  Hardware: {hw_target.get('gpu', 'Unknown')}")
    print(f"  VRAM Budget: {vram_budget:.1f} GB")
    print(f"  Resident models VRAM:  {resident_vram:.1f} GB")
    print(f"  On-demand models VRAM: {ondemand_vram:.1f} GB (max single load)")
    print(f"  Total if all loaded:   {resident_vram + ondemand_vram:.1f} GB")
    print(f"  Budget check:          {'✓ OK' if resident_vram <= vram_budget else '✗ EXCEEDED'}")
    
    # Loading strategies
    print(f"\nLOADING STRATEGIES:")
    print("-"*70)
    strategies = registry.get("loading_strategies", {})
    for strategy_id, strategy in strategies.items():
        load_order = strategy.get("load_order", [])
        # Only count models that are available
        available_in_strategy = [m for m in load_order if m in [a["id"] for a in available]]
        vram_req = strategy.get("total_vram_nvfp4_gb", 0)
        print(f"  {strategy_id:<20} {len(available_in_strategy)}/{len(load_order)} models  ~{vram_req:.1f}GB VRAM")
        print(f"    {strategy.get('description', '')}")
    
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
    
    all_ok = print_report(results, registry)
    
    if not all_ok:
        print("\nTo download missing models:")
        print("  bash scripts/download_models.sh")
        print("  # or")
        print("  python scripts/download_model.py all")
        print("\nFor gated models (like SAM3), visit the HuggingFace page to request access.")
        sys.exit(1)
    else:
        print("\n✓ All models verified!")
        print("\nNext steps:")
        print("  1. Convert to TensorRT: bash scripts/optimize_tensorrt.sh")
        print("  2. Load standard session: python scripts/load_models.py strategy --strategy standard_trading")
        sys.exit(0)


if __name__ == "__main__":
    main()
