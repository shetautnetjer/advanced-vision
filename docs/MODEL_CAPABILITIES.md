# Model Capabilities & Settings — Advanced Vision Brain

**Last Updated:** 2026-03-18  
**Hardware:** RTX 5070 Ti 16GB  
**VRAM Budget:** 14GB (2GB reserved for system)

---

## Current Model Settings Overview

| Model | Role | Residency | VRAM | Quantization | Inference Framework | Speed |
|-------|------|-----------|------|--------------|---------------------|-------|
| **Eagle2-2B** | Scout | Resident | 3.2GB | FP16 (TensorRT) | transformers 4.37.2 | ~300-500ms/image |
| **Qwen3.5-4B-NVFP4** | Reviewer | On-demand | 4.0GB | NVFP4 | vLLM | ~2-3s/analysis |
| **Qwen3.5-2B-NVFP4** | Backup | On-demand | 2.5GB | NVFP4 | vLLM | ~1-2s/analysis |
| **MobileSAM** | Segmentation | Resident | 0.5GB | FP16 | Native | 12ms/image |
| **YOLOv8n** | Detection | Resident | 0.4GB | TensorRT | TensorRT | <50ms/frame |
| **YOLOv8s** | Detection (accurate) | On-demand | 0.9GB | TensorRT | TensorRT | ~100ms/frame |

**VRAM Savings:** 2.5GB freed by making Qwen2B on-demand (was resident)

---

## Model-by-Model Capabilities

### Eagle2-2B (Primary Scout)

**Settings:**
```yaml
path: models/Eagle2-2B
quantization: fp16
vram: 3.2GB
max_batch_size: 4
max_model_len: 4096
inference: transformers==4.37.2  # NOT vLLM
```

**What It Can Do:**
- ✅ Fast ROI crop classification (~300-500ms)
- ✅ Screen analysis (what changed, why it matters)
- ✅ Pattern detection (charts, UI elements)
- ✅ Basic UI element classification (button, modal, form)
- ✅ Scout notes (recommendations for next steps)

**What It CANNOT Do (Current Settings):**
- ❌ Deep reasoning (limited to fast classification)
- ❌ Multi-chart analysis (context window too small)
- ❌ Complex trading signal validation
- ❌ Long-form text generation

**Test Coverage:**
- Located: `tests/test_governed_pipeline.py` (lines testing Eagle integration)
- Gitignored: Model weights (4GB in `models/Eagle2-2B/`)

---

### Qwen3.5-4B-NVFP4 (Primary Reviewer)

**Settings:**
```yaml
path: models/Qwen3.5-4B-NVFP4
quantization: nvfp4
vram: 4.0GB
max_batch_size: 8
max_model_len: 32768
inference: vLLM
env:
  VLLM_NVFP4_GEMM_BACKEND: marlin
  VLLM_TEST_FORCE_FP8_MARLIN: 1
```

**What It Can Do:**
- ✅ Deep chart analysis (multi-timeframe)
- ✅ Trading signal validation
- ✅ Complex reasoning with thinking mode
- ✅ Multi-chart correlation analysis
- ✅ Risk assessment (high/medium/low)
- ✅ Long-form explanations (up to 32k tokens)

**What It CANNOT Do (Current Settings):**
- ❌ Real-time inference (2-3s latency too slow for hot path)
- ❌ Resident operation (VRAM constraints)
- ❌ Batch > 8 (memory limits)

**Test Coverage:**
- Located: `tests/test_trading.py` (reviewer tests)
- Gitignored: Model weights (4GB in `models/Qwen3.5-4B-NVFP4/`)

---

### Qwen3.5-2B-NVFP4 (Backup/Light Tasks)

**Settings:**
```yaml
path: models/Qwen3.5-2B-NVFP4
quantization: nvfp4
vram: 2.5GB
max_batch_size: 16
max_model_len: 32768
inference: vLLM
role: expert (on-demand)
```

**What It Can Do:**
- ✅ Light analysis (faster than 4B)
- ✅ Backup when 4B unavailable
- ✅ Higher batch size (16 vs 8)

**What It CANNOT Do (Current Settings):**
- ❌ Deep analysis (less capable than 4B)
- ❌ Scout role (Eagle2 is faster for that)

**Test Coverage:**
- Located: `tests/test_trading.py`
- Gitignored: Model weights (2.5GB in `models/Qwen3.5-2B-NVFP4/`)

---

### MobileSAM (Segmentation)

**Settings:**
```yaml
path: models/MobileSAM
quantization: fp16
vram: 0.5GB
speed: 12ms/image
encoder: TinyViT (5M params)
residency: always_resident
```

