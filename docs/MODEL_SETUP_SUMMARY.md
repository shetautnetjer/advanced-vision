# Model Setup Summary - Advanced Vision Trading Pipeline

## ✅ Completed Tasks

### 1. Model Downloads

| Model | Source | Size | Checksum (SHA256) | Status |
|-------|--------|------|-------------------|--------|
| Qwen3.5-2B-NVFP4 | AxionML/Qwen3.5-2B-NVFP4 | 2.4GB | `5b1ff604da8f6ef4eabb5ace15101e4529c5ec43d366e77c5e8051663925f209` | ✅ Downloaded |
| Qwen3.5-4B-NVFP4 | AxionML/Qwen3.5-4B-NVFP4 | 4.0GB | `b090745ecd57ea63d52a8f97bb4a85eda463fc8063763c88f0d9e17daab14268` | ✅ Downloaded |

**Total Disk Usage:** 6.5 GB

**Download Method:** `huggingface_hub.snapshot_download()` with `hf_transfer` for fast download

### 2. vLLM Configuration

**File:** `config/vllm.yaml`

**Key Settings:**
- Server: `0.0.0.0:8000`
- Quantization: `modelopt` (NVFP4)
- Target GPU: RTX 5070 Ti 16GB
- VRAM Budget: 14GB (reserving 2GB for system)

**Model Configurations:**
```yaml
qwen3.5-2b-nvfp4:
  vram_usage_gb: 2.5
  gpu_memory_utilization: 0.70
  max_model_len: 32768
  role: scout

qwen3.5-4b-nvfp4:
  vram_usage_gb: 4.0
  gpu_memory_utilization: 0.75
  max_model_len: 32768
  role: reviewer
```

### 3. Launch Script

**File:** `scripts/start_vllm.sh`

**Features:**
- List models with VRAM usage
- Dry-run mode for testing
- GPU detection via nvidia-smi
- Background/foreground modes
- Configurable ports

**Usage:**
```bash
./scripts/start_vllm.sh --list-models     # List available models
./scripts/start_vllm.sh --dry-run          # Test configuration
./scripts/start_vllm.sh qwen3.5-2b-nvfp4   # Start 2B model
./scripts/start_vllm.sh qwen3.5-4b-nvfp4 --port 8001  # Start 4B on port 8001
```

### 4. Model Manager

**File:** `src/advanced_vision/models/model_manager.py`

**Features:**
- VRAM-aware sequential loading
- Automatic model swapping
- State tracking (loaded/unloading/error)
- Dry-run mode for testing
- LRU eviction for VRAM management
- Context manager support
- CLI interface

**VRAM Management:**
- Tracks VRAM usage per model
- High/low watermarks for swapping
- Configurable residency timeout (5 min default)
- Default resident: Scout (2B) model

**Usage:**
```python
from advanced_vision.models import ModelManager

# Dry-run mode for testing
manager = ModelManager(dry_run=True)

# Load models
manager.load_model("qwen3.5-2b-nvfp4")
manager.load_model("qwen3.5-4b-nvfp4")

# Check status
manager.print_status()

# Cleanup
manager.cleanup()
```

### 5. Documentation

**Files Created:**
- `models/README.md` - Model setup and usage guide
- `config/vllm.yaml` - vLLM configuration
- `scripts/start_vllm.sh` - Launch script
- `src/advanced_vision/models/__init__.py` - Module exports

## 📊 VRAM Analysis

### RTX 5070 Ti 16GB Budget
```
Total VRAM:        16.0 GB
System Reserve:     2.0 GB
─────────────────────────
Available:         14.0 GB
```

### Loading Scenarios
| Configuration | VRAM Used | Available | Status |
|---------------|-----------|-----------|--------|
| 2B only       | 2.5 GB    | 11.5 GB   | ✅ Safe |
| 4B only       | 4.0 GB    | 10.0 GB   | ✅ Safe |
| 2B + 4B       | 6.5 GB    | 7.5 GB    | ✅ Safe |
| 7B only       | 7.0 GB    | 7.0 GB    | ✅ Safe |
| 2B + 7B       | 9.5 GB    | 4.5 GB    | ✅ Safe |
| 4B + 7B       | 11.0 GB   | 3.0 GB    | ⚠️ Tight |
| 2B + 4B + 7B  | 13.5 GB   | 0.5 GB    | ❌ Risky |

## 🔧 File Structure

```
/home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision/
├── config/
│   └── vllm.yaml                    # vLLM configuration
├── models/
│   ├── Qwen3.5-2B-NVFP4/            # 2.4GB
│   │   ├── model.safetensors
│   │   ├── config.json
│   │   └── ...
│   ├── Qwen3.5-4B-NVFP4/            # 4.0GB
│   │   ├── model.safetensors
│   │   ├── config.json
│   │   └── ...
│   └── README.md                    # Model documentation
├── scripts/
│   └── start_vllm.sh               # Launch script (+x)
└── src/advanced_vision/models/
    ├── __init__.py                 # Module exports
    └── model_manager.py            # VRAM-aware manager
```

## 🧪 Testing Results

### Dry Run Test
```bash
$ ./scripts/start_vllm.sh --dry-run
[INFO] Dry Run Mode - Testing Configuration
[SUCCESS] Found: Qwen3.5-2B-NVFP4 (2.4G)
[SUCCESS] Found: Qwen3.5-4B-NVFP4 (4.0G)
[INFO] GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB
[SUCCESS] Dry run complete - no errors detected
```

### Model Manager Test
```python
manager = ModelManager(dry_run=True)
manager.load_model('qwen3.5-2b-nvfp4')
manager.load_model('qwen3.5-4b-nvfp4')
manager.print_status()
```
**Output:**
```
Mode: DRY-RUN
VRAM: 6.5GB / 16.0GB (53.1% used)
Available: 7.5GB
Models:
  ● qwen3.5-2b-nvfp4     [scout   ] VRAM: 2.5GB
  ● qwen3.5-4b-nvfp4     [reviewer] VRAM: 4.0GB
```

## 🚀 Next Steps

### 1. Install vLLM (Optional)
```bash
source .venv/bin/activate
pip install vllm
```

### 2. Start vLLM Server
```bash
# Terminal 1: Scout model
./scripts/start_vllm.sh qwen3.5-2b-nvfp4

# Terminal 2: Reviewer model (different port)
./scripts/start_vllm.sh qwen3.5-4b-nvfp4 --port 8001
```

### 3. Test Inference
```python
import requests

# Scout model
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "Qwen3.5-2B-NVFP4",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)
print(response.json())
```

### 4. TensorRT-LLM Optimization (Optional)
For maximum performance with NVFP4 on RTX 5070 Ti:
```bash
# Build TensorRT-LLM engine
python3 -m tensorrt_llm.build ...
```

## 📝 Notes

- **NVFP4 Format:** Requires Blackwell/RTX 50 series GPU (RTX 5070 Ti ✅)
- **vLLM:** Current implementation assumes external vLLM process
- **Dry-Run Mode:** Fully functional for testing without GPU load
- **Auto-Swapping:** Enabled by default, can be disabled
- **Model 7B:** Not downloaded (optional), requires ~7GB VRAM

## 🔗 References

- AxionML/Qwen3.5-2B-NVFP4: https://huggingface.co/AxionML/Qwen3.5-2B-NVFP4
- AxionML/Qwen3.5-4B-NVFP4: https://huggingface.co/AxionML/Qwen3.5-4B-NVFP4
- vLLM NVFP4 Docs: https://docs.vllm.ai/en/latest/quantization/supported_dtypes.html
- TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM
