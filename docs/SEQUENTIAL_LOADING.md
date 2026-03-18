# Sequential Loading Strategy - VRAM Management

## Overview

This document defines the optimal model loading order and strategies for maintaining VRAM usage under 14GB on an RTX 5070 Ti (16GB total).

---

## Resident Models (Always Loaded During Trading)

These models form the core pipeline and remain loaded throughout trading sessions:

### Load Order (Sequential for Minimal Fragmentation) ⭐ UPDATED

```
Step 1: YOLOv8n (Nano)     [VRAM: 0.4 GB]  Total:  0.4 GB
Step 2: MobileSAM          [VRAM: 0.5 GB]  Total:  0.9 GB  ⭐ NEW
Step 3: Qwen2.5-VL-2B      [VRAM: 2.2 GB]  Total:  3.1 GB
Step 4: Eagle2-2B          [VRAM: 3.2 GB]  Total:  6.3 GB
Step 5: Stock Pattern YOLO [VRAM: 0.9 GB]  Total:  7.2 GB
─────────────────────────────────────────────────────────
Resident Subtotal:                        7.2 GB
Pipeline Overhead:                        0.5 GB
System/OS Reserve:                        1.5 GB
Safety Headroom:                          2.0 GB
─────────────────────────────────────────
Total Used:                              11.2 GB / 14 GB
Available for On-Demand:                  5.5 GB
```

### Why This Order?

1. **YOLOv8n First (Smallest)**
   - Loads quickly, provides immediate UI detection
   - Small footprint allows subsequent large models to fit
   - Detects trading interface elements ASAP

2. **MobileSAM Second (NEW - Keep Resident!)**
   - Only 0.5 GB VRAM - tiny footprint
   - 12ms inference - incredibly fast
   - Same SAM decoder - full compatibility
   - Always available for quick segmentation tasks
   - No need to load heavy SAM3 for most operations

3. **Qwen2.5-VL-2B Third**
   - Medium size fits in remaining contiguous space
   - Reviewer ready for detailed analysis

4. **Eagle2-2B Fourth**
   - Largest resident model
   - Loading after Qwen prevents fragmentation
   - Scout model ready for ROI classification

5. **Stock Pattern YOLO Last**
   - Smallest specialized model
   - Fits in remaining gaps
   - Chart pattern detection ready

---

## On-Demand Models (Load When Needed)

### Priority Queue

```python
ON_DEMAND_MODELS = {
    "yolov8s": {
        "priority": 1,      # Upgrade detection accuracy
        "vram_gb": 0.9,
        "load_time_ms": 600,
        "use_case": "Higher accuracy detection"
    },
    "sam2-tiny": {
        "priority": 2,      # Alternative segmentation
        "vram_gb": 0.7,
        "load_time_ms": 800,
        "use_case": "Lightweight segmentation (if MobileSAM insufficient)"
    },
    "sam3": {
        "priority": 3,      # Heavy precision mode - last resort
        "vram_gb": 2.4,
        "load_time_ms": 3500,
        "use_case": "Pixel-perfect segmentation (MobileSAM fallback)"
    }
}
```

**Note:** MobileSAM is now RESIDENT (0.5 GB). Only load SAM3 when:
- MobileSAM precision insufficient
- Complex multi-object segmentation needed
- Post-processing validation required
```

### On-Demand Loading Protocol

```python
class OnDemandLoader:
    """
    Context manager for safe on-demand model loading.
    Automatically handles loading/unloading with VRAM checks.
    """
    
    def __init__(self, model_id: str, swap_out: List[str] = None):
        self.model_id = model_id
        self.swap_out = swap_out or []  # Models to temporarily unload
        self.model = None
        
    def __enter__(self):
        # Check available VRAM
        available = get_available_vram_gb()
        required = ON_DEMAND_MODELS[self.model_id]["vram_gb"]
        
        if available < required:
            # Swap out lower priority models
            for swap_id in self.swap_out:
                if swap_id in LOADED_MODELS:
                    unload_model(swap_id)
                    
        # Load the on-demand model
        self.model = load_model(self.model_id)
        return self.model
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Always unload on-demand models
        if self.model:
            unload_model(self.model_id)
        
        # Restore swapped models if needed
        for swap_id in self.swap_out:
            if swap_id not in LOADED_MODELS:
                load_model(swap_id)