**What It Can Do:**
- ✅ Fast segmentation (12ms vs SAM3's 2921ms)
- ✅ UI element isolation
- ✅ ROI extraction
- ✅ SAM-compatible decoder

**What It CANNOT Do (Current Settings):**
- ❌ Pixel-perfect accuracy (73% vs SAM3's 88%)
- ❌ Complex pattern segmentation

**Trade-off:** Speed (12ms) vs Accuracy (73%)

**Test Coverage:**
- Located: Integration tests in `tests/test_governed_pipeline.py`
- Gitignored: Model weights (~10MB in `models/MobileSAM/`)

---

### YOLOv8n (Detection)

**Settings:**
```yaml
checkpoint: models/yolov8n.pt
format: tensorrt
vram: 0.4GB
speed: <50ms/frame
```

**What It Can Do:**
- ✅ Real-time object detection
- ✅ UI element detection
- ✅ Tripwire/trigger detection
- ✅ Always resident for speed

**Test Coverage:**
- Located: `tests/test_video.py`, `tests/test_e2e_pipeline.py`
- Gitignored: `yolov8n.pt` (~6MB)

---

## Test Inventory: What's Tracked vs Gitignored

### Tests IN Repo (Committed)
```
tests/
├── test_action_verifier.py          # Action validation tests
├── test_e2e_pipeline.py            # End-to-end pipeline tests
├── test_execution_preconditions.py # 48 tests - governor gates
├── test_governed_pipeline.py       # 30 tests - full pipeline
├── test_governor.py                # 49 tests - policy engine
├── test_integration_e5.py          # Integration tests
├── test_packet_validation.py       # 44 tests - schema validation
├── test_schema_registry.py         # 42 tests - schema loading
├── test_schemas.py                 # Schema-specific tests
├── test_smoke.py                   # Smoke tests
├── test_trading.py                 # Trading/reviewer tests
├── test_video_e4.py                # Video processing v4
├── test_video.py                   # Video processing
├── test_wss_agent_subscriber.py    # WSS subscriber tests
├── test_wss_integration.py         # WSS integration
├── test_wss_server.py              # WSS server tests
├── test_wss_v2.py                  # 38 tests - WSS v2
```

**Total Tests in Repo:** 200+ (code only, no model weights)

### Gitignored (NOT in Repo)
```
# Model Weights (Large Files)
models/Eagle2-2B/              # 4GB - Eagle model weights
models/Qwen3.5-4B-NVFP4/       # 4GB - Qwen 4B weights
models/Qwen3.5-2B-NVFP4/       # 2.5GB - Qwen 2B weights
models/MobileSAM/              # 10MB - SAM weights
models/SAM3/                   # 3.4GB - SAM3 (gated)
*.pt                           # All YOLO checkpoints
*.pth
*.safetensors                  # Eagle/Qwen weights
*.bin
*.ckpt
*.gguf

# Test Outputs
.pytest_cache/                 # Test cache
coverage/                      # Coverage reports
htmlcov/                       # HTML coverage
*.log                          # Test logs
logs/                          # Runtime logs

# Environment
.env                           # API keys, secrets
.venv-computer-use/            # Primary local computer-use runtime
```

---

## Capability Gaps to Address

### 1. Eagle2 Writing Quality
**Current:** Fast classification only (~400ms)  
**Gap:** Cannot generate long-form text or deep reasoning  
**Mitigation:** Eagle2 outputs feed to Qwen4B reviewer for deep analysis

### 2. Qwen4B Speed
**Current:** 2-3s latency (on-demand loading)  
**Gap:** Too slow for hot path (target: <500ms)  
**Mitigation:** Used only for reviewer lane, not scout lane

### 3. SAM Accuracy vs Speed
**Current:** MobileSAM 73% accuracy at 12ms  
**Gap:** SAM3 is 88% accurate but 2921ms (240x slower)  
**Trade-off:** MobileSAM default, SAM3 for critical accuracy only

---

## Recommended Capability Tests to Add

1. **Eagle2 Classification Benchmark**
   - Test on sample UI screenshots
   - Measure accuracy vs latency
   - Document confidence thresholds

2. **Qwen4B Reviewer Quality**
   - Test trading signal validation
   - Compare 4B vs 2B vs Eagle2 on same inputs
   - Measure reasoning depth

3. **MobileSAM Segmentation Quality**
   - Test on trading chart screenshots
   - Compare ROI extraction accuracy
   - Validate SAM3 upgrade path

4. **End-to-End Latency Tests**
   - Full pipeline: Capture → YOLO → Eagle → Governor → WSS
   - Target: <5s total (currently unknown actual)

---

## Settings Brain Summary

**For Fast Scout (Eagle2):**
- Always resident, 3.2GB VRAM
- FP16 TensorRT, transformers 4.37.2
- Fast classification, no deep reasoning

**For Deep Review (Qwen4B):**
- On-demand, 4GB VRAM
- NVFP4 quantized, vLLM inference
- Deep analysis, 2-3s latency acceptable

**For Segmentation (MobileSAM):**
- Always resident, 0.5GB VRAM
- 12ms inference, 73% accuracy
- Speed prioritized over accuracy

**Next Steps:**
1. Add capability benchmarks for each model
2. Document actual vs expected performance
3. Add regression tests for model quality
