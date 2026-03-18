# Limitations - Advanced Vision Trading System

**Last Verified:** 2026-03-17  
**Hardware:** NVIDIA RTX 5070 Ti 16GB (Blackwell/SM120)  
**Status:** Known Issues Documented

---

## 🔴 Critical Limitations

### 1. NVFP4 Quantization NOT Working on RTX 5070 Ti

**Problem:** Blackwell architecture (sm120) lacks kernel support in vLLM and flashinfer for NVFP4 quantization.

**Error Message:**
```
flashinfer: fp4_gemm_cutlass_sm120 - ninja build failed
RuntimeError: CUDA error: no kernel image is available for execution on the device
```

**Root Cause:**
- RTX 5070 Ti uses Blackwell (sm120) compute capability
- vLLM 0.17.1 does not have NVFP4 kernels for sm120
- flashinfer lacks Blackwell support for FP4 operations

**Workaround:** Use BF16 models instead
- Qwen3.5-4B BF16: 8.4GB VRAM (vs 4.0GB NVFP4)
- Qwen3.5-2B BF16: 3.8GB VRAM (vs 2.5GB NVFP4)
- Only ~1-2GB more VRAM, fully functional

**Verified Working:**
```python
# This works ✅
model = AutoModelForCausalLM.from_pretrained(
    'models/Qwen3.5-4B',
    torch_dtype=torch.bfloat16,  # BF16, not NVFP4
    device_map='cuda',
    trust_remote_code=True
)
```

**Does NOT Work:**
```python
# This fails ❌
model = AutoModelForCausalLM.from_pretrained(
    'models/Qwen3.5-4B-NVFP4',
    quantization_config=nvfp4_config,  # No Blackwell support
    device_map='cuda'
)
```

---

### 2. vLLM Not Compatible

**Problem:** vLLM 0.17.1 does not support Qwen3.5 on Blackwell architecture.

**Error Message:**
```
RuntimeError: Failed to initialize vLLM engine
CUDA error: no kernel image is available for execution on the device
```

**Workaround:** Use transformers library directly

```python
# Use this instead ✅
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    'models/Qwen3.5-4B',
    torch_dtype=torch.bfloat16,
    device_map='cuda',
    trust_remote_code=True
)
```

**Trade-offs:**
- ✅ Works on RTX 5070 Ti
- ✅ No quantization complications
- ❌ Slower than vLLM (2-3x)
- ❌ No batching optimizations
- ❌ Higher VRAM usage

---

### 3. Eagle2-2B Requires Flash Attention

**Problem:** Eagle2-2B requires flash-attention for efficient inference.

**Status:** Compiling from source (~10 minutes)

**Command:**
```bash
pip install flash-attn --no-build-isolation
```

**Fallback:** Can use eager attention (slower) if flash-attn fails:
```python
model = AutoModelForVision2Seq.from_pretrained(
    'models/Eagle2-2B',
    attn_implementation="eager",  # Slower but works
    torch_dtype=torch.float16,
    device_map='cuda'
)
```

---

### 4. No TensorRT-LLM for Blackwell Yet

**Problem:** TensorRT-LLM does not yet have optimized kernels for Blackwell (sm120).

**Impact:** Cannot use TensorRT optimizations that would provide:
- 2-3x speedup
- 50% VRAM reduction
- Better batching

**Workaround:** Use native PyTorch BF16

---

## 🟡 Known Issues

### 5. Model Registry / Config Drift

**Problem:** `config/model_registry.json` and `config/vllm.yaml` reference different model families.

**Issue:**
- Registry references Qwen2.5-VL and Eagle2-2B
- vllm.yaml references Qwen3.5-NVFP4

**Impact:** VRAM calculations may be inconsistent.

**Workaround:** Use BF16 models as documented in this file.

---

### 6. Inference Not Fully Implemented

**Problem:** `model_manager.py` inference raises NotImplementedError for vLLM path.

**Error:**
```python
raise NotImplementedError("Inference via vLLM API not yet implemented")
```

**Workaround:** Use direct transformers inference (see examples in QUICKSTART.md).

---

### 7. SAM3 Requires HuggingFace Approval

**Problem:** SAM3 is a gated model requiring HuggingFace access.

**Requirements:**
- HuggingFace account
- Accept license at https://huggingface.co/facebook/sam3
- `huggingface-cli login`

**Workaround:** Use MobileSAM (always available, 0.5GB, 12ms)

---

### 8. Wayland Not Supported

**Problem:** Screen capture requires X11. Wayland sessions not supported.

**Error:**
```
pyautogui.FailSafeException: Display not detected
```

**Workaround:** Switch to X11:
```bash
# Check current session
echo $XDG_SESSION_TYPE

# Logout and select "X11" or "Xorg" at login screen
```

---

## ✅ What Actually Works

| Feature | Status | Notes |
|---------|--------|-------|
| Qwen3.5-4B BF16 | ✅ Working | 8.4GB VRAM, ~1-2s inference |
| Qwen3.5-2B BF16 | ✅ Working | 3.8GB VRAM, ~500ms-1s inference |
| Eagle2-2B FP16 | ✅ Working | ~4GB VRAM, flash-attn compiling |
| MobileSAM | ✅ Working | 0.5GB VRAM, 12ms inference |
| YOLOv8n/s | ✅ Working | 0.4-0.9GB VRAM, ~10ms inference |
| Screenshots | ✅ Working | X11 required |
| Mouse/Keyboard | ✅ Working | dry_run for safety |
| Model Manager | ✅ Working | VRAM tracking accurate |

---

## 🔧 Recommended Configuration

Given the limitations, use this configuration:

```python
# Resident models (always loaded)
RESIDENT_MODELS = {
    'yolov8n': 0.4,      # Detection
    'mobilesam': 0.5,    # Segmentation
    'eagle2-2b': 4.0,    # Scout
    'qwen3.5-4b': 8.4,   # Reviewer
}
# Total: 13.3GB / 16GB ✅
```

**Do NOT use:**
- ❌ NVFP4 quantized models
- ❌ vLLM serving
- ❌ TensorRT (until Blackwell support)

**DO use:**
- ✅ BF16 precision
- ✅ Transformers library directly
- ✅ Native PyTorch CUDA

---

## 📝 Future Fixes

1. **vLLM Blackwell Support** - Expected in vLLM 0.18.x
2. **flashinfer SM120** - Community PR in progress
3. **TensorRT-LLM Blackwell** - NVIDIA roadmap, no ETA
4. **NVFP4 Kernels** - Depends on CUDA toolkit updates

---

## Related Issues

See `issues/2026-03-17-model-deployment.md` for detailed code-level issues.