# Usage example:
def analyze_complex_pattern(image):
    # Temporarily load SAM3 for precise segmentation
    with OnDemandLoader("sam3", swap_out=["stock-pattern-yolo"]) as sam:
        mask = sam.segment(image)
        features = extract_features(mask)
    # SAM3 automatically unloaded, stock-pattern-yolo restored
    return features
```

---

## Loading Scenarios

### Scenario 1: Standard Trading Session

```python
def load_standard_session():
    """
    Full pipeline for active trading.
    VRAM Used: 7.2 GB (Resident) + 0 GB (On-demand) = 7.2 GB
    """
    load_model("yolov8n")
    load_model("mobilesam")      # ⭐ NEW - Always resident
    load_model("qwen2.5-vl-2b")
    load_model("eagle2-2b")
    load_model("stock-pattern-yolo")
    
    # On-demand available: YOLOv8s, SAM2-tiny, SAM3
    # MobileSAM handles most segmentation needs!
```

### Scenario 2: Deep Analysis Mode

```python
def load_deep_analysis():
    """
    High-accuracy mode with SAM3 fallback.
    VRAM Used: 7.2 GB (Resident) + 2.4 GB (SAM3) = 9.6 GB
    """
    # Standard resident set (includes MobileSAM)
    load_model("yolov8n")
    load_model("mobilesam")      # Quick segmentation always available
    load_model("qwen2.5-vl-2b")
    load_model("eagle2-2b")
    load_model("stock-pattern-yolo")
    
    # Only load SAM3 when MobileSAM insufficient
    with OnDemandLoader("sam3") as sam:
        result = sam.segment(very_complex_pattern)
```

### Scenario 3: Fast Scout Mode

```python
def load_fast_scout():
    """
    Minimal set for quick ROI detection.
    VRAM Used: 3.1 GB
    """
    load_model("yolov8n")
    load_model("mobilesam")      # Segmentation available
    load_model("qwen2.5-vl-2b")
    # Eagle and stock pattern loaded on-demand if ROI detected
```

### Scenario 4: MobileSAM-Only Minimal Mode

```python
def load_minimal():
    """
    Ultra-minimal for background monitoring.
    VRAM Used: 0.9 GB
    """
    load_model("yolov8n")
    load_model("mobilesam")      # Segmentation if needed
    # Everything else on-demand
```

### Scenario 4: Accuracy Swap Mode

```python
def swap_to_high_accuracy():
    """
    Temporarily upgrade detection accuracy.
    VRAM remains constant (swap, don't stack).
    """
    unload_model("yolov8n")      # Free 0.4 GB
    load_model("yolov8s")        # Use 0.9 GB
    # Net change: +0.5 GB (still within budget)
```

---

## VRAM Fragmentation Prevention

### Pre-allocation Strategy

```python
import torch

def preallocate_vram_pool():
    """
    Pre-allocate VRAM in contiguous blocks to prevent fragmentation.
    Call at startup before loading any models.
    """
    # Reserve a small buffer for PyTorch allocations
    torch.cuda.set_per_process_memory_fraction(0.875)  # 14GB of 16GB
    
    # Warm up CUDA context
    dummy = torch.randn(100, 100).cuda()
    del dummy
    torch.cuda.empty_cache()

def defragment_vram():
    """
    Force VRAM defragmentation.
    Use sparingly - causes brief pause.
    """
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    
    # Optional: Trigger GC
    import gc
    gc.collect()
```

### Loading Best Practices

```python
# ❌ BAD: Load large, then small (fragmentation)
load_model("eagle2-2b")    # 3.2 GB
load_model("yolov8n")      # 0.4 GB - leaves small gap
load_model("qwen2.5-vl")   # May not fit in fragmented space

# ✅ GOOD: Load small to large (defragmented)
load_model("yolov8n")      # 0.4 GB
load_model("stock-pattern") # 0.9 GB
load_model("qwen2.5-vl")   # 2.2 GB
load_model("eagle2-2b")    # 3.2 GB - contiguous allocation
```

---

## Emergency VRAM Recovery

```python
class VRAMManager:
    """
    Emergency VRAM recovery when approaching limit.
    """
    
    def __init__(self, threshold_gb: float = 13.0):
        self.threshold_gb = threshold_gb
        
    def check_and_recover(self):
        """Call periodically or before large allocations."""
        used_gb = get_used_vram_gb()
        
        if used_gb > self.threshold_gb:
            self._emergency_cleanup()
            
    def _emergency_cleanup(self):
        """Aggressive cleanup when near limit."""
        # 1. Clear caches
        torch.cuda.empty_cache()
        
        # 2. Unload lowest priority on-demand models
        for model_id in ["sam3", "yolov8s"]:
            if model_id in LOADED_MODELS:
                unload_model(model_id)
                
        # 3. Force synchronization
        torch.cuda.synchronize()
        
        # 4. If still critical, pause processing
        if get_used_vram_gb() > 14.5:
            self._critical_alert()
            
    def _critical_alert(self):
        """Notify system of critical VRAM state."""
        logger.error("CRITICAL: VRAM exhausted. Pausing pipeline.")
        # Trigger emergency handoff or pause
```

---

## Session State Transitions

```
┌─────────────┐     detect ROI      ┌─────────────┐
│   IDLE      │ ──────────────────▶ │ FAST SCOUT  │
│  (0 GB)     │                     │  (3.6 GB)   │
└─────────────┘                     └──────┬──────┘
       ▲                                   │ confirm pattern
       │                                   ▼
       │                            ┌─────────────┐
       └─────────────────────────── │   ACTIVE    │
         unload all                  │  (7.2 GB)   │
                                    └──────┬──────┘
                                           │ need precision
                                           ▼
                                    ┌─────────────┐
                                    │    DEEP     │
                                    │  ANALYSIS   │
                                    │  (9.1 GB)   │
                                    └─────────────┘
```

---

## Monitoring Dashboard

```python
def print_vram_status():
    """Real-time VRAM monitoring."""
    used = get_used_vram_gb()
    total = 16.0
    budget = 14.0
    
    print(f"VRAM Usage: {used:.1f}/{total:.1f} GB ({used/total*100:.1f}%)")
    print(f"Budget:     {used:.1f}/{budget:.1f} GB ({used/budget*100:.1f}%)")
    print(f"Headroom:   {budget-used:.1f} GB")
    print("")
    print("Loaded Models:")
    for model_id in LOADED_MODELS:
        vram = MODEL_REGISTRY[model_id]["vram"]["tensorrt_gb"]
        print(f"  • {model_id}: {vram:.1f} GB")
```

---

## Quick Reference

| Mode | Models | VRAM | Use Case |
|------|--------|------|----------|
| Idle | None | 0 GB | System startup |
| Fast Scout | YOLOv8n + Eagle2 | 3.6 GB | Quick ROI scan |
| Standard | All resident | 6.7 GB | Active trading |
| Deep Analysis | Standard + SAM3 | 9.1 GB | Complex patterns |
| Maximum | All loaded | 11.5 GB | Stress testing only |

---

## File Locations

```
config/
  └── model_registry.json      # Model definitions

scripts/
  ├── download_models.sh       # Download all models
  ├── download_model.py        # Granular download
  ├── load_models.py           # Loading orchestration
  └── optimize_tensorrt.sh     # TensorRT conversion

docs/
  ├── VRAM_USAGE.md            # Detailed VRAM breakdown
  ├── TENSORRT_OPTIMIZATION.md # Optimization guide
  └── SEQUENTIAL_LOADING.md    # This file
```
 # Granular download
  ├── load_models.py           # Loading orchestration
  └── optimize_tensorrt.sh     # TensorRT conversion

docs/
  ├── VRAM_USAGE.md            # Detailed VRAM breakdown
  ├── TENSORRT_OPTIMIZATION.md # Optimization guide
  └── SEQUENTIAL_LOADING.md    # This file
```
